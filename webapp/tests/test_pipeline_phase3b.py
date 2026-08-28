"""
Suite de non-régression Phase 3B — intégration progressive du Response
Strategy Engine et du Local Response Engine dans `conversation_manager.py`.

Contrairement aux suites précédentes (moteurs isolés), celle-ci exerce
RÉELLEMENT `conversation_manager.stream_reply()`/`regenerate_last()` — le
point d'entrée production — sur un utilisateur créé par le test lui-même
dans une base SQLite temporaire (jamais la base réelle, jamais un compte
préexistant), avec le quota contourné (mock) pour ne pas consommer de quota,
et chaque conversation de test créée puis supprimée. Le fournisseur IA actif
est `FakeProvider` (pas d'appel réseau, voir
`chatbot/providers/fake_provider.py`) — sûr à exercer réellement ici.
"""
import tempfile
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

import db
import quota_service
from chatbot import cache as llm_cache, conversation_manager as cm
from chatbot.services import pipeline_metrics, response_strategy as rs
from quota_service import QuotaType


class Phase3BTestCase(unittest.TestCase):
    """Bascule chaque flag à son état par défaut avant/après chaque test —
    un test qui modifie un flag ne doit jamais en affecter un autre. Isole
    aussi la base de données : chaque test tourne sur une base SQLite
    temporaire fraîche, avec son propre utilisateur créé ici — jamais sur la
    base réelle ni sur un compte préexistant (voir CLAUDE.md, exigence de
    tests autonomes)."""

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

        user_id = db.create_user("phase3b@test.local", "phase3b_user", "Phase3B Test", "x")
        self.REAL_USER = {"id": user_id, "pseudo": "Phase3B Test", "level": 1}

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
        conv = cm.create_conversation(self.REAL_USER["id"], "Test Phase 3B")
        conv_id = conv["id"]
        try:
            outputs = []
            for message in messages:
                text = "".join(cm.stream_reply(
                    self.REAL_USER, conv_id, message, mentions=mentions_map.get(message), debug=debug,
                ))
                outputs.append(text)
            return outputs
        finally:
            cm.delete_conversation(conv_id, self.REAL_USER["id"])


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
        self.assertIn("reformuler", obtenu)


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
        conv = cm.create_conversation(self.REAL_USER["id"], "Test compat")
        try:
            text = "".join(cm.stream_reply(self.REAL_USER, conv["id"], "Salut"))
            self.assertTrue(text)
        finally:
            cm.delete_conversation(conv["id"], self.REAL_USER["id"])

    def test_regenerate_last_fonctionne_avec_le_nouveau_pipeline(self):
        conv = cm.create_conversation(self.REAL_USER["id"], "Test regenerate")
        try:
            "".join(cm.stream_reply(self.REAL_USER, conv["id"], "C'est quoi une puissance ?"))
            regenerated = "".join(cm.regenerate_last(self.REAL_USER, conv["id"]))
            self.assertTrue(regenerated)
            stats = pipeline_metrics.snapshot()
            self.assertIn(rs.ENGINE_KNOWLEDGE, stats["by_engine"])
        finally:
            cm.delete_conversation(conv["id"], self.REAL_USER["id"])

    def test_attach_action_cards_toujours_fonctionnel(self):
        conv = cm.create_conversation(self.REAL_USER["id"], "Test cards")
        try:
            "".join(cm.stream_reply(self.REAL_USER, conv["id"], "Donne-moi un exercice sur les puissances"))
            cards = cm.attach_action_cards(self.REAL_USER, conv["id"])
            self.assertIsInstance(cards, list)
        finally:
            cm.delete_conversation(conv["id"], self.REAL_USER["id"])


