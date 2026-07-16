"""
Suite de non-régression Phase 3B — intégration progressive du Response
Strategy Engine et du Local Response Engine dans `conversation_manager.py`.

Contrairement aux suites précédentes (moteurs isolés), celle-ci exerce
RÉELLEMENT `conversation_manager.stream_reply()`/`regenerate_last()` — le
point d'entrée production — sur un utilisateur réel (`mehdisellmi`, id=1),
avec le quota contourné (mock) pour ne pas consommer le quota réel de
l'utilisateur, et chaque conversation de test créée puis supprimée. Le
fournisseur IA actif est `FakeProvider` (pas d'appel réseau, voir
`chatbot/providers/fake_provider.py`) — sûr à exercer réellement ici.
"""
import unittest
from unittest.mock import patch

from chatbot import cache as llm_cache, conversation_manager as cm
from chatbot.services import pipeline_metrics, response_strategy as rs

REAL_USER = {"id": 1, "pseudo": "mehdisellmi", "level": 1}


class Phase3BTestCase(unittest.TestCase):
    """Bascule chaque flag à son état par défaut avant/après chaque test —
    un test qui modifie un flag ne doit jamais en affecter un autre."""

    def setUp(self):
        self._flags = (
            cm.ENABLE_INTENT_ENGINE_V2, cm.ENABLE_STUDENT_CONTEXT, cm.ENABLE_RESPONSE_STRATEGY,
            cm.ENABLE_LOCAL_RESPONSE_ENGINE, cm.ENABLE_LLM_FALLBACK,
        )
        self._allowed_engines_backup = set(cm.LOCAL_RESPONSE_ENGINE_ALLOWED_ENGINES)
        pipeline_metrics.reset()
        rs.clear_cache()
        llm_cache.clear()  # évite qu'une réponse LLM mise en cache par un autre test/fichier ne fausse celui-ci
        self._quota_patch = patch.object(cm, "check_and_increment_quota", return_value=1)
        self._quota_patch.start()

    def tearDown(self):
        self._quota_patch.stop()
        (cm.ENABLE_INTENT_ENGINE_V2, cm.ENABLE_STUDENT_CONTEXT, cm.ENABLE_RESPONSE_STRATEGY,
         cm.ENABLE_LOCAL_RESPONSE_ENGINE, cm.ENABLE_LLM_FALLBACK) = self._flags
        cm.LOCAL_RESPONSE_ENGINE_ALLOWED_ENGINES.clear()
        cm.LOCAL_RESPONSE_ENGINE_ALLOWED_ENGINES.update(self._allowed_engines_backup)
        pipeline_metrics.reset()
        rs.clear_cache()
        llm_cache.clear()

    def run_conversation(self, messages, mentions_map=None, debug=False):
        """Crée une conversation de test réelle, envoie chaque message, la
        supprime ensuite. Renvoie la liste des réponses (texte complet)."""
        mentions_map = mentions_map or {}
        conv = cm.create_conversation(REAL_USER["id"], "Test Phase 3B")
        conv_id = conv["id"]
        try:
            outputs = []
            for message in messages:
                text = "".join(cm.stream_reply(
                    REAL_USER, conv_id, message, mentions=mentions_map.get(message), debug=debug,
                ))
                outputs.append(text)
            return outputs
        finally:
            cm.delete_conversation(conv_id, REAL_USER["id"])


class TestAncienPipeline(Phase3BTestCase):
    """Tous les nouveaux flags désactivés : le pipeline doit se comporter
    EXACTEMENT comme avant la Phase 3B — uniquement des moteurs "legacy_*"/
    "llm"/"clarification", jamais rule_engine/knowledge_engine/dashboard/
    search_service (labels introduits par cette phase)."""

    def test_aucun_nouveau_moteur_nest_utilise(self):
        cm.ENABLE_RESPONSE_STRATEGY = False
        cm.ENABLE_LOCAL_RESPONSE_ENGINE = False
        cm.ENABLE_STUDENT_CONTEXT = False

        outputs = self.run_conversation([
            "Salut", "Resous 2x + 4 = 10", "C'est quoi une puissance ?", "Quelle est ma progression ?",
        ])
        self.assertTrue(all(outputs))
        stats = pipeline_metrics.snapshot()
        nouveaux_moteurs = {rs.ENGINE_RULE, rs.ENGINE_KNOWLEDGE, rs.ENGINE_DASHBOARD, rs.ENGINE_SEARCH}
        self.assertFalse(set(stats["by_engine"]) & nouveaux_moteurs)

    def test_reponses_identiques_aux_moteurs_legacy(self):
        """Les fonctions legacy (`rule_engine.try_handle`, etc.) restent
        appelées et produisent le même texte qu'avant cette phase."""
        cm.ENABLE_RESPONSE_STRATEGY = False
        cm.ENABLE_LOCAL_RESPONSE_ENGINE = False

        from chatbot import rule_engine
        attendu = rule_engine.try_handle("Salut")
        [obtenu] = self.run_conversation(["Salut"])
        self.assertEqual(obtenu, attendu)


