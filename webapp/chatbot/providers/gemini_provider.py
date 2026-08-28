"""
Implémentation Gemini (Google) du contrat ChatProvider — utilise exclusivement
l'API officielle Google GenAI (clé API standard Google AI Studio via la
variable d'environnement GEMINI_API_KEY), jamais Vertex AI/un projet Google
Cloud. La clé n'est jamais lue ailleurs que dans ce fichier et n'est jamais
transmise au frontend — voir provider_manager.py qui instancie cette classe
côté serveur uniquement (même architecture que anthropic_provider.py).
"""
import logging
import os
import time

from google import genai
from google.genai import errors, types

from .base import ChatProvider, ProviderUnavailableError

logger = logging.getLogger("chatbot.providers.gemini")

# Un 429 SANS "limit: 0" (voir _is_zero_quota_error) est une rafale de
# requêtes transitoire (RPM), pas une panne durable — elle se résorbe
# normalement en quelques secondes. Sans repli automatique ici, le plan Free
# (un seul candidat dans MODEL_CHAIN_BY_PLAN, voir provider_manager.py)
# n'avait plus AUCUN candidat restant dès le premier 429 et retombait
# immédiatement sur FakeProvider pour ce message — alors que Gemini était en
# réalité toujours utilisable une seconde plus tard. Backoff exponentiel
# borné à 3 tentatives, uniquement tant qu'aucun fragment n'a encore été
# transmis à l'appelant (voir stream_chat ci-dessous) : une réponse déjà
# partiellement diffusée à l'élève ne doit jamais être rejouée depuis le
# début (même philosophie que llm_fallback_service.generate()).
_TRANSIENT_RETRY_DELAYS_SECONDS = (2, 4, 8)

# TTL du cache d'indisponibilité (provider_manager.mark_unavailable) par
# famille de panne — voir _classify_error() ci-dessous. Audit du 2026-07-26 :
# un vrai quota JOURNALIER Google ("limit: 20, quotaId: ...PerDay...") n'a
# RIEN à voir avec une rafale RPM ("limit: 60, quotaId: ...PerMinute...") —
# le premier ne se résorbe pas avant plusieurs heures, le second en quelques
# secondes. Un seul TTL fixe de 15 minutes pour les deux traitait le premier
# cas comme s'il allait se résoudre tout seul (il ne se résout pas) et le
# second comme s'il fallait attendre un quart d'heure (bien trop long).
_TTL_RPM_TPM_SECONDS = 5 * 60                     # rafale RPM/TPM ou surcharge sans détail de quota
_TTL_QUOTA_PROJET_SECONDS = 6 * 60 * 60           # quota du projet Google Cloud dépassé
_TTL_QUOTA_JOURNALIER_SECONDS = 12 * 60 * 60      # quota journalier dépassé (reset quotidien Google, heure exacte inconnue de l'API)
_TTL_QUOTA_ZERO_SECONDS = 24 * 60 * 60            # quota Free Tier figé à 0 (facturation à activer manuellement)
_TTL_CLE_INVALIDE_SECONDS = 24 * 60 * 60          # clé API invalide/expirée/accès refusé
_TTL_MODELE_INDISPONIBLE_SECONDS = 24 * 60 * 60   # modèle introuvable/déprécié (404)

_MESSAGE_BY_CATEGORY = {
    "quota_zero": (
        "Quota Gemini Free Tier à 0 pour ce modèle (facturation Google AI "
        "Studio non activée sur ce projet)."
    ),
    "quota_journalier": (
        "Quota Gemini journalier dépassé pour ce modèle (se réinitialise sous 24h)."
    ),
    "quota_projet": "Quota Gemini du projet Google Cloud dépassé.",
    "modele_indisponible": (
        "Le modèle Gemini demandé est introuvable ou n'est plus disponible "
        "(vérifie le nom du modèle configuré)."
    ),
}

# gemini-2.5-flash/-pro/-flash-lite renvoient une 404 "no longer available to
# new users" pour toute clé API Google AI Studio créée après leur dépréciation
# (vérifié par un appel réel, voir tests/test_gemini_provider.py) — le modèle
# par défaut doit rester un modèle confirmé disponible pour les nouvelles clés.
DEFAULT_MODEL = "gemini-3-flash-preview"

