"""
Source unique de vérité des quotas d'utilisation (limitations numériques
quotidiennes) pour NovaMath.

Architecture stricte, identique à plan_service.py :

    server.py  →  quota_service.py  →  db.py

jamais l'inverse. Ce module :
- reçoit un `user` déjà chargé (même convention que plan_service.py — aucune
  requête SQL sur la table `users` ici, uniquement des lectures/écritures sur
  `user_daily_usage` via db.py) ;
- est indépendant de Stripe : ne lit jamais les tables/webhooks Stripe, se
  contente d'utiliser plan_service.get_plan(user) pour connaître le palier ;
- est indépendant du chatbot : aucun compteur n'est géré dans
  webapp/chatbot/ — toute limitation, présente ou future, passe par ici.

Le plan (Plan.FREE/PREMIUM/ULTRA, voir plan_service.py) fixe la limite
quotidienne de chaque QuotaType via QUOTA_MATRIX, seule source de vérité des
valeurs numériques — ne jamais coder une limite ailleurs dans le projet.

Branché sur le chatbot (QuotaType.CHAT_MESSAGES — voir
chatbot/conversation_manager.py::check_and_increment_quota, seul point
d'envoi d'un message réel au moteur IA) et exposé en lecture via
GET /api/quota (usage_snapshot_all, voir server.py). Les autres QuotaType
(PDF_ANALYSIS, AI_GENERATIONS, CUSTOM_EXERCISES, EXPORTS) restent prêts mais
non consommés par aucune route à ce jour — les brancher se fait à l'identique
(consume() + peek_exceeded() au point d'entrée concerné), sans toucher à ce
module.
"""
import logging
from datetime import datetime, timezone
from enum import Enum

import db
from plan_service import Plan, get_plan

logger = logging.getLogger("quota_service")


class QuotaType(Enum):
    CHAT_MESSAGES = "chat_messages"
    PDF_ANALYSIS = "pdf_analysis"
    AI_GENERATIONS = "ai_generations"
    CUSTOM_EXERCISES = "custom_exercises"
    EXPORTS = "exports"


# None = illimité (palier Ultra). Jamais 0 pour signifier "illimité" — 0 est
# une vraie limite (aucun accès, ex: PDF_ANALYSIS/CUSTOM_EXERCISES/EXPORTS en
# Free), None est l'absence de limite, sémantique volontairement distincte.
UNLIMITED = None

# ── Matrice centralisée ──────────────────────────────────────────────────────
# Unique endroit du projet qui connaît la limite quotidienne d'un quota pour
# un palier donné. Ne jamais dupliquer ces valeurs ailleurs (routes, chatbot,
# frontend) — toujours lire via get_limit()/QUOTA_MATRIX.
QUOTA_MATRIX = {
    Plan.FREE: {
        QuotaType.CHAT_MESSAGES: 25,
        QuotaType.PDF_ANALYSIS: 0,
        QuotaType.AI_GENERATIONS: 20,
        QuotaType.CUSTOM_EXERCISES: 0,
        QuotaType.EXPORTS: 0,
    },
    Plan.PREMIUM: {
        QuotaType.CHAT_MESSAGES: 250,
        QuotaType.PDF_ANALYSIS: 25,
        QuotaType.AI_GENERATIONS: 500,
        QuotaType.CUSTOM_EXERCISES: 100,
        QuotaType.EXPORTS: 20,
    },
    Plan.ULTRA: {
        QuotaType.CHAT_MESSAGES: UNLIMITED,
        QuotaType.PDF_ANALYSIS: UNLIMITED,
        QuotaType.AI_GENERATIONS: UNLIMITED,
        QuotaType.CUSTOM_EXERCISES: UNLIMITED,
        QuotaType.EXPORTS: UNLIMITED,
    },
}

# Ordre croissant des paliers — sert à proposer le palier suivant qui offre
# davantage sur un quota donné (même principe que plan_service._PLAN_ORDER).
_PLAN_ORDER = (Plan.FREE, Plan.PREMIUM, Plan.ULTRA)


class QuotaExceededError(Exception):
    """Levée par consume() quand la consommation demandée dépasserait la
    limite quotidienne. Réutilisable partout dans le projet (routes futures,
    chatbot) pour un traitement uniforme — jamais reconstruite ad hoc.

    Attributs :
        quota (QuotaType)     — le quota concerné.
        remaining (int)       — unités restantes au moment du refus (0 ici,
                                 puisque la demande a été refusée).
        limit (int)           — limite quotidienne du palier actuel.
        required_plan (Plan)  — palier le moins élevé qui débloquerait plus
                                 (typiquement le palier suivant)."""

    def __init__(self, quota, remaining, limit, required_plan):
        self.quota = quota
        self.remaining = remaining
        self.limit = limit
        self.required_plan = required_plan
        super().__init__(
            f"Quota {quota.value!r} dépassé ({remaining}/{limit} restant(s) aujourd'hui) — "
            f"passe à {required_plan.value} pour augmenter cette limite."
        )


