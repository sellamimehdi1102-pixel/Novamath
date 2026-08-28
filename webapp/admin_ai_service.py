"""
Service pour le module "Gestion des fournisseurs IA" (/admin/ia) —
lecture ET écriture désormais : l'administrateur peut créer/modifier/activer/
désactiver/supprimer un fournisseur, réordonner les priorités, choisir les
fournisseurs par abonnement, tester un fournisseur en conditions réelles et
lancer un health-check. Réutilise intégralement `ai_provider_service.py`
(façade de lecture/écriture sur `db.py`) : ce module n'exécute JAMAIS de SQL
lui-même — toute écriture passe par une fonction déjà exposée par
`ai_provider_service.py`.

Architecture stricte, identique au reste du projet :

    server.py  →  admin_ai_service.py  →  ai_provider_service.py  →  db.py

jamais l'inverse. Seule évolution par rapport à la phase précédente : ce
module importe désormais `chatbot.provider_manager.PROVIDERS` (le registre
{provider_key: classe}, en LECTURE SEULE) pour deux usages strictement
délimités : (1) valider qu'un `provider_key` saisi par l'admin correspond
bien à un fournisseur réellement implémenté — sans cela, une valeur invalide
enregistrée en base ferait planter get_provider() au prochain message réel
d'un élève sur ce plan (voir provider_manager.py, RuntimeError non rattrapée
par llm_fallback_service.generate()) ; (2) instancier directement la classe
d'un fournisseur pour test_connection()/run_health_check() ci-dessous, sans
jamais passer par provider_manager.get_provider()/select_llm_for_user()
(qui dépendent de CHATBOT_PROVIDER/du plan de l'utilisateur admin connecté —
hors sujet ici, on teste le fournisseur précis choisi dans l'interface).
Ce module n'importe et ne modifie JAMAIS conversation_manager.py,
llm_fallback_service.py, ni aucun fichier de webapp/chatbot/providers/ —
aucune conversation élève n'est jamais lue, écrite, ni influencée par ce
module.

── Politique "aucune donnée inventée" (lecture) ────────────────────────────
Identique à admin_dashboard_service.py/admin_user_profile_service.py : tout
champ structurellement absent renvoie {"available": False, "value": None,
"reason": "..."}, JAMAIS un 0/chaîne vide/date fabriquée.

── Politique d'écriture ─────────────────────────────────────────────────────
Chaque fonction d'écriture renvoie (ok: bool, errors: dict[str, str]) — ou
(id, errors) pour une création — JAMAIS une exception pour une erreur de
validation métier (priorité/code dupliqué, fallback sur soi-même, champ vide,
fournisseur utilisé...) : ce sont des erreurs UTILISATEUR normales, à
afficher dans le formulaire, pas des pannes serveur. Toute erreur autre
(SQL, réellement inattendue) continue de remonter comme exception, à charge
de server.py de la traduire en 500 (même politique que le reste du projet).

Une API indépendante par onglet de la fiche détaillée d'un fournisseur (voir
server.py) — chaque fonction *_provider_* ci-dessous correspond à UNE route,
pour permettre le lazy loading réel côté frontend (même contrat que
admin_user_profile_service.py : ouvrir l'onglet "Consommation" ne déclenche
aucune lecture de santé, par exemple).

── Journal d'activité (voir tout en bas du fichier) ────────────────────────
Chaque fonction d'écriture ci-dessus a un équivalent "*_logged" qui l'appelle
SANS rien changer à son comportement/sa signature de retour, puis enregistre
UNE entrée dans le journal via admin_ai_log_service.py (create/update/delete/
enable-disable/reorder/subscriptions/test/health-check). server.py appelle
exclusivement les versions "*_logged" — les fonctions d'origine restent
inchangées et directement testables isolément (voir tests existants),
jamais dupliquées."""
import time as _time
from datetime import datetime, timezone

import admin_ai_log_service
import ai_provider_key_service
import ai_provider_service as svc
from chatbot import provider_manager

_KNOWN_SUBSCRIPTIONS = ("free", "premium", "ultra")

NO_HEALTH_DATA = "Ce fournisseur n'a jamais été testé (aucun health-check n'a encore été exécuté)."
NO_USAGE_DATA = (
    "Aucun appel réel n'a encore été comptabilisé pour ce fournisseur (ai_provider_usage n'est pas "
    "encore alimentée par le chatbot)."
)


def _na(reason):
    return {"available": False, "value": None, "reason": reason}


def _ok(value):
    return {"available": True, "value": value}


def _field(value, reason):
    """Champ optionnel d'une ligne SQL (colonne NULLable) : NULL n'est jamais
    affiché comme une valeur, toujours comme une absence honnête avec sa
    raison exacte."""
    return _ok(value) if value is not None else _na(reason)