class TestRegenerateConcurrence(Phase3BTestCase):
    """Durcissement production : deux régénérations concurrentes (double-clic,
    double onglet) sur le MÊME dernier message assistant ne doivent produire
    qu'UNE seule nouvelle réponse et consommer le quota qu'UNE seule fois —
    voir db.delete_message (jeton de course) et conversation_manager.
    regenerate_last."""

    def test_plusieurs_regenerations_concurrentes_ne_dupliquent_jamais(self):
        """6 threads appellent regenerate_last en même temps (Barrier) sur LE
        MÊME dernier message assistant. Avec un moteur de réponse aussi rapide
        que FakeProvider/le moteur local, plusieurs threads peuvent réellement
        gagner des tours SUCCESSIFS légitimes (thread A régénère, puis thread
        B régénère à son tour la nouvelle réponse de A, etc.) plutôt qu'une
        collision unique — ce n'est pas un bug, exiger "un seul gagnant total"
        serait donc un faux invariant. L'invariant réellement garanti par le
        durcissement (voir db.delete_message) est plus précis : chaque
        SUCCÈS correspond à EXACTEMENT un message assistant et EXACTEMENT une
        consommation de quota — jamais un succès qui laisse deux messages ou
        décrémente deux fois. On le vérifie en ralentissant artificiellement
        la fenêtre critique (patch de db.delete_message avec un léger délai)
        pour forcer un chevauchement réel et déterministe entre threads."""
        import threading
        import time as time_module

        conv = cm.create_conversation(self.REAL_USER["id"], "Test regenerate concurrent")
        try:
            "".join(cm.stream_reply(self.REAL_USER, conv["id"], "C'est quoi une puissance ?"))
            messages_before = db.list_messages(conv["id"])
            self.assertEqual(len(messages_before), 2)  # message utilisateur + réponse assistant

            n_threads = 6
            barrier = threading.Barrier(n_threads)
            results = []
            errors = []
            quota_calls = []
            lock = threading.Lock()

            def fake_quota(user):
                with lock:
                    quota_calls.append(1)
                return len(quota_calls)

            real_delete_message = db.delete_message

            def slow_delete_message(message_id):
                # Élargit délibérément la fenêtre entre "lire les messages" et
                # "gagner/perdre la course sur le DELETE" : sans ce délai,
                # FakeProvider est si rapide qu'un seul thread à la fois se
                # présente réellement à cette ligne (voir docstring), ce qui
                # ne teste jamais le cas de vraie collision.
                time_module.sleep(0.05)
                return real_delete_message(message_id)

            self._quota_patch.stop()
            counting_patch = patch.object(cm, "check_and_increment_quota", side_effect=fake_quota)
            counting_patch.start()
            delete_patch = patch.object(db, "delete_message", side_effect=slow_delete_message)
            delete_patch.start()

            def worker():
                barrier.wait()  # tous les threads démarrent regenerate_last au même instant
                try:
                    text = "".join(cm.regenerate_last(self.REAL_USER, conv["id"]))
                    with lock:
                        results.append(text)
                except ValueError as e:
                    with lock:
                        errors.append(e)

            threads = [threading.Thread(target=worker) for _ in range(n_threads)]
            try:
                for t in threads:
                    t.start()
                for t in threads:
                    t.join()
            finally:
                delete_patch.stop()
                counting_patch.stop()
                self._quota_patch.start()

            self.assertGreaterEqual(len(results), 1, "au moins une régénération doit réussir")
            self.assertEqual(len(results) + len(errors), n_threads)
            for e in errors:
                self.assertTrue(
                    "déjà en cours de régénération" in str(e) or "Rien à régénérer" in str(e),
                    f"message d'erreur inattendu : {e}",
                )

            # L'invariant central : jamais plus de messages assistant que de
            # succès réels, jamais plus de quota consommé que de succès réels
            # — quel que soit le nombre exact de gagnants (1 ou plusieurs
            # tours successifs légitimes selon le timing).
            messages_after = db.list_messages(conv["id"])
            self.assertEqual(len(messages_after), 1 + len(results))
            self.assertEqual(len(quota_calls), len(results))
        finally:
            cm.delete_conversation(conv["id"], self.REAL_USER["id"])


class TestCachePostFallback(Phase3BTestCase):
    """Release Candidate : si llm_fallback_service.generate() bascule vers un
    AUTRE fournisseur/modèle que celui initialement sélectionné (incident
    transitoire sur le fournisseur visé), la réponse ne doit JAMAIS être mise
    en cache sous la clé du fournisseur initial — sinon un futur message
    identique, alors que le fournisseur visé est redevenu disponible,
    recevrait à tort la réponse générée par le fournisseur de repli."""

    def _fake_generate_with_fallback(self, actual_provider, actual_model, text):
        def _generate(messages, system_prompt, chatbot_settings, user=None, call_info=None,
                      intent_result=None, class_level=None):
            call_info["provider"] = actual_provider
            call_info["model"] = actual_model
            yield text
        return _generate

    def test_reponse_mise_en_cache_sous_la_cle_du_fournisseur_reellement_utilise(self):
        conv = cm.create_conversation(self.REAL_USER["id"], "Test cache post-fallback")
        try:
            with patch.object(cm.provider_manager, "select_llm_for_user", return_value=("anthropic", "claude-x")), \
                 patch.object(cm.llm_fallback_service, "generate",
                               side_effect=self._fake_generate_with_fallback("gemini", "gemini-y", "Réponse de repli.")):
                text = "".join(cm.stream_reply(self.REAL_USER, conv["id"], "Question test cache fallback."))
            self.assertEqual(text, "Réponse de repli.")

            stale_key = llm_cache.make_key(
                self.REAL_USER["id"], "anthropic", "claude-x", "Question test cache fallback.",
            )
            actual_key = llm_cache.make_key(
                self.REAL_USER["id"], "gemini", "gemini-y", "Question test cache fallback.",
            )
            self.assertIsNone(
                llm_cache.get(stale_key),
                "la réponse ne doit jamais être servie sous la clé du fournisseur initialement visé",
            )
            self.assertEqual(llm_cache.get(actual_key), "Réponse de repli.")
        finally:
            cm.delete_conversation(conv["id"], self.REAL_USER["id"])


