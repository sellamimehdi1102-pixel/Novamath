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

from .base import ChatProvider

DEFAULT_MODEL = "claude-sonnet-5"


class AnthropicConnectionError(RuntimeError):
    """Levée quand l'API Anthropic est injoignable, la clé API est absente/
    invalide, ou que le compte n'a plus de crédit — jamais une erreur liée à
    un abonnement Claude Pro, qui n'est jamais utilisé ici."""


class AnthropicProvider(ChatProvider):
    def __init__(self, model=None):
        self._api_key = os.environ.get("ANTHROPIC_API_KEY")
        self._model = model or DEFAULT_MODEL
        self._client = anthropic.Anthropic(api_key=self._api_key) if self._api_key else None

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
        client = self._require_client()
        try:
            with client.messages.stream(
                model=self._model,
                system=system,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            ) as stream:
                for text in stream.text_stream:
                    yield text
        except anthropic.AuthenticationError as exc:
            raise AnthropicConnectionError("Clé API Anthropic invalide ou expirée.") from exc
        except anthropic.APIConnectionError as exc:
            raise AnthropicConnectionError(
                "Impossible de joindre l'API Anthropic (vérifie la connexion réseau)."
            ) from exc
        except anthropic.RateLimitError as exc:
            raise AnthropicConnectionError(
                "Limite de requêtes Anthropic atteinte, réessaie dans un instant."
            ) from exc
        except anthropic.APIError as exc:
            raise AnthropicConnectionError(f"L'API Anthropic a répondu avec une erreur : {exc}") from exc
