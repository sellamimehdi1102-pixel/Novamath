"""
Suite de tests Phase 4 — outils d'audit et de perfectionnement (Missions
1 à 8). Ces outils sont des ANALYSEURS PURS : aucun ne modifie une réponse
envoyée à l'élève ni un fichier de cours. Cette suite vérifie leur
correction sur les données réelles du projet (contenu de cours, immuable
pendant les tests), et (Mission 9) que le hook d'observabilité ajouté à
`conversation_manager.py` reste désactivable sans changer la réponse.
"""
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import db
from chatbot import conversation_manager as cm
from chatbot.services import (
    diversity_audit, dev_dashboard, knowledge_audit, llm_call_analytics,
    pipeline_metrics, response_quality, response_strategy as rs, ux_analytics,
)

# Utilisateur factice (jamais inséré en base) : uniquement utilisé par les
# tests qui appellent `response_strategy.decide_strategy(..., student_context=...)`
# avec un `student_context` explicite — aucune de ces fonctions ne touche la
# base de données ou un fichier de progression réel, donc aucun besoin d'un
# compte existant. `id` n'a pas besoin d'être un identifiant valide.
REAL_USER = {"id": 999999, "pseudo": "test_user", "level": 1}


# ── Mission 1 : audit de complétude ─────────────────────────────────────────
class TestKnowledgeAudit(unittest.TestCase):
    def test_audit_chapter_connu(self):
        result = knowledge_audit.audit_chapter("Chapitre_1")
        self.assertIsNotNone(result)
        self.assertEqual(result["chapter_id"], "Chapitre_1")
        self.assertGreater(result["notion_count"], 0)
        self.assertEqual(result["definitions"], 100.0)  # donnée réelle connue

    def test_audit_chapitre_inconnu_renvoie_none(self):
        self.assertIsNone(knowledge_audit.audit_chapter("Chapitre_999"))

    def test_audit_all_score_global_coherent(self):
        result = knowledge_audit.audit_all()
        self.assertEqual(result["total_chapters"], 12)
        self.assertGreater(result["total_notions"], 0)
        self.assertTrue(0 <= result["project_score_global"] <= 100)

    def test_poids_des_dimensions_somme_100(self):
        self.assertEqual(sum(knowledge_audit.DIMENSION_WEIGHTS.values()), 100)

    def test_format_chapter_report_ne_plante_pas(self):
        report = knowledge_audit.format_chapter_report(knowledge_audit.audit_chapter("Chapitre_1"))
        self.assertIn("Score global", report)


# ── Mission 2 : détection des manques ────────────────────────────────────────
class TestGapDetection(unittest.TestCase):
    def test_gaps_connus_sur_les_donnees_reelles(self):
        """Les champs proprietes/prerequis/liens/vocabulaire/demonstrations
        sont vides sur TOUTES les notions migrées aujourd'hui (constaté par
        l'audit réel, voir rapport de phase) — ce test fige ce constat."""
        summary = knowledge_audit.gaps_summary()
        for dim in ("proprietes", "prerequis", "liens", "vocabulaire", "demonstrations"):
            self.assertEqual(summary[dim], summary_total_notions())

    def test_gaps_tries_par_priorite(self):
        gaps = knowledge_audit.list_gaps()
        priorities = [g["priority"] for g in gaps]
        self.assertEqual(priorities, sorted(priorities))

    def test_gaps_scopes_par_chapitre(self):
        gaps_ch1 = knowledge_audit.list_gaps("Chapitre_1")
        self.assertTrue(all(g["chapter_id"] == "Chapitre_1" for g in gaps_ch1))


def summary_total_notions():
    return knowledge_audit.audit_all()["total_notions"]