# ── Fournisseurs IA (carte 1 + onglet "Informations générales") ─────────────
def _serialize_provider(provider, providers_by_id):
    fallback = providers_by_id.get(provider["fallback_provider_id"]) if provider["fallback_provider_id"] else None
    return {
        "id": provider["id"],
        "name": provider["name"],
        "provider_key": provider["provider_key"],
        "model_name": provider["model_name"],
        "enabled": bool(provider["enabled"]),
        "priority": provider["priority"],
        "badge": _field(provider["badge"], "Aucun badge défini pour ce fournisseur."),
        "icon": _field(provider["icon"], "Aucune icône définie pour ce fournisseur."),
        "color": _field(provider["color"], "Aucune couleur définie pour ce fournisseur."),
        "description": _field(provider["description"], "Aucune description définie pour ce fournisseur."),
        "fallback_provider": _ok({"id": fallback["id"], "name": fallback["name"]}) if fallback else _na(
            "Aucun fournisseur de secours configuré pour celui-ci."
        ),
        "created_at": _ok(provider["created_at"]),
        "updated_at": _ok(provider["updated_at"]),
    }


def list_providers():
    """Carte 1 "Fournisseurs IA" — tous les fournisseurs de ai_providers."""
    providers = svc.list_providers()
    if not providers:
        return {"providers": None, "reason": "Aucun fournisseur IA n'est configuré dans ai_providers."}
    by_id = {p["id"]: p for p in providers}
    return {"providers": [_serialize_provider(p, by_id) for p in providers], "reason": None}


def get_provider_info(provider_id):
    """Onglet "Informations générales" de la fiche détaillée — mêmes champs
    que la carte 1, pour UN seul fournisseur. None si `provider_id` inconnu
    (404 côté route)."""
    provider = svc.get_provider(provider_id)
    if provider is None:
        return None
    by_id = {p["id"]: p for p in svc.list_providers()}
    return _serialize_provider(provider, by_id)


# ── Abonnements (carte 2, lecture seule) ────────────────────────────────────
def list_subscriptions():
    """Carte 2 "Abonnements" — mapping FREE/PREMIUM/ULTRA → fournisseur(s),
    depuis subscription_ai_mapping, trié par priorité du fournisseur associé
    (voir ai_provider_service.list_all_mappings → db.list_subscription_ai_mappings)."""
    mappings = svc.list_all_mappings()
    if not mappings:
        return _na("Aucune correspondance abonnement → fournisseur n'est configurée dans subscription_ai_mapping.")
    by_id = {p["id"]: p for p in svc.list_providers()}
    grouped = {}
    for m in mappings:
        provider = by_id.get(m["provider_id"])
        if provider is None:
            continue  # ligne orpheline improbable (FK ON DELETE CASCADE), ignorée sans jamais planter
        grouped.setdefault(m["subscription"], []).append({
            "provider_id": provider["id"],
            "name": provider["name"],
            "badge": provider["badge"],
        })
    return _ok(grouped)


# ── État des fournisseurs (carte 3 + onglet "État") ─────────────────────────
def _serialize_health(health):
    return {
        "last_success": _field(health["last_success"], "Aucun succès n'a encore été enregistré."),
        "last_failure": _field(health["last_failure"], "Aucun échec n'a encore été enregistré."),
        "latency_ms": _field(health["latency_ms"], "Aucune latence mesurée pour la dernière requête."),
        "average_latency": _field(health["average_latency"], "Aucune latence moyenne mesurée."),
        "total_requests": _ok(health["total_requests"]),
        "total_errors": _ok(health["total_errors"]),
        "success_rate": _field(health["success_rate"], "Taux de succès non calculable (aucune requête enregistrée)."),
        "http_code": _field(health["http_code"], "Aucun code HTTP enregistré."),
        "last_error": _field(health["last_error"], "Aucune erreur enregistrée."),
        "updated_at": _ok(health["updated_at"]),
    }


def list_health():
    """Carte 3 "État des fournisseurs" — un fournisseur sans ligne dans
    ai_provider_health n'a jamais été testé : son état est `available: False`,
    jamais un statut deviné (même politique que
    admin_dashboard_service._card_ai_providers_status, déjà en production)."""
    providers = svc.list_providers()
    if not providers:
        return {"items": None, "reason": "Aucun fournisseur IA n'est configuré."}
    health_by_provider = {h["provider_id"]: h for h in svc.list_health()}
    items = []
    for p in providers:
        health = health_by_provider.get(p["id"])
        items.append({
            "provider_id": p["id"],
            "name": p["name"],
            "health": _ok(_serialize_health(health)) if health else _na(NO_HEALTH_DATA),
        })
    return {"items": items, "reason": None}


def get_provider_health(provider_id):
    """Onglet "État" de la fiche détaillée — None si `provider_id` inconnu."""
    provider = svc.get_provider(provider_id)
    if provider is None:
        return None
    health = svc.get_health(provider_id)
    return _ok(_serialize_health(health)) if health else _na(NO_HEALTH_DATA)


