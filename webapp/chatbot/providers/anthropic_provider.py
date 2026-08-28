"""
Implémentation Claude (Anthropic) du contrat ChatProvider — fournisseur par
défaut de NovaMath. Utilise exclusivement l'API officielle Anthropic (clé API
standard via la variable d'environnement ANTHROPIC_API_KEY), jamais un
abonnement Claude Pro. La clé n'est jamais lue ailleurs que dans ce fichier et
n'est jamais transmise au frontend — voir provider_manager.py qui instancie
cette classe côté serveur uniquement.
"""
import os

import anthropic

from .base import ChatProvider, ProviderUnavailableError

DEFAULT_MODEL = "claude-sonnet-5"

# Sans timeout explicite, le SDK Anthropic utilise son défaut interne
# (connect=5s, mais read/write/pool=600s chacun — vérifié sur l'environnement,
# voir anthropic.DEFAULT_TIMEOUT) : un incident fournisseur "silencieux"
# (connexion TCP acceptée, plus aucun octet envoyé, pas d'erreur réseau
# franche) peut alors bloquer un thread worker gunicorn jusqu'à 10 minutes
# (voir audit production, gunicorn.conf.py::GUNICORN_TIMEOUT=60 par défaut —
# largement dépassé). 45s laisse largement le temps à une réponse normale de
# démarrer/continuer à streamer tout en bornant un blocage silencieux à une
# durée raisonnable ; ANTHROPIC_TIMEOUT permet de l'ajuster sans redéploiement
# de code si la latence réelle du fournisseur l'exige.
DEFAULT_TIMEOUT_SECONDS = 45


class AnthropicConnectionError(ProviderUnavailableError):
    """Levée quand l'API Anthropic est injoignable, la clé API est absente/
    invalide, ou que le compte n'a plus de crédit — jamais une erreur liée à
    un abonnement Claude Pro, qui n'est jamais utilisé ici. `durable=True`
    pour clé invalide/crédit épuisé : ces cas ne se résolvent jamais tout
    seuls, provider_manager.py les met en cache d'indisponibilité plutôt que
    de les retenter à chaque message."""


class AnthropicProvider(ChatProvider):
    def __init__(self, model=None, api_key=None):
        # `api_key` explicite (haute disponibilité, voir
        # ai_provider_key_service.available_keys_for_rotation) prime sur la
        # variable d'environnement — comportement historique inchangé quand
        # aucune clé DB n'est configurée pour ce fournisseur.
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._model = model or DEFAULT_MODEL
        self._timeout = float(os.environ.get("ANTHROPIC_TIMEOUT", DEFAULT_TIMEOUT_SECONDS))
        self._client = (
            anthropic.Anthropic(api_key=self._api_key, timeout=self._timeout) if self._api_key else None
        )

    def has_credentials(self):
        return bool(self._api_key)

    def _require_client(self):
        if self._client is None:
            raise AnthropicConnectionError(
                "La clé API Anthropic n'est pas configurée. Définis la variable "
                "d'environnement ANTHROPIC_API_KEY côté serveur (jamais dans le "
                "code ni le frontend), avec une clé API standard — pas un "
                "abonnement Claude Pro."
            )
        return self._client

    def health(self):
        client = None
        try:
            client = self._require_client()
        except AnthropicConnectionError as exc:
            return {"ok": False, "detail": str(exc)}
        try:
            client.models.list(limit=1)
            return {"ok": True, "detail": ""}
        except anthropic.AuthenticationError as exc:
            return {
                "ok": False,
                "detail": "Clé API Anthropic invalide ou expirée.",
                "error": str(exc),
            }
        except anthropic.APIConnectionError as exc:
            return {
                "ok": False,
                "detail": "Impossible de joindre l'API Anthropic (vérifie la connexion réseau).",
                "error": str(exc),
            }
        except anthropic.APIError as exc:
            return {
                "ok": False,
                "detail": "L'API Anthropic a répondu avec une erreur.",
                "error": str(exc),
            }

    def available_models(self):
        return {}

    def current_model(self):
        return self._model

    def stream_chat(self, messages, system, temperature=0.7, max_tokens=1024):
        # `temperature` fait partie du contrat commun ChatProvider (réglable
        # par élève/admin, voir chatbot_settings/system_settings), mais
        # claude-sonnet-5 rejette ce paramètre avec un 400 explicite
        # ("`temperature` is deprecated for this model") quelle que soit sa
        # valeur — vérifié par un appel réel (audit 2026-08-24). On accepte
        # donc toujours l'argument pour respecter l'interface, sans jamais le
        # transmettre à l'API Anthropic.
        client = self._require_client()
        self.last_usage = None
        self.last_finish_reason = None
        try:
            with client.messages.stream(
                model=self._model,
                system=system,
                messages=messages,
                max_tokens=max_tokens,
            ) as stream:
                for text in stream.text_stream:
                    yield text
                final_message = stream.get_final_message()
                usage = final_message.usage
                self.last_usage = {
                    "prompt_tokens": usage.input_tokens,
                    "completion_tokens": usage.output_tokens,
                    "total_tokens": usage.input_tokens + usage.output_tokens,
                }
                self.last_finish_reason = final_message.stop_reason
        except anthropic.AuthenticationError as exc:
            raise AnthropicConnectionError(
                "Clé API Anthropic invalide ou expirée.", durable=True,
            ) from exc
        except anthropic.APIConnectionError as exc:
            raise AnthropicConnectionError(
                "Impossible de joindre l'API Anthropic (vérifie la connexion réseau)."
            ) from exc
        except anthropic.RateLimitError as exc:
            raise AnthropicConnectionError(
                "Limite de requêtes Anthropic atteinte, réessaie dans un instant."
            ) from exc
        except anthropic.APIError as exc:
            # Anthropic répond un compte à crédit épuisé par un 400
            # invalid_request_error générique (pas un code dédié) — vérifié par
            # un appel réel (voir audit provider health-check) : le message
            # contient explicitement "credit balance is too low".
            durable = "credit balance is too low" in str(exc).lower()
            raise AnthropicConnectionError(
                f"L'API Anthropic a répondu avec une erreur : {exc}", durable=durable,
            ) from exc
