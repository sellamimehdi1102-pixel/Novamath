"""
Suite fonctionnelle du Student Context Resolver v2 (Response Engine v2,
Phase 2) : forme du StudentContext, normalisation des paramètres/mentions/
historique, résolution canonique du chapitre/topic courant, comportement du
cache (TTL, invalidation), et non-régression sur context_builder.py/
variable_resolver.py (aucun changement de comportement, seulement 2 champs
additifs : mastered_topics, et le resolver lui-même).
"""
import unittest
from unittest.mock import patch

from chatbot import context_builder, student_context_resolver as scr
from chatbot.validate_student_context import validate_student_context

FAKE_HISTORY = [
    # Chapitre_4 : Condition de colinéarité — ratée (doit apparaître en faible)
    *[{"chapter": "Chapitre_4", "notion": "Condition de colinéarité", "correct": False} for _ in range(5)],
    # Chapitre_5 : même texte de notion, réussie (doit apparaître en maîtrisée, PAS conflatée avec Chapitre_4)
    *[{"chapter": "Chapitre_5", "notion": "Condition de colinéarité", "correct": True} for _ in range(12)],
]


def _fake_stats(history=None):
    return {"xp": 0, "badges": [], "series": [], "history": history if history is not None else []}


def _fake_settings():
    return {"chatbot": {"responseLength": "detaille", "mode": "professeur"}, "favorites": ["Chapitre_1"], "language": "fr"}


class TestFormeDuContexte(unittest.TestCase):
    @patch("chatbot.student_context_resolver.read_user_course_progress")
    @patch("chatbot.student_context_resolver.read_user_stats")
    @patch("chatbot.student_context_resolver.read_user_settings")
    def test_resolve_produit_un_contexte_valide(self, mock_settings, mock_stats, mock_progress):
        mock_stats.return_value = _fake_stats(FAKE_HISTORY)
        mock_settings.return_value = _fake_settings()
        mock_progress.return_value = {}
        scr.clear_cache()

        user = {"id": "test-user-1", "pseudo": "Alice", "level": 2}
        context = scr.resolve(user, use_cache=False)

        errors = validate_student_context(context)
        self.assertEqual(errors, [], f"StudentContext invalide : {errors}")

    @patch("chatbot.student_context_resolver.read_user_course_progress")
    @patch("chatbot.student_context_resolver.read_user_stats")
    @patch("chatbot.student_context_resolver.read_user_settings")
    def test_utilisateur_sans_donnees_ne_plante_pas(self, mock_settings, mock_stats, mock_progress):
        """Un élève neuf (aucun fichier de données) doit produire un contexte
        valide avec des champs vides, jamais une exception."""
        mock_stats.return_value = _fake_stats()
        mock_settings.return_value = {"chatbot": {}, "favorites": [], "language": "fr"}
        mock_progress.return_value = {}
        scr.clear_cache()

        user = {"id": "brand-new-user", "pseudo": "Bob", "level": 1}
        context = scr.resolve(user, use_cache=False)

        self.assertEqual(validate_student_context(context), [])
        self.assertEqual(context["notions_faibles"], [])
        self.assertEqual(context["topics_faibles"], [])


class TestDesambiguisationTopicsMaitrisesEtFaibles(unittest.TestCase):
    """Preuve directe que le resolver n'hérite PAS du bug de conflation
    corrigé lors du chantier canonical_ids : "Condition de colinéarité"
    (texte identique en Chapitre_4 et Chapitre_5) doit apparaître comme
    FAIBLE pour Chapitre_4 et MAÎTRISÉE pour Chapitre_5, jamais mélangées."""

    @patch("chatbot.student_context_resolver.read_user_course_progress")
    @patch("chatbot.student_context_resolver.read_user_stats")
    @patch("chatbot.student_context_resolver.read_user_settings")
    def test_topics_correctement_distingues(self, mock_settings, mock_stats, mock_progress):
        mock_stats.return_value = _fake_stats(FAKE_HISTORY)
        mock_settings.return_value = _fake_settings()
        mock_progress.return_value = {}
        scr.clear_cache()

        user = {"id": "test-user-2", "pseudo": "Chloé", "level": 2}
        context = scr.resolve(user, use_cache=False)

        weak_chapters = {t["chapter_id"] for t in context["topics_faibles"]}
        mastered_chapters = {t["chapter_id"] for t in context["topics_maitrises"]}
        self.assertIn("Chapitre_4", weak_chapters)
        self.assertIn("Chapitre_5", mastered_chapters)
        self.assertNotIn("Chapitre_5", weak_chapters)
        self.assertNotIn("Chapitre_4", mastered_chapters)


class TestNormalisationParametres(unittest.TestCase):
    def test_valeurs_par_defaut(self):
        params = scr._normalize_parametres({})
        self.assertEqual(params["longueur"], "normal")
        self.assertEqual(params["niveau_explication"], "auto")
        self.assertTrue(params["memoire_activee"])

    def test_valeurs_fournies(self):
        params = scr._normalize_parametres({"responseLength": "court", "mode": "examen", "temperature": 0.2})
        self.assertEqual(params["longueur"], "court")
        self.assertEqual(params["mode"], "examen")
        self.assertEqual(params["temperature"], 0.2)


