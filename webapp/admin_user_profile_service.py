"""
Service en lecture seule pour la fiche complète d'un utilisateur
(/admin/users/:id) — aucune écriture, aucune action destructive (pas de
suppression, suspension, modification, réinitialisation, changement de plan
ou de rôle : explicitement hors périmètre de ce chantier, comme pour
admin_users_service.py).

Architecture stricte, identique au reste du projet :

    server.py  →  admin_user_profile_service.py  →  db.py / auth.py

jamais l'inverse. Réutilise les fonctions de lecture déjà existantes plutôt
que d'en dupliquer la logique (auth.read_user_stats/read_user_course_progress
sont déjà importées de la même façon par webapp/chatbot/context_builder.py et
webapp/chatbot/student_context_resolver.py — précédent déjà établi dans ce
projet, pas une nouvelle convention).

── Politique "aucune donnée inventée" ──────────────────────────────────────
Identique à admin_dashboard_service.py/admin_users_service.py : chaque champ
qui n'a structurellement AUCUNE source de données renvoie
{"available": False, "value": None, "reason": "..."}, JAMAIS une valeur
fabriquée (0, chaîne vide, date factice). Un audit exhaustif du projet a
précédé ce chantier — chaque cas "available: False" ci-dessous est documenté
avec la raison EXACTE de l'absence (voir chaque constante *_UNAVAILABLE).

Une API indépendante par onglet (voir server.py) — chaque fonction ci-dessous
correspond exactement à UNE route, et ne lit que ce dont son onglet a besoin
(jamais un agrégat géant unique), pour permettre le lazy loading réel côté
frontend : ouvrir l'onglet "Cours" ne déclenche aucune lecture chatbot ni
stats, par exemple.
"""
from collections import Counter
from pathlib import Path
import json

import ai_request_log_service
import auth
import curriculum_registry
import db
import support_service
import two_factor_service

ROOT = Path(__file__).resolve().parent.parent
REVIEWS_PATH = ROOT / "data" / "reviews.json"


def _na(reason):
    return {"available": False, "value": None, "reason": reason}


def _ok(value):
    return {"available": True, "value": value}


NO_IP_DATA = _na("Aucun événement de sécurité avec adresse IP n'a encore été journalisé pour ce compte.")
AI_CONSUMPTION_EMPTY_MESSAGE = "Ce compte n'a encore jamais utilisé le chatbot (aucune réponse, locale ou LLM, ne lui a jamais été envoyée)."
NO_AI_REQUEST_DATA = _na(AI_CONSUMPTION_EMPTY_MESSAGE)
# "Classe", "Prénom/Nom", temps de lecture Cours/Apprentissage et "Date
# d'achat" ont été retirés de cette fiche (chantier de simplification du
# panneau admin) : ces champs étaient structurellement vides à 100 % des cas
# (aucune source de données n'existe), donc affichés en permanence comme
# "Aucune donnée disponible" — un placeholder permanent plutôt qu'une vraie
# information, désormais interdit (voir NO_PAYMENT_HISTORY précédemment ici).


def _user_row(user_id):
    return db.get_user_by_id(user_id)


# ── 1. Informations ──────────────────────────────────────────────────────
def get_profile(user_id):
    user = _user_row(user_id)
    if user is None:
        return None

    latest_ip = db.get_latest_ip_for_user(user_id)
    return {
        "id": user["id"],
        "avatar": user["avatar"],
        "pseudo": user["pseudo"],
        "email": user["email"],
        "plan": _ok(user["plan"]),
        "role": _ok(user["role"]),
        "account_status": _ok(user["account_status"]),
        "created_at": _ok(user["created_at"]),
        "last_login_at": _ok(user["last_login_at"]) if user["last_login_at"] else _na(
            "Ce compte ne s'est jamais reconnecté depuis sa création (last_login_at est NULL)."
        ),
        "total_time_s": _ok(user["total_time_s"]),
        "recent_ip": _ok({"ip": latest_ip["ip"], "recorded_at": latest_ip["created_at"]}) if latest_ip else NO_IP_DATA,
        # Méthode de connexion réelle (users.auth_provider — 'local', 'google'
        # ou 'guest') : toujours disponible, jamais None en base (Chantier
        # Administrateur "Utilisateurs", Phase 2).
        "auth_provider": _ok(user["auth_provider"]),
        # Réutilise two_factor_service.is_enabled() telle quelle (même
        # fonction que /api/auth/me côté compte lui-même) — aucune deuxième
        # logique de calcul de cet état.
        "two_factor_enabled": _ok(two_factor_service.is_enabled(user)),
        # Même règle canonique que auth.py::_public_user (champ
        # "email_verified" de /api/auth/me) : un compte local ou invité n'a
        # aucun fournisseur externe garantissant que l'adresse existe
        # réellement ; tout le reste (OAuth, aujourd'hui uniquement Google)
        # l'a déjà vérifiée avant la création du compte. Reproduite ici à
        # l'identique plutôt que de recalculer un critère différent.
        "email_verified": _ok(user["auth_provider"] not in ("local", "guest")),
    }