class TestNouveauPipeline(Phase3BTestCase):
    """Tous les flags activés (comportement par défaut de cette phase)."""

    def test_taux_de_reponses_locales_eleve(self):
        outputs = self.run_conversation([
            "Salut", "Merci", "Resous 2x + 4 = 10", "C'est quoi une puissance ?",
            "Quelle est ma progression ?", "Les puissances",
        ])
        self.assertTrue(all(outputs))
        stats = pipeline_metrics.snapshot()
        self.assertGreaterEqual(stats["local_response_rate_pct"], 80.0)

    def test_moteurs_du_perimetre_deploye_sont_utilises(self):
        self.run_conversation(["Salut", "C'est quoi une puissance ?", "Quelle est ma progression ?"])
        stats = pipeline_metrics.snapshot()
        self.assertIn(rs.ENGINE_RULE, stats["by_engine"])
        self.assertIn(rs.ENGINE_KNOWLEDGE, stats["by_engine"])
        self.assertIn(rs.ENGINE_DASHBOARD, stats["by_engine"])

    def test_exercise_engine_reste_sur_lancien_chemin_etape_4_non_faite(self):
        """Exercise Engine n'est PAS dans LOCAL_RESPONSE_ENGINE_ALLOWED_ENGINES
        aujourd'hui (Étape 4, volontairement pas encore faite) — doit encore
        passer par `legacy_local_knowledge`."""
        self.run_conversation(["Donne-moi un exercice sur les puissances"])
        stats = pipeline_metrics.snapshot()
        self.assertIn("legacy_local_knowledge", stats["by_engine"])
        self.assertNotIn(rs.ENGINE_EXERCISE, stats["by_engine"])

    def test_mention_dashboard_repond_localement(self):
        mentions = [{"type": "data", "data_key": "dashboard", "label": "Dashboard"}]
        [obtenu] = self.run_conversation(["@Dashboard"], mentions_map={"@Dashboard": mentions})
        self.assertTrue(obtenu)
        stats = pipeline_metrics.snapshot()
        self.assertIn(rs.ENGINE_DASHBOARD, stats["by_engine"])

    def test_clarification_toujours_prioritaire(self):
        [obtenu] = self.run_conversation(["......"])
        self.assertIn("Pouvez-vous reformuler", obtenu)