# Sans timeout explicite, le SDK google-genai n'en applique aucun par défaut
# (httpx sans limite) : un incident fournisseur silencieux (connexion ouverte,
# plus aucun octet envoyé) peut bloquer un thread worker gunicorn indéfiniment
# (voir audit production, gunicorn.conf.py::GUNICORN_TIMEOUT=60 par défaut —
# largement dépassé). Même valeur et même raisonnement que
# anthropic_provider.DEFAULT_TIMEOUT_SECONDS ; GEMINI_TIMEOUT_MS permet de
# l'ajuster sans redéploiement. Unité : millisecondes (HttpOptions.timeout).
DEFAULT_TIMEOUT_MS = 45_000


class GeminiConnectionError(ProviderUnavailableError):
    """Levée quand l'API Gemini est injoignable, la clé API est absente/
    invalide, ou que le quota est dépassé. `durable=True` pour clé invalide/
    accès refusé/quota Free Tier à 0 (voir _is_zero_quota_error) — ces cas ne
    se résolvent jamais tout seuls, provider_manager.py les met en cache
    d'indisponibilité plutôt que de les retenter à chaque message."""


def _is_invalid_api_key_error(exc):
    """Distingue une clé API invalide/expirée des autres erreurs 4xx.

    Contrairement à Anthropic (401 AuthenticationError dédiée), l'API Gemini
    répond une clé invalide par un ClientError 400 générique (INVALID_ARGUMENT)
    avec le message "API key not valid..." — vérifié par un appel réel à
    l'API (voir tests/test_gemini_provider.py::TestConnectiviteReelleSansVraieCle).
    401/403 sont conservés en repli au cas où Google ferait évoluer cette
    réponse vers un code d'authentification plus conventionnel."""
    if exc.code in (401, 403):
        return True
    return exc.code == 400 and "api key not valid" in (exc.message or "").lower()


def _is_zero_quota_error(exc):
    """Distingue un 429 structurel (quota Free Tier figé à 0 pour ce modèle —
    ne se résoudra jamais tout seul tant que la facturation Google AI Studio
    n'est pas activée) d'un 429 transitoire (rafale de requêtes, se résorbe
    de lui-même) — vérifié par un appel réel (voir audit Google AI Studio) :
    le message contient explicitement "limit: 0" dans le premier cas, absent
    pour un vrai sursaut de RPM sur un palier payant."""
    return "limit: 0" in (exc.message or "")


def _error_body(exc):
    """Corps JSON brut de l'erreur Google, jamais deviné : voir
    google.genai.errors.APIError.__init__, qui stocke dans `.details` soit
    {"error": {...}} (transport requests/httpx standard, réponse .json()
    complète), soit directement le dict d'erreur (transport "replay"/
    websocket, voir APIError.raise_for_response). Les deux formes sont
    normalisées ici pour que le reste du code n'ait jamais à s'en soucier."""
    details = getattr(exc, "details", None)
    if isinstance(details, dict):
        inner = details.get("error")
        if isinstance(inner, dict):
            return inner
        return details
    return {}


def _quota_violations(exc):
    """Violations google.rpc.QuotaFailure présentes dans l'erreur — la vraie
    réponse Google (voir audit du 2026-07-26) place dans `error.details` un
    tableau d'objets typés par `@type`, dont au plus un
    "type.googleapis.com/google.rpc.QuotaFailure" listant les quotas
    dépassés (quotaId/quotaMetric/quotaValue). Renvoie [] si absent (429 sans
    détail de quota exploitable — surcharge générique du backend)."""
    for item in _error_body(exc).get("details") or []:
        if str(item.get("@type", "")).endswith("QuotaFailure"):
            return item.get("violations") or []
    return []


class _GeminiErrorClassification:
    """Résultat de _classify_error() ci-dessous : une famille de panne Gemini
    précise (jamais juste "429"), avec la conduite à tenir pour chacune.

    `retry_in_process` : True si le backoff exponentiel local (2s/4s/8s,
    voir stream_chat) a une chance réelle de résoudre le problème (rafale
    RPM/TPM, surcharge momentanée du backend) ; False si retenter dans les
    secondes qui suivent est structurellement inutile (quota journalier,
    clé invalide, modèle introuvable) — dans ce cas, échec immédiat.

    `ttl_seconds` : durée du cache d'indisponibilité (provider_manager.
    mark_unavailable) à appliquer si cette panne est confirmée durable."""

    __slots__ = ("category", "retry_in_process", "ttl_seconds", "detail")

    def __init__(self, category, retry_in_process, ttl_seconds, detail):
        self.category = category
        self.retry_in_process = retry_in_process
        self.ttl_seconds = ttl_seconds
        self.detail = detail


