"""
Service du module "Gestion des abonnements" (/admin/subscriptions) —
panneau d'administration complet des 3 plans NovaMath (Free/Premium/Ultra) :
consultation du catalogue, statistiques réelles, modification, activation/
désactivation.

IMPORTANT — ce que ce module NE fait PAS :
- Il ne modifie JAMAIS plan_service.py (FEATURE_MATRIX) ni quota_service.py
  (QUOTA_MATRIX) : ces deux modules restent l'UNIQUE source de vérité des
  droits/quotas réellement appliqués au chatbot. Le catalogue administrable
  (table subscription_plans, voir subscription_plan_service.py) est un
  calque de présentation, exactement comme ai_providers l'était pour
  provider_manager.py avant sa migration — éditer un plan ici change ce qui
  s'affiche dans ce panneau, jamais ce qui est réellement appliqué.
- Il ne modifie JAMAIS stripe_service.py/stripe_webhook_service.py/
  billing_service.py : le prix affiché dans ce panneau est un champ
  catalogue (voir subscription_plan_service.py), jamais un appel Stripe.
  Le montant réellement facturé reste piloté par STRIPE_PRICE_PREMIUM/
  STRIPE_PRICE_ULTRA (variables d'environnement), totalement inchangé.
- Il n'ajoute AUCUNE requête SQL nouvelle en dehors de celles déjà exposées
  par db.py — la lecture/écriture passe par subscription_plan_service.py
  (catalogue), admin_users_service.py (onglet Utilisateurs, réutilisé tel
  quel) et admin_ai_log_service.py (onglet Historique + journalisation des
  écritures, réutilisé tel quel).

Architecture stricte, identique au reste du projet :

    server.py  →  admin_subscriptions_service.py  →  subscription_plan_service.py /
                   admin_users_service.py / admin_ai_log_service.py
                   →  db.py

jamais l'inverse.

── Politique "aucune donnée inventée" ──────────────────────────────────────
Identique à admin_dashboard_service.py/admin_ai_service.py : tout champ
structurellement absent ou non mesurable renvoie
{"available": False, "value": None, "reason": "..."}, JAMAIS un 0/texte
fabriqué.

── Chantier de simplification (page Abonnements) ───────────────────────────
4 cartes de statistiques (revenus générés, renouvellements, taux de
conversion, taux de churn) ont été supprimées : elles étaient
structurellement TOUJOURS indisponibles (stripe_webhook_service.py ne
journalise que le TYPE d'événement Stripe, jamais un montant ni le
billing_reason ; aucun suivi de cohorte ni historique du nombre d'abonnés
n'existe) — un placeholder permanent, jamais une vraie donnée. L'onglet "IA"
de la fiche détaillée (get_plan_ai) a été supprimé : plus aucun frontend ne
l'appelait depuis que cette information a été déplacée vers la section
"Fournisseurs IA par plan" de la page Abonnements elle-même (voir
admin-subscriptions.js). `quota_monthly` a été retiré du formulaire/affichage
catalogue (voir subscription_plan_service.update_plan) : aucun mécanisme de
quota mensuel n'existe dans quota_service.py, uniquement des quotas
journaliers — ce champ n'était qu'un espace réservé jamais branché.
"""
from datetime import datetime, timedelta, timezone

import admin_ai_log_service
import admin_users_service
import db
import quota_service
import subscription_plan_service as catalog
from plan_service import FEATURE_MATRIX, Feature, Plan

_KNOWN_PLANS = tuple(p.value for p in Plan)

STATS_WINDOW_DAYS = 30

FEATURE_LABELS = {
    Feature.CHATBOT: "Chatbot pédagogique",
    Feature.CHATBOT_UNLIMITED: "Chatbot sans quota quotidien",
    Feature.ADVANCED_AI: "IA avancée (génération sur mesure)",
    Feature.ADVANCED_EXPLANATIONS: "Explications avancées",
    Feature.COURSES: "Accès aux cours",
    Feature.EXERCISES: "Accès aux exercices",
    Feature.CUSTOM_EXERCISES: "Exercices personnalisés",
    Feature.STATISTICS: "Statistiques",
    Feature.HISTORY: "Historique",
    Feature.GOALS: "Objectifs quotidiens",
    Feature.EXPORT: "Export de données",
    Feature.PROFILE_ANALYTICS: "Statistiques de profil avancées",
    Feature.EARLY_ACCESS: "Accès anticipé aux nouveautés",
    Feature.PRIORITY_QUEUE: "File d'attente prioritaire",
    Feature.PRIORITY_SUPPORT: "Support prioritaire",
    Feature.LONG_RESPONSES: "Réponses longues",
}

