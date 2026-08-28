"""
Implémentation Gemini (Google) du contrat ChatProvider — utilise exclusivement
l'API officielle Google GenAI (clé API standard Google AI Studio via la
variable d'environnement GEMINI_API_KEY), jamais Vertex AI/un projet Google
Cloud. La clé n'est jamais lue ailleurs que dans ce fichier et n'est jamais
transmise au frontend — voir provider_manager.py qui instancie cette classe
côté serveur uniquement (même architecture que anthropic_provider.py).
"""
import os

from google import genai
from google.genai import errors, types

from .base import ChatProvider

# gemini-2.5-flash/-pro/-flash-lite renvoient une 404 "no longer available to
# new users" pour toute clé API Google AI Studio créée après leur dépréciation
# (vérifié par un appel réel, voir tests/test_gemini_provider.py) — le modèle
# par défaut doit rester un modèle confirmé disponible pour les nouvelles clés.
DEFAULT_MODEL = "gemini-3-flash-preview"


class GeminiConnectionError(RuntimeError):
    """Levée quand l'API Gemini est injoignable, la clé API est absente/
    invalide, ou que le quota est dépassé."""


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


def _translate_messages(messages):
    """Traduit le format interne NovaMath (role "user"/"assistant", voir
    conversation_manager.py) vers le format Gemini (role "user"/"model" —
    Gemini n'utilise jamais "assistant")."""
    return [
        {"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
        for m in messages
    ]


class GeminiProvider(ChatProvider):
    def __init__(self, model=None):
        self._api_key = os.environ.get("GEMINI_API_KEY")
        self._model = model or DEFAULT_MODEL
        self._client = genai.Client(api_key=self._api_key) if self._api_key else None

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
        try:
            stream = client.models.generate_content_stream(
                model=self._model,
                contents=_translate_messages(messages),
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )
            for chunk in stream:
                if chunk.text:
                    yield chunk.text
        except errors.ClientError as exc:
            if _is_invalid_api_key_error(exc):
                raise GeminiConnectionError("Clé API Gemini invalide ou expirée.") from exc
            if exc.code == 429:
                raise GeminiConnectionError(
                    "Limite de requêtes Gemini atteinte, réessaie dans un instant."
                ) from exc
            raise GeminiConnectionError(f"L'API Gemini a refusé la requête : {exc}") from exc
        except errors.ServerError as exc:
            raise GeminiConnectionError(
                "Impossible de joindre l'API Gemini (vérifie la connexion réseau)."
            ) from exc
        except errors.APIError as exc:
            raise GeminiConnectionError(f"L'API Gemini a répondu avec une erreur : {exc}") from exc
