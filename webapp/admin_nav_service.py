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


# Rôles minimums : reprend les décisions déjà actées dans le document
# d'architecture de l'espace Administration (chantier précédent) — Dashboard/
# Utilisateurs/Analytics/Support restent accessibles à SUPPORT (rôle interne
# le plus bas), IA, Abonnements et Journal exigent ADMIN (données sensibles/
# techniques/financières), Paramètres exige SUPER_ADMIN (impact le plus
# large). Un seul endroit à modifier si ces paliers doivent évoluer.
MODULES = (
    AdminModule("dashboard", "Dashboard", "🏠", "/admin", Role.SUPPORT, implemented=True),
    AdminModule("users", "Utilisateurs", "👥", "/admin/users", Role.SUPPORT, implemented=True),
    AdminModule("ai", "IA", "🤖", "/admin/ia", Role.ADMIN, implemented=True),
    AdminModule("subscriptions", "Abonnements", "💳", "/admin/subscriptions", Role.ADMIN, implemented=True),
    AdminModule("analytics", "Analytics", "📊", "/admin/analytics", Role.SUPPORT, implemented=True),
    AdminModule("support", "Support", "🛠", "/admin/support", Role.SUPPORT, implemented=True),
    AdminModule("health", "Santé du système", "❤", "/admin/health", Role.ADMIN, implemented=True),
    AdminModule("settings", "Paramètres", "⚙", "/admin/settings", Role.SUPER_ADMIN, implemented=True),
    AdminModule("journal", "Journal", "📜", "/admin/journal", Role.ADMIN, implemented=True),
)


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
    }
