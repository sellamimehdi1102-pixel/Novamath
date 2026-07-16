"""
Implémentation Claude (Anthropic) du contrat ChatProvider. La clé API n'est
jamais lue ailleurs que dans ce fichier et n'est jamais transmise au frontend
— voir provider_manager.py qui l'instancie côté serveur uniquement.
"""
import os

import anthropic

from .base import ChatProvider

DEFAULT_MODEL = "claude-sonnet-5"


class AnthropicProvider(ChatProvider):
    def __init__(self, model=None):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY n'est pas configurée. Définis cette variable "
                "d'environnement côté serveur (jamais dans le code ni le frontend)."
            )
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model or DEFAULT_MODEL

    def stream_chat(self, messages, system, temperature=0.7, max_tokens=1024):
        with self._client.messages.stream(
            model=self._model,
            system=system,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        ) as stream:
            for text in stream.text_stream:
                yield text