# ── Consommation (carte 4 + onglet "Consommation") ──────────────────────────
def _serialize_usage_row(row):
    return {
        "date": row["date"],
        "input_tokens": row["input_tokens"],
        "output_tokens": row["output_tokens"],
        # Chantier "fiabilité des données d'analytics IA" (audit 2026-08-27) :
        # total_tokens (colonne ai_provider_usage déjà alimentée par
        # record_llm_usage(), voir ai_provider_service.py) n'était jusqu'ici
        # jamais exposée à l'admin — le coût affiché (estimated_cost) inclut
        # pourtant déjà les tokens de réflexion Gemini (total_tokens - input -
        # output, voir estimate_llm_cost()), sans qu'aucun chiffre visible ne
        # permette de le vérifier. `row["total_tokens"]` existe toujours
        # (colonne NOT NULL DEFAULT 0, voir db.py) même sur une ligne créée
        # avant l'ajout de cette colonne — jamais None ici.
        "total_tokens": row["total_tokens"],
        "requests": row["requests"],
        "estimated_cost": row["estimated_cost"],
    }


def _aggregate_usage(rows):
    return {
        "input_tokens": sum(r["input_tokens"] for r in rows),
        "output_tokens": sum(r["output_tokens"] for r in rows),
        "total_tokens": sum(r["total_tokens"] for r in rows),
        "requests": sum(r["requests"] for r in rows),
        "estimated_cost": sum(r["estimated_cost"] for r in rows),
        "daily": [_serialize_usage_row(r) for r in rows],
    }


def _build_daily_chart(rows):
    """Série journalière TOUS fournisseurs confondus (tokens input+output par
    jour), pour le graphique de la carte 4 — jamais un 0 fabriqué pour un
    jour sans ligne : seuls les jours réellement présents dans
    ai_provider_usage apparaissent (pas de fenêtre glissante complétée
    artificiellement, contrairement à admin_dashboard_service._fill_missing_days
    qui, elle, complète une fenêtre calendaire connue de comptes déjà réels —
    ici, il n'existe aucune notion de fenêtre attendue pour une consommation
    IA qui n'a peut-être jamais démarré)."""
    by_date = {}
    for r in rows:
        entry = by_date.setdefault(r["date"], {"date": r["date"], "tokens": 0})
        entry["tokens"] += (r["input_tokens"] or 0) + (r["output_tokens"] or 0)
    return sorted(by_date.values(), key=lambda e: e["date"])


def list_usage():
    """Carte 4 "Consommation IA" — agrégat + détail journalier par
    fournisseur, et un graphique journalier global (tous fournisseurs)."""
    providers = svc.list_providers()
    if not providers:
        return {"items": None, "reason": "Aucun fournisseur IA n'est configuré.", "chart": _na(NO_USAGE_DATA)}

    all_usage = svc.list_usage()
    by_provider = {}
    for row in all_usage:
        by_provider.setdefault(row["provider_id"], []).append(row)

    items = []
    for p in providers:
        rows = by_provider.get(p["id"], [])
        items.append({
            "provider_id": p["id"],
            "name": p["name"],
            "usage": _ok(_aggregate_usage(rows)) if rows else _na(NO_USAGE_DATA),
        })

    chart = _ok(_build_daily_chart(all_usage)) if all_usage else _na(NO_USAGE_DATA)
    return {"items": items, "reason": None, "chart": chart}


def get_provider_usage(provider_id):
    """Onglet "Consommation" de la fiche détaillée — None si `provider_id`
    inconnu."""
    provider = svc.get_provider(provider_id)
    if provider is None:
        return None
    rows = svc.list_usage(provider_id=provider_id)
    return _ok(_aggregate_usage(rows)) if rows else _na(NO_USAGE_DATA)


# ── Configuration (onglet "Configuration", lecture seule) ───────────────────
def get_provider_config(provider_id):
    """Onglet "Configuration" — les champs de configuration bruts d'un
    fournisseur, jamais une valeur métier calculée. None si `provider_id`
    inconnu."""
    provider = svc.get_provider(provider_id)
    if provider is None:
        return None
    by_id = {p["id"]: p for p in svc.list_providers()}
    fallback = by_id.get(provider["fallback_provider_id"]) if provider["fallback_provider_id"] else None
    return {
        "provider_key": _ok(provider["provider_key"]),
        "model_name": _ok(provider["model_name"]),
        "priority": _ok(provider["priority"]),
        "fallback_provider": _ok({"id": fallback["id"], "name": fallback["name"]}) if fallback else _na(
            "Aucun fournisseur de secours configuré pour celui-ci."
        ),
        "enabled": _ok(bool(provider["enabled"])),
        "code": _field(provider["code"], "Aucun code défini pour ce fournisseur."),
        "badge": _field(provider["badge"], "Aucun badge défini pour ce fournisseur."),
        "description": _field(provider["description"], "Aucune description définie pour ce fournisseur."),
        "icon": _field(provider["icon"], "Aucune icône définie pour ce fournisseur."),
        "color": _field(provider["color"], "Aucune couleur définie pour ce fournisseur."),
    }


# ── Écriture : validation ────────────────────────────────────────────────────
def _clean_str(value):
    value = (value or "").strip() if isinstance(value, str) else value
    return value or None


