"""
Service du "Journal d'administration" (/admin/journal) — historique COMPLET
et INDÉPENDANT de chaque action effectuée depuis les panneaux
d'administration IA (création/modification/suppression/activation/
désactivation/réordonnancement de priorité/abonnements IA/test/health-check)
ET Abonnements (modification du catalogue/activation-désactivation d'un
plan) — voir ACTIONS ci-dessous pour la liste complète. Écrit et lit
EXCLUSIVEMENT la table ai_admin_log via db.py. Le nom du module/de la table
("ai_admin_log") est un héritage historique (créé pour le module IA en
premier) : ce journal est désormais le journal d'administration générique du
projet, réutilisé tel quel par tout nouveau module plutôt que d'en dupliquer
un second (voir admin_subscriptions_service.py).

Architecture stricte, identique au reste du projet :

    server.py / admin_ai_service.py / admin_subscriptions_service.py
        →  admin_ai_log_service.py  →  db.py

jamais l'inverse. Ce module n'importe RIEN de webapp/chatbot/ ni de
provider_manager.py : il ne fait qu'enregistrer/lire des événements déjà
survenus, ailleurs — il n'a AUCUNE influence sur le chatbot, ni sur la
logique de sélection de fournisseur, ni sur aucun provider, ni sur Stripe.
Le supprimer entièrement ne changerait strictement rien au fonctionnement du
chatbot ni de la facturation.

── Écriture ─────────────────────────────────────────────────────────────────
record() effectue UN SEUL INSERT atomique (voir db.create_ai_admin_log) —
jamais un enregistrement partiel. Appelée exclusivement par les fonctions
"*_logged" de admin_ai_service.py/admin_subscriptions_service.py, jamais
directement par server.py, pour que la correspondance action <-> entrée de
journal reste centralisée à un seul endroit par module.

── Lecture ──────────────────────────────────────────────────────────────────
Recherche/filtres/pagination appliqués en SQL (LIMIT/OFFSET), jamais en
mémoire côté Python — même politique que admin_users_service.py.
`provider_id`/`provider_name` désignent, historiquement, un fournisseur IA —
admin_subscriptions_service.py les réutilise comme pointeur générique vers
"la ressource concernée" (provider_id=None, provider_name="Abonnement
<plan>") plutôt que d'ajouter une colonne dédiée pour un seul module de
plus."""
import csv
import io
import json

import db

PAGE_SIZE_DEFAULT = 25
PAGE_SIZE_MAX = 100

# Le plafond dur d'un export vit dans db._AI_ADMIN_LOG_EXPORT_LIMIT (10000,
# appliqué par list_ai_admin_log_for_export) — la constante MAX_EXPORT_ROWS
# qui existait ici en doublon documentaire n'était jamais lue par aucun code
# (chantier de simplification du panneau admin), retirée.

# Whitelist stricte des actions journalisées — reprise EXACTEMENT par
# admin_ai_service.py (voir ses fonctions "*_logged"), jamais une chaîne
# libre construite ailleurs.
ACTIONS = (
    "create_provider",
    "update_provider",
    "delete_provider",
    "enable_provider",
    "disable_provider",
    "reorder_priority",
    "update_subscription",
    "health_check",
    "test_connection",
    "update_plan",
    "enable_plan",
    "disable_plan",
    "create_api_key",
    "update_api_key",
    "delete_api_key",
    "test_api_key",
    "update_setting",
    "test_smtp",
    "create_backup",
    "restore_backup",
    "delete_backup",
    "analytics_export_csv",
    "analytics_export_excel",
    "analytics_export_pdf",
    "analytics_report",
)