class TestNormalisationMentionsEtHistorique(unittest.TestCase):
    def test_mention_data_conservee_telle_quelle(self):
        resolved = scr._normalize_mentions([{"type": "data", "data_key": "dashboard", "label": "Dashboard"}])
        self.assertEqual(resolved, [{"type": "data", "data_key": "dashboard", "label": "Dashboard"}])

    def test_mention_cours_resolue_avec_chapter_id_canonique(self):
        resolved = scr._normalize_mentions([
            {"type": "cours", "chapter_id": "Chapitre_1", "notion_id": "puissances-entieres-relatives"},
        ])
        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0]["chapter_id"], "Chapitre_1")
        self.assertEqual(resolved[0]["topic_id"], "puissances-entieres-relatives")

    def test_mention_invalide_ignoree_silencieusement(self):
        resolved = scr._normalize_mentions([{"type": "cours", "chapter_id": "Chapitre_1", "notion_id": "n-existe-pas"}])
        self.assertEqual(resolved, [])

    def test_historique_tronque(self):
        rows = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"msg{i}"} for i in range(30)]
        normalized = scr._normalize_history(rows)
        self.assertEqual(len(normalized), scr._MAX_HISTORY_TURNS)
        self.assertEqual(normalized[-1]["content"], "msg29")


class TestCache(unittest.TestCase):
    @patch("chatbot.student_context_resolver.read_user_course_progress")
    @patch("chatbot.student_context_resolver.read_user_stats")
    @patch("chatbot.student_context_resolver.read_user_settings")
    def test_second_appel_utilise_le_cache(self, mock_settings, mock_stats, mock_progress):
        mock_stats.return_value = _fake_stats()
        mock_settings.return_value = {"chatbot": {}, "favorites": [], "language": "fr"}
        mock_progress.return_value = {}
        scr.clear_cache()

        user = {"id": "cache-test-user", "pseudo": "Dan", "level": 1}
        scr.resolve(user, use_cache=True)
        scr.resolve(user, use_cache=True)

        # read_user_stats ne doit avoir été appelé qu'UNE fois (le second
        # resolve() a servi le contexte caché, pas relu le disque).
        self.assertEqual(mock_stats.call_count, 1)

    @patch("chatbot.student_context_resolver.read_user_course_progress")
    @patch("chatbot.student_context_resolver.read_user_stats")
    @patch("chatbot.student_context_resolver.read_user_settings")
    def test_invalidate_force_un_recalcul(self, mock_settings, mock_stats, mock_progress):
        mock_stats.return_value = _fake_stats()
        mock_settings.return_value = {"chatbot": {}, "favorites": [], "language": "fr"}
        mock_progress.return_value = {}
        scr.clear_cache()

        user = {"id": "cache-test-user-2", "pseudo": "Eve", "level": 1}
        scr.resolve(user, use_cache=True)
        scr.invalidate(user["id"])
        scr.resolve(user, use_cache=True)

        self.assertEqual(mock_stats.call_count, 2)

    @patch("chatbot.student_context_resolver.read_user_course_progress")
    @patch("chatbot.student_context_resolver.read_user_stats")
    @patch("chatbot.student_context_resolver.read_user_settings")
    def test_ttl_expire(self, mock_settings, mock_stats, mock_progress):
        mock_stats.return_value = _fake_stats()
        mock_settings.return_value = {"chatbot": {}, "favorites": [], "language": "fr"}
        mock_progress.return_value = {}
        scr.clear_cache()

        user = {"id": "cache-test-user-3", "pseudo": "Faz", "level": 1}
        scr.resolve(user, use_cache=True)
        # Force l'expiration en avançant artificiellement le timestamp caché.
        ts, value = scr._cache[user["id"]]
        scr._cache[user["id"]] = (ts - scr._CACHE_TTL_SECONDS - 1, value)
        scr.resolve(user, use_cache=True)

        self.assertEqual(mock_stats.call_count, 2)


class TestValidateur(unittest.TestCase):
    def test_detecte_un_topic_id_invalide(self):
        context = {
            "user_id": "x", "pseudo": "y", "niveau": "z", "niveau_brut": 1,
            "chapitre_courant": "Chapitre_1", "topic_courant": "n-existe-pas",
            "notions_maitrisees": [], "notions_faibles": [], "topics_maitrises": [], "topics_faibles": [],
            "mentions": [], "historique_conversation": [],
            "parametres": {
                "longueur": None, "niveau_explication": None, "mode": None, "memoire_activee": None,
                "historique_active": None, "provider": None, "modele": None, "temperature": None,
            },
            "statistiques": {"accuracy": None, "total_exercices": 0, "temps_total": "0 min", "temps_jour": "0 min", "temps_semaine": "0 min"},
            "dashboard": {"objectif_du_jour": {}, "chapitres_en_cours": [], "meilleur_chapitre": None, "chapitre_le_plus_faible": None},
            "preferences": {"langue": "fr", "niveau_explication": "auto", "favoris": []},
            "progression": {},
        }
        errors = validate_student_context(context)
        self.assertTrue(any("topic_courant" in e for e in errors))

    def test_contexte_reel_ne_produit_aucune_erreur(self):
        with patch("auth.read_user_course_progress", return_value={}), \
             patch("auth.read_user_stats", return_value=_fake_stats()), \
             patch("auth.read_user_settings", return_value={"chatbot": {}, "favorites": [], "language": "fr"}):
            scr.clear_cache()
            context = scr.resolve({"id": "validator-test", "pseudo": "Gaz", "level": 1}, use_cache=False)
        self.assertEqual(validate_student_context(context), [])


if __name__ == "__main__":
    unittest.main()