def _validate_provider_payload(data, exclude_id=None):
    """Valide un payload de création/modification de fournisseur. Renvoie
    (errors, clean) : `errors` est un dict {champ: message}, vide si tout est
    valide ; `clean` contient les valeurs prêtes à être passées à
    ai_provider_service.create_provider()/update_provider() (utilisable même
    si `errors` n'est pas vide, mais ne doit alors jamais être persisté)."""
    errors = {}
    name = _clean_str(data.get("name"))
    provider_key = _clean_str(data.get("provider_key"))
    model_name = _clean_str(data.get("model_name"))
    priority = data.get("priority")
    fallback_provider_id = data.get("fallback_provider_id") or None
    code = _clean_str(data.get("code"))

    if not name:
        errors["name"] = "Le nom est obligatoire."
    if not provider_key:
        errors["provider_key"] = "provider_key est obligatoire."
    elif provider_key not in provider_manager.PROVIDERS:
        errors["provider_key"] = (
            f"provider_key inconnu : {provider_key!r} (valeurs possibles : "
            f"{', '.join(sorted(provider_manager.PROVIDERS))})."
        )
    if not model_name:
        errors["model_name"] = "model_name est obligatoire."
    if not isinstance(priority, int) or isinstance(priority, bool) or priority < 0:
        errors["priority"] = "La priorité doit être un entier positif ou nul."

    for p in svc.list_providers():
        if exclude_id is not None and p["id"] == exclude_id:
            continue
        if "priority" not in errors and isinstance(priority, int) and p["priority"] == priority:
            errors["priority"] = f"La priorité {priority} est déjà utilisée par {p['name']!r}."
        if code and p["code"] == code:
            errors["code"] = f"Le code {code!r} est déjà utilisé par {p['name']!r}."

    if fallback_provider_id is not None:
        if exclude_id is not None and fallback_provider_id == exclude_id:
            errors["fallback_provider_id"] = "Un fournisseur ne peut pas être son propre fournisseur de secours."
        elif svc.get_provider(fallback_provider_id) is None:
            errors["fallback_provider_id"] = "Le fournisseur de secours sélectionné est introuvable."

    clean = {
        "name": name, "provider_key": provider_key, "model_name": model_name,
        "priority": priority, "fallback_provider_id": fallback_provider_id, "code": code,
        "description": _clean_str(data.get("description")),
        "badge": _clean_str(data.get("badge")),
        "icon": _clean_str(data.get("icon")),
        "color": _clean_str(data.get("color")),
        "enabled": bool(data.get("enabled", True)),
    }
    return errors, clean


# ── Écriture : fournisseurs ──────────────────────────────────────────────────
def create_provider(data):
    """Crée un fournisseur après validation complète. Renvoie (provider_id,
    errors) — provider_id est None si `errors` n'est pas vide (rien n'est
    créé dans ce cas)."""
    errors, clean = _validate_provider_payload(data)
    if errors:
        return None, errors
    provider_id = svc.create_provider(
        clean["name"], clean["provider_key"], clean["model_name"],
        enabled=clean["enabled"], priority=clean["priority"],
        fallback_provider_id=clean["fallback_provider_id"], code=clean["code"],
        description=clean["description"], badge=clean["badge"], icon=clean["icon"], color=clean["color"],
    )
    return provider_id, {}


def update_provider(provider_id, data):
    """Remplace l'intégralité des champs modifiables d'un fournisseur
    existant, après validation. Renvoie (ok, errors)."""
    if svc.get_provider(provider_id) is None:
        return False, {"_": "Fournisseur introuvable."}
    errors, clean = _validate_provider_payload(data, exclude_id=provider_id)
    if errors:
        return False, errors
    svc.update_provider(
        provider_id, clean["name"], clean["provider_key"], clean["model_name"],
        clean["enabled"], clean["priority"], fallback_provider_id=clean["fallback_provider_id"],
        code=clean["code"], description=clean["description"], badge=clean["badge"],
        icon=clean["icon"], color=clean["color"],
    )
    return True, {}


def delete_provider(provider_id):
    """Supprime un fournisseur — REFUSÉ si un abonnement l'utilise encore
    (voir subscription_ai_mapping), pour ne jamais vider silencieusement la
    chaîne d'un plan. Renvoie (ok, errors)."""
    if svc.get_provider(provider_id) is None:
        return False, {"_": "Fournisseur introuvable."}
    used_by = sorted({m["subscription"] for m in svc.list_all_mappings() if m["provider_id"] == provider_id})
    if used_by:
        return False, {"_": f"Impossible de supprimer : encore utilisé par l'abonnement {', '.join(used_by)}."}
    svc.delete_provider(provider_id)
    return True, {}


def set_provider_enabled(provider_id, enabled):
    """Active/désactive un fournisseur sans toucher à ses autres champs.
    Renvoie (ok, errors)."""
    if svc.get_provider(provider_id) is None:
        return False, {"_": "Fournisseur introuvable."}
    svc.set_provider_enabled(provider_id, bool(enabled))
    return True, {}


