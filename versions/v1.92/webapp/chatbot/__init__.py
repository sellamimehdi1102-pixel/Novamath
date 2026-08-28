"""
Module Chatbot pédagogique NovaMath.

Architecture en couches (Frontend -> Conversation Manager -> Prompt Builder ->
Context Builder -> Rule Engine -> Provider Manager -> Provider -> API) :
chaque couche ne connaît que celle immédiatement en dessous, ce qui permet de
changer de fournisseur IA (provider_manager.py) ou d'enrichir la logique
interne (rule_engine.py, à terme un Math Engine/RAG Engine) sans jamais
toucher au reste de la chaîne.
"""
