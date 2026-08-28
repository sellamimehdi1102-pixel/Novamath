"""
Service en lecture seule pour la page "Gestion des utilisateurs"
(/admin/users) — aucune écriture, aucune action destructive (pas de
suppression, modification, suspension, réinitialisation, changement
d'abonnement ou de rôle : tout cela est explicitement hors périmètre de ce
chantier).

Architecture stricte, identique au reste du projet :

    server.py  →  admin_users_service.py  →  db.py

jamais l'inverse. Ce module ne dépend ni de Flask ni de rôles/permissions
(déjà tranchés par role_service.py au niveau de la route, jamais recontrôlés
ici) — voir server.py::api_admin_users.

── "Classe" (colonne supprimée) ─────────────────────────────────────────────
NovaMath ne persiste aujourd'hui AUCUNE classe par utilisateur en base (la
classe active est résolue par requête, jamais stockée sur la ligne `users` —
voir webapp/chatbot/student_context_resolver.py). Une colonne "Classe"
existait ici mais restait structurellement vide à 100 % des cas : supprimée
(chantier de simplification du panneau admin) plutôt que de rester affichée
comme "Aucune donnée disponible" en permanence.

── account_status (filtre "Statut") ────────────────────────────────────────
Il n'existe pas de mécanisme de suspension dédié dans NovaMath : le filtre
réutilise la colonne réelle `users.account_status` (déjà écrite par
consent_service.py — SEC-04), dont les 3 valeurs possibles sont 'active',
'pending_parental_consent' et 'parental_consent_refused'.

Avant le Chantier Administrateur "Utilisateurs" (Phase 2), ce filtre
regroupait les 2 dernières valeurs sous un bucket générique "Suspendu" — masquant
la distinction "en attente d'action du parent" vs "consentement explicitement
refusé", pourtant utile pour prioriser (voir l'alerte "consentements
parentaux en attente" du Dashboard, qui compte spécifiquement
'pending_parental_consent'). Le filtre expose désormais les 3 valeurs
réelles telles quelles, sans reconstruction.

── payment_status (filtre "Paiement en échec") ─────────────────────────────
Réutilise `users.stripe_subscription_status` (écrite par
stripe_webhook_service.py/billing_service.py) — une donnée INDÉPENDANTE de
`plan` et de `account_status` (voir _validate_payment_status). Seule valeur
acceptée : "failed", qui sélectionne 'past_due'/'unpaid' — mêmes 2 statuts que
l'alerte "paiements en échec" du Dashboard (admin_dashboard_service.
count_users_with_failed_payment), pour que la même définition de "paiement en
échec" soit utilisée partout dans l'admin.
"""
import db
from role_service import Role
from plan_service import Plan

PAGE_SIZE_DEFAULT = 25
PAGE_SIZE_MAX = 100

# Whitelist stricte des colonnes triables — jamais une chaîne du client
# injectée directement dans la clause SQL ORDER BY (voir db.list_users_admin).
_SORT_COLUMNS = {
    "pseudo": "pseudo",
    "email": "email",
    "plan": "plan",
    "role": "role",
    "last_login_at": "last_login_at",
    "created_at": "created_at",
    "total_time_s": "total_time_s",
}

_VALID_ROLES = {r.value for r in Role}
_VALID_PLANS = {p.value for p in Plan}
_VALID_ACCOUNT_STATUSES = {"active", "pending_parental_consent", "parental_consent_refused"}
_VALID_PAYMENT_STATUSES = {"failed"}


def _clean_sort(sort_by, sort_dir):
    column = _SORT_COLUMNS.get(sort_by, _SORT_COLUMNS["created_at"])
    direction = "ASC" if str(sort_dir).lower() == "asc" else "DESC"
    return column, direction


def _clean_page(page, page_size):
    try:
        page = max(1, int(page))
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = int(page_size)
    except (TypeError, ValueError):
        page_size = PAGE_SIZE_DEFAULT
    page_size = max(1, min(page_size, PAGE_SIZE_MAX))
    return page, page_size


def _serialize_user(row):
    return {
        "id": row["id"],
        "name": row["pseudo"],
        "email": row["email"],
        "avatar": row["avatar"],
        "plan": row["plan"],
        "role": row["role"],
        # Valeur réelle telle quelle (3 valeurs possibles, voir
        # _VALID_ACCOUNT_STATUSES) — plus de reconstruction "active"/
        # "suspended" (Chantier Administrateur "Utilisateurs", Phase 2).
        "account_status": row["account_status"],
        "last_login_at": row["last_login_at"],
        "created_at": row["created_at"],
        "total_time_s": row["total_time_s"],
    }


def list_users(search=None, role=None, plan=None, account_status=None, payment_status=None,
                sort_by="created_at", sort_dir="desc", page=1, page_size=PAGE_SIZE_DEFAULT):
    """CRM utilisateur en lecture seule — recherche/filtres/tri appliqués en
    SQL (LIMIT/OFFSET), jamais en mémoire côté Python, pour rester performant
    quel que soit le nombre de comptes (voir db.list_users_admin)."""
    search = (search or "").strip() or None
    role = role if role in _VALID_ROLES else None
    plan = plan if plan in _VALID_PLANS else None
    account_status = account_status if account_status in _VALID_ACCOUNT_STATUSES else None
    payment_status = payment_status if payment_status in _VALID_PAYMENT_STATUSES else None

    column, direction = _clean_sort(sort_by, sort_dir)
    page, page_size = _clean_page(page, page_size)
    offset = (page - 1) * page_size

    total = db.count_users_admin(search=search, role=role, plan=plan, account_status=account_status, payment_status=payment_status)
    rows = db.list_users_admin(
        search=search, role=role, plan=plan, account_status=account_status, payment_status=payment_status,
        sort_by=column, sort_dir=direction, limit=page_size, offset=offset,
    )

    total_pages = max(1, (total + page_size - 1) // page_size)
    return {
        "items": [_serialize_user(r) for r in rows],
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
    }
