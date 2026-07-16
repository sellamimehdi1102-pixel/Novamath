"""
Point de sortie unique vers le fournisseur IA actif — Phase Q du chantier
v2.12 : le LLM ne doit plus être que le filet de sécurité, jamais le premier
réflexe (voir local_knowledge_service.py, interrogé en premier par
conversation_manager.py). Isole explicitement le seul module qu'un
changement de fournisseur IA (Claude, OpenAI, Mistral, Ollama, Gemini...)
doit impacter — provider_manager.py gère déjà le choix du fournisseur, ce
module se contente d'exposer un point d'appel nommé et stable.
"""
from .. import provider_manager


def generate(messages, system_prompt, chatbot_settings):
    """Générateur de fragments texte — délègue entièrement au fournisseur
    actif. Aucune logique métier ici : elle vit dans local_knowledge_service.py
    et dans le pipeline en amont de conversation_manager.py."""
    provider = provider_manager.get_provider(
        provider=chatbot_settings.get("provider"),
        model=chatbot_settings.get("model"),
    )
    yield from provider.stream_chat(
        messages,
        system_prompt,
        temperature=float(chatbot_settings.get("temperature", 0.6)),
    )
