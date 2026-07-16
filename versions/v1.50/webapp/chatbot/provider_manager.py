"""
Point d'entrée UNIQUE pour résoudre le fournisseur IA actif. Changer de
fournisseur (OpenAI/Gemini/DeepSeek/Qwen/Llama/OpenRouter/LM Studio/API perso)
= ajouter une entrée à PROVIDERS + une classe dans webapp/chatbot/providers/,
puis changer CHATBOT_PROVIDER (ou le réglage utilisateur "provider") — jamais
toucher au reste de la chaîne (conversation_manager, prompt_builder, routes
Flask). FakeProvider (aucune API, réponses assemblées depuis les cours
NovaMath via le Knowledge Engine) est le fournisseur par défaut aujourd'hui.
Anthropic (API officielle Claude) et Ollama (modèle local) restent
disponibles en option, sélectionnables sans aucun changement de code.
"""
import os

from .providers.anthropic_provider import AnthropicProvider
from .providers.fake_provider import FakeProvider
from .providers.ollama_provider import OllamaProvider

PROVIDERS = {
    "fake": FakeProvider,
    "ollama": OllamaProvider,
    "anthropic": AnthropicProvider,
}

# Catalogue statique de secours, utilisé si le provider ne peut pas détecter
# ses modèles dynamiquement (ex: Ollama arrêté) — voir available_models().
MODELS = {
    "fake": {
        "moteur-novamath": "Moteur NovaMath (sans IA, par défaut)",
    },
    "ollama": {
        "mistral": "Mistral (par défaut)",
    },
    "anthropic": {
        "claude-sonnet-5": "Claude Sonnet 5 (équilibré)",
        "claude-opus-4-8": "Claude Opus 4.8 (le plus capable)",
        "claude-haiku-4-5-20251001": "Claude Haiku 4.5 (le plus rapide)",
    },
}

_instance_cache = {}


def active_provider_name(override=None):
    return override or os.environ.get("CHATBOT_PROVIDER", "fake")


def get_provider(provider=None, model=None):
    name = active_provider_name(provider)
    provider_cls = PROVIDERS.get(name)
    if provider_cls is None:
        raise RuntimeError(f"Fournisseur IA inconnu : {name}")
    cache_key = (name, model)
    if cache_key not in _instance_cache:
        _instance_cache[cache_key] = provider_cls(model=model)
    return _instance_cache[cache_key]


def available_models(provider=None):
    """Modèles disponibles pour le fournisseur actif : détection dynamique
    en priorité (ex: modèles réellement installés dans Ollama via /api/tags),
    repli sur le catalogue statique MODELS si la détection échoue ou ne
    retourne rien (fournisseur arrêté, catalogue non applicable...)."""
    name = active_provider_name(provider)
    try:
        detected = get_provider(provider=name).available_models()
    except Exception:
        detected = {}
    return detected or MODELS.get(name, {})


def health_check(provider=None):
    name = active_provider_name(provider)
    try:
        return {"provider": name, **get_provider(provider=name).health()}
    except Exception as exc:
        return {"provider": name, "ok": False, "detail": str(exc)}
