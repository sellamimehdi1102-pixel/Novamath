"""
Suite dédiée au Chantier 10 "architecture solide et centralisée du feature
gating par abonnement" (2026-08-25).

Ce chantier n'a PAS recréé l'architecture (déjà centralisée depuis le
Chantier 8 : Plan/Feature/FEATURE_MATRIX/has_feature()/requires_feature()
dans plan_service.py, user.features exposé par auth.py::_public_user). Il a
consolidé le SEUL vrai point de divergence trouvé par l'audit : abonnement.js
recalculait localement l'accès à une feature à partir de user.plan (le plan
RÉEL) au lieu de faire confiance à user.features (déjà Owner-aware) — voir
webapp/static/js/__tests__/abonnement.test.js pour la régression JS
correspondante, et sidebar.test.js pour la couverture (jusqu'ici absente) du
mécanisme de cadenas PAGE_FEATURE_REQUIREMENTS.

Ce fichier couvre exclusivement ce qui n'est PAS déjà couvert par
test_plan_service.py (matrices Free/Premium/Ultra, has_feature, requires_feature,
minimal_plan_for_feature) ni par test_owner_test_plan_service.py (effective_plan,
/api/auth/me, Owner) ni par test_server_feature_gating.py (routes protégées) —
jamais dupliqué :

- TestFeatureInconnueJamaisAccordee : une valeur de feature qui n'existe pas
  dans Feature ne doit JAMAIS accorder d'accès, quel que soit le plan
  (garde-fou "fail-closed", pas seulement vérifié par construction du type
  mais explicitement testé pour ne jamais régresser silencieusement).
- TestAucuneComparaisonDePlanEnDurCoteJs : garde-fou structurel (analyse
  statique du dépôt) — aucun fichier JS de production ne doit recalculer une
  décision d'accès via planMeetsRequirement()/comparaison de user.plan en dur
  en dehors de features.js lui-même (sa propre définition + son repli
  documenté dans hasFeature()) — empêche la réapparition du bug corrigé dans
  abonnement.js.
"""
import re
import unittest
from pathlib import Path

import plan_service
from plan_service import Feature, Plan


class TestFeatureInconnueJamaisAccordee(unittest.TestCase):
    def test_chaine_inconnue_jamais_accordee_meme_pour_ultra(self):
        user = {"id": 1, "plan": "ultra"}
        self.assertFalse(plan_service.has_feature(user, "feature_qui_n_existe_pas"))

    def test_chaine_vide_jamais_accordee(self):
        user = {"id": 1, "plan": "ultra"}
        self.assertFalse(plan_service.has_feature(user, ""))

    def test_none_jamais_accorde(self):
        user = {"id": 1, "plan": "ultra"}
        self.assertFalse(plan_service.has_feature(user, None))

    def test_aucune_exception_levee(self):
        # Fail-closed, jamais fail-crash : une valeur inattendue ne doit
        # jamais faire planter la vérification d'accès (qui bloquerait alors
        # TOUT l'utilisateur au lieu de simplement refuser cette feature).
        user = {"id": 1, "plan": "free"}
        try:
            plan_service.has_feature(user, object())
        except Exception as exc:  # pragma: no cover - ne doit jamais arriver
            self.fail(f"has_feature() a levé {type(exc).__name__}: {exc}")


class TestAucuneComparaisonDePlanEnDurCoteJs(unittest.TestCase):
    """Analyse statique légère (regex, pas un vrai parseur JS) du dépôt —
    volontairement stricte : toute nouvelle occurrence doit être justifiée
    explicitement (ajoutée à ALLOWED) plutôt que de passer inaperçue."""

    STATIC_JS_DIR = Path(__file__).resolve().parent.parent / "static" / "js"

    # Fichiers où `planMeetsRequirement(` est légitime :
    # - features.js : sa propre définition, et son unique repli documenté
    #   dans hasFeature() (utilisé UNIQUEMENT si user.features est absent).
    # - __tests__/features.test.js : teste directement cette fonction pure.
    ALLOWED_PLAN_MEETS_REQUIREMENT = {"features.js", "features.test.js"}

    def test_planMeetsRequirement_jamais_utilise_hors_de_features_js(self):
        offenders = []
        for path in self.STATIC_JS_DIR.rglob("*.js"):
            if path.name in self.ALLOWED_PLAN_MEETS_REQUIREMENT:
                continue
            text = path.read_text(encoding="utf-8")
            if re.search(r"\bplanMeetsRequirement\s*\(", text):
                offenders.append(str(path.relative_to(self.STATIC_JS_DIR)))
        self.assertEqual(
            offenders, [],
            "planMeetsRequirement() utilisé hors de features.js — décision "
            "d'accès potentiellement recalculée localement au lieu de passer "
            f"par hasFeature(user, feature) : {offenders}",
        )

    def test_aucune_comparaison_directe_de_user_plan_pour_decider_un_acces(self):
        # Recherche restrictive : `user.plan === "premium"` / `user.plan == 'ultra'`
        # etc., UNIQUEMENT dans les fichiers de production (pas les tests, pas
        # les widgets qui affichent légitimement le nom du plan réel — voir
        # identity.js::planLabel(user.plan) ou owner-test-panel.js comparant
        # son propre état de test, jamais une décision d'accès à une feature).
        pattern = re.compile(r"user\.plan\s*===?\s*[\"'](free|premium|ultra)[\"']")
        allowed = {"owner-test-panel.js"}  # widget Owner : compare son état interne, pas un accès feature
        offenders = []
        for path in self.STATIC_JS_DIR.glob("*.js"):
            if path.name in allowed:
                continue
            text = path.read_text(encoding="utf-8")
            if pattern.search(text):
                offenders.append(path.name)
        self.assertEqual(
            offenders, [],
            f"Comparaison directe de user.plan trouvée hors des exceptions connues : {offenders}",
        )


class TestFeatureMatrixSeuleSourceDuPlanMinimum(unittest.TestCase):
    """minimal_plan_for_feature() doit rester dérivé de FEATURE_MATRIX —
    jamais une seconde table à resynchroniser à la main côté backend (à la
    différence du repli purement cosmétique FEATURE_META côté JS, documenté
    comme un miroir volontaire de labels d'affichage)."""

    def test_minimal_plan_for_feature_coherent_pour_toute_feature_connue(self):
        for feature in Feature:
            minimal = plan_service.minimal_plan_for_feature(feature)
            for plan in Plan:
                attendu = feature in plan_service.FEATURE_MATRIX[plan]
                if plan_service._PLAN_ORDER.index(plan) >= plan_service._PLAN_ORDER.index(minimal):
                    self.assertTrue(
                        attendu,
                        f"{feature} devrait être incluse dans {plan} (>= {minimal}) via FEATURE_MATRIX",
                    )


if __name__ == "__main__":
    unittest.main()