QUOTA_LABELS = {
    quota_service.QuotaType.CHAT_MESSAGES: "Messages chatbot / jour",
    quota_service.QuotaType.PDF_ANALYSIS: "Analyses de PDF / jour",
    quota_service.QuotaType.AI_GENERATIONS: "Générations IA / jour",
    quota_service.QuotaType.CUSTOM_EXERCISES: "Exercices personnalisés / jour",
    quota_service.QuotaType.EXPORTS: "Exports / jour",
    # LLM_CALLS manquait déjà ici avant ce chantier (get_plan_features ci-dessous
    # indexe QUOTA_LABELS[q] pour CHAQUE QuotaType, sans .get() ni valeur par
    # défaut — un KeyError latent, jamais couvert par un test). Ajouté en même
    # temps qu'EXERCISES_DAILY par simple prudence : cette dict devait de toute
    # façon être mise à jour pour ce nouveau QuotaType, autant corriger l'écart
    # préexistant plutôt que le laisser planter la même route un peu plus tard.
    quota_service.QuotaType.LLM_CALLS: "Appels IA réels / jour",
    quota_service.QuotaType.EXERCISES_DAILY: "Exercices classiques / jour",
}


def _na(reason):
    return {"available": False, "value": None, "reason": reason}


def _ok(value):
    return {"available": True, "value": value}


def _field(value, reason):
    return _ok(value) if value is not None else _na(reason)


def _since(days):
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


# ── Lecture : catalogue ──────────────────────────────────────────────────────
def _serialize_plan_summary(row, user_counts):
    return {
        "plan": row["plan"],
        "name": row["name"],
        "description": _field(row["description"], "Aucune description définie pour cet abonnement."),
        "price_amount_cents": _field(row["price_amount_cents"], "Aucun prix défini pour cet abonnement."),
        "currency": _field(row["currency"], "Aucune devise définie pour cet abonnement."),
        "duration_label": _field(row["duration_label"], "Aucune durée définie pour cet abonnement."),
        "display_order": row["display_order"],
        "active": row["active"],
        "user_count": _ok(user_counts.get(row["plan"], 0)),
    }


def list_plans():
    """Carte principale du module — les 3 plans catalogués + nombre réel
    d'utilisateurs par plan (voir db.count_users_by_plan, déjà utilisé par
    admin_dashboard_service.py — même source, jamais recalculée
    différemment)."""
    rows = catalog.list_plans()
    if not rows:
        return {"plans": None, "reason": "Aucun abonnement n'est configuré dans subscription_plans."}
    user_counts = db.count_users_by_plan()
    return {"plans": [_serialize_plan_summary(r, user_counts) for r in rows], "reason": None}


def _global_stats():
    """Statistiques globales du module, sur une fenêtre glissante de
    STATS_WINDOW_DAYS jours — voir la politique "aucune donnée inventée" en
    tête de fichier pour la justification des mesures indisponibles."""
    since = _since(STATS_WINDOW_DAYS)
    return {
        "window_days": STATS_WINDOW_DAYS,
        "new_subscribers": _ok(db.count_security_events_since("stripe_subscription_created", since)),
        "cancellations": _ok(db.count_security_events_since("stripe_subscription_deleted", since)),
    }


def get_overview():
    return {**list_plans(), "stats": _global_stats()}


