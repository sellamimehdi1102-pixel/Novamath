"""
Service du module Administration -> Support (/admin/support) — gestion
complète des tickets de support : tableau (recherche/tri/filtres/pagination
déléguée au backend, même pattern que admin_users_service.py), fiche ticket
(conversation/pièces jointes/notes internes/historique/statut/assignation).

Architecture stricte, identique au reste du projet :

    server.py  →  support_service.py  →  db.py / support_attachment_service.py

jamais l'inverse. Ce module ne dépend ni de Flask ni de rôles/permissions
(déjà tranchés côté route, jamais recontrôlés ici).

── Origine des tickets ──────────────────────────────────────────────────────
Un ticket est TOUJOURS créé par un utilisateur réel (create_ticket(), appelée
par POST /api/support/tickets) — l'administration ne peut jamais fabriquer un
ticket depuis ce panneau, garantissant que chaque ligne du tableau reflète une
vraie demande.

(Les affichages "Vue d'ensemble" et "Tickets par catégorie" du panneau
Support ont été retirés — doublons du Dashboard/Analytics et des filtres du
tableau, voir chantier de simplification du panneau admin. overview_stats()
reste ici : elle est toujours utilisée par admin_analytics_service.py, JAMAIS
via une route HTTP dédiée au panneau Support.)
"""
import db

PAGE_SIZE_DEFAULT = 25
PAGE_SIZE_MAX = 100

CATEGORIES = ("bug", "paiement", "ia", "compte", "technique", "autre")
CATEGORY_LABELS = {
    "bug": "Bug", "paiement": "Paiement", "ia": "IA", "compte": "Compte",
    "technique": "Technique", "autre": "Autre",
}
PRIORITIES = ("faible", "normale", "haute", "urgente")
STATUSES = ("open", "in_progress", "closed")
STATUS_LABELS = {"open": "Ouvert", "in_progress": "En cours", "closed": "Fermé"}

_SORT_COLUMNS = {
    "created_at": "created_at",
    "updated_at": "updated_at",
    "last_response_at": "last_response_at",
    "priority": "priority",
    "status": "status",
    "category": "category",
}


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


def _serialize_ticket_row(row):
    return {
        "id": row["id"],
        "user_pseudo": row["user_pseudo"],
        "user_email": row["user_email"],
        "subject": row["subject"],
        "category": row["category"],
        "category_label": CATEGORY_LABELS.get(row["category"], row["category"]),
        "priority": row["priority"],
        "status": row["status"],
        "status_label": STATUS_LABELS.get(row["status"], row["status"]),
        "assigned_admin_name": row["assigned_admin_name"],
        "created_at": row["created_at"],
        "last_response_at": row["last_response_at"],
    }