class TestRemboursementQuotaSurExceptionAvantLlm(Phase3BTestCase):
    """Release Candidate : une exception survenant AVANT tout appel réel au
    fournisseur IA (ex: bug dans la classification d'intention, le contexte
    RAG...) ne doit jamais laisser le quota facturé (check_and_increment_
    quota, en tête de stream_reply) sans qu'aucune réponse n'ait été produite
    — voir quota_service.refund(), câblé dans stream_reply."""

    def test_exception_avant_le_llm_rembourse_le_quota(self):
        self._quota_patch.stop()
        conv = cm.create_conversation(self.REAL_USER["id"], "Test remboursement quota")
        try:
            used_before = quota_service.usage_snapshot(self.REAL_USER, QuotaType.CHAT_MESSAGES)["used"]

            with patch.object(cm, "_classify_intent", side_effect=RuntimeError("panne simulée")):
                with self.assertRaises(RuntimeError):
                    "".join(cm.stream_reply(self.REAL_USER, conv["id"], "Une question."))

            used_after = quota_service.usage_snapshot(self.REAL_USER, QuotaType.CHAT_MESSAGES)["used"]
            self.assertEqual(used_after, used_before, "le quota facturé doit être intégralement remboursé")

            # Le message utilisateur reste persisté (l'historique de la
            # conversation ne doit jamais être perdu), mais aucune réponse
            # assistant n'a été produite pour ce tour.
            rows = db.list_messages(conv["id"])
            self.assertEqual([r["role"] for r in rows], ["user"])
        finally:
            self._quota_patch.start()
            cm.delete_conversation(conv["id"], self.REAL_USER["id"])

    def test_reponse_reussie_consomme_normalement_le_quota(self):
        """Non-régression : le chemin normal (aucune exception) continue de
        facturer exactement 1 unité, exactement comme avant ce correctif."""
        self._quota_patch.stop()
        conv = cm.create_conversation(self.REAL_USER["id"], "Test quota chemin normal")
        try:
            used_before = quota_service.usage_snapshot(self.REAL_USER, QuotaType.CHAT_MESSAGES)["used"]
            "".join(cm.stream_reply(self.REAL_USER, conv["id"], "Une question normale."))
            used_after = quota_service.usage_snapshot(self.REAL_USER, QuotaType.CHAT_MESSAGES)["used"]
            self.assertEqual(used_after, used_before + 1)
        finally:
            self._quota_patch.start()
            cm.delete_conversation(conv["id"], self.REAL_USER["id"])


