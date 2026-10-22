"""
Registre de navigation de l'espace Administration — source UNIQUE de vérité
du menu latéral ET de la protection des routes de chaque module. Aucune
logique métier : uniquement la structure du shell (id/label/icône/chemin/
rôle minimum/état "implémenté").

Le frontend ne connaît JAMAIS un rôle ni une règle de permission — il se
contente d'afficher la liste déjà filtrée que ce module renvoie (voir
modules_for_user()). C'est ce module, seul, qui décide "qui voit quoi",
exactement comme plan_service.py décide seul "quel plan a droit à quoi" et
quota_service.py "quelle limite pour quel plan" — même architecture, même
règle de centralisation stricte.

Réutilisé à deux endroits dans server.py :
  - GET /api/admin/nav (menu réellement affiché, filtré par rôle) ;
  - l'enregistrement des routes /admin/<module> (chaque route protégée par
    EXACTEMENT le rôle minimum déclaré ici — un seul endroit à modifier pour
    changer le rôle requis par un module, jamais une décision dupliquée entre
    le menu et la route qui le sert).
"""
from dataclasses import dataclass

from role_service import Role, has_role_at_least


@dataclass(frozen=True)
class AdminModule:
    id: str
    label: str
    icon: str
    path: str
    minimum_role: Role
    # False : la route existe et ne renvoie jamais 404, mais affiche
    # uniquement "Cette fonctionnalité sera disponible prochainement." —
    # aucune fonctionnalité métier n'est développée pour ce module à ce
    # stade (voir server.py::serve_admin_module).
    implemented: bool
    # Regroupement purement visuel du menu (sidebar), décidé lors du grand
    # nettoyage admin (2026-10-22) : "suivi" (observation/monitoring),
    # "gestion" (actions sur les utilisateurs/abonnements/support), ou
    # "configuration" (réglages système). N'affecte JAMAIS les permissions
    # ni les routes — uniquement l'ordre d'affichage des sections dans
    # admin-shell.js::renderSidebar. N'importe pas dans modules_for_user()/
    # module_by_path() ni dans server.py, qui continuent de n'utiliser que
    # l'ordre de déclaration ci-dessous.
    category: str


# Rôles minimums : reprend les décisions déjà actées dans le document
# d'architecture de l'espace Administration (chantier précédent) — Dashboard/
# Utilisateurs/Analytics/Support restent accessibles à SUPPORT (rôle interne
# le plus bas), IA, Abonnements et Journal exigent ADMIN (données sensibles/
# techniques/financières), Paramètres exige SUPER_ADMIN (impact le plus
# large). Un seul endroit à modifier si ces paliers doivent évoluer.
MODULES = (
    AdminModule("dashboard", "Dashboard", "🏠", "/admin", Role.SUPPORT, implemented=True, category="suivi"),
    AdminModule("users", "Utilisateurs", "👥", "/admin/users", Role.SUPPORT, implemented=True, category="gestion"),
    AdminModule("ai", "IA", "🤖", "/admin/ia", Role.ADMIN, implemented=True, category="configuration"),
    AdminModule(
        "subscriptions", "Abonnements", "💳", "/admin/subscriptions", Role.ADMIN, implemented=True, category="gestion"
    ),
    AdminModule("analytics", "Analytics", "📊", "/admin/analytics", Role.SUPPORT, implemented=True, category="suivi"),
    AdminModule("support", "Support", "🛠", "/admin/support", Role.SUPPORT, implemented=True, category="gestion"),
    AdminModule(
        "health", "Santé du système", "❤", "/admin/health", Role.ADMIN, implemented=True, category="suivi"
    ),
    AdminModule(
        "settings", "Paramètres", "⚙", "/admin/settings", Role.SUPER_ADMIN, implemented=True, category="configuration"
    ),
    AdminModule("journal", "Journal", "📜", "/admin/journal", Role.ADMIN, implemented=True, category="suivi"),
    # Phase 2A (audit admin, 2026-10-21) : données financières réelles
    # (revenus/paiements Stripe) — SUPER_ADMIN comme Paramètres, jamais ADMIN,
    # vu la sensibilité des montants réels par rapport au catalogue éditable
    # du module Abonnements.
    AdminModule(
        "finance", "Finance", "💰", "/admin/finance", Role.SUPER_ADMIN, implemented=True, category="gestion"
    ),
    # Phase 2 Cloudflare (audit admin, 2026-10-21) : fréquentation du site
    # (Cloudflare Web Analytics, données EXTERNES au site, jamais les comptes
    # Mathadap — voir cloudflare_analytics_service.py) — ADMIN comme IA/
    # Abonnements/Journal, décision validée explicitement pour ce module
    # (plutôt que SUPPORT comme le module "Analytics" interne).
    AdminModule(
        "frequentation", "Fréquentation", "🌐", "/admin/frequentation", Role.ADMIN, implemented=True, category="suivi"
    ),
)

# Ordre d'affichage des sections de la sidebar (grand nettoyage admin,
# 2026-10-22) — "Suivi" (observation/monitoring), "Gestion" (actions sur
# utilisateurs/abonnements/support), "Configuration" (réglages système).
CATEGORY_ORDER = ("suivi", "gestion", "configuration")
CATEGORY_LABELS = {"suivi": "Suivi", "gestion": "Gestion", "configuration": "Configuration"}


def modules_for_user(user):
    """Modules visibles pour `user`, dans l'ordre déclaré ci-dessus — jamais
    trié/filtré autrement, le frontend affiche cette liste telle quelle."""
    return [m for m in MODULES if has_role_at_least(user, m.minimum_role)]


def module_by_path(path):
    return next((m for m in MODULES if m.path == path), None)


def serialize_module(module):
    return {
        "id": module.id,
        "label": module.label,
        "icon": module.icon,
        "path": module.path,
        "implemented": module.implemented,
        "category": module.category,
    }
