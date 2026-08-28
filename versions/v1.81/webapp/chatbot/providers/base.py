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

    def health(self):
        """Renvoie {"ok": bool, "detail": str}. Implémentation par défaut
        optimiste (providers cloud sans endpoint de santé dédié) — les
        providers locaux (Ollama) la redéfinissent avec un vrai test réseau."""
        return {"ok": True, "detail": ""}

    def available_models(self):
        """Dict {id_modele: libellé affichable}. Par défaut vide (le
        provider_manager retombe alors sur son propre catalogue statique)."""
        return {}

    def current_model(self):
        return getattr(self, "_model", None)

    def switch_model(self, model):
        """Change le modèle utilisé par cette instance sans recréer le
        provider. Par défaut, modifie simplement l'attribut interne."""
        self._model = model
