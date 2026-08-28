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

from .base import ChatProvider

DEFAULT_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "mistral"
DEFAULT_TIMEOUT = 60


class OllamaConnectionError(RuntimeError):
    """Levée quand Ollama n'est pas joignable (arrêté, mauvaise URL...)."""


class OllamaProvider(ChatProvider):
    def __init__(self, model=None):
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
                break