# ── Mission 3 : classification et journalisation des appels LLM ─────────────
class TestLLMCallAnalytics(unittest.TestCase):
    def setUp(self):
        llm_call_analytics.reset()

    def test_classify_reason_strategy_none(self):
        self.assertEqual(llm_call_analytics.classify_reason(None), llm_call_analytics.REASON_PROBLEME_ROUTAGE)

    # `student_context` explicite avec un contexte élève "complet" (au sens
    # de `response_strategy._context_is_complete` : chapitre courant OU
    # historique d'exercices non vide) — le score de confiance dépend de
    # cette complétude (30 pts moteur dispo + 15 pts contexte complet = 45
    # >= CONFIDENCE_THRESHOLD=40). Sans ce contexte explicite, la fonction
    # relirait le fichier de progression réel de l'utilisateur (auth.py
    # read_user_stats), rendant le test dépendant d'un état externe mutable.
    _COMPLETE_CONTEXT = {"statistiques": {"total_exercices": 1}}

    def test_classify_reason_hors_programme(self):
        strategy = rs.decide_strategy(
            "Raconte-moi une blague sur les licornes qui font du velo", REAL_USER, use_cache=False,
            student_context=self._COMPLETE_CONTEXT,
        )
        self.assertEqual(llm_call_analytics.classify_reason(strategy), llm_call_analytics.REASON_HORS_PROGRAMME)

    def test_record_et_snapshot(self):
        strategy = rs.decide_strategy(
            "Question totalement hors programme sur les licornes", REAL_USER, use_cache=False,
            student_context=self._COMPLETE_CONTEXT,
        )
        llm_call_analytics.record("Question totalement hors programme sur les licornes", strategy)
        snap = llm_call_analytics.snapshot()
        self.assertEqual(snap["total_llm_calls_logged"], 1)
        self.assertIn(llm_call_analytics.REASON_HORS_PROGRAMME, snap["by_reason"])

    def test_record_ne_leve_jamais_exception(self):
        try:
            llm_call_analytics.record("message", "pas-une-vraie-strategie")
        except Exception as exc:  # ne doit jamais arriver
            self.fail(f"record() a levé une exception : {exc}")

    def test_suggest_reduction_ne_plante_jamais(self):
        strategy = rs.decide_strategy("Raconte-moi une blague", REAL_USER, use_cache=False)
        llm_call_analytics.record("Raconte-moi une blague", strategy)
        suggestions = llm_call_analytics.suggest_reductions()
        self.assertGreaterEqual(len(suggestions), 1)
        self.assertIn("suggestion", suggestions[0])


# ── Mission 5 : qualité des réponses ────────────────────────────────────────
class TestResponseQuality(unittest.TestCase):
    def test_score_texte_vide(self):
        result = response_quality.score_response("", [])
        self.assertEqual(result["score_global"], 0.0)

    def test_score_reponse_riche(self):
        result = response_quality.score_response(
            "Voici la définition. Voici la méthode. Voici un exemple.",
            ["introduction", "definition", "methode", "exemple", "ouverture"],
        )
        self.assertGreater(result["score_global"], 50)
        self.assertIn("definition", result["blocs_presents"])

    def test_score_draft_reel(self):
        from chatbot.services import knowledge_response_composer as krc
        strategy = rs.decide_strategy("C'est quoi une puissance ?", REAL_USER, use_cache=False)
        draft = krc.compose(strategy, student_context={})
        result = response_quality.score_draft(draft)
        self.assertTrue(0 <= result["score_global"] <= 100)


# ── Mission 6 : diversité ────────────────────────────────────────────────────
class TestDiversityAudit(unittest.TestCase):
    def test_audit_pool_size_detecte_les_petits_pools(self):
        result = diversity_audit.audit_pool_size()
        self.assertTrue(any(v["sous_le_minimum_recommande"] for v in result.values()))

    def test_simulate_usage_deterministe_avec_seed(self):
        r1 = diversity_audit.simulate_usage(n=50, seed=1)
        r2 = diversity_audit.simulate_usage(n=50, seed=1)
        self.assertEqual(r1, r2)

    def test_low_diversity_pools_ne_plante_pas(self):
        result = diversity_audit.low_diversity_pools(n=50, seed=1)
        self.assertIsInstance(result, list)


# ── Mission 7 : UX (périmètre honnête) ──────────────────────────────────────
class TestUXAnalytics(unittest.TestCase):
    def test_report_liste_bien_ce_qui_nest_pas_mesurable(self):
        report = ux_analytics.report()
        self.assertIn("nombre_de_clics", report["non_mesurable_avec_les_donnees_actuelles"])

    def test_messages_incompris_sans_requete(self):
        pipeline_metrics.reset()
        result = ux_analytics.messages_incompris()
        self.assertEqual(result["count"], 0)