# ── Lecture : fiche détaillée ────────────────────────────────────────────────
def get_plan_info(plan):
    row = catalog.get_plan(plan)
    if row is None:
        return None
    user_counts = db.count_users_by_plan()
    return {
        "plan": row["plan"],
        "name": row["name"],
        "description": _field(row["description"], "Aucune description définie pour cet abonnement."),
        "active": row["active"],
        "display_order": row["display_order"],
        "user_count": _ok(user_counts.get(row["plan"], 0)),
        "created_at": _ok(row["created_at"]),
        "updated_at": _ok(row["updated_at"]),
    }


def get_plan_pricing(plan):
    row = catalog.get_plan(plan)
    if row is None:
        return None
    return {
        "price_amount_cents": _field(row["price_amount_cents"], "Aucun prix défini pour cet abonnement."),
        "currency": _field(row["currency"], "Aucune devise définie pour cet abonnement."),
        "duration_label": _field(row["duration_label"], "Aucune durée définie pour cet abonnement."),
        "note": (
            "Prix affiché à titre de catalogue pour ce panneau d'administration — le montant réellement "
            "facturé par Stripe reste piloté par STRIPE_PRICE_PREMIUM/STRIPE_PRICE_ULTRA (variables "
            "d'environnement) et n'est jamais modifié depuis cet écran."
        ),
    }


def get_plan_features(plan):
    row = catalog.get_plan(plan)
    if row is None:
        return None
    plan_enum = Plan.from_value(plan)
    real_features = [
        {"key": f.value, "label": FEATURE_LABELS.get(f, f.value)}
        for f in sorted(FEATURE_MATRIX[plan_enum], key=lambda f: FEATURE_LABELS.get(f, f.value))
    ]
    real_quotas = [
        {
            "key": q.value, "label": QUOTA_LABELS[q],
            "limit": quota_service.QUOTA_MATRIX[plan_enum][q],
            "unlimited": quota_service.QUOTA_MATRIX[plan_enum][q] is None,
        }
        for q in quota_service.QuotaType
    ]
    return {
        "advantages": row["advantages"],
        "limits": row["limits"],
        "quota_daily": _field(row["quota_daily"], "Aucun quota quotidien catalogue défini (illimité ou non renseigné)."),
        "quota_chatbot": _field(row["quota_chatbot"], "Aucun quota chatbot catalogue défini (illimité ou non renseigné)."),
        "real_features": real_features,
        "real_quotas": real_quotas,
        "real_note": (
            "\"real_features\"/\"real_quotas\" reflètent ce qui est RÉELLEMENT appliqué aujourd'hui par "
            "plan_service.py/quota_service.py (lecture seule, non modifiable depuis ce panneau)."
        ),
    }


def get_plan_users(plan, search=None, page=1, page_size=None):
    """Onglet "Utilisateurs" — délègue entièrement à admin_users_service.py
    (déjà pagination/recherche/tri en SQL), filtré sur ce seul plan. Aucune
    logique de liste d'utilisateurs dupliquée ici."""
    if catalog.get_plan(plan) is None:
        return None
    return admin_users_service.list_users(
        search=search, plan=plan, page=page,
        page_size=page_size or admin_users_service.PAGE_SIZE_DEFAULT,
    )


def get_plan_history(plan, page=1, page_size=None):
    """Onglet "Historique" — délègue à admin_ai_log_service.py (le journal
    d'administration déjà créé), filtré sur les entrées concernant CE plan
    (voir update_plan_logged/set_plan_active_logged ci-dessous, qui
    journalisent toutes avec provider_name=f"Abonnement {plan}")."""
    if catalog.get_plan(plan) is None:
        return None
    return admin_ai_log_service.list_log(
        provider_name=f"Abonnement {plan}", page=page, page_size=page_size or admin_ai_log_service.PAGE_SIZE_DEFAULT,
    )


# ── Écriture : validation ────────────────────────────────────────────────────
def _clean_str_list(value, field_name, errors, max_items=20, max_len=200):
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        errors[field_name] = f"{field_name} doit être une liste de textes."
        return []
    cleaned = [v.strip() for v in value if v.strip()][:max_items]
    if any(len(v) > max_len for v in cleaned):
        errors[field_name] = f"Chaque élément de {field_name} doit faire au plus {max_len} caractères."
    return cleaned