def list_tickets(search=None, status=None, category=None, priority=None, assigned_admin_id=None,
                  sort_by="created_at", sort_dir="desc", page=1, page_size=PAGE_SIZE_DEFAULT):
    search = (search or "").strip() or None
    status = status if status in STATUSES else None
    category = category if category in CATEGORIES else None
    priority = priority if priority in PRIORITIES else None
    try:
        assigned_admin_id = int(assigned_admin_id) if assigned_admin_id else None
    except (TypeError, ValueError):
        assigned_admin_id = None

    column, direction = _clean_sort(sort_by, sort_dir)
    page, page_size = _clean_page(page, page_size)
    offset = (page - 1) * page_size

    total = db.count_support_tickets(
        search=search, status=status, category=category, priority=priority, assigned_admin_id=assigned_admin_id,
    )
    rows = db.list_support_tickets_admin(
        search=search, status=status, category=category, priority=priority, assigned_admin_id=assigned_admin_id,
        sort_by=column, sort_dir=direction, limit=page_size, offset=offset,
    )
    total_pages = max(1, (total + page_size - 1) // page_size)
    return {
        "items": [_serialize_ticket_row(r) for r in rows],
        "page": page, "page_size": page_size, "total": total, "total_pages": total_pages,
    }


# ── Création (utilisateur) ──────────────────────────────────────────────────
def create_ticket(user_id, subject, category, body, priority="normale"):
    subject = (subject or "").strip()
    body = (body or "").strip()
    if not subject or category not in CATEGORIES or not body:
        return None, "Sujet, catégorie et message sont obligatoires (catégorie invalide sinon)."
    if priority not in PRIORITIES:
        priority = "normale"
    ticket_id = db.create_support_ticket(user_id, subject, category, priority=priority)
    message_id = db.create_support_ticket_message(ticket_id, "user", user_id, body)
    message = db.get_support_ticket_message(message_id)
    db.update_support_ticket(ticket_id, last_response_at=message["created_at"])
    return ticket_id, None


def list_tickets_for_user(user_id):
    return db.list_support_tickets_for_user(user_id)


# ── Fiche ticket (admin ET utilisateur, selon l'appelant) ───────────────────
# `closed_at` n'est plus renvoyé ici (chantier de simplification du panneau
# admin) : jamais affiché côté frontend, et l'information est déjà visible
# via `history` (l'événement "status_changed" vers "closed" porte son propre
# horodatage) — un doublon inutile plutôt qu'un champ manquant.
# `first_admin_response_at` est désormais renvoyé (était produit par
# add_message() mais jamais relu) : affiché sur la fiche pour vérifier le
# délai de première réponse d'un ticket précis.
def get_ticket_detail(ticket_id):
    ticket = db.get_support_ticket(ticket_id)
    if ticket is None:
        return None
    messages = db.list_support_ticket_messages(ticket_id)
    message_ids = [m["id"] for m in messages]
    attachments = db.list_support_ticket_attachments_for_messages(message_ids)
    attachments_by_message = {}
    for att in attachments:
        attachments_by_message.setdefault(att["message_id"], []).append({
            "id": att["id"], "filename": att["original_filename"],
            "size_bytes": att["size_bytes"], "content_type": att["content_type"],
        })
    notes = db.list_support_ticket_notes(ticket_id)
    history = db.list_support_ticket_history(ticket_id)

    return {
        "id": ticket["id"],
        "user_id": ticket["user_id"],
        "user_pseudo": ticket["user_pseudo"],
        "user_email": ticket["user_email"],
        "subject": ticket["subject"],
        "category": ticket["category"],
        "category_label": CATEGORY_LABELS.get(ticket["category"], ticket["category"]),
        "priority": ticket["priority"],
        "status": ticket["status"],
        "status_label": STATUS_LABELS.get(ticket["status"], ticket["status"]),
        "assigned_admin_id": ticket["assigned_admin_id"],
        "assigned_admin_name": ticket["assigned_admin_name"],
        "created_at": ticket["created_at"],
        "updated_at": ticket["updated_at"],
        "first_admin_response_at": ticket["first_admin_response_at"],
        "satisfaction_rating": ticket["satisfaction_rating"],
        "messages": [
            {
                "id": m["id"], "author_type": m["author_type"], "author_id": m["author_id"],
                "body": m["body"], "created_at": m["created_at"],
                "attachments": attachments_by_message.get(m["id"], []),
            }
            for m in messages
        ],
        "notes": [
            {"id": n["id"], "admin_id": n["admin_id"], "body": n["body"], "created_at": n["created_at"]}
            for n in notes
        ],
        "history": [
            {
                "id": h["id"], "event_type": h["event_type"], "from_value": h["from_value"],
                "to_value": h["to_value"], "actor_admin_id": h["actor_admin_id"], "created_at": h["created_at"],
            }
            for h in history
        ],
    }


def add_message(ticket_id, author_type, author_id, body):
    body = (body or "").strip()
    if not body:
        return None, "Le message ne peut pas être vide."
    ticket = db.get_support_ticket(ticket_id)
    if ticket is None:
        return None, "Ticket introuvable."
    message_id = db.create_support_ticket_message(ticket_id, author_type, author_id, body)
    now = db.get_support_ticket_message(message_id)["created_at"]
    updates = {"last_response_at": now}
    if author_type == "admin" and ticket["first_admin_response_at"] is None:
        updates["first_admin_response_at"] = now
    db.update_support_ticket(ticket_id, **updates)
    return message_id, None


def add_attachment(message_id, original_filename, stored_path, size_bytes, content_type):
    return db.create_support_ticket_attachment(message_id, original_filename, stored_path, size_bytes, content_type)


def add_note(ticket_id, admin_id, body):
    body = (body or "").strip()
    if not body:
        return None, "La note ne peut pas être vide."
    if db.get_support_ticket(ticket_id) is None:
        return None, "Ticket introuvable."
    return db.create_support_ticket_note(ticket_id, admin_id, body), None


def change_status(ticket_id, new_status, actor_admin_id):
    if new_status not in STATUSES:
        return False, "Statut invalide."
    ticket = db.get_support_ticket(ticket_id)
    if ticket is None:
        return False, "Ticket introuvable."
    if ticket["status"] == new_status:
        return True, None
    updates = {"status": new_status}
    if new_status == "closed":
        updates["closed_at"] = db.get_support_ticket(ticket_id)["updated_at"]
    elif ticket["status"] == "closed":
        updates["closed_at"] = None  # réouverture : le ticket n'est plus "résolu"
    db.update_support_ticket(ticket_id, **updates)
    db.create_support_ticket_history_event(
        ticket_id, "status_changed", ticket["status"], new_status, actor_admin_id,
    )
    return True, None


def assign_admin(ticket_id, admin_id, actor_admin_id):
    ticket = db.get_support_ticket(ticket_id)
    if ticket is None:
        return False, "Ticket introuvable."
    if ticket["assigned_admin_id"] == admin_id:
        return True, None
    db.update_support_ticket(ticket_id, assigned_admin_id=admin_id)
    db.create_support_ticket_history_event(
        ticket_id, "assigned",
        str(ticket["assigned_admin_id"]) if ticket["assigned_admin_id"] else None,
        str(admin_id) if admin_id else None,
        actor_admin_id,
    )
    return True, None


def set_satisfaction_rating(ticket_id, user_id, rating):
    ticket = db.get_support_ticket(ticket_id)
    if ticket is None or ticket["user_id"] != user_id:
        return False, "Ticket introuvable."
    try:
        rating = int(rating)
    except (TypeError, ValueError):
        return False, "Note invalide."
    if rating < 1 or rating > 5:
        return False, "La note doit être comprise entre 1 et 5."
    db.update_support_ticket(ticket_id, satisfaction_rating=rating)
    return True, None


# ── Statistiques agrégées, utilisées uniquement par admin_analytics_service.py
# et admin_dashboard_service.py (aucune route HTTP dédiée au panneau Support
# ne les expose : la carte "Vue d'ensemble" a été retirée du panneau Support,
# doublon du Dashboard/Analytics).
#
# `today_count`/`week_count`/`month_count`/`avg_response_seconds`/
# `avg_resolution_seconds`/`resolution_rate_pct`/`avg_satisfaction_rating`/
# `satisfaction_ratings_count` ont été retirés (chantier de simplification du
# panneau admin) : grep exhaustif de tous les appelants (admin_analytics_
# service.py, admin_dashboard_service.py) confirme qu'AUCUN ne lit ces 8
# champs — seuls open_count/in_progress_count/closed_count/total_count le
# sont. Ces 8 champs faisaient exécuter 6 requêtes SQL réelles (dont 3 AVG)
# à chaque chargement du Dashboard/Analytics pour un résultat jamais
# consulté. Les recréer serait une nouvelle fonctionnalité (interdit par la
# consigne de fin de refonte) — voir db.support_tickets_overview_stats().
def overview_stats():
    stats = db.support_tickets_overview_stats()
    return {
        "open_count": stats["open_count"],
        "in_progress_count": stats["in_progress_count"],
        "closed_count": stats["closed_count"],
        "total_count": stats["total_count"],
    }