class TestFeatureFlagsIndependants(Phase3BTestCase):
    def test_response_strategy_seul_ne_change_jamais_la_reponse(self):
        """ENABLE_RESPONSE_STRATEGY=True mais ENABLE_LOCAL_RESPONSE_ENGINE=False
        : la décision est calculée (aparté) mais la réponse doit rester celle
        de l'ancien pipeline (Étape 1 : jamais de changement de réponse)."""
        cm.ENABLE_RESPONSE_STRATEGY = True
        cm.ENABLE_LOCAL_RESPONSE_ENGINE = False

        from chatbot import rule_engine
        attendu = rule_engine.try_handle("Salut")
        [obtenu] = self.run_conversation(["Salut"])
        self.assertEqual(obtenu, attendu)
        stats = pipeline_metrics.snapshot()
        self.assertIn("legacy_internal", stats["by_engine"])
        self.assertNotIn(rs.ENGINE_RULE, stats["by_engine"])

    def test_local_response_engine_sans_response_strategy_reste_inactif(self):
        """Le Local Response Engine dépend de la décision du Strategy Engine
        — le désactiver désactive de fait le remplacement de réponse, même
        si ENABLE_LOCAL_RESPONSE_ENGINE=True."""
        cm.ENABLE_RESPONSE_STRATEGY = False
        cm.ENABLE_LOCAL_RESPONSE_ENGINE = True

        self.run_conversation(["Salut"])
        stats = pipeline_metrics.snapshot()
        self.assertNotIn(rs.ENGINE_RULE, stats["by_engine"])
        self.assertIn("legacy_internal", stats["by_engine"])

    def test_student_context_desactive_nempeche_pas_dashboard(self):
        """local_response_engine calcule son propre StudentContext si celui
        fourni est None — Dashboard doit continuer à fonctionner même avec
        ENABLE_STUDENT_CONTEXT=False."""
        cm.ENABLE_STUDENT_CONTEXT = False
        [obtenu] = self.run_conversation(["Quelle est ma progression ?"])
        self.assertTrue(obtenu)
        stats = pipeline_metrics.snapshot()
        self.assertIn(rs.ENGINE_DASHBOARD, stats["by_engine"])

    def test_intent_engine_v2_desactive_retombe_sur_intents_historiques(self):
        """Un intent introduit par le portage (ex. RESUME, "résume-moi") doit
        redevenir NONE_INTENT quand ENABLE_INTENT_ENGINE_V2=False — vérifié
        directement sur _classify_intent (fonction pure, pas besoin de
        rejouer tout le pipeline)."""
        from chatbot.services import intent_service
        cm.ENABLE_INTENT_ENGINE_V2 = False
        result = cm._classify_intent("Résume-moi les puissances", {"chapters_in_progress": []})
        self.assertEqual(result["intent"], intent_service.NONE_INTENT)

        cm.ENABLE_INTENT_ENGINE_V2 = True
        result = cm._classify_intent("Résume-moi les puissances", {"chapters_in_progress": []})
        self.assertEqual(result["intent"], intent_service.RESUME)

    def test_llm_fallback_desactive_renvoie_le_message_fixe(self):
        cm.ENABLE_LLM_FALLBACK = False
        [obtenu] = self.run_conversation(["Raconte-moi une blague sur les licornes qui font du velo"])
        self.assertEqual(obtenu, cm.LLM_DISABLED_MESSAGE)
        stats = pipeline_metrics.snapshot()
        self.assertIn("llm_disabled", stats["by_engine"])
        self.assertNotIn("llm", stats["by_engine"])


class TestActivationPartielle(Phase3BTestCase):
    def test_perimetre_restreint_a_dashboard_uniquement(self):
        """Retirer Knowledge/Search du périmètre déployé doit faire retomber
        les questions de définition sur l'ancien pipeline, sans toucher au
        comportement de Dashboard."""
        cm.LOCAL_RESPONSE_ENGINE_ALLOWED_ENGINES.clear()
        cm.LOCAL_RESPONSE_ENGINE_ALLOWED_ENGINES.update({rs.ENGINE_RULE, rs.ENGINE_DASHBOARD})

        self.run_conversation(["C'est quoi une puissance ?", "Quelle est ma progression ?"])
        stats = pipeline_metrics.snapshot()
        self.assertNotIn(rs.ENGINE_KNOWLEDGE, stats["by_engine"])
        self.assertIn("legacy_internal", stats["by_engine"])
        self.assertIn(rs.ENGINE_DASHBOARD, stats["by_engine"])

    def test_perimetre_vide_equivaut_a_lancien_pipeline(self):
        cm.LOCAL_RESPONSE_ENGINE_ALLOWED_ENGINES.clear()
        self.run_conversation(["Salut", "Quelle est ma progression ?"])
        stats = pipeline_metrics.snapshot()
        nouveaux_moteurs = {rs.ENGINE_RULE, rs.ENGINE_KNOWLEDGE, rs.ENGINE_DASHBOARD, rs.ENGINE_SEARCH}
        self.assertFalse(set(stats["by_engine"]) & nouveaux_moteurs)


class TestCompatibiliteAscendante(Phase3BTestCase):
    def test_stream_reply_sans_argument_debug_fonctionne_toujours(self):
        """Les appelants existants (server.py) n'ont jamais besoin de passer
        `debug` — l'ancienne signature reste valide."""
        conv = cm.create_conversation(REAL_USER["id"], "Test compat")
        try:
            text = "".join(cm.stream_reply(REAL_USER, conv["id"], "Salut"))
            self.assertTrue(text)
        finally:
            cm.delete_conversation(conv["id"], REAL_USER["id"])

    def test_regenerate_last_fonctionne_avec_le_nouveau_pipeline(self):
        conv = cm.create_conversation(REAL_USER["id"], "Test regenerate")
        try:
            "".join(cm.stream_reply(REAL_USER, conv["id"], "C'est quoi une puissance ?"))
            regenerated = "".join(cm.regenerate_last(REAL_USER, conv["id"]))
            self.assertTrue(regenerated)
            stats = pipeline_metrics.snapshot()
            self.assertIn(rs.ENGINE_KNOWLEDGE, stats["by_engine"])
        finally:
            cm.delete_conversation(conv["id"], REAL_USER["id"])

    def test_attach_action_cards_toujours_fonctionnel(self):
        conv = cm.create_conversation(REAL_USER["id"], "Test cards")
        try:
            "".join(cm.stream_reply(REAL_USER, conv["id"], "Donne-moi un exercice sur les puissances"))
            cards = cm.attach_action_cards(REAL_USER, conv["id"])
            self.assertIsInstance(cards, list)
        finally:
            cm.delete_conversation(conv["id"], REAL_USER["id"])