def move_provider_priority(provider_id, direction):
    """`direction` : "up" ou "down" — échange la priorité de `provider_id`
    avec son voisin immédiat dans l'ordre global (voir svc.list_providers,
    trié priority ASC puis id ASC). Toujours un ÉCHANGE entre deux lignes
    existantes : ne casse jamais l'unicité des priorités, contrairement à une
    réécriture arbitraire. Renvoie (ok, errors)."""
    providers = svc.list_providers()
    idx = next((i for i, p in enumerate(providers) if p["id"] == provider_id), None)
    if idx is None:
        return False, {"_": "Fournisseur introuvable."}
    neighbor_idx = idx - 1 if direction == "up" else idx + 1
    if direction not in ("up", "down"):
        return False, {"_": "Direction invalide (attendu : up/down)."}
    if neighbor_idx < 0 or neighbor_idx >= len(providers):
        return False, {"_": "Ce fournisseur est déjà à cette extrémité de la liste."}
    current, neighbor = providers[idx], providers[neighbor_idx]
    svc.update_provider(
        current["id"], current["name"], current["provider_key"], current["model_name"],
        current["enabled"], neighbor["priority"], fallback_provider_id=current["fallback_provider_id"],
        code=current["code"], description=current["description"], badge=current["badge"],
        icon=current["icon"], color=current["color"],
    )
    svc.update_provider(
        neighbor["id"], neighbor["name"], neighbor["provider_key"], neighbor["model_name"],
        neighbor["enabled"], current["priority"], fallback_provider_id=neighbor["fallback_provider_id"],
        code=neighbor["code"], description=neighbor["description"], badge=neighbor["badge"],
        icon=neighbor["icon"], color=neighbor["color"],
    )
    return True, {}


# ── Écriture : abonnements ───────────────────────────────────────────────────
def set_subscription_providers(subscription, provider_ids):
    """Remplace l'intégralité des fournisseurs associés à `subscription` par
    `provider_ids` (dans cet ordre) — REFUSÉ si la liste est vide (un
    abonnement doit garder au moins un fournisseur assigné) ou si un id est
    inconnu. L'ordre d'UTILISATION réel dans la chaîne reste déterminé par la
    priorité globale de chaque fournisseur (voir move_provider_priority
    ci-dessus) : `provider_ids` ne fixe que l'appartenance au plan, jamais un
    ordre propre au mapping (aucune colonne d'ordre dans
    subscription_ai_mapping). Renvoie (ok, errors)."""
    if subscription not in _KNOWN_SUBSCRIPTIONS:
        return False, {"_": f"Abonnement inconnu : {subscription!r}."}
    provider_ids = list(dict.fromkeys(provider_ids or []))
    if not provider_ids:
        return False, {"_": "Un abonnement doit conserver au moins un fournisseur assigné."}
    for pid in provider_ids:
        if svc.get_provider(pid) is None:
            return False, {"_": f"Fournisseur introuvable : {pid}."}

    for m in svc.list_mappings_for_subscription(subscription):
        svc.delete_mapping(m["id"])
    for pid in provider_ids:
        svc.map_subscription_to_provider(subscription, pid)
    return True, {}


# ── Prompt de test partagé par test_connection()/run_health_check() ─────────
_TEST_MESSAGES = [{"role": "user", "content": "Réponds uniquement par le mot ok."}]
_TEST_SYSTEM_PROMPT = "Tu es un simple test technique. Réponds uniquement par le mot ok, sans rien ajouter d'autre."


def _instantiate_provider(provider_row):
    """Instancie DIRECTEMENT la classe du fournisseur configuré, sans passer
    par provider_manager.get_provider() (qui résout via CHATBOT_PROVIDER/
    active_provider_name — non pertinent ici, on cible un fournisseur précis
    choisi par l'admin, quel que soit le réglage d'environnement du serveur).
    None si provider_key ne correspond à aucune classe connue (configuration
    invalide, ne devrait plus arriver après _validate_provider_payload, mais
    jamais supposé ici)."""
    provider_cls = provider_manager.PROVIDERS.get(provider_row["provider_key"])
    if provider_cls is None:
        return None
    return provider_cls(model=provider_row["model_name"])


