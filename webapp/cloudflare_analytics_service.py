"""
Service pour le module admin "Fréquentation" (/admin/frequentation) —
Phase 2 Cloudflare (audit admin, 2026-10-21 ; finalisation après introspection
réelle du schéma, autorisée explicitement, le même jour). Lecture SEULE des
statistiques de fréquentation du site (déjà suivi en production via
webapp/static/js/analyticsBeacon.js) via l'API GraphQL Cloudflare Analytics,
dataset "rumPageloadEventsAdaptiveGroups" (niveau compte, disponible sur le
plan gratuit).

Architecture stricte, identique au reste du projet :

    server.py  →  cloudflare_analytics_service.py  →  config.py (secrets)
                                                    →  API GraphQL Cloudflare

jamais l'inverse. Ce module ne modifie JAMAIS aucune donnée Mathadap — il ne
fait qu'interroger, en LECTURE, une API externe en lecture seule.

── Distinct des statistiques internes Mathadap ─────────────────────────────
Ce module mesure la FRÉQUENTATION DU SITE (visites, pages vues) telle que vue
par Cloudflare — jamais les comptes/l'activité pédagogique Mathadap (voir
admin_analytics_service.py pour cela). Les deux ne sont JAMAIS mélangés dans
une même métrique.

── Champs GraphQL CONFIRMÉS par introspection réelle du schéma (2026-10-21,
   compte Cloudflare réel, requêtes __type/__schema UNIQUEMENT — aucune
   donnée d'analytics réelle interrogée à cette occasion) ─────────────────
  - dataset : Account.rumPageloadEventsAdaptiveGroups (type
    "AccountRumPageloadEventsAdaptiveGroups"), niveau compte (accountTag) ;
  - filtre : "AccountRumPageloadEventsAdaptiveGroupsFilter_InputObject",
    avec notamment "siteTag"/"datetime_geq"/"datetime_leq" (confirmés) ;
  - métriques : "count" (uint64, pages vues) et "sum { visits }" (uint64,
    visites — distinctes des pages vues, PAS un nombre de visiteurs uniques
    identifiés, voir _VISITS_DEFINITION_NOTE) ;
  - dimensions utilisées : "date" (Date, regroupement quotidien),
    "requestPath" (pages), "countryName" (pays), "refererHost" (sources de
    trafic), "userAgentBrowser" (navigateurs), "deviceType" (appareils) ;
  - tri : enum "AccountRumPageloadEventsAdaptiveGroupsOrderBy", confirmé
    "count_DESC"/"sum_visits_DESC"/"date_ASC"/"requestPath_ASC"/
    "countryName_ASC"/"refererHost_ASC" (parmi 56 valeurs).
Champs disponibles mais volontairement non utilisés ici (hors périmètre
demandé) : "avg", "confidence", dimensions "bot"/"deliveryType"/
"navigationType"/"browserEngine"/"osVersion"/"browserVersion".

── Politique "aucune donnée inventée" ──────────────────────────────────────
{"available": False, "value": None, "reason": "...", "status": "not_configured"|"api_error"}
pour :
  - l'intégration non configurée (variables d'environnement absentes) ;
  - une erreur de transport (réseau/timeout/HTTP), une erreur GraphQL totale,
    ou une erreur GraphQL PARTIELLE touchant spécifiquement cette métrique
    (voir _extract_total/_extract_grouped : chaque métrique/classement est
    évalué indépendamment à partir de la même réponse — un alias en erreur
    n'empêche jamais l'affichage des autres) ;
  - une réponse Cloudflare dans une forme inattendue.
Une période RÉELLEMENT sans trafic (liste vide renvoyée par Cloudflare, champ
présent mais aucune ligne) est distinguée de ces cas : elle reste
{"available": True, "value": [] ou 0, "status": "ok", "note": "Aucune donnée
... période."} — jamais un échec, jamais un zéro silencieux qui masquerait
une erreur. Jamais une donnée fabriquée pour combler une métrique
indisponible.

`status` (ajouté Chantier Fréquentation, 2026-10-22) est le champ
discriminant EXPLICITE que consomme admin-frequentation.js pour choisir le
message/l'action de l'état vide groupé (voir sa docstring) : "not_configured"
(intégration non configurée, aucune action possible), "api_error" (échec
réseau/GraphQL, bouton "Réessayer" pertinent) ou "ok" (valeur réelle, y
compris zéro) — jamais déduit côté client par un string-matching fragile sur
le texte de `reason`, qui reste un texte humain libre, pas un contrat.
"""
import logging
import time
from datetime import datetime, timedelta, timezone

