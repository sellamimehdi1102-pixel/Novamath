"""
Garde-fou automatique — Chantier "Synchronisation globale des abonnements"
(2026-08-27), Phase 7.

Vérifie que les pages CLIENT statiques (abonnement.html, index.html) restent
cohérentes avec les SEULES sources de vérité réelles :

    quota_service.QUOTA_MATRIX          (CHAT_MESSAGES/LLM_CALLS/EXERCISES_DAILY)
    server.py::_SUGGESTIONS_LIMIT_BY_PLAN

Les valeurs attendues sont LUES depuis ces constantes Python, jamais
recopiées manuellement une seconde fois ici — si QUOTA_MATRIX change un jour
sans que abonnement.html/index.html ne soient mis à jour, ces tests échouent
immédiatement (c'est tout l'objectif : empêcher qu'une future modification
de quota redevienne silencieusement fausse dans le marketing).

Seule exception assumée : les 3 prix (0€/6,99€/12,99€) — aucune constante
Python ne les porte (voir abonnement.html, commentaire dédié : les montants
réellement facturés viennent de Stripe via STRIPE_PRICE_PREMIUM/
STRIPE_PRICE_ULTRA, des identifiants opaques, pas des montants ; dupliquer un
appel Stripe réel dans ce test unitaire serait disproportionné pour 3
constantes qui n'ont plus changé depuis leur dernière vérification manuelle,
voir Chantier 6). Ces 3 valeurs restent donc des littéraux ici, comme dans le
HTML lui-même.
"""
import unittest
from pathlib import Path

import quota_service
import server
from plan_service import Plan
from quota_service import QuotaType

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

# Textes qui ne doivent plus jamais réapparaître sur une page CLIENT —
# chacun confirmé faux par l'audit (Feature déclarée mais jamais consommée
# par aucune route, ou différenciation par plan inexistante en pratique).
_FORBIDDEN_CLIENT_PROMISES = (
    "Statistiques avancées et badges exclusifs",
    "Statistiques avancées",
    "badges exclusifs",
    "Support prioritaire par email",
    "Support prioritaire dédié",
    "Priorité de traitement",
    "réponse < 24h",
    "Accès anticipé aux nouvelles fonctionnalités",
    "Accès anticipé aux nouveautés",
    "Génération d'exercices sur mesure illimitée",
    "Conversations plus longues",
    "Réponses très longues",
    "1 export PDF par mois",
    "Exports PDF illimités",
    "Recommandations personnalisées",
)


def _read(filename):
    return (STATIC_DIR / filename).read_text(encoding="utf-8")


class _ClientPageCoherenceMixin:
    """Appliqué à abonnement.html ET index.html (voir sous-classes) — les
    deux pages doivent raconter exactement la même histoire (Phase 6)."""

    filename = None  # défini par les sous-classes

    def setUp(self):
        self.html = _read(self.filename)

    def test_aucune_promesse_interdite(self):
        for text in _FORBIDDEN_CLIENT_PROMISES:
            self.assertNotIn(text, self.html, f"Promesse obsolète encore présente : {text!r}")

    def test_chat_messages_correspond_a_quota_matrix(self):
        for plan in (Plan.FREE, Plan.PREMIUM, Plan.ULTRA):
            limit = quota_service.QUOTA_MATRIX[plan][QuotaType.CHAT_MESSAGES]
            self.assertIsNotNone(limit, f"CHAT_MESSAGES ne devrait jamais être illimité ({plan})")
            self.assertIn(f"{limit} messages/jour", self.html)

    def test_appels_ia_jour_absent_de_laffichage_client(self):
        # Chantier "Simplification affichage chatbot" (2026-08-27) : le
        # nombre d'appels IA/jour (LLM_CALLS) n'est plus affiché sur les
        # pages client, volontairement — seul le nombre de messages
        # chatbot/jour reste visible. QUOTA_MATRIX/LLM_CALLS restent
        # inchangés côté backend (voir quota_service.py) : ce test garantit
        # uniquement que ce chiffre ne réapparaît plus dans le marketing.
        self.assertNotIn("appels IA/jour", self.html)

    def test_exercises_daily_correspond_a_quota_matrix(self):
        free_limit = quota_service.QUOTA_MATRIX[Plan.FREE][QuotaType.EXERCISES_DAILY]
        premium_limit = quota_service.QUOTA_MATRIX[Plan.PREMIUM][QuotaType.EXERCISES_DAILY]
        ultra_limit = quota_service.QUOTA_MATRIX[Plan.ULTRA][QuotaType.EXERCISES_DAILY]
        self.assertIn(f"{free_limit} exercices/jour", self.html)
        self.assertIn(f"{premium_limit} exercices/jour", self.html)
        self.assertIsNone(ultra_limit, "Ultra doit rester illimité pour EXERCISES_DAILY")
        self.assertIn("Exercices illimités", self.html)

    def test_suggestions_correspond_a_suggestions_limit_by_plan(self):
        for plan in (Plan.FREE, Plan.PREMIUM, Plan.ULTRA):
            limit = server._SUGGESTIONS_LIMIT_BY_PLAN[plan]
            self.assertIn(f"{limit} suggestions de révision", self.html)

    def test_prix_inchanges(self):
        # Littéraux assumés — voir docstring du module.
        self.assertIn("0€", self.html)
        self.assertIn("6,99€", self.html)
        self.assertIn("12,99€", self.html)

    # Chantier "Différenciateurs Premium/Ultra" (2026-08-27) : les 2 nouveaux
    # différenciateurs réellement implémentés doivent apparaître UNE FOIS,
    # dans la bonne carte — jamais sur Free (littéraux assumés : ce sont des
    # noms de fonctionnalités, aucune constante Python ne les porte, comme
    # les prix ci-dessus).
    def test_bilan_notion_uniquement_dans_premium_et_ultra(self):
        self.assertIn("Bilan de progression détaillé par notion", self.html)

    def test_generation_sur_mesure_uniquement_dans_ultra(self):
        self.assertIn("Génération d'exercices sur mesure", self.html)


class TestAbonnementHtmlCoherence(_ClientPageCoherenceMixin, unittest.TestCase):
    filename = "abonnement.html"


class TestIndexHtmlCoherence(_ClientPageCoherenceMixin, unittest.TestCase):
    filename = "index.html"


class TestSuggestionsLimitByPlanEstBienUneMatricePlan(unittest.TestCase):
    """Garde-fou structurel : _SUGGESTIONS_LIMIT_BY_PLAN doit couvrir
    exactement les 3 plans, dans l'ordre croissant attendu — si un futur
    chantier modifie ces valeurs sans mettre à jour le HTML, les tests
    ci-dessus échoueront ; celui-ci protège contre une matrice mal formée."""

    def test_couvre_exactement_les_3_plans(self):
        self.assertEqual(set(server._SUGGESTIONS_LIMIT_BY_PLAN.keys()), {Plan.FREE, Plan.PREMIUM, Plan.ULTRA})

    def test_ordre_croissant_free_premium_ultra(self):
        m = server._SUGGESTIONS_LIMIT_BY_PLAN
        self.assertLess(m[Plan.FREE], m[Plan.PREMIUM])
        self.assertLess(m[Plan.PREMIUM], m[Plan.ULTRA])


if __name__ == "__main__":
    unittest.main()