class TestRetryLast(Phase3BTestCase):
    """`retry_last` (robustesse réseau) : rejoue la génération pour le
    dernier message utilisateur sans jamais le dupliquer en base — le cas
    d'une tentative précédente interrompue avant toute réponse persistée."""

    def test_leve_une_erreur_si_la_conversation_est_vide(self):
        conv = cm.create_conversation(REAL_USER["id"], "Test retry vide")
        try:
            with self.assertRaises(ValueError):
                "".join(cm.retry_last(REAL_USER, conv["id"]))
        finally:
            cm.delete_conversation(conv["id"], REAL_USER["id"])

    def test_leve_une_erreur_si_une_reponse_a_deja_ete_persistee(self):
        """Le dernier message est déjà un message assistant (le tour a
        réussi) : rien à réessayer, c'est `regenerate_last` qu'il faut
        utiliser — jamais `retry_last`, pour ne jamais générer deux réponses
        pour un même tour."""
        conv = cm.create_conversation(REAL_USER["id"], "Test retry deja repondu")
        try:
            "".join(cm.stream_reply(REAL_USER, conv["id"], "Salut"))
            with self.assertRaises(ValueError):
                "".join(cm.retry_last(REAL_USER, conv["id"]))
        finally:
            cm.delete_conversation(conv["id"], REAL_USER["id"])

    def test_genere_une_reponse_sans_dupliquer_le_message_utilisateur(self):
        """Simule l'état laissé par une tentative échouée avant toute
        persistance assistant (panne réseau/fournisseur) : un seul message
        utilisateur en base, aucune réponse. `retry_last` doit produire une
        réponse et l'historique final ne doit contenir qu'UN SEUL message
        utilisateur — jamais un second envoi du même texte."""
        conv = cm.create_conversation(REAL_USER["id"], "Test retry echec reseau")
        try:
            cm.db.add_message(conv["id"], "user", "C'est quoi une puissance ?")
            texte = "".join(cm.retry_last(REAL_USER, conv["id"]))
            self.assertTrue(texte)

            rows = cm.db.list_messages(conv["id"])
            roles = [r["role"] for r in rows]
            self.assertEqual(roles.count("user"), 1)
            self.assertEqual(roles, ["user", "assistant"])
        finally:
            cm.delete_conversation(conv["id"], REAL_USER["id"])


class TestErreursAbsorbees(Phase3BTestCase):
    def test_panne_du_strategy_engine_ne_bloque_pas_la_reponse(self):
        with patch(
            "chatbot.conversation_manager.response_strategy.decide_strategy",
            side_effect=RuntimeError("panne simulée"),
        ):
            [obtenu] = self.run_conversation(["Salut"])
        self.assertTrue(obtenu)
        stats = pipeline_metrics.snapshot()
        self.assertIn("legacy_internal", stats["by_engine"])

    def test_panne_du_local_response_engine_ne_bloque_pas_la_reponse(self):
        with patch(
            "chatbot.conversation_manager.local_response_engine.generate",
            side_effect=RuntimeError("panne simulée"),
        ):
            [obtenu] = self.run_conversation(["C'est quoi une puissance ?"])
        self.assertTrue(obtenu)


class TestMetriques(Phase3BTestCase):
    def test_snapshot_sans_requete_ne_plante_pas(self):
        pipeline_metrics.reset()
        stats = pipeline_metrics.snapshot()
        self.assertEqual(stats["total_requests"], 0)
        self.assertEqual(stats["local_response_rate_pct"], 0.0)

    def test_reset_reinitialise_tout(self):
        self.run_conversation(["Salut"])
        pipeline_metrics.reset()
        stats = pipeline_metrics.snapshot()
        self.assertEqual(stats["total_requests"], 0)
        self.assertEqual(stats["by_engine"], {})


if __name__ == "__main__":
    unittest.main()