# ── Health-check réel (écrit ai_provider_health, jamais les conversations) ──
def _record_health_result(provider_id, ok, latency_ms, error_detail):
    """Comptabilité partagée par run_health_check() et test_connection()
    ci-dessous — UPSERT du snapshot ai_provider_health à partir d'un
    résultat déjà obtenu (ok/latence/erreur), pour ne jamais dupliquer ce
    calcul de moyenne glissante/taux de réussite deux fois."""
    now = datetime.now(timezone.utc).isoformat()
    previous = svc.get_health(provider_id)
    total_requests = (previous["total_requests"] if previous else 0) + 1
    total_errors = (previous["total_errors"] if previous else 0) + (0 if ok else 1)
    success_rate = round(100 * (total_requests - total_errors) / total_requests, 2)
    previous_avg = previous["average_latency"] if previous else None
    average_latency = (
        float(latency_ms) if previous_avg is None
        else round((previous_avg * (total_requests - 1) + latency_ms) / total_requests, 2)
    )
    svc.record_health(
        provider_id,
        last_success=now if ok else (previous["last_success"] if previous else None),
        last_failure=now if not ok else (previous["last_failure"] if previous else None),
        http_code=200 if ok else None,
        latency_ms=latency_ms,
        average_latency=average_latency,
        total_requests=total_requests,
        total_errors=total_errors,
        success_rate=success_rate,
        last_error=None if ok else error_detail,
    )


def run_health_check(provider_id):
    """Lance un VRAI health-check (instance.health() du fournisseur réel,
    voir chatbot/providers/base.py::ChatProvider.health) et enregistre le
    résultat dans ai_provider_health via _record_health_result() ci-dessus.
    Ne touche JAMAIS aux conversations/messages d'un élève : health()
    n'envoie qu'un appel de diagnostic (ex : lister les modèles
    disponibles), rien n'est stocké côté conversation, et il n'expose aucun
    compte de tokens (pas une génération réelle) — voir test_connection()
    ci-dessous pour un test qui en récupère. None si `provider_id` est
    inconnu (404 côté route)."""
    provider_row = svc.get_provider(provider_id)
    if provider_row is None:
        return None
    instance = _instantiate_provider(provider_row)

    started = _time.perf_counter()
    if instance is None:
        result = {"ok": False, "detail": f"provider_key inconnu : {provider_row['provider_key']!r}."}
    else:
        try:
            result = instance.health()
        except Exception as exc:
            result = {"ok": False, "detail": str(exc)}
    latency_ms = round((_time.perf_counter() - started) * 1000)

    _record_health_result(provider_id, result["ok"], latency_ms, result.get("detail"))
    return {"ok": result["ok"], "detail": result.get("detail", ""), "latency_ms": latency_ms}


# ── "Tester la connexion" (bouton dédié, admin panel IA) ────────────────────
# Contrairement à run_health_check() (instance.health(), simple diagnostic
# sans génération réelle, gratuit) : test_connection() envoie un VRAI prompt
# (donc récupère de vrais tokens via instance.last_usage, voir
# gemini_provider.py/anthropic_provider.py) ET enregistre le résultat dans
# ai_provider_health via _record_health_result() ci-dessus — en une seule
# action (l'ancien bouton "Tester", qui envoyait le même prompt réel SANS
# enregistrer les stats de santé, a été retiré : strictement dominé par
# celui-ci pour un coût identique, voir chantier de simplification admin).
# Ne touche JAMAIS aux conversations réelles d'un élève.
def test_connection(provider_id):
    """None si `provider_id` est inconnu (404 côté route)."""
    provider_row = svc.get_provider(provider_id)
    if provider_row is None:
        return None
    instance = _instantiate_provider(provider_row)

    started = _time.perf_counter()
    if instance is None:
        ok, error_detail, tokens, response_preview = False, f"provider_key inconnu : {provider_row['provider_key']!r}.", None, None
    else:
        try:
            fragments = list(instance.stream_chat(_TEST_MESSAGES, _TEST_SYSTEM_PROMPT, max_tokens=16))
            ok, error_detail = True, None
            tokens = instance.last_usage
            response_preview = "".join(fragments).strip()[:200]
        except Exception as exc:
            ok, error_detail, tokens, response_preview = False, str(exc), None, None
    latency_ms = round((_time.perf_counter() - started) * 1000)

    _record_health_result(provider_id, ok, latency_ms, error_detail)
    return {
        "ok": ok,
        "detail": error_detail or "",
        "latency_ms": latency_ms,
        "model": instance.current_model() if instance is not None else provider_row["model_name"],
        "tokens": tokens,
        "response_preview": response_preview,
    }


# ── Journal d'activité : une fonction "*_logged" par action, appelée par
# server.py à la place de la fonction d'origine ci-dessus (jamais les deux à
# la fois pour une même requête) — voir docstring du module. Chaque wrapper :
# (1) capture l'état AVANT si pertinent, (2) appelle la fonction d'origine
# SANS RIEN Y CHANGER, (3) capture l'état APRÈS si l'action a réussi,
# (4) enregistre une entrée via admin_ai_log_service.record(), toujours,
# succès comme échec, (5) renvoie EXACTEMENT ce que renvoyait la fonction
# d'origine — server.py n'a donc besoin d'aucune logique conditionnelle
# supplémentaire pour traiter la réponse HTTP.
def _snapshot(provider_id):
    """Photo JSON-sérialisable d'un fournisseur pour le journal — un
    sous-ensemble des champs métier, jamais les colonnes techniques
    (created_at/updated_at, déjà couvertes par created_at de la ligne de
    journal elle-même)."""
    row = svc.get_provider(provider_id)
    if row is None:
        return None
    return {
        "name": row["name"], "provider_key": row["provider_key"], "model_name": row["model_name"],
        "enabled": bool(row["enabled"]), "priority": row["priority"],
        "fallback_provider_id": row["fallback_provider_id"], "code": row["code"],
    }


