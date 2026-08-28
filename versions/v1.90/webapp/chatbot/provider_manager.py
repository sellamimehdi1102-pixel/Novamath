"""
Point d'entrée UNIQUE pour résoudre le fournisseur IA actif. C'est une
décision interne à NovaMath, jamais un réglage utilisateur : changer de
fournisseur (OpenAI/Gemini/DeepSeek/Qwen/Llama/OpenRouter/LM Studio/API perso)
= ajouter une entrée à PROVIDERS + une classe dans webapp/chatbot/providers/,
puis changer la variable d'environnement CHATBOT_PROVIDER — jamais toucher au
reste de la chaîne (conversation_manager, prompt_builder, routes Flask), et
jamais exposer ce choix côté client. FakeProvider (aucune API, réponses
assemblées depuis les cours NovaMath via le Knowledge Engine) est le
fournisseur par défaut aujourd'hui. Anthropic (API officielle Claude), Gemini
(API officielle Google) et Ollama (modèle local) restent disponibles en
option côté serveur uniquement.
"""
import os

from .providers.anthropic_provider import AnthropicProvider
from .providers.fake_provider import FakeProvider
from .providers.gemini_provider import GeminiProvider
from .providers.ollama_provider import OllamaProvider

PROVIDERS = {
    "fake": FakeProvider,
    "ollama": OllamaProvider,
    "anthropic": AnthropicProvider,
    "gemini": GeminiProvider,
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
    # gemini-2.5-* renvoie une 404 "no longer available to new users" pour
    # toute clé API créée après leur dépréciation (vérifié par un appel réel) —
    # -flash-preview confirmé fonctionnel en conditions réelles ; -pro-preview
    # est listé par l'API mais a renvoyé un 429 RESOURCE_EXHAUSTED (quota
    # dépassé) lors du test réel : vérifier le palier de facturation Google AI
    # Studio du projet avant de l'utiliser en production.
    "gemini": {
        "gemini-3-flash-preview": "Gemini 3 Flash (rapide)",
        "gemini-3-pro-preview": "Gemini 3 Pro (le plus capable)",
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