# ── Mission 8 : tableau de bord agrégé ──────────────────────────────────────
class TestDevDashboard(unittest.TestCase):
    def test_snapshot_ne_plante_pas(self):
        data = dev_dashboard.snapshot(quality_sample_size=3)
        self.assertIn("pipeline", data)
        self.assertIn("knowledge_coverage", data)
        self.assertIn("response_quality_estimate", data)

    def test_format_report_ne_plante_pas(self):
        report = dev_dashboard.format_report(quality_sample_size=3)
        self.assertIn("Tableau de bord", report)


# ── Mission 9 : tout est optionnel, désactivable, sans régression ──────────
class TestMission9NonRegression(unittest.TestCase):
    """Exerce réellement `conversation_manager.stream_reply()` — a besoin
    d'un compte utilisateur valide en base. Utilise une base SQLite
    temporaire et un utilisateur créé par le test lui-même (jamais la base
    réelle, jamais un compte préexistant)."""

    def setUp(self):
        self._flag_backup = cm.ENABLE_LLM_CALL_ANALYTICS
        self._quota_patch = patch.object(cm, "check_and_increment_quota", return_value=1)
        self._quota_patch.start()
        llm_call_analytics.reset()
        pipeline_metrics.reset()

        tmp_dir = tempfile.mkdtemp()
        data_dir_backup, db_path_backup = db.DATA_DIR, db.DB_PATH
        db.DATA_DIR = Path(tmp_dir)
        db.DB_PATH = db.DATA_DIR / "novamath.db"
        db.init_db()

        def _restore_db():
            db.DATA_DIR = data_dir_backup
            db.DB_PATH = db_path_backup
            shutil.rmtree(tmp_dir, ignore_errors=True)

        self.addCleanup(_restore_db)

        user_id = db.create_user("phase4-mission9@test.local", "phase4_mission9", "Mission9 Test", "x")
        self.user = {"id": user_id, "pseudo": "Mission9 Test", "level": 1}

    def tearDown(self):
        cm.ENABLE_LLM_CALL_ANALYTICS = self._flag_backup
        self._quota_patch.stop()
        llm_call_analytics.reset()
        pipeline_metrics.reset()

    def test_analytics_desactive_ne_journalise_rien(self):
        cm.ENABLE_LLM_CALL_ANALYTICS = False
        conv = cm.create_conversation(self.user["id"], "Test Mission 9")
        try:
            list(cm.stream_reply(self.user, conv["id"], "Raconte-moi une blague sur les licornes qui font du velo"))
        finally:
            cm.delete_conversation(conv["id"], self.user["id"])
        self.assertEqual(llm_call_analytics.snapshot()["total_llm_calls_logged"], 0)

    def test_analytics_active_ne_change_pas_la_reponse(self):
        """La réponse doit être identique, flag activé ou non — cette
        journalisation est un pur aparté."""
        message = "Raconte-moi une blague sur les licornes qui font du velo"

        cm.ENABLE_LLM_CALL_ANALYTICS = False
        conv = cm.create_conversation(self.user["id"], "Test Mission 9 A")
        try:
            reponse_sans = "".join(cm.stream_reply(self.user, conv["id"], message))
        finally:
            cm.delete_conversation(conv["id"], self.user["id"])

        cm.ENABLE_LLM_CALL_ANALYTICS = True
        conv = cm.create_conversation(self.user["id"], "Test Mission 9 B")
        try:
            reponse_avec = "".join(cm.stream_reply(self.user, conv["id"], message))
        finally:
            cm.delete_conversation(conv["id"], self.user["id"])

        self.assertEqual(reponse_sans, reponse_avec)

    def test_panne_de_lanalytics_nempeche_pas_la_reponse(self):
        """`_record_llm_call` (conversation_manager.py) protège l'appel à
        llm_call_analytics.record() par son propre try/except — une panne ne
        doit JAMAIS empêcher la réponse d'être envoyée à l'élève."""
        with patch(
            "chatbot.conversation_manager.llm_call_analytics.record",
            side_effect=RuntimeError("panne simulée"),
        ):
            conv = cm.create_conversation(self.user["id"], "Test Mission 9 panne")
            try:
                texte = "".join(cm.stream_reply(self.user, conv["id"], "Raconte-moi une blague sur les licornes"))
            finally:
                cm.delete_conversation(conv["id"], self.user["id"])
        self.assertTrue(texte)


if __name__ == "__main__":
    unittest.main()