import requests

import config

logger = logging.getLogger("cloudflare_analytics_service")

GRAPHQL_ENDPOINT = "https://api.cloudflare.com/client/v4/graphql"
REQUEST_TIMEOUT_SECONDS = 10

# Quota Cloudflare par défaut : 300 requêtes GraphQL / 5 minutes au niveau du
# compte. Ce cache mémoire process-local évite qu'un simple rafraîchissement
# de la page admin ne consomme ce quota à chaque chargement — combiné à
# l'agrégation de toutes les métriques compatibles dans UNE SEULE requête par
# fonction publique (voir overview()/charts()/rankings() ci-dessous, chacune
# n'effectue qu'un unique appel réseau), un chargement complet de la page
# Fréquentation ne coûte que 3 requêtes au quota, pas 1 par métrique. Dédié
# (plutôt que webapp/chatbot/cache.py::LRUCache, qui n'a aucune notion
# d'expiration temporelle — éviction par taille, pas par âge) — jamais
# réutilisé tel quel pour ce module.
CACHE_TTL_SECONDS = 10 * 60

WINDOW_CHOICES = ("7j", "30j", "90j")
WINDOW_LABELS = {"7j": "7 jours", "30j": "30 jours", "90j": "90 jours"}
_WINDOW_DAYS = {"7j": 7, "30j": 30, "90j": 90}

# Couvre large (jusqu'à 90 lignes nécessaires pour une fenêtre "90j" groupée
# par jour) sans être excessif — "limit" plafonne le nombre de GROUPES
# renvoyés (donc de jours/pages/pays/référents/navigateurs/appareils
# distincts), jamais le nombre d'évènements sous-jacents.
_DAILY_QUERY_LIMIT = 100
# "Limite les classements à 10 résultats" (consigne explicite) — jamais
# paramétrable depuis la route HTTP, une seule valeur dans tout le module.
_RANKINGS_LIMIT = 10

_NOT_CONFIGURED_REASON = (
    "Intégration Cloudflare Web Analytics non configurée — variables "
    "d'environnement CLOUDFLARE_API_TOKEN/CLOUDFLARE_ACCOUNT_TAG/"
    "CLOUDFLARE_SITE_TAG absentes. Voir .env.example."
)

_PARTIAL_GRAPHQL_ERROR_REASON = (
    "L'API Cloudflare a renvoyé une erreur GraphQL partielle pour cette métrique."
)
_MISSING_FIELD_REASON = "Réponse Cloudflare dans un format inattendu (champ manquant)."
_MALFORMED_REASON = "Réponse Cloudflare dans un format inattendu."

# "Visites" (sum.visits) est une mesure RUM interne à Cloudflare (une ligne
# comptée par groupe de pages vues rapprochées dans le temps pour une même
# session de navigation) — jamais à présenter comme un nombre de personnes
# ou d'appareils distincts réellement identifiés (Cloudflare Web Analytics
# est cookie-free, aucun identifiant persistant n'existe pour ça).
_VISITS_DEFINITION_NOTE = (
    "Mesure interne Cloudflare (RUM) — ne correspond pas à un nombre de "
    "visiteurs uniques identifiés individuellement."
)

_PREVIOUS_PERIOD_NOTE = "Période précédente de même durée, pour comparaison."

_NO_TRAFFIC_NOTE = "Aucune donnée de fréquentation sur cette période."


def _na(reason, status):
    """`status` est le champ discriminant explicite consommé par le
    frontend (admin-frequentation.js) pour distinguer "non configuré"
    (aucune action possible), "erreur API" (bouton Réessayer pertinent) et
    "ok" (valeur réelle, y compris zéro) — jamais déduit côté client par un
    string-matching fragile sur `reason` (fragile car `reason` peut changer
    de texte sans préavis, voir chantier Fréquentation, 2026-10-22)."""
    return {"available": False, "value": None, "reason": reason, "status": status}


def _ok(value, note=None):
    result = {"available": True, "value": value, "status": "ok"}
    if note:
        result["note"] = note
    return result


