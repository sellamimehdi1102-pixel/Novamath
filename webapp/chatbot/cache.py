"""
Cache mémoire simple pour les réponses du chatbot : si la même question est
reposée par le même utilisateur, avec le même fournisseur/modèle actif, la
réponse déjà générée est réutilisée immédiatement au lieu d'interroger de
nouveau le Knowledge/Retrieval Engine ou un futur fournisseur IA (latence
réseau, coût). Volontairement en mémoire process (pas de Redis ni de
persistance disque) : perdre le cache au redémarrage du serveur est sans
conséquence, ce n'est qu'une accélération.
"""
from collections import OrderedDict

MAX_ENTRIES = 200


def normalize_message(message):
    """Normalisation de message partagée par tous les caches mémoire du
    chatbot (clé insensible à la casse/aux espaces superflus) — réutilisée
    telle quelle par response_strategy.py plutôt que réimplémentée."""
    return " ".join((message or "").strip().lower().split())


class LRUCache:
    """Cache mémoire LRU borné générique (OrderedDict), réutilisable par tout
    module ayant besoin d'un cache process-local avec éviction — évite qu'un
    même mécanisme (move_to_end + popitem au dépassement) soit réimplémenté à
    chaque nouveau cache du chatbot."""

    def __init__(self, max_entries):
        self.max_entries = max_entries
        self._store = OrderedDict()

    def get(self, key):
        if key not in self._store:
            return None
        self._store.move_to_end(key)
        return self._store[key]

    def set(self, key, value):
        self._store[key] = value
        self._store.move_to_end(key)
        if len(self._store) > self.max_entries:
            self._store.popitem(last=False)

    def clear(self):
        self._store.clear()

    def __len__(self):
        return len(self._store)


_store = LRUCache(MAX_ENTRIES)  # (user_id, provider, model, message_normalisé) -> réponse


def make_key(user_id, provider, model, message, class_level=None, topic=None):
    """`topic` (optionnel, chapter_id résolu par intent_service.classify) :
    sans lui, un message ambigu ("réexplique", "encore"...) donnerait
    exactement la même clé de cache dans deux conversations différentes du
    même utilisateur, même si le Current Learning Context (voir
    conversation_manager.py) y désigne deux notions différentes — la réponse
    mise en cache pour l'une serait alors servie à tort dans l'autre."""
    return (user_id, provider, model or "", class_level or "seconde", normalize_message(message), topic or "")


def get(key):
    return _store.get(key)


def set(key, value):
    _store.set(key, value)


def clear():
    """Vide le cache — utilisé par les tests pour repartir d'un état connu
    (éviter qu'une réponse LLM mise en cache par un test ne soit réutilisée
    par un autre), jamais nécessaire en usage normal."""
    _store.clear()