ACTION_LABELS = {
    "create_provider": "Création d'un fournisseur",
    "update_provider": "Modification d'un fournisseur",
    "delete_provider": "Suppression d'un fournisseur",
    "enable_provider": "Activation d'un fournisseur",
    "disable_provider": "Désactivation d'un fournisseur",
    "reorder_priority": "Changement de priorité",
    "update_subscription": "Modification des abonnements",
    "update_plan": "Modification d'un abonnement",
    "enable_plan": "Activation d'un abonnement",
    "disable_plan": "Désactivation d'un abonnement",
    "health_check": "Health-check",
    "test_connection": "Test de connexion",
    "create_api_key": "Ajout d'une clé API",
    "update_api_key": "Modification d'une clé API",
    "delete_api_key": "Suppression d'une clé API",
    "test_api_key": "Test d'une clé API",
    "update_setting": "Modification d'un paramètre",
    "test_smtp": "Test d'envoi SMTP",
    "create_backup": "Création d'une sauvegarde",
    "restore_backup": "Restauration d'une sauvegarde",
    "delete_backup": "Suppression d'une sauvegarde",
    "analytics_export_csv": "Export Analytics (CSV)",
    "analytics_export_excel": "Export Analytics (Excel)",
    "analytics_export_pdf": "Export Analytics (PDF)",
    "analytics_report": "Génération d'un rapport Analytics",
}

_RESULTS = ("success", "error")

_EXPORT_COLUMNS = (
    "id", "created_at", "admin_name", "admin_role", "ip", "action",
    "provider_name", "result", "error_message", "old_values", "new_values",
)


def record(actor, action, provider_id=None, provider_name=None,
           old_values=None, new_values=None, result="success", error_message=None):
    """Enregistre UN événement. `actor` : dict {"id", "name", "role", "ip"}
    résolu par l'appelant (voir server.py::_admin_actor) — ce module ne
    dépend jamais de role_service.py ni de Flask, il reçoit des valeurs déjà
    résolues, comme le fait le reste de l'architecture (ex: ai_provider_
    service.py qui ignore plan_service.py). `actor` peut être vide/None de
    façon strictement défensive (ne devrait jamais arriver, ces actions
    exigent déjà @login_required) : l'entrée est alors écrite avec un
    administrateur "inconnu", jamais perdue silencieusement.

    `old_values`/`new_values` : dict JSON-sérialisables ou None — sérialisés
    ici (jamais par l'appelant), pour que ce module reste le seul point qui
    connaît le format de stockage réel de la colonne."""
    actor = actor or {}
    db.create_ai_admin_log(
        admin_user_id=actor.get("id"),
        admin_name=actor.get("name") or "Administrateur inconnu",
        admin_role=actor.get("role") or "inconnu",
        ip=actor.get("ip"),
        action=action,
        provider_id=provider_id,
        provider_name=provider_name,
        old_values=json.dumps(old_values, ensure_ascii=False) if old_values is not None else None,
        new_values=json.dumps(new_values, ensure_ascii=False) if new_values is not None else None,
        result=result if result in _RESULTS else "error",
        error_message=error_message,
    )


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


def _clean_filters(search, admin_user_id, provider_id, action, result, date_from, date_to):
    search = (search or "").strip() or None
    try:
        admin_user_id = int(admin_user_id) if admin_user_id not in (None, "") else None
    except (TypeError, ValueError):
        admin_user_id = None
    try:
        provider_id = int(provider_id) if provider_id not in (None, "") else None
    except (TypeError, ValueError):
        provider_id = None
    action = action if action in ACTIONS else None
    result = result if result in _RESULTS else None
    # Bornes de date au format ISO 8601 (YYYY-MM-DD ou datetime complet) —
    # comparaison texte directe, valide car created_at est toujours stocké en
    # ISO 8601 UTC (voir db._now()) : l'ordre lexicographique d'une chaîne
    # ISO 8601 correspond exactement à l'ordre chronologique.
    date_from = (date_from or "").strip() or None
    date_to = (date_to or "").strip() or None
    if date_to and len(date_to) == 10:  # "YYYY-MM-DD" -> borne haute incluse jusqu'à 23:59:59
        date_to = f"{date_to}T23:59:59.999999+00:00"
    return search, admin_user_id, provider_id, action, result, date_from, date_to


def _serialize_entry(row):
    return {
        "id": row["id"],
        "created_at": row["created_at"],
        "admin": {"id": row["admin_user_id"], "name": row["admin_name"], "role": row["admin_role"]},
        "ip": row["ip"],
        "action": row["action"],
        "action_label": ACTION_LABELS.get(row["action"], row["action"]),
        # `provider_id` est None pour une action au niveau d'un abonnement
        # (voir admin_ai_service.set_subscription_providers_logged), qui
        # renseigne alors uniquement `provider_name` (ex: "Abonnement free") —
        # le bloc "provider" doit donc apparaître dès que L'UN des deux est
        # renseigné, jamais seulement quand provider_id est non NULL.
        "provider": {"id": row["provider_id"], "name": row["provider_name"]}
        if (row["provider_id"] is not None or row["provider_name"]) else None,
        "old_values": json.loads(row["old_values"]) if row["old_values"] else None,
        "new_values": json.loads(row["new_values"]) if row["new_values"] else None,
        "result": row["result"],
        "error_message": row["error_message"],
    }