def is_configured():
    """True si les 3 variables nécessaires sont toutes positionnées — jamais
    un appel réseau tant que ce n'est pas le cas (voir chaque fonction
    publique ci-dessous, qui vérifie ceci avant toute requête)."""
    return bool(
        config.CLOUDFLARE_API_TOKEN
        and config.CLOUDFLARE_ACCOUNT_TAG
        and config.CLOUDFLARE_SITE_TAG
    )


def resolve_window(window):
    """(window normalisé, since_dt, until_dt) en UTC. Volontairement limité à
    7j/30j/90j : seules ces 3 fenêtres ont un sens vis-à-vis de la rétention
    réelle de Cloudflare Web Analytics (données brutes non échantillonnées 7
    jours, historique échantillonné jusqu'à 6 mois — voir _sampling_note)."""
    if window not in WINDOW_CHOICES:
        window = "30j"
    # Arrondi à la minute : deux appels successifs dans la même minute
    # obtiennent exactement les mêmes bornes, donc la même clé de cache (voir
    # CACHE_TTL_SECONDS) — sans cet arrondi, `datetime.now()` changerait à
    # chaque appel et le cache TTL ne serait jamais réellement exploité.
    until_dt = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    since_dt = until_dt - timedelta(days=_WINDOW_DAYS[window])
    return window, since_dt, until_dt


def _sampling_note(window):
    """Cloudflare ne conserve les données BRUTES (non échantillonnées) que 7
    jours ; au-delà, l'historique accessible (jusqu'à 6 mois) est agrégé à
    environ 10% du volume d'origine — toute fenêtre dépassant 7 jours doit
    donc signaler explicitement ce fait (consigne "Signale si les données
    historiques sont échantillonnées"), jamais le laisser deviner."""
    if window == "7j":
        return None
    return (
        "Fenêtre au-delà de 7 jours : au-delà de cette durée, Cloudflare ne "
        "conserve plus les données brutes mais un échantillon agrégé "
        "(environ 10% du volume d'origine) — voir sa documentation Web "
        "Analytics. Les totaux restent indicatifs, pas une mesure exacte."
    )


def list_filters():
    """GET /api/admin/frequentation/filters — même convention que
    admin_analytics_service.list_filters() : le frontend affiche ces options
    telles quelles, aucune règle devinée côté client."""
    return {"windows": [{"value": k, "label": WINDOW_LABELS[k]} for k in WINDOW_CHOICES], "default": "30j"}


# ── Cache TTL mémoire process-local ──────────────────────────────────────────
_cache = {}


def _cache_get(key):
    entry = _cache.get(key)
    if entry is None:
        return None
    expires_at, value = entry
    if time.monotonic() >= expires_at:
        del _cache[key]
        return None
    return value


def _cache_set(key, value):
    _cache[key] = (time.monotonic() + CACHE_TTL_SECONDS, value)


def clear_cache():
    """Vide le cache — utilisé par les tests pour repartir d'un état connu,
    jamais nécessaire en usage normal (le TTL suffit)."""
    _cache.clear()


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _base_filter(since_dt, until_dt):
    return {
        "siteTag": config.CLOUDFLARE_SITE_TAG,
        "datetime_geq": _iso(since_dt),
        "datetime_leq": _iso(until_dt),
    }


def _build_overview_query(since_dt, until_dt):
    """UNE SEULE requête pour pages vues + visites, période courante ET
    période précédente de même durée (deux alias du même champ, filtres
    différents) — voir docstring du module pour les champs confirmés."""
    period_length = until_dt - since_dt
    query = """
    query GetOverview(
      $accountTag: string!
      $current: AccountRumPageloadEventsAdaptiveGroupsFilter_InputObject!
      $previous: AccountRumPageloadEventsAdaptiveGroupsFilter_InputObject!
    ) {
      viewer {
        accounts(filter: {accountTag: $accountTag}) {
          current: rumPageloadEventsAdaptiveGroups(filter: $current, limit: 1) {
            count
            sum { visits }
          }
          previous: rumPageloadEventsAdaptiveGroups(filter: $previous, limit: 1) {
            count
            sum { visits }
          }
        }
      }
    }
    """
    variables = {
        "accountTag": config.CLOUDFLARE_ACCOUNT_TAG,
        "current": _base_filter(since_dt, until_dt),
        "previous": _base_filter(since_dt - period_length, since_dt),
    }
    return query, variables


