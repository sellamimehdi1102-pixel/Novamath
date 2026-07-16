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

_store = OrderedDict()  # (user_id, provider, model, message_normalisé) -> réponse


def _normalize(message):
    return " ".join((message or "").strip().lower().split())


def make_key(user_id, provider, model, message):
    return (user_id, provider, model or "", _normalize(message))


def get(key):
    if key not in _store:
        return None
    _store.move_to_end(key)  # LRU : marquer comme récemment utilisé
    return _store[key]


def set(key, value):
    _store[key] = value
    _store.move_to_end(key)
    if len(_store) > MAX_ENTRIES:
        _store.popitem(last=False)