def list_log(search=None, admin_user_id=None, provider_id=None, action=None, result=None,
             date_from=None, date_to=None, page=1, page_size=PAGE_SIZE_DEFAULT, provider_name=None):
    """Historique paginé, filtré en SQL — voir _clean_filters pour la
    validation stricte de chaque paramètre (whitelist action/result, entiers
    pour les ids, jamais une valeur brute injectée dans une requête).
    `provider_name` (égalité exacte) : réservé aux appels internes de
    confiance (ex: admin_subscriptions_service.py, jamais une entrée HTTP
    brute) — non validé par _clean_filters, transmis tel quel à db.py."""
    search, admin_user_id, provider_id, action, result, date_from, date_to = _clean_filters(
        search, admin_user_id, provider_id, action, result, date_from, date_to,
    )
    page, page_size = _clean_page(page, page_size)
    offset = (page - 1) * page_size

    total = db.count_ai_admin_log(
        search=search, admin_user_id=admin_user_id, provider_id=provider_id,
        action=action, result=result, date_from=date_from, date_to=date_to, provider_name=provider_name,
    )
    rows = db.list_ai_admin_log(
        search=search, admin_user_id=admin_user_id, provider_id=provider_id,
        action=action, result=result, date_from=date_from, date_to=date_to,
        limit=page_size, offset=offset, provider_name=provider_name,
    )
    total_pages = max(1, (total + page_size - 1) // page_size)
    return {
        "items": [_serialize_entry(r) for r in rows],
        "page": page, "page_size": page_size, "total": total, "total_pages": total_pages,
    }


def list_filters():
    """Options réellement présentes dans le journal, pour peupler les menus
    déroulants "Administrateur"/"Fournisseur" côté frontend sans jamais lister
    un compte ou un fournisseur qui n'apparaît nulle part dans l'historique."""
    return {
        "admins": [{"id": r["admin_user_id"], "name": r["admin_name"]} for r in db.list_ai_admin_log_distinct_admins()],
        "providers": [{"id": r["provider_id"], "name": r["provider_name"]} for r in db.list_ai_admin_log_distinct_providers()],
        "actions": [{"value": a, "label": ACTION_LABELS[a]} for a in ACTIONS],
    }


def _export_rows(search, admin_user_id, provider_id, action, result, date_from, date_to):
    search, admin_user_id, provider_id, action, result, date_from, date_to = _clean_filters(
        search, admin_user_id, provider_id, action, result, date_from, date_to,
    )
    return db.list_ai_admin_log_for_export(
        search=search, admin_user_id=admin_user_id, provider_id=provider_id,
        action=action, result=result, date_from=date_from, date_to=date_to,
    )


def export_json(search=None, admin_user_id=None, provider_id=None, action=None, result=None,
                 date_from=None, date_to=None):
    """Renvoie la liste sérialisée (même format que list_log()["items"]),
    plafonnée à MAX_EXPORT_ROWS — jamais un export illimité en mémoire."""
    rows = _export_rows(search, admin_user_id, provider_id, action, result, date_from, date_to)
    return [_serialize_entry(r) for r in rows]


def export_csv(search=None, admin_user_id=None, provider_id=None, action=None, result=None,
                date_from=None, date_to=None):
    """Renvoie le contenu CSV (texte) prêt à être servi tel quel — colonnes
    fixes (voir _EXPORT_COLUMNS), old_values/new_values réencodés en JSON
    compact dans leur propre colonne (jamais éclatés en colonnes dynamiques,
    qui varieraient selon l'action)."""
    rows = _export_rows(search, admin_user_id, provider_id, action, result, date_from, date_to)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(_EXPORT_COLUMNS)
    for row in rows:
        writer.writerow([row[col] if row[col] is not None else "" for col in _EXPORT_COLUMNS])
    return buffer.getvalue()