def _today():
    """Date du jour en UTC, format ISO YYYY-MM-DD — même fuseau que le reste
    du projet (voir db.py::_now, en UTC également)."""
    return datetime.now(timezone.utc).date().isoformat()


def _next_plan_with_more(current_plan, quota):
    """Palier le moins élevé, strictement après `current_plan`, qui offre une
    limite plus généreuse (ou illimitée) sur `quota`. Reste correct même si
    QUOTA_MATRIX venait à être modifiée de façon non strictement croissante :
    ne suppose jamais que "le palier suivant" est automatiquement meilleur,
    le vérifie explicitement."""
    current_limit = QUOTA_MATRIX[current_plan][quota]
    idx = _PLAN_ORDER.index(current_plan)
    for plan in _PLAN_ORDER[idx + 1:]:
        limit = QUOTA_MATRIX[plan][quota]
        if limit is None or (current_limit is not None and limit > current_limit):
            return plan
    # Déjà au palier le plus élevé (ou aucun palier supérieur n'offre plus) :
    # ne devrait pas arriver en pratique (Ultra est toujours illimité, donc
    # consume() ne lève jamais QuotaExceededError pour un utilisateur Ultra),
    # mais on renvoie tout de même le palier le plus élevé plutôt que lever
    # une exception dans une exception.
    return _PLAN_ORDER[-1]


def get_limit(user, quota):
    """Limite quotidienne de `quota` pour le palier de `user`, ou None si
    illimité (palier Ultra)."""
    plan = get_plan(user)
    return QUOTA_MATRIX[plan][quota]


def is_unlimited(user, quota):
    """True si `user` n'a aucune limite numérique sur `quota` aujourd'hui."""
    return get_limit(user, quota) is None


def get_usage(user, quota, day=None):
    """Unités de `quota` déjà consommées par `user` à `day` (aujourd'hui par
    défaut, format ISO YYYY-MM-DD). 0 si aucune ligne n'existe encore — pas
    encore consommé aujourd'hui, ou nouveau jour : la réinitialisation est
    implicite (une nouvelle date = une nouvelle ligne, voir db.py::SCHEMA),
    jamais une tâche de purge séparée à appeler."""
    day = day or _today()
    return db.get_daily_usage(user["id"], quota.value, day)


def get_remaining(user, quota, day=None):
    """Unités de `quota` encore consommables par `user` à `day` (aujourd'hui
    par défaut), ou None si illimité. Ne descend jamais sous 0."""
    limit = get_limit(user, quota)
    if limit is None:
        return None
    return max(0, limit - get_usage(user, quota, day))


def can_consume(user, quota, amount=1, day=None):
    """True si `user` peut consommer `amount` unités de `quota` sans dépasser
    sa limite quotidienne (toujours True si illimité).

    Fonction de lecture seule, destinée à un aperçu (ex: afficher "3 messages
    restants" côté client) — ne réserve rien. Un appel à can_consume() suivi
    d'un consume() séparé n'est PAS garanti atomique sous accès concurrents
    (fenêtre entre les deux appels) : pour l'enforcement réel, appeler
    consume() directement et intercepter QuotaExceededError, jamais
    can_consume() seul comme garde-fou."""
    limit = get_limit(user, quota)
    if limit is None:
        return True
    return get_usage(user, quota, day) + amount <= limit


def reset_if_needed(user, quota):
    """Garantit qu'une ligne d'usage existe pour `user`/`quota`/aujourd'hui,
    en la créant à 0 si absente (idempotent, voir db.py::ensure_daily_usage_row).
    N'est PAS un prérequis avant get_usage/get_remaining/consume (qui gèrent
    déjà l'absence de ligne) — utile pour un appelant qui veut garantir
    explicitement l'existence de la ligne du jour avant de la lire directement
    en base (ex: un futur tableau de bord d'usage agrégé). Renvoie l'usage
    courant après coup (0 si la ligne vient d'être créée)."""
    day = _today()
    db.ensure_daily_usage_row(user["id"], quota.value, day)
    return get_usage(user, quota, day)