def _errors_to_message(errors):
    if not errors:
        return None
    return "; ".join(f"{key}: {value}" for key, value in errors.items())


def create_provider_logged(actor, data):
    provider_id, errors = create_provider(data)
    ok = not errors
    after = _snapshot(provider_id) if ok else None
    admin_ai_log_service.record(
        actor, action="create_provider",
        provider_id=provider_id, provider_name=after["name"] if after else data.get("name"),
        old_values=None, new_values=after,
        result="success" if ok else "error", error_message=_errors_to_message(errors),
    )
    return provider_id, errors


def update_provider_logged(actor, provider_id, data):
    before = _snapshot(provider_id)
    ok, errors = update_provider(provider_id, data)
    after = _snapshot(provider_id) if ok else None
    admin_ai_log_service.record(
        actor, action="update_provider",
        provider_id=provider_id, provider_name=(after or before or {}).get("name") or data.get("name"),
        old_values=before, new_values=after,
        result="success" if ok else "error", error_message=_errors_to_message(errors),
    )
    return ok, errors


def delete_provider_logged(actor, provider_id):
    before = _snapshot(provider_id)
    ok, errors = delete_provider(provider_id)
    admin_ai_log_service.record(
        actor, action="delete_provider",
        provider_id=provider_id, provider_name=before["name"] if before else None,
        old_values=before, new_values=None,
        result="success" if ok else "error", error_message=_errors_to_message(errors),
    )
    return ok, errors


def set_provider_enabled_logged(actor, provider_id, enabled):
    before = _snapshot(provider_id)
    ok, errors = set_provider_enabled(provider_id, enabled)
    admin_ai_log_service.record(
        actor, action="enable_provider" if enabled else "disable_provider",
        provider_id=provider_id, provider_name=before["name"] if before else None,
        old_values={"enabled": before["enabled"]} if before else None,
        new_values={"enabled": bool(enabled)} if ok else None,
        result="success" if ok else "error", error_message=_errors_to_message(errors),
    )
    return ok, errors


def move_provider_priority_logged(actor, provider_id, direction):
    before = _snapshot(provider_id)
    ok, errors = move_provider_priority(provider_id, direction)
    after = _snapshot(provider_id) if ok else None
    admin_ai_log_service.record(
        actor, action="reorder_priority",
        provider_id=provider_id, provider_name=(before or after or {}).get("name"),
        old_values={"priority": before["priority"]} if before else None,
        new_values={"priority": after["priority"], "direction": direction} if after else None,
        result="success" if ok else "error", error_message=_errors_to_message(errors),
    )
    return ok, errors


def set_subscription_providers_logged(actor, subscription, provider_ids):
    """Le journal n'a pas de colonne dédiée à l'abonnement concerné (une
    seule table, partagée avec les actions par fournisseur) : le libellé
    "Abonnement <plan>" est enregistré dans `provider_name` — un choix
    pragmatique pour rester sur UNE seule table de journal plutôt que d'en
    créer une seconde pour ce seul cas, voir le rapport de ce chantier."""
    before_ids = sorted(m["provider_id"] for m in svc.list_mappings_for_subscription(subscription))
    ok, errors = set_subscription_providers(subscription, provider_ids)
    admin_ai_log_service.record(
        actor, action="update_subscription",
        provider_id=None, provider_name=f"Abonnement {subscription}",
        old_values={"provider_ids": before_ids},
        new_values={"provider_ids": sorted(provider_ids or [])} if ok else None,
        result="success" if ok else "error", error_message=_errors_to_message(errors),
    )
    return ok, errors


def run_health_check_logged(actor, provider_id):
    result = run_health_check(provider_id)
    if result is None:
        return None
    provider_row = svc.get_provider(provider_id)
    admin_ai_log_service.record(
        actor, action="health_check",
        provider_id=provider_id, provider_name=provider_row["name"] if provider_row else None,
        old_values=None, new_values=result,
        result="success" if result.get("ok") else "error", error_message=None if result.get("ok") else result.get("detail"),
    )
    return result


def test_connection_logged(actor, provider_id):
    result = test_connection(provider_id)
    if result is None:
        return None
    provider_row = svc.get_provider(provider_id)
    admin_ai_log_service.record(
        actor, action="test_connection",
        provider_id=provider_id, provider_name=provider_row["name"] if provider_row else None,
        old_values=None, new_values=result,
        result="success" if result.get("ok") else "error", error_message=None if result.get("ok") else result.get("detail"),
    )
    return result


