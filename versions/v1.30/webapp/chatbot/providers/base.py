"""
Contrat unique que tout fournisseur IA doit respecter. Le reste du code
(conversation_manager.py notamment) ne dépasse jamais cette interface : changer
de fournisseur (OpenAI, Gemini, DeepSeek, un serveur local...) revient à
écrire une nouvelle classe ici et à l'enregistrer dans provider_manager.py,
sans toucher à quoi que ce soit d'autre.
"""
from abc import ABC, abstractmethod


class ChatProvider(ABC):
    @abstractmethod
    def stream_chat(self, messages, system, temperature=0.7, max_tokens=1024):
        """Doit retourner un générateur de fragments de texte (str), au fil de
        l'arrivée de la réponse du modèle (streaming)."""
        raise NotImplementedError
