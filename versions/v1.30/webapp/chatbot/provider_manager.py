"""
Point d'entrée UNIQUE pour résoudre le fournisseur IA actif. Changer de
fournisseur (Phase 2 : OpenAI/Gemini/DeepSeek/Qwen/Mistral/Llama/OpenRouter/
Ollama/LM Studio/API perso) = ajouter une entrée à PROVIDERS + une classe dans
webapp/chatbot/providers/, puis changer CHATBOT_PROVIDER — jamais toucher au
reste de la chaîne (conversation_manager, prompt_builder, routes Flask).
"""
import os

from .providers.anthropic_provider import AnthropicProvider

PROVIDERS = {
    "anthropic": AnthropicProvider,
}

MODELS = {
    "anthropic": {
        "claude-sonnet-5": "Claude Sonnet 5 (équilibré)",
        "claude-opus-4-8": "Claude Opus 4.8 (le plus capable)",
        "claude-haiku-4-5-20251001": "Claude Haiku 4.5 (le plus rapide)",
    },
}

_instance_cache = {}


def active_provider_name():
    return os.environ.get("CHATBOT_PROVIDER", "anthropic")


def get_provider(model=None):
    name = active_provider_name()
    provider_cls = PROVIDERS.get(name)
    if provider_cls is None:
        raise RuntimeError(f"Fournisseur IA inconnu : {name}")
    cache_key = (name, model)
    if cache_key not in _instance_cache:
        _instance_cache[cache_key] = provider_cls(model=model)
    return _instance_cache[cache_key]


def available_models():
    return MODELS.get(active_provider_name(), {})