# ── Haute disponibilité IA : clés API multiples par fournisseur ────────────
# Voir ai_provider_key_service.py pour le chiffrement/la rotation — ce module
# se contente de valider les entrées admin, masquer la clé à l'affichage, et
# journaliser (même politique "*_logged" que le reste du fichier).
def _serialize_api_key(row):
    """Jamais la clé en clair, ni même son chiffré — seuls les 4 derniers
    caractères du texte déchiffré serviraient à la reconnaître, mais même ça
    exigerait un déchiffrement inutile ici : l'écran d'administration n'a
    besoin que du label et des statistiques, jamais de la valeur de la clé
    une fois enregistrée (voir docstring du module ai_provider_key_service)."""
    avg_response_time_ms = (
        round(row["total_response_time_ms"] / row["request_count"]) if row["request_count"] else None
    )
    return {
        "id": row["id"],
        "provider_key": row["provider_key"],
        "label": row["label"],
        "enabled": bool(row["enabled"]),
        "priority": row["priority"],
        "request_count": row["request_count"],
        "failure_count": row["failure_count"],
        "fallback_count": row["fallback_count"],
        "avg_response_time_ms": avg_response_time_ms,
        "last_used_at": row["last_used_at"],
        "last_success_at": row["last_success_at"],
        "last_failure_at": row["last_failure_at"],
        "last_error": row["last_error"],
        "quota_exceeded_until": row["quota_exceeded_until"],
        "in_cooldown": ai_provider_key_service.is_in_cooldown(row),
        "created_at": row["created_at"],
    }


def list_api_keys(provider_key=None):
    return [_serialize_api_key(row) for row in ai_provider_key_service.list_keys(provider_key)]


def _validate_api_key_payload(data):
    errors = {}
    provider_key = (data.get("provider_key") or "").strip()
    label = (data.get("label") or "").strip()
    raw_api_key = (data.get("api_key") or "").strip()
    if provider_key not in provider_manager.PROVIDERS:
        errors["provider_key"] = f"Fournisseur inconnu : {provider_key!r}."
    if not label:
        errors["label"] = "Le libellé est obligatoire."
    if not raw_api_key:
        errors["api_key"] = "La clé API est obligatoire."
    return errors


def create_api_key(data):
    errors = _validate_api_key_payload(data)
    if errors:
        return None, errors
    try:
        row = ai_provider_key_service.create_key(
            data["provider_key"].strip(), data["label"].strip(), data["api_key"].strip(),
            priority=int(data.get("priority") or 0),
        )
    except ai_provider_key_service.KeyEncryptionNotConfigured as exc:
        return None, {"_": str(exc)}
    return row["id"], {}


def update_api_key(key_id, data):
    row = ai_provider_key_service.get_key(key_id)
    if row is None:
        return False, {"_": "Clé introuvable."}
    fields = {}
    if "label" in data:
        label = (data.get("label") or "").strip()
        if not label:
            return False, {"label": "Le libellé est obligatoire."}
        fields["label"] = label
    if "enabled" in data:
        fields["enabled"] = bool(data.get("enabled"))
    if "priority" in data:
        fields["priority"] = int(data.get("priority") or 0)
    ai_provider_key_service.update_key(key_id, **fields)
    return True, {}


def delete_api_key(key_id):
    row = ai_provider_key_service.get_key(key_id)
    if row is None:
        return False, {"_": "Clé introuvable."}
    ai_provider_key_service.delete_key(key_id)
    return True, {}


def test_api_key(key_id):
    return ai_provider_key_service.test_key(key_id)


def create_api_key_logged(actor, data):
    key_id, errors = create_api_key(data)
    admin_ai_log_service.record(
        actor, action="create_api_key",
        provider_name=data.get("provider_key"),
        old_values=None, new_values={"label": data.get("label"), "priority": data.get("priority")},
        result="success" if key_id else "error", error_message=_errors_to_message(errors) if errors else None,
    )
    return key_id, errors


def update_api_key_logged(actor, key_id, data):
    row = ai_provider_key_service.get_key(key_id)
    ok, errors = update_api_key(key_id, data)
    admin_ai_log_service.record(
        actor, action="update_api_key",
        provider_name=row["provider_key"] if row else None,
        old_values=None, new_values=data,
        result="success" if ok else "error", error_message=_errors_to_message(errors) if errors else None,
    )
    return ok, errors


def delete_api_key_logged(actor, key_id):
    row = ai_provider_key_service.get_key(key_id)
    ok, errors = delete_api_key(key_id)
    admin_ai_log_service.record(
        actor, action="delete_api_key",
        provider_name=row["provider_key"] if row else None,
        old_values={"label": row["label"]} if row else None, new_values=None,
        result="success" if ok else "error", error_message=_errors_to_message(errors) if errors else None,
    )
    return ok, errors


def test_api_key_logged(actor, key_id):
    result = test_api_key(key_id)
    if result is None:
        return None
    row = ai_provider_key_service.get_key(key_id)
    admin_ai_log_service.record(
        actor, action="test_api_key",
        provider_name=row["provider_key"] if row else None,
        old_values=None, new_values=result,
        result="success" if result.get("ok") else "error", error_message=None if result.get("ok") else result.get("detail"),
    )
    return result