def _build_daily_query(since_dt, until_dt):
    """UNE SEULE requête groupée par `dimensions { date }` (confirmé par
    introspection) pour toute la fenêtre — remplace l'ancienne boucle d'une
    requête par jour (plus de champ de regroupement quotidien deviné à
    contourner)."""
    query = """
    query GetDaily(
      $accountTag: string!
      $filter: AccountRumPageloadEventsAdaptiveGroupsFilter_InputObject!
      $limit: uint64!
    ) {
      viewer {
        accounts(filter: {accountTag: $accountTag}) {
          daily: rumPageloadEventsAdaptiveGroups(filter: $filter, limit: $limit, orderBy: [date_ASC]) {
            count
            sum { visits }
            dimensions { date }
          }
        }
      }
    }
    """
    variables = {
        "accountTag": config.CLOUDFLARE_ACCOUNT_TAG,
        "filter": _base_filter(since_dt, until_dt),
        "limit": _DAILY_QUERY_LIMIT,
    }
    return query, variables


# (clé_résultat, alias_graphql, clé_dimension) — un seul endroit pour la liste
# des 5 classements, réutilisé par _build_rankings_query ET rankings().
_RANKING_SPECS = (
    ("top_pages", "topPages", "requestPath"),
    ("top_countries", "topCountries", "countryName"),
    ("top_referrers", "topReferrers", "refererHost"),
    ("top_browsers", "topBrowsers", "userAgentBrowser"),
    ("top_devices", "topDevices", "deviceType"),
)


def _build_rankings_query(since_dt, until_dt):
    """UNE SEULE requête pour les 5 classements (pages/pays/référents/
    navigateurs/appareils) — 5 alias du même champ, chacun avec sa propre
    dimension de regroupement et trié par `count_DESC` (confirmé)."""
    aliases_graphql = "\n".join(
        f"""
          {alias}: rumPageloadEventsAdaptiveGroups(filter: $filter, limit: $limit, orderBy: [count_DESC]) {{
            count
            sum {{ visits }}
            dimensions {{ {dimension_key} }}
          }}
        """
        for _result_key, alias, dimension_key in _RANKING_SPECS
    )
    query = f"""
    query GetRankings(
      $accountTag: string!
      $filter: AccountRumPageloadEventsAdaptiveGroupsFilter_InputObject!
      $limit: uint64!
    ) {{
      viewer {{
        accounts(filter: {{accountTag: $accountTag}}) {{
          {aliases_graphql}
        }}
      }}
    }}
    """
    variables = {
        "accountTag": config.CLOUDFLARE_ACCOUNT_TAG,
        "filter": _base_filter(since_dt, until_dt),
        "limit": _RANKINGS_LIMIT,
    }
    return query, variables