# ── 2. Activité (timeline) ───────────────────────────────────────────────
_SECURITY_EVENT_LABELS = {
    "login_success": "Connexion réussie",
    "login_failed": "Tentative de connexion échouée",
    "account_created": "Compte créé",
    "password_changed": "Mot de passe modifié",
    "two_factor_enabled": "2FA activée",
    "two_factor_disabled": "2FA désactivée",
    "two_factor_verified": "Code 2FA vérifié",
}


def get_activity(user_id):
    user = _user_row(user_id)
    if user is None:
        return None

    events = []
    for e in db.list_security_events_for_user(user_id):
        events.append({
            "type": "security",
            "label": _SECURITY_EVENT_LABELS.get(e["event_type"], e["event_type"]),
            "created_at": e["created_at"],
            "meta": {"ip": e["ip"]} if e["ip"] else None,
        })
    for c in db.list_conversations(user_id):
        events.append({
            "type": "conversation",
            "label": f"Conversation « {c['title']} » créée",
            "created_at": c["created_at"],
            "meta": {"conversation_id": c["id"]},
        })
    reviews = [r for r in _read_reviews() if r.get("user_id") == user_id]
    for r in reviews:
        events.append({
            "type": "review", "label": "Avis publié", "created_at": r.get("date"),
            "meta": {"rating": r.get("rating")},
        })
    events.sort(key=lambda e: e["created_at"] or "", reverse=True)

    # Les catégories structurellement sans donnée (paiements, bugs, erreurs,
    # consultations de cours, tentatives d'exercice) ne sont plus listées ici
    # — bruit sans valeur pour un admin, elles ne seront jamais alimentées
    # (voir chantier de simplification du panneau admin). Seules les
    # catégories réellement mesurées (sécurité/conversations/avis) figurent
    # dans la timeline ci-dessus.
    return {
        "events": events[:100],
        "total_events": len(events),
    }