def _classify_error(exc):
    """Analyse RÉELLE du corps d'erreur Google (jamais une simple recherche
    de sous-chaîne dans le message, contrairement à l'ancienne
    _is_zero_quota_error seule) pour distinguer les familles de 429/404 qui
    demandent des conduites très différentes — voir audit du 2026-07-26, qui
    a mis en évidence qu'un quota JOURNALIER réellement épuisé
    (quotaId="GenerateRequestsPerDayPerProjectPerModel-FreeTier", limit=20)
    n'était classé ni "limit: 0" (donc pas durable) ni jamais mis en cache,
    provoquant un cycle de 14s de tentatives inutiles À CHAQUE message tant
    que le quota journalier restait épuisé :

    - 404 (modèle introuvable/déprécié) : jamais résolu automatiquement.
    - 429 "limit: 0" (voir _is_zero_quota_error) : facturation non activée,
      jamais résolu automatiquement.
    - 429 avec QuotaFailure.quotaId contenant "PerDay" : quota journalier,
      ne se résorbe pas avant plusieurs heures — échec immédiat, pas de
      backoff local (inutile), TTL long.
    - 429 avec quotaId contenant "PerProject" (sans "PerDay" ni "PerMinute") :
      quota du projet Google Cloud, même logique, TTL un peu plus court.
    - 429 avec quotaId contenant "PerMinute" (RPM ou TPM), ou 429 sans aucun
      détail QuotaFailure exploitable (surcharge générique du backend) :
      rafale transitoire — le backoff local existant (2s/4s/8s) reste
      pertinent ; si les 3 tentatives échouent quand même, mise en cache
      courte (5 min) pour ne pas rejouer inutilement le même cycle de 14s à
      CHAQUE message suivant pendant que la rafale se poursuit.

    Renvoie None si `exc` n'est ni un 404 ni un 429 (autre 4xx générique,
    traité par l'appelant comme avant)."""
    if exc.code == 404:
        return _GeminiErrorClassification(
            "modele_indisponible", False, _TTL_MODELE_INDISPONIBLE_SECONDS,
            f"modèle introuvable ou déprécié ({exc.message})",
        )
    if exc.code != 429:
        return None

    if _is_zero_quota_error(exc):
        return _GeminiErrorClassification(
            "quota_zero", False, _TTL_QUOTA_ZERO_SECONDS,
            "quota Free Tier figé à 0 (facturation Google AI Studio non activée)",
        )

    violations = _quota_violations(exc)
    quota_id = violations[0].get("quotaId", "") if violations else ""
    quota_metric = violations[0].get("quotaMetric", "") if violations else ""

    if "PerDay" in quota_id:
        return _GeminiErrorClassification(
            "quota_journalier", False, _TTL_QUOTA_JOURNALIER_SECONDS,
            f"quota journalier dépassé ({quota_id})",
        )
    if "PerMinute" in quota_id:
        return _GeminiErrorClassification(
            "quota_rpm_tpm", True, _TTL_RPM_TPM_SECONDS,
            f"limite par minute (RPM/TPM) dépassée ({quota_id})",
        )
    if quota_id and "PerProject" in quota_id:
        return _GeminiErrorClassification(
            "quota_projet", False, _TTL_QUOTA_PROJET_SECONDS,
            f"quota du projet dépassé ({quota_id})",
        )
    return _GeminiErrorClassification(
        "surcharge_temporaire", True, _TTL_RPM_TPM_SECONDS,
        f"surcharge temporaire du backend Gemini ({quota_metric or 'aucun détail de quota fourni'})",
    )