def _graphql_query(query, variables):
    """Appel réel unique à l'API GraphQL Cloudflare. JAMAIS invoqué tant que
    is_configured() est False, jamais invoqué par aucun test (requests.post
    toujours mocké — voir test_cloudflare_analytics_service.py).

    Renvoie (data, transport_error, graphql_errors) :
      - `transport_error` (str) non-None UNIQUEMENT pour un échec au niveau
        transport (réseau/timeout/HTTP/JSON invalide/erreur GraphQL totale
        sans aucune donnée exploitable) — dans ce cas `data` est toujours
        None, l'appelant doit considérer TOUTES les métriques de cette
        requête comme indisponibles ;
      - `graphql_errors` (liste ou None) : erreurs GraphQL PARTIELLES
        éventuelles alors que `data` reste exploitable pour les alias non
        affectés — voir _extract_total/_extract_grouped, qui décident au cas
        par cas, jamais une invalidation globale pour une erreur partielle."""
    try:
        resp = requests.post(
            GRAPHQL_ENDPOINT,
            json={"query": query, "variables": variables},
            headers={"Authorization": f"Bearer {config.CLOUDFLARE_API_TOKEN}"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.Timeout:
        logger.warning("Délai d'attente dépassé en interrogeant l'API Cloudflare.")
        return None, "Délai d'attente dépassé en interrogeant l'API Cloudflare.", None
    except requests.RequestException:
        logger.warning("Erreur réseau en interrogeant l'API Cloudflare.")
        return None, "Erreur réseau en interrogeant l'API Cloudflare.", None

    if resp.status_code != 200:
        logger.warning("Statut HTTP inattendu de l'API Cloudflare : %s", resp.status_code)
        return None, f"L'API Cloudflare a répondu avec le statut {resp.status_code}.", None

    try:
        payload = resp.json()
    except ValueError:
        logger.warning("Réponse Cloudflare non-JSON.")
        return None, "Réponse Cloudflare dans un format inattendu.", None

    graphql_errors = payload.get("errors") or None
    data = payload.get("data")
    if data is None:
        if graphql_errors:
            logger.warning("Erreurs GraphQL renvoyées par Cloudflare (totale, aucune donnée).")
            return None, "L'API Cloudflare a renvoyé une erreur GraphQL.", graphql_errors
        return None, "Réponse Cloudflare dans un format inattendu.", None

    if graphql_errors:
        logger.warning("Erreurs GraphQL PARTIELLES renvoyées par Cloudflare (données partiellement exploitables).")
    return data, None, graphql_errors


def _first_account(data):
    """Nœud `accounts[0]` de la réponse, ou {} si absent/malformé — jamais
    une exception non interceptée. Un dict vide fait échouer PROPREMENT
    chaque lookup d'alias dans _extract_total/_extract_grouped (traité comme
    "champ manquant"), sans jamais planter."""
    try:
        return data["viewer"]["accounts"][0]
    except (KeyError, IndexError, TypeError):
        return {}


def _extract_total(accounts_node, alias, graphql_errors):
    """(count, visits, erreur_ou_None) pour un alias NON groupé (limit:1,
    aucune dimension demandée — Cloudflare renvoie alors une unique ligne
    agrégeant tous les évènements filtrés). Une liste vide est une période
    SANS TRAFIC réelle (0, 0, None), jamais une erreur — distinguée d'un
    alias absent de la réponse (champ manquant, probablement une erreur
    GraphQL partielle sur CET alias)."""
    if alias not in accounts_node:
        reason = _PARTIAL_GRAPHQL_ERROR_REASON if graphql_errors else _MISSING_FIELD_REASON
        return None, None, reason
    rows = accounts_node[alias]
    if not rows:
        return 0, 0, None
    try:
        row = rows[0]
        return row["count"], row["sum"]["visits"], None
    except (KeyError, TypeError):
        return None, None, _MALFORMED_REASON


def _extract_grouped(accounts_node, alias, dimension_key, graphql_errors):
    """(liste_de_{label,pageviews,visits}_ou_None, erreur_ou_None) pour un
    alias GROUPÉ par `dimension_key`. Une liste vide reste une liste vide
    valide (période sans trafic), jamais une erreur."""
    if alias not in accounts_node:
        reason = _PARTIAL_GRAPHQL_ERROR_REASON if graphql_errors else _MISSING_FIELD_REASON
        return None, reason
    rows = accounts_node[alias]
    try:
        items = [
            {
                "label": row["dimensions"][dimension_key] or "(inconnu)",
                "pageviews": row["count"],
                "visits": row["sum"]["visits"],
            }
            for row in rows
        ]
    except (KeyError, TypeError):
        return None, _MALFORMED_REASON
    return items, None


def _fetch_accounts_node(cache_key, build_query):
    """Récupère (accounts_node, graphql_errors) pour `cache_key`, via le
    cache TTL si disponible, sinon un unique appel réseau (query/variables
    fournis par `build_query()`, appelé seulement en cas de cache manquant —
    jamais construit inutilement). (None, None, transport_error) si l'appel
    réseau échoue au niveau transport (voir _graphql_query)."""
    cached = _cache_get(cache_key)
    if cached is not None:
        accounts_node, graphql_errors = cached
        return accounts_node, graphql_errors, None

    query, variables = build_query()
    data, transport_error, graphql_errors = _graphql_query(query, variables)
    if transport_error:
        return None, None, transport_error

    accounts_node = _first_account(data)
    _cache_set(cache_key, (accounts_node, graphql_errors))
    return accounts_node, graphql_errors, None


def overview(window):
    """GET /api/admin/frequentation/overview?window=... — (payload, error).
    `error` non-None uniquement pour une valeur de `window` invalide (aucune
    pour l'instant, voir resolve_window qui retombe silencieusement sur
    "30j" — paramètre conservé pour une cohérence de signature avec
    admin_analytics_service.overview/charts/rankings)."""
    window, since_dt, until_dt = resolve_window(window)
    result = {
        "window": window,
        "pageviews": _na(_NOT_CONFIGURED_REASON, "not_configured"),
        "pageviews_previous_period": _na(_NOT_CONFIGURED_REASON, "not_configured"),
        "visits": _na(_NOT_CONFIGURED_REASON, "not_configured"),
        "visits_previous_period": _na(_NOT_CONFIGURED_REASON, "not_configured"),
        "sampling_note": _sampling_note(window),
    }
    if not is_configured():
        return result, None

    cache_key = ("overview", since_dt.isoformat(), until_dt.isoformat())
    accounts_node, graphql_errors, transport_error = _fetch_accounts_node(
        cache_key, lambda: _build_overview_query(since_dt, until_dt)
    )
    if transport_error:
        for key in ("pageviews", "pageviews_previous_period", "visits", "visits_previous_period"):
            result[key] = _na(transport_error, "api_error")
        return result, None

    current_count, current_visits, current_err = _extract_total(accounts_node, "current", graphql_errors)
    previous_count, previous_visits, previous_err = _extract_total(accounts_node, "previous", graphql_errors)

    result["pageviews"] = _na(current_err, "api_error") if current_err else _ok(current_count)
    result["visits"] = (
        _na(current_err, "api_error") if current_err else _ok(current_visits, note=_VISITS_DEFINITION_NOTE)
    )
    result["pageviews_previous_period"] = (
        _na(previous_err, "api_error") if previous_err else _ok(previous_count, note=_PREVIOUS_PERIOD_NOTE)
    )
    result["visits_previous_period"] = (
        _na(previous_err, "api_error")
        if previous_err
        else _ok(previous_visits, note=f"{_PREVIOUS_PERIOD_NOTE} {_VISITS_DEFINITION_NOTE}")
    )
    return result, None


def charts(window):
    """GET /api/admin/frequentation/charts?window=... — évolution quotidienne
    des pages vues ET des visites, via UNE SEULE requête groupée par
    `dimensions { date }` (confirmé par introspection)."""
    window, since_dt, until_dt = resolve_window(window)
    result = {
        "window": window,
        "daily": _na(_NOT_CONFIGURED_REASON, "not_configured"),
        "sampling_note": _sampling_note(window),
    }
    if not is_configured():
        return result, None

    cache_key = ("daily", since_dt.isoformat(), until_dt.isoformat())
    accounts_node, graphql_errors, transport_error = _fetch_accounts_node(
        cache_key, lambda: _build_daily_query(since_dt, until_dt)
    )
    if transport_error:
        result["daily"] = _na(transport_error, "api_error")
        return result, None

    items, error = _extract_grouped(accounts_node, "daily", "date", graphql_errors)
    if error:
        result["daily"] = _na(error, "api_error")
        return result, None

    days = sorted(
        ({"date": it["label"], "pageviews": it["pageviews"], "visits": it["visits"]} for it in items),
        key=lambda d: d["date"],
    )
    result["daily"] = _ok(days, note=None if days else _NO_TRAFFIC_NOTE)
    return result, None


def rankings(window):
    """GET /api/admin/frequentation/rankings?window=... — pages les plus
    consultées, répartition géographique, sources de trafic, navigateurs et
    appareils — 5 classements obtenus via UNE SEULE requête (5 alias, voir
    _build_rankings_query), chacun limité à _RANKINGS_LIMIT (10) résultats et
    trié par `count_DESC` (confirmé par introspection)."""
    window, since_dt, until_dt = resolve_window(window)
    result = {"window": window, "sampling_note": _sampling_note(window)}
    for result_key, _alias, _dim in _RANKING_SPECS:
        result[result_key] = _na(_NOT_CONFIGURED_REASON, "not_configured")
    if not is_configured():
        return result, None

    cache_key = ("rankings", since_dt.isoformat(), until_dt.isoformat())
    accounts_node, graphql_errors, transport_error = _fetch_accounts_node(
        cache_key, lambda: _build_rankings_query(since_dt, until_dt)
    )
    if transport_error:
        for result_key, _alias, _dim in _RANKING_SPECS:
            result[result_key] = _na(transport_error, "api_error")
        return result, None

    for result_key, alias, dimension_key in _RANKING_SPECS:
        items, error = _extract_grouped(accounts_node, alias, dimension_key, graphql_errors)
        result[result_key] = (
            _na(error, "api_error") if error else _ok(items, note=None if items else _NO_TRAFFIC_NOTE)
        )

    return result, None