def consume(user, quota, amount=1):
    """Consomme `amount` unités de `quota` pour `user` aujourd'hui et renvoie
    le nouveau total consommé. Lève QuotaExceededError si la limite du palier
    actuel serait dépassée — dans ce cas, RIEN n'est facturé (voir ci-dessous).

    Transactionnel et robuste aux appels concurrents sans verrou applicatif :
    l'incrément est posé d'abord via une unique opération SQL atomique
    (db.increment_daily_usage, UPSERT SQLite — voir db.py), puis le nouveau
    total est comparé à la limite. S'il la dépasse, l'incrément qui vient
    d'être posé est immédiatement annulé par un décrément tout aussi atomique
    avant de lever l'exception : jamais de lire-puis-écrire séparé qui
    laisserait une fenêtre à un appel concurrent, et jamais de dépassement
    facturé au-delà de la limite même si plusieurs requêtes arrivent en même
    temps pile à la limite."""
    if is_unlimited(user, quota):
        return db.increment_daily_usage(user["id"], quota.value, _today(), amount)

    day = _today()
    limit = get_limit(user, quota)
    new_count = db.increment_daily_usage(user["id"], quota.value, day, amount)
    if new_count > limit:
        db.increment_daily_usage(user["id"], quota.value, day, -amount)
        err = _build_exceeded_error(user, quota)
        logger.info(
            "Quota %s dépassé pour l'utilisateur %s (limite %s/jour).",
            quota.value, user["id"], limit,
        )
        raise err
    return new_count


def _build_exceeded_error(user, quota):
    """Construit (sans la lever) la QuotaExceededError décrivant l'état
    actuel de `quota` pour `user` — factorisé pour être utilisé à la fois par
    consume() (qui la lève réellement après un dépassement constaté) et par
    peek_exceeded() (contrôle en lecture seule, mêmes informations, sans rien
    consommer)."""
    return QuotaExceededError(
        quota=quota,
        remaining=get_remaining(user, quota) or 0,
        limit=get_limit(user, quota),
        required_plan=_next_plan_with_more(get_plan(user), quota),
    )


def peek_exceeded(user, quota):
    """Contrôle en lecture seule : renvoie une QuotaExceededError décrivant
    le dépassement si `user` a déjà atteint sa limite quotidienne de `quota`,
    sans rien consommer ; None si de la marge reste disponible (ou si
    illimité). Utilisé pour répondre par un vrai code HTTP 429 AVANT
    d'ouvrir un flux SSE (dont le code HTTP ne peut plus changer une fois les
    en-têtes envoyés, voir server.py) — l'enforcement réel et autoritaire
    reste consume(), seule fonction qui consomme effectivement."""
    if can_consume(user, quota):
        return None
    return _build_exceeded_error(user, quota)


def exceeded_error_payload(err):
    """Traduit une QuotaExceededError en dict JSON-sérialisable, au format
    429 attendu par le frontend (voir api.js/abonnement.js) :

        {"error": "quota_exceeded", "quota": "...", "remaining": 0,
         "limit": 25, "required_plan": "premium"}

    `required_plan` est None si err.required_plan est absent (ne devrait pas
    arriver en pratique : consume()/peek_exceeded() ne lèvent jamais pour un
    palier déjà illimité, donc il existe toujours un palier supérieur à
    proposer) — gardé par robustesse plutôt que par nécessité observée."""
    return {
        "error": "quota_exceeded",
        "quota": err.quota.value,
        "remaining": err.remaining,
        "limit": err.limit,
        "required_plan": err.required_plan.value if err.required_plan else None,
    }


def usage_snapshot(user, quota):
    """Aperçu JSON-sérialisable de l'usage du jour pour `quota` :
        {"used": int, "remaining": int|None, "limit": int|None, "unlimited": bool}
    remaining/limit valent None quand illimité (palier Ultra) — jamais 0, qui
    signifierait à tort "plus aucune marge"."""
    limit = get_limit(user, quota)
    unlimited = limit is None
    return {
        "used": get_usage(user, quota),
        "remaining": None if unlimited else get_remaining(user, quota),
        "limit": limit,
        "unlimited": unlimited,
    }


def usage_snapshot_all(user):
    """usage_snapshot() pour chaque QuotaType, clé = quota.value — support de
    GET /api/quota (voir server.py). Un seul appel couvre tous les quotas
    actuels et futurs sans qu'il soit nécessaire de toucher à cette fonction
    lors de l'ajout d'un nouveau QuotaType."""
    return {quota.value: usage_snapshot(user, quota) for quota in QuotaType}