def _translate_messages(messages):
    """Traduit le format interne NovaMath (role "user"/"assistant", voir
    conversation_manager.py) vers le format Gemini (role "user"/"model" —
    Gemini n'utilise jamais "assistant")."""
    return [
        {"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
        for m in messages
    ]


class GeminiProvider(ChatProvider):
    def __init__(self, model=None, api_key=None):
        # `api_key` explicite (haute disponibilité, voir
        # ai_provider_key_service.available_keys_for_rotation) prime sur la
        # variable d'environnement — comportement historique inchangé quand
        # aucune clé DB n'est configurée pour ce fournisseur.
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self._model = model or DEFAULT_MODEL
        self._timeout_ms = int(os.environ.get("GEMINI_TIMEOUT_MS", DEFAULT_TIMEOUT_MS))
        self._client = (
            genai.Client(
                api_key=self._api_key,
                http_options=types.HttpOptions(timeout=self._timeout_ms),
            )
            if self._api_key else None
        )

    def has_credentials(self):
        return bool(self._api_key)

    def _require_client(self):
        if self._client is None:
            raise GeminiConnectionError(
                "La clé API Gemini n'est pas configurée. Définis la variable "
                "d'environnement GEMINI_API_KEY côté serveur (jamais dans le "
                "code ni le frontend), avec une clé API Google AI Studio "
                "standard — pas un projet Vertex AI."
            )
        return self._client

    def health(self):
        client = None
        try:
            client = self._require_client()
        except GeminiConnectionError as exc:
            return {"ok": False, "detail": str(exc)}
        try:
            client.models.list(config=types.ListModelsConfig(page_size=1))
            return {"ok": True, "detail": ""}
        except errors.ClientError as exc:
            if _is_invalid_api_key_error(exc):
                return {
                    "ok": False,
                    "detail": "Clé API Gemini invalide ou expirée.",
                    "error": str(exc),
                }
            return {
                "ok": False,
                "detail": "L'API Gemini a refusé la requête.",
                "error": str(exc),
            }
        except errors.ServerError as exc:
            return {
                "ok": False,
                "detail": "Impossible de joindre l'API Gemini (vérifie la connexion réseau).",
                "error": str(exc),
            }
        except errors.APIError as exc:
            return {
                "ok": False,
                "detail": "L'API Gemini a répondu avec une erreur.",
                "error": str(exc),
            }

    def available_models(self):
        return {}

    def current_model(self):
        return self._model

    def stream_chat(self, messages, system, temperature=0.7, max_tokens=1024):
        client = self._require_client()
        self.last_usage = None
        # Chantier 6 (bug "réponses parfois coupées") : le finish_reason de
        # chaque chunk (None pendant le stream, renseigné sur le dernier —
        # STOP/MAX_TOKENS/SAFETY/...) n'était lu nulle part avant ce chantier,
        # rendant une troncature par max_output_tokens indiscernable d'une fin
        # normale à tous les niveaux du pipeline. Exposé ici pour que
        # llm_fallback_service puisse le journaliser (voir son appelant).
        self.last_finish_reason = None
        contents = _translate_messages(messages)
        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=temperature,
            max_output_tokens=max_tokens,
            # Chantier 6 (bug "réponses parfois coupées") : sans thinking_config,
            # les modèles Gemini 3 partagent max_output_tokens ENTRE le
            # raisonnement interne ("thinking") et la réponse visible — vérifié
            # par appel réel (audit 2026-08-25) : sur une explication
            # pédagogique longue, jusqu'à 96% du budget (979/1024 tokens) est
            # parti dans les tokens de réflexion invisibles, ne laissant que
            # ~40 tokens visibles à l'élève (réponse coupée après une phrase).
            # thinking_level="low" réduit ce raisonnement (588 tokens dans le
            # même test, contre 979) sans le supprimer entièrement (résultats
            # encore corrects sur des exercices de lycée, contrairement à
            # thinking_budget=0 qui désactive le raisonnement — écarté pour ne
            # pas dégrader la qualité pédagogique) — laisse largement plus de
            # place à la réponse réellement affichée. Le budget déjà consommé
            # par le raisonnement est facturé au tarif OUTPUT quoi qu'il arrive
            # (voir ai_provider_service.py, Chantier 3), donc ce réglage réduit
            # potentiellement le coût réel autant qu'il améliore la complétude.
            thinking_config=types.ThinkingConfig(thinking_level="low"),
        )
        yielded_any = False
        retry_attempt = 0
        while True:
            try:
                stream = client.models.generate_content_stream(
                    model=self._model, contents=contents, config=config,
                )
                for chunk in stream:
                    if chunk.usage_metadata:
                        self.last_usage = {
                            "prompt_tokens": chunk.usage_metadata.prompt_token_count,
                            "completion_tokens": chunk.usage_metadata.candidates_token_count,
                            "total_tokens": chunk.usage_metadata.total_token_count,
                        }
                    candidates = getattr(chunk, "candidates", None)
                    if candidates:
                        reason = getattr(candidates[0], "finish_reason", None)
                        if reason is not None:
                            self.last_finish_reason = str(reason)
                    if chunk.text:
                        yielded_any = True
                        yield chunk.text
                if retry_attempt > 0:
                    logger.warning("Gemini disponible de nouveau")
                return
            except errors.ClientError as exc:
                if _is_invalid_api_key_error(exc):
                    raise GeminiConnectionError(
                        "Clé API Gemini invalide ou expirée.",
                        durable=True, ttl_seconds=_TTL_CLE_INVALIDE_SECONDS,
                    ) from exc

                classification = _classify_error(exc)

                if classification is not None and not classification.retry_in_process:
                    # Quota journalier/projet/zéro, modèle introuvable : le
                    # backoff local (2s/4s/8s) n'a AUCUNE chance de résoudre
                    # ça — retenter ne fait que retarder inutilement le repli
                    # sur FakeProvider de 14 secondes à chaque message. Échec
                    # immédiat, mis en cache pour la durée adaptée à la
                    # famille de panne (voir _classify_error).
                    logger.warning(
                        "Gemini indisponible — raison : %s", classification.detail,
                    )
                    raise GeminiConnectionError(
                        _MESSAGE_BY_CATEGORY.get(classification.category, str(exc)),
                        durable=True, ttl_seconds=classification.ttl_seconds,
                    ) from exc

                if classification is not None and classification.retry_in_process:
                    # Rafale RPM/TPM ou surcharge momentanée du backend : le
                    # backoff exponentiel existant reste pertinent, tant
                    # qu'aucun fragment n'a encore été transmis à l'appelant
                    # (sinon, rejouer depuis le début dupliquerait une réponse
                    # déjà partiellement diffusée à l'élève — comportement
                    # inchangé, l'exception remonte immédiatement).
                    if not yielded_any and retry_attempt < len(_TRANSIENT_RETRY_DELAYS_SECONDS):
                        delay = _TRANSIENT_RETRY_DELAYS_SECONDS[retry_attempt]
                        retry_attempt += 1
                        logger.warning(
                            "Gemini temporairement limité — raison : %s", classification.detail,
                        )
                        logger.warning(
                            "Nouvelle tentative %d/%d dans %d s",
                            retry_attempt, len(_TRANSIENT_RETRY_DELAYS_SECONDS), delay,
                        )
                        time.sleep(delay)
                        continue
                    # Les 3 tentatives ont toutes échoué (ou un fragment avait
                    # déjà été transmis) : mise en cache COURTE uniquement si
                    # rien n'a encore été diffusé — une rafale RPM/TPM qui
                    # continue encore après 14s de backoff mérite quelques
                    # minutes de répit avant le prochain message, mais une
                    # panne survenue après un début de réponse ne doit
                    # jamais être mise en cache (elle ne dit rien sur l'état
                    # général du fournisseur, juste sur CETTE requête).
                    if not yielded_any:
                        logger.warning(
                            "Toutes les tentatives ont échoué → FakeProvider — "
                            "raison : %s — mis en cache %d min",
                            classification.detail, classification.ttl_seconds // 60,
                        )
                    raise GeminiConnectionError(
                        "Limite de requêtes Gemini atteinte, réessaie dans un instant.",
                        durable=not yielded_any,
                        ttl_seconds=classification.ttl_seconds if not yielded_any else None,
                    ) from exc

                raise GeminiConnectionError(f"L'API Gemini a refusé la requête : {exc}") from exc
            except errors.ServerError as exc:
                raise GeminiConnectionError(
                    "Impossible de joindre l'API Gemini (vérifie la connexion réseau)."
                ) from exc
            except errors.APIError as exc:
                raise GeminiConnectionError(f"L'API Gemini a répondu avec une erreur : {exc}") from exc