class TestRetryLast(Phase3BTestCase):
    """`retry_last` (robustesse réseau) : rejoue la génération pour le
    dernier message utilisateur sans jamais le dupliquer en base — le cas
    d'une tentative précédente interrompue avant toute réponse persistée."""

    def test_leve_une_erreur_si_la_conversation_est_vide(self):
        conv = cm.create_conversation(self.REAL_USER["id"], "Test retry vide")
        try:
            with self.assertRaises(ValueError):
                "".join(cm.retry_last(self.REAL_USER, conv["id"]))
        finally:
            cm.delete_conversation(conv["id"], self.REAL_USER["id"])

    def test_leve_une_erreur_si_une_reponse_a_deja_ete_persistee(self):
        """Le dernier message est déjà un message assistant (le tour a
        réussi) : rien à réessayer, c'est `regenerate_last` qu'il faut
        utiliser — jamais `retry_last`, pour ne jamais générer deux réponses
        pour un même tour."""
        conv = cm.create_conversation(self.REAL_USER["id"], "Test retry deja repondu")
        try:
            "".join(cm.stream_reply(self.REAL_USER, conv["id"], "Salut"))
            with self.assertRaises(ValueError):
                "".join(cm.retry_last(self.REAL_USER, conv["id"]))
        finally:
            cm.delete_conversation(conv["id"], self.REAL_USER["id"])

    def test_relache_la_reservation_apres_echec_et_permet_un_nouvel_essai(self):
        """Durcissement production : la réclamation posée par retry_last ne
        doit jamais bloquer un VRAI nouvel essai séquentiel après un échec
        (panne réseau/fournisseur qui se reproduit) — seule une course
        concurrente doit être bloquée, jamais une nouvelle tentative après
        que la précédente a définitivement échoué."""
        conv = cm.create_conversation(self.REAL_USER["id"], "Test retry relache")
        try:
            db.add_message(conv["id"], "user", "Salut")

            def failing_generator(*_args, **_kwargs):
                raise RuntimeError("panne réseau simulée")
                yield  # pragma: no cover - jamais atteint, garde la fonction generator

            with patch.object(cm, "_generate_assistant_reply", side_effect=failing_generator):
                with self.assertRaises(RuntimeError):
                    list(cm.retry_last(self.REAL_USER, conv["id"]))

            # Aucun message assistant n'a été persisté par l'essai échoué.
            messages = db.list_messages(conv["id"])
            self.assertEqual(len(messages), 1)
            self.assertEqual(messages[0]["role"], "user")

            # Un second essai (séquentiel, la réservation a été relâchée)
            # doit réussir normalement.
            result = "".join(cm.retry_last(self.REAL_USER, conv["id"]))
            self.assertTrue(result)
            messages_after = db.list_messages(conv["id"])
            self.assertEqual(len(messages_after), 2)
            self.assertEqual(messages_after[-1]["role"], "assistant")
        finally:
            cm.delete_conversation(conv["id"], self.REAL_USER["id"])


class TestRetryLastConcurrence(Phase3BTestCase):
    """Durcissement production : deux `retry_last` concurrents (double-clic,
    double onglet) sur le MÊME message utilisateur en attente ne doivent
    produire qu'UNE seule réponse assistant — même protection que
    regenerate_last (voir db.claim_message_retry)."""

    def test_plusieurs_retry_concurrents_ne_dupliquent_jamais(self):
        import threading
        import time as time_module

        conv = cm.create_conversation(self.REAL_USER["id"], "Test retry concurrent")
        try:
            db.add_message(conv["id"], "user", "C'est quoi une puissance ?")

            n_threads = 6
            barrier = threading.Barrier(n_threads)
            results = []
            errors = []
            lock = threading.Lock()

            real_claim = db.claim_message_retry

            def slow_claim(message_id):
                # Élargit la fenêtre critique pour forcer une vraie collision
                # entre threads (voir test analogue sur regenerate_last).
                time_module.sleep(0.05)
                return real_claim(message_id)

            with patch.object(db, "claim_message_retry", side_effect=slow_claim):
                def worker():
                    barrier.wait()
                    try:
                        text = "".join(cm.retry_last(self.REAL_USER, conv["id"]))
                        with lock:
                            results.append(text)
                    except ValueError as e:
                        with lock:
                            errors.append(e)

                threads = [threading.Thread(target=worker) for _ in range(n_threads)]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join()

            self.assertEqual(len(results), 1, f"un seul retry doit produire du texte : {results}")
            self.assertEqual(len(errors), n_threads - 1)
            for e in errors:
                self.assertIn("déjà en cours de génération", str(e))

            messages_after = db.list_messages(conv["id"])
            self.assertEqual(len(messages_after), 2)  # user + LA seule réponse assistant
        finally:
            cm.delete_conversation(conv["id"], self.REAL_USER["id"])

    def test_genere_une_reponse_sans_dupliquer_le_message_utilisateur(self):
        """Simule l'état laissé par une tentative échouée avant toute
        persistance assistant (panne réseau/fournisseur) : un seul message
        utilisateur en base, aucune réponse. `retry_last` doit produire une
        réponse et l'historique final ne doit contenir qu'UN SEUL message
        utilisateur — jamais un second envoi du même texte."""
        conv = cm.create_conversation(self.REAL_USER["id"], "Test retry echec reseau")
        try:
            cm.db.add_message(conv["id"], "user", "C'est quoi une puissance ?")
            texte = "".join(cm.retry_last(self.REAL_USER, conv["id"]))
            self.assertTrue(texte)

            rows = cm.db.list_messages(conv["id"])
            roles = [r["role"] for r in rows]
            self.assertEqual(roles.count("user"), 1)
            self.assertEqual(roles, ["user", "assistant"])
        finally:
            cm.delete_conversation(conv["id"], self.REAL_USER["id"])


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