def _read_reviews():
    """Même fichier/logique que server.py::_read_reviews et
    admin_dashboard_service.py::_read_reviews (dupliqué à l'identique, en
    lecture seule — précédent déjà établi dans ce projet plutôt qu'un import
    croisé entre services admin) : un fichier absent est une base saine sans
    aucun avis publié, jamais une erreur."""
    if not REVIEWS_PATH.exists():
        return []
    with open(REVIEWS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ── 3. Cours (progression par chapitre, vue agrégée) ────────────────────
def get_courses(user_id):
    user = _user_row(user_id)
    if user is None:
        return None

    chapters = []
    for class_level in curriculum_registry.CURRICULUM_REGISTRY:
        progress = auth.read_user_course_progress(user_id, class_level=class_level)
        for chapter_id, notions in progress.items():
            if not notions:
                continue
            statuses = [n.get("status") for n in notions.values()]
            done = sum(1 for s in statuses if s == "done")
            last_updated = max((n.get("updatedAt") or 0) for n in notions.values())
            chapters.append({
                "class_level": class_level,
                "chapter_id": chapter_id,
                "notions_total": len(notions),
                "notions_done": done,
                "progress_pct": round((done / len(notions)) * 100, 1) if notions else 0.0,
                "last_updated_at": last_updated or None,
            })
    chapters.sort(key=lambda c: c["last_updated_at"] or 0, reverse=True)

    return {
        "chapters": chapters if chapters else None,
        "chapters_reason": None if chapters else "Aucune progression de lecture enregistrée pour ce compte (data/user_course_progress).",
    }


# ── 4. Exercices ──────────────────────────────────────────────────────────
def get_exercises(user_id):
    user = _user_row(user_id)
    if user is None:
        return None

    stats = auth.read_user_stats(user_id)
    history = stats.get("history", [])
    total = len(history)

    if total == 0:
        return {
            "total": 0,
            "success_rate": None,
            "chapters_with_most_errors": None,
            "last_exercise": _na("Aucun exercice n'a encore été réalisé par ce compte."),
            "time_spent_s": _ok(0),
        }

    correct = sum(1 for h in history if h.get("correct"))
    error_counter = Counter(h.get("chapter") for h in history if not h.get("correct") and h.get("chapter"))
    top_errors = [{"chapter": chapter, "errors": n} for chapter, n in error_counter.most_common(5)]

    last = history[-1]
    return {
        "total": total,
        "success_rate": round((correct / total) * 100, 1),
        "chapters_with_most_errors": top_errors if top_errors else None,
        "last_exercise": _ok({
            "chapter": last.get("chapter"), "correct": bool(last.get("correct")),
            "duration_s": last.get("duration_s"),
            # Réellement écrit par static/js/store.js::recordAnswer (champ
            # "ts", epoch ms) à chaque réponse — corrige une régression du
            # chantier Utilisateurs qui l'avait, à tort, cru toujours nul.
            "date": last.get("ts"),
        }),
        "time_spent_s": _ok(sum(h.get("duration_s") or 0 for h in history)),
    }


# ── 5. Chatbot ────────────────────────────────────────────────────────────
def get_chatbot(user_id):
    """Onglet Chatbot de la fiche utilisateur, en DEUX sections :

    - ACTIVITÉ CHATBOT : toujours alimentée depuis conversations/
      chatbot_messages (jamais depuis ai_request_logs) — reflète l'usage réel
      du chatbot (voir db.chatbot_engine_breakdown_for_user/
      chatbot_time_spent_seconds_for_user, alimentées par le tag engine/
      provider posé sur chaque message assistant dans conversation_manager.py).
    - CONSOMMATION IA : calculée EXCLUSIVEMENT à partir de ai_request_logs
      (voir ai_request_log_service.py), JAMAIS depuis ai_provider_usage
      (agrégat global de l'administration, voir admin_dashboard_service.py —
      sans lien avec un utilisateur précis). Couvre désormais TOUT traitement
      ayant produit une réponse — Gemini/Claude (tokens/coût réels) ET moteur
      local/cache/clarification (tokens ESTIMÉS par heuristique, coût
      toujours 0 — voir ai_request_log_service.record_local_response). Un
      champ n'est "Aucune donnée disponible" que si ce compte n'a encore
      JAMAIS reçu la moindre réponse du chatbot, réelle ou locale."""
    user = _user_row(user_id)
    if user is None:
        return None

    conversations = db.list_conversations(user_id)
    conversations_count = len(conversations)
    messages_count = db.count_messages_for_user(user_id)
    last_conversation = conversations[0] if conversations else None

    engine_breakdown = db.chatbot_engine_breakdown_for_user(user_id)
    time_spent_s = db.chatbot_time_spent_seconds_for_user(user_id)

    stats = ai_request_log_service.stats_for_user(user_id)
    ai_history = ai_request_log_service.list_for_user(user_id, limit=20)
    ai_source_breakdown = ai_request_log_service.source_breakdown_for_user(user_id)

    return {
        # ── Activité chatbot (conversations/messages, toujours disponible) ──
        "conversations_count": conversations_count,
        "messages_count": messages_count,
        "last_conversation": _ok({
            "id": last_conversation["id"], "title": last_conversation["title"],
            "updated_at": last_conversation["updated_at"],
        }) if last_conversation else _na("Aucune conversation n'a encore été créée par ce compte."),
        "history": [
            {"id": c["id"], "title": c["title"], "created_at": c["created_at"], "updated_at": c["updated_at"]}
            for c in conversations[:20]
        ],
        "time_spent_s": _ok(round(time_spent_s)),
        "local_responses_count": _ok(engine_breakdown["local"]),
        "llm_responses_count": _ok(engine_breakdown["llm"]),
        "uncategorized_responses_count": _ok(engine_breakdown["uncategorized"]),
        "engine_breakdown": _ok(engine_breakdown["by_bucket"]),
        # ── Consommation IA (ai_request_logs, TOUT moteur — LLM + local) ────
        "ai_consumption_available": stats is not None,
        "ai_consumption_empty_message": None if stats else AI_CONSUMPTION_EMPTY_MESSAGE,
        "ai_requests_total": _ok(stats["total_requests"]) if stats else NO_AI_REQUEST_DATA,
        "ai_tokens_total": _ok(stats["total_tokens"]) if stats else NO_AI_REQUEST_DATA,
        "ai_input_tokens": _ok(stats["input_tokens"]) if stats else NO_AI_REQUEST_DATA,
        "ai_output_tokens": _ok(stats["output_tokens"]) if stats else NO_AI_REQUEST_DATA,
        "ai_cost": _ok(round(stats["total_cost"], 6)) if stats else NO_AI_REQUEST_DATA,
        # Tokens réels (Gemini/Claude, comptage fournisseur) vs estimés
        # (moteur local/cache/clarification, heuristique ~4 car./token) —
        # jamais présentés comme une seule et même donnée facturée.
        "ai_real_tokens": _ok(stats["real_tokens"]) if stats else NO_AI_REQUEST_DATA,
        "ai_estimated_tokens": _ok(stats["estimated_tokens"]) if stats else NO_AI_REQUEST_DATA,
        "ai_real_requests": _ok(stats["real_requests"]) if stats else NO_AI_REQUEST_DATA,
        "ai_estimated_requests": _ok(stats["estimated_requests"]) if stats else NO_AI_REQUEST_DATA,
        "ai_source_breakdown": _ok(ai_source_breakdown) if ai_source_breakdown else NO_AI_REQUEST_DATA,
        "ai_most_used_provider": _ok(stats["most_used_provider"]) if stats else NO_AI_REQUEST_DATA,
        "ai_last_provider": _ok(stats["last_provider"]) if stats else NO_AI_REQUEST_DATA,
        "ai_last_model": _ok(stats["last_model"]) if stats else NO_AI_REQUEST_DATA,
        "ai_avg_response_time_ms": _ok(stats["avg_response_time_ms"]) if stats else NO_AI_REQUEST_DATA,
        "ai_last_used_at": _ok(stats["last_used_at"]) if stats else NO_AI_REQUEST_DATA,
        "ai_call_history": [
            {
                "provider": r["provider"], "model": r["model"],
                "input_tokens": r["input_tokens"], "output_tokens": r["output_tokens"],
                "total_tokens": r["total_tokens"], "estimated_cost": r["estimated_cost"],
                "response_time_ms": r["response_time_ms"], "success": bool(r["success"]),
                "fallback": bool(r["fallback"]), "created_at": r["created_at"],
                "engine": r.get("engine"), "source": r.get("source"), "estimated": bool(r.get("estimated")),
            }
            for r in ai_history
        ] if ai_history else None,
        "ai_call_history_reason": None if ai_history else AI_CONSUMPTION_EMPTY_MESSAGE,
    }


# ── 6. Apprentissage (notions réellement étudiées) ───────────────────────
def get_learning(user_id):
    user = _user_row(user_id)
    if user is None:
        return None

    notions = []
    for class_level in curriculum_registry.CURRICULUM_REGISTRY:
        progress = auth.read_user_course_progress(user_id, class_level=class_level)
        for chapter_id, chapter_notions in progress.items():
            for notion_id, data in chapter_notions.items():
                notions.append({
                    "class_level": class_level,
                    "chapter_id": chapter_id,
                    "notion_id": notion_id,
                    "status": data.get("status"),
                    "updated_at": data.get("updatedAt"),
                })
    notions.sort(key=lambda n: n["updated_at"] or 0, reverse=True)

    return {
        "notions": notions if notions else None,
        "notions_reason": None if notions else "Aucune notion de cours consultée n'est enregistrée pour ce compte.",
    }


# ── 7. Abonnement ─────────────────────────────────────────────────────────
def get_subscription(user_id):
    user = _user_row(user_id)
    if user is None:
        return None

    # "Renouvellement"/"Expiration"/"Historique des paiements"/"Date d'achat"
    # retirés de l'affichage : placeholders permanents, jamais implémentés
    # (aucune donnée locale, uniquement disponible via un appel direct à
    # l'API Stripe non effectué ici — stripe_webhook_events n'est qu'une
    # table d'idempotence technique, sans user_id).
    return {
        "plan": _ok(user["plan"]),
        "stripe_subscription_status": _ok(user["stripe_subscription_status"]) if user["stripe_subscription_status"] else _na(
            "Aucun abonnement Stripe n'a jamais été initié pour ce compte."
        ),
        "has_stripe_customer": _ok(bool(user["stripe_customer_id"])),
    }


# ── 8. Support ────────────────────────────────────────────────────────────
NO_TICKETS_REASON = "Aucun ticket support n'a été créé par ce compte."


def get_support(user_id):
    """Onglet Support de la fiche utilisateur (Chantier Administrateur
    "Utilisateurs", Phase 2) — réutilise support_service.list_tickets_for_user
    telle quelle (aucun nouveau système de tickets, aucune requête SQL
    ajoutée à côté). Labels identiques à /admin/support (support_service.
    CATEGORY_LABELS/STATUS_LABELS), pour ne jamais afficher un wording
    différent du reste de l'admin. Strictement informatif : aucune action
    (répondre/fermer/assigner) n'est exposée ici — ce chantier reste en
    lecture seule, comme tout admin_user_profile_service.py."""
    user = _user_row(user_id)
    if user is None:
        return None

    tickets = support_service.list_tickets_for_user(user_id)
    return {
        "tickets": [
            {
                "id": t["id"],
                "subject": t["subject"],
                "category": t["category"],
                "category_label": support_service.CATEGORY_LABELS.get(t["category"], t["category"]),
                "priority": t["priority"],
                "status": t["status"],
                "status_label": support_service.STATUS_LABELS.get(t["status"], t["status"]),
                "created_at": t["created_at"],
                "updated_at": t["updated_at"],
            }
            for t in tickets
        ] if tickets else None,
        "tickets_reason": None if tickets else NO_TICKETS_REASON,
    }