def _clean_optional_nonneg_int(value, field_name, errors):
    """None = illimité/non défini (toujours accepté). Toute autre valeur doit
    être un entier positif ou nul."""
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        errors[field_name] = f"{field_name} doit être un entier positif ou nul, ou vide (illimité)."
        return None
    return value


def _validate_plan_payload(data):
    errors = {}
    name = (data.get("name") or "").strip()
    if not name:
        errors["name"] = "Le nom est obligatoire."

    price_amount_cents = _clean_optional_nonneg_int(data.get("price_amount_cents"), "price_amount_cents", errors)
    currency = (data.get("currency") or "").strip() or None
    duration_label = (data.get("duration_label") or "").strip() or None
    if price_amount_cents is not None and not currency:
        errors["currency"] = "La devise est obligatoire dès qu'un prix est défini."

    quota_daily = _clean_optional_nonneg_int(data.get("quota_daily"), "quota_daily", errors)
    quota_chatbot = _clean_optional_nonneg_int(data.get("quota_chatbot"), "quota_chatbot", errors)

    display_order = data.get("display_order", 0)
    if not isinstance(display_order, int) or isinstance(display_order, bool):
        errors["display_order"] = "L'ordre d'affichage doit être un entier."
        display_order = 0

    advantages = _clean_str_list(data.get("advantages"), "advantages", errors)
    limits = _clean_str_list(data.get("limits"), "limits", errors)

    clean = {
        "name": name, "description": (data.get("description") or "").strip() or None,
        "price_amount_cents": price_amount_cents, "currency": currency, "duration_label": duration_label,
        "advantages": advantages, "limits": limits,
        "quota_daily": quota_daily, "quota_chatbot": quota_chatbot,
        "display_order": display_order, "active": bool(data.get("active", True)),
    }
    return errors, clean


def _snapshot(plan):
    row = catalog.get_plan(plan)
    if row is None:
        return None
    return {k: row[k] for k in (
        "name", "description", "price_amount_cents", "currency", "duration_label",
        "advantages", "limits", "quota_daily", "quota_chatbot",
        "display_order", "active",
    )}


def _errors_to_message(errors):
    if not errors:
        return None
    return "; ".join(f"{key}: {value}" for key, value in errors.items())


# ── Écriture : catalogue (journalisée) ───────────────────────────────────────
def update_plan_logged(actor, plan, data):
    """Remplace l'intégralité des champs catalogue modifiables d'un plan,
    après validation, et journalise l'action (voir admin_ai_log_service.py —
    le journal d'administration déjà créé, réutilisé tel quel). Renvoie
    (ok, errors)."""
    if plan not in _KNOWN_PLANS or catalog.get_plan(plan) is None:
        return False, {"_": "Abonnement introuvable."}
    errors, clean = _validate_plan_payload(data)
    before = _snapshot(plan)
    if errors:
        admin_ai_log_service.record(
            actor, action="update_plan", provider_id=None, provider_name=f"Abonnement {plan}",
            old_values=before, new_values=None, result="error", error_message=_errors_to_message(errors),
        )
        return False, errors

    catalog.update_plan(
        plan, clean["name"], clean["description"], clean["price_amount_cents"], clean["currency"],
        clean["duration_label"], clean["advantages"], clean["limits"], clean["quota_daily"],
        clean["quota_chatbot"], clean["display_order"], clean["active"],
    )
    after = _snapshot(plan)
    admin_ai_log_service.record(
        actor, action="update_plan", provider_id=None, provider_name=f"Abonnement {plan}",
        old_values=before, new_values=after, result="success", error_message=None,
    )
    return True, {}


def set_plan_active_logged(actor, plan, active):
    if plan not in _KNOWN_PLANS or catalog.get_plan(plan) is None:
        return False, {"_": "Abonnement introuvable."}
    before = _snapshot(plan)
    catalog.set_plan_active(plan, active)
    admin_ai_log_service.record(
        actor, action="enable_plan" if active else "disable_plan",
        provider_id=None, provider_name=f"Abonnement {plan}",
        old_values={"active": before["active"]} if before else None,
        new_values={"active": bool(active)}, result="success", error_message=None,
    )
    return True, {}
