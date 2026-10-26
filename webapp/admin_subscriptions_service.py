"""
Service du module "Gestion des abonnements" (/admin/subscriptions) —
panneau d'administration complet des 3 plans Mathadap (Free/Premium/Ultra) :
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

Audit admin (2026-10-22) : les 2 cartes "Nouveaux abonnements (30j)"/
"Résiliations (30j)" (fonction `_global_stats`, retirée) ont été supprimées
de ce module — elles dupliquaient EXACTEMENT les mêmes compteurs déjà
affichés par le module Finance (get_subscriptions_overview,
admin_finance_service.py), devenu la seule référence pour les indicateurs
d'abonnement agrégés. `db.count_security_events_since` et les événements de
sécurité sous-jacents restent utilisés par Finance, rien n'a été supprimé
côté data/db. ATTENTION : Finance exige le rôle SUPER_ADMIN alors
qu'Abonnements n'exige qu'ADMIN (voir admin_nav_service.py) — un ADMIN non
SUPER_ADMIN ne voit donc plus ces deux chiffres nulle part ; voir
l'explication affichée à la place dans admin-subscriptions.js/admin.html et
le rapport de ce chantier pour cette conséquence, qui n'a pas été résolue
unilatéralement (aucune permission n'a été modifiée).

Audit admin (2026-10-22), suite — simplification visuelle : la section
"Statistiques" de la page Abonnements (admin.html, ex-#admin-subscriptions-
stats-title) ne contenait déjà plus qu'une phrase de renvoi vers Finance
(aucune carte, aucun appel API) depuis la suppression ci-dessus — elle a été
retirée et sa phrase fusionnée (raccourcie) dans le hint déjà existant sous
la section "Plans". Changement purement d'affichage (admin.html +
admin-subscriptions.test.js) : aucune donnée, route, ni permission touchée.
"""
import admin_ai_log_service
import admin_users_service
import config
import db
import quota_service
import stripe_reconciliation_service
import stripe_service
import subscription_plan_service as catalog
from plan_service import FEATURE_MATRIX, Feature, Plan

_KNOWN_PLANS = tuple(p.value for p in Plan)

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
    # include_guests=False (audit admin 2026-10-20) : un invité a toujours
    # plan="free" par défaut, gonflant sinon le nombre affiché pour Free.
    user_counts = db.count_users_by_plan(include_guests=False)
    return {"plans": [_serialize_plan_summary(r, user_counts) for r in rows], "reason": None}


def _stripe_environment():
    """Bannière d'environnement Stripe affichée au-dessus du bouton de
    réconciliation — aucun appel réseau (uniquement le préfixe de la clé,
    voir stripe_service.operating_mode, et config.IS_PRODUCTION) : doit
    rester instantané et ne jamais échouer si Stripe est injoignable.
    `reconciliation_blocked` reflète EXACTEMENT la même condition que le
    blocage dur appliqué par stripe_reconciliation_service.reconcile() —
    affichée ici pour que l'admin comprenne pourquoi le bouton est
    grisé/refuse, jamais comme une protection en soi (la vraie protection
    est côté serveur, voir ce module et stripe_reconciliation_service.py)."""
    mode = stripe_service.operating_mode()
    return {
        "mode": mode,
        "app_environment": "production" if config.IS_PRODUCTION else "developpement",
        "reconciliation_blocked": mode == "production" and not config.IS_PRODUCTION,
        "reconciliation_requires_confirmation": mode == "production" and config.IS_PRODUCTION,
    }


def get_overview():
    """Audit admin (2026-10-22), décision validée : ce module n'affiche plus
    "Nouveaux abonnements"/"Résiliations" sur une fenêtre glissante — ces
    deux compteurs dupliquaient EXACTEMENT ceux de get_subscriptions_overview
    (admin_finance_service.py, même calcul via db.count_security_events_since),
    où ils restent affichés, désormais la seule référence pour les
    indicateurs d'abonnement agrégés. `db.count_security_events_since` et
    l'événement de sécurité sous-jacent ne sont PAS supprimés (toujours
    utilisés par Finance) — seul l'appel/l'affichage ici a été retiré. Ce
    module reste centré sur le catalogue (plans, prix, fonctionnalités,
    quotas réellement appliqués, réconciliation)."""
    return {**list_plans(), "stripe_environment": _stripe_environment()}


# ── Lecture : fiche détaillée ────────────────────────────────────────────────
def get_plan_info(plan):
    row = catalog.get_plan(plan)
    if row is None:
        return None
    user_counts = db.count_users_by_plan(include_guests=False)
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


def reconcile_stripe_logged(actor, limit=None, offset=0, confirmed=False):
    """Lance UN lot de réconciliation Stripe ↔ DB locale (lecture seule, voir
    stripe_reconciliation_service.py) et journalise l'action comme tout le
    reste de ce module — déclenchement exclusivement manuel (voir
    server.py), jamais une tâche planifiée. Renvoie (ok, result_or_errors) :
    `ok=False` avec `{"_": message, "code": ...}` si l'opération est
    refusée (Stripe non configuré, blocage dur local/production, ou
    confirmation manquante — voir stripe_reconciliation_service.py pour le
    détail des 3 cas), jamais une exception qui remonterait telle quelle à
    l'admin. `code` permet à server.py de choisir le bon statut HTTP sans
    dupliquer cette logique."""
    kwargs = {"offset": offset, "confirmed": confirmed}
    if limit is not None:
        kwargs["limit"] = limit
    try:
        report = stripe_reconciliation_service.reconcile(**kwargs)
    except stripe_reconciliation_service.StripeReconciliationBlocked as exc:
        admin_ai_log_service.record(
            actor, action="reconcile_stripe", provider_id=None, provider_name="Stripe",
            old_values=None, new_values=None, result="error", error_message=str(exc),
        )
        return False, {"_": str(exc), "code": "blocked_local_production"}
    except stripe_reconciliation_service.StripeReconciliationConfirmationRequired as exc:
        # Pas encore une tentative refusée : l'admin n'a simplement pas
        # confirmé — jamais journalisé comme une erreur (voir le "error"
        # ci-dessus, réservé à un vrai refus/échec).
        return False, {"_": str(exc), "code": "confirmation_required"}
    except stripe_reconciliation_service.StripeReconciliationUnavailable as exc:
        admin_ai_log_service.record(
            actor, action="reconcile_stripe", provider_id=None, provider_name="Stripe",
            old_values=None, new_values=None, result="error", error_message=str(exc),
        )
        return False, {"_": str(exc), "code": "not_configured"}

    admin_ai_log_service.record(
        actor, action="reconcile_stripe", provider_id=None, provider_name="Stripe",
        old_values=None,
        new_values={
            "mode": report["mode"], "checked": report["checked"],
            "divergences": len(report["divergences"]), "errors": len(report["errors"]),
        },
        result="success" if not report["errors"] else "error",
        error_message=None if not report["errors"] else f"{len(report['errors'])} erreur(s) réseau/Stripe pendant le lot.",
    )
    return True, report
