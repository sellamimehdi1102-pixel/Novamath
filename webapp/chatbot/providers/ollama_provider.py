"""
Implémentation Ollama (modèle local, aucune API cloud) du contrat ChatProvider.
Fournisseur par défaut de NovaMath : toutes les communications passent par
l'API HTTP locale d'Ollama (http://127.0.0.1:11434 par défaut), jamais depuis
le frontend — cette classe est instanciée uniquement côté serveur, par
provider_manager.py.
"""
import json
import os

import requests

from .base import ChatProvider, ProviderUnavailableError

DEFAULT_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "mistral"
DEFAULT_TIMEOUT = 60


class OllamaConnectionError(ProviderUnavailableError):
    """Levée quand Ollama n'est pas joignable (arrêté, mauvaise URL...) —
    toujours transitoire (durable=False, valeur par défaut) : un serveur
    local peut être redémarré à tout moment, jamais mis en cache
    d'indisponibilité comme une clé API cloud invalide."""


class OllamaProvider(ChatProvider):
    def __init__(self, model=None, api_key=None):
        self._base_url = os.environ.get("OLLAMA_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
        self._model = model or os.environ.get("OLLAMA_MODEL", DEFAULT_MODEL)
        self._timeout = float(os.environ.get("OLLAMA_TIMEOUT", DEFAULT_TIMEOUT))

    # ── Santé / modèles ──────────────────────────────────────────────────────
    def health(self):
        try:
            resp = requests.get(f"{self._base_url}/api/tags", timeout=3)
            resp.raise_for_status()
            return {"ok": True, "detail": ""}
        except requests.RequestException as exc:
            return {
                "ok": False,
                "detail": "Le moteur d'intelligence artificielle local n'est pas démarré.",
                "error": str(exc),
            }

    def available_models(self):
        try:
            resp = requests.get(f"{self._base_url}/api/tags", timeout=3)
            resp.raise_for_status()
            models = resp.json().get("models", [])
            return {m["name"]: m["name"] for m in models}
        except (requests.RequestException, ValueError, KeyError):
            return {}

    def current_model(self):
        return self._model

    # ── Génération ───────────────────────────────────────────────────────────
    def stream_chat(self, messages, system, temperature=0.7, max_tokens=1024):
        payload = {
            "model": self._model,
            "messages": [{"role": "system", "content": system}, *messages],
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        try:
            resp = requests.post(
                f"{self._base_url}/api/chat",
                json=payload,
                stream=True,
                timeout=self._timeout,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise OllamaConnectionError(
                "Le moteur d'intelligence artificielle local n'est pas démarré. "
                "Lance Ollama (`ollama serve`) puis réessaie."
            ) from exc

        self.last_usage = None
        # `with resp:` (au lieu d'une simple variable locale) : garantit que
        # la connexion HTTP sortante vers Ollama est TOUJOURS fermée — même
        # si le client NovaMath se déconnecte en plein stream (GeneratorExit
        # remonté par server.py à travers cette boucle) ou si une exception
        # est levée depuis la boucle (JSON invalide, erreur applicative) —
        # au lieu de compter sur le ramasse-miettes CPython pour libérer la
        # socket (comportement fiable en pratique mais non garanti par le
        # langage, voir anthropic_provider.py qui utilise déjà `with ... as
        # stream:` pour la même raison, et l'audit production correspondant).
        with resp:
            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                except ValueError:
                    continue
                if chunk.get("error"):
                    raise OllamaConnectionError(chunk["error"])
                content = chunk.get("message", {}).get("content")
                if content:
                    yield content
                if chunk.get("done"):
                    prompt_tokens = chunk.get("prompt_eval_count")
                    completion_tokens = chunk.get("eval_count")
                    if prompt_tokens is not None or completion_tokens is not None:
                        self.last_usage = {
                            "prompt_tokens": prompt_tokens,
                            "completion_tokens": completion_tokens,
                            "total_tokens": (prompt_tokens or 0) + (completion_tokens or 0),
                        }
                    break
