"""
Chantier "audit fonctionnel des paramètres du chatbot" (2026-10-18) : vérifie
que chaque réglage encore présent dans la section Chatbot (Paramètres) a un
effet RÉEL démontré sur la génération — pas seulement une présence dans le
code. Niveau d'explication/Mode/Longueur/Mémoire sont déjà démontrés par
`test_prompt_priority_mode_intent.py` et les docstrings de `prompt_builder.py`
(instructions distinctes injectées dans le prompt système selon la valeur) ;
ce fichier couvre le seul réglage encore sans test dédié : "Historique"
(`historyEnabled`), dont l'effet avait été établi par simple lecture de code
lors de l'audit (chatbot/conversation_manager.py::stream_reply) mais jamais
démontré par un test reproductible.

Base SQLite temporaire isolée, `FakeProvider` (aucun appel payant) — même
pattern que `test_perimetre_pedagogique.py`/`test_formules_et_reformulation_
fraiche.py`.
"""
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import db
from chatbot import cache as llm_cache, conversation_manager as cm
from chatbot.services import pipeline_metrics


class TestHistoriqueEffetReel(unittest.TestCase):
    """"Historique" (historyEnabled) : si désactivé, le fournisseur IA ne
    doit recevoir QUE le message courant — jamais les tours précédents de la
    même conversation (voir conversation_manager.py::stream_reply, ligne
    `history_rows = db.list_messages(conversation_id) if history_enabled
    else [...]`)."""

    MESSAGE_HORS_MOTEUR_LOCAL = (
        "Décris la vie quotidienne d'un hippopotame astronaute qui collectionne les parapluies"
    )

    def setUp(self):
        pipeline_metrics.reset()
        llm_cache.clear()

        tmp_dir = tempfile.mkdtemp()
        self._data_dir_backup, self._db_path_backup = db.DATA_DIR, db.DB_PATH
        db.DATA_DIR = Path(tmp_dir)
        db.DB_PATH = db.DATA_DIR / "novamath.db"
        db.init_db()

        def _restore_db():
            db.DATA_DIR = self._data_dir_backup
            db.DB_PATH = self._db_path_backup
            shutil.rmtree(tmp_dir, ignore_errors=True)

        self.addCleanup(_restore_db)

        user_id = db.create_user("histo@test.local", "histo_user", "Histo Test", "x")
        self.user = {"id": user_id, "pseudo": "Histo Test", "level": 1}
        conv = cm.create_conversation(self.user["id"], "Test historique")
        self.conv_id = conv["id"]
        self.addCleanup(lambda: cm.delete_conversation(self.user["id"], self.conv_id))

        # Deux tours déjà présents dans la conversation AVANT le message
        # testé — c'est cette présence (ou non) dans l'historique transmis
        # qui est l'objet de ce test.
        db.add_message(self.conv_id, "user", "Premier message du passé", engine=None)
        db.add_message(self.conv_id, "assistant", "Première réponse du passé", engine="llm")

    def tearDown(self):
        pipeline_metrics.reset()
        llm_cache.clear()

    def _run_with_settings(self, chatbot_settings):
        # `chatbot_settings` est résolu par conversation_manager via le
        # profil utilisateur réel (auth.read_user_settings), jamais passé en
        # paramètre direct de stream_reply — on écrit donc le réglage
        # exactement comme le ferait `write_user_settings` (même mécanisme
        # que l'API /api/settings), pour exercer le VRAI chemin de
        # résolution plutôt qu'un mock de la fonction elle-même.
        import auth
        auth.write_user_settings(self.user["id"], {"chatbot": chatbot_settings})
        # `build_messages(history_rows)` (prompt_builder.py) reçoit EXACTEMENT
        # ce que `history_enabled` a produit (voir conversation_manager.py::
        # stream_reply, juste avant) — c'est le point d'observation le plus
        # direct de l'effet réel, plus précis qu'un espionnage de
        # `db.list_messages` (appelé aussi ailleurs dans le pipeline pour
        # d'autres besoins, sans rapport avec ce réglage).
        with patch.object(cm, "check_and_increment_quota", return_value=1):
            with patch.object(cm, "build_messages", wraps=cm.build_messages) as build_messages_spy:
                text = "".join(cm.stream_reply(self.user, self.conv_id, self.MESSAGE_HORS_MOTEUR_LOCAL))
        return text, build_messages_spy

    def test_historique_active_transmet_bien_les_messages_precedents_au_fournisseur(self):
        text, build_messages_spy = self._run_with_settings({"historyEnabled": True})
        self.assertTrue(text.strip())
        build_messages_spy.assert_called_once()
        history_rows_received = build_messages_spy.call_args[0][0]
        # Les 2 tours déjà présents (setUp) + le message courant déjà
        # persisté par stream_reply avant cet appel.
        contents = [m["content"] for m in history_rows_received]
        self.assertIn("Premier message du passé", contents)
        self.assertIn("Première réponse du passé", contents)
        self.assertIn(self.MESSAGE_HORS_MOTEUR_LOCAL, contents)

    def test_historique_desactive_ne_transmet_jamais_les_messages_precedents(self):
        text, build_messages_spy = self._run_with_settings({"historyEnabled": False})
        self.assertTrue(text.strip())
        build_messages_spy.assert_called_once()
        history_rows_received = build_messages_spy.call_args[0][0]
        contents = [m["content"] for m in history_rows_received]
        # Seul le message courant est transmis — les 2 tours précédents
        # (setUp) n'atteignent jamais le fournisseur IA.
        self.assertEqual(contents, [self.MESSAGE_HORS_MOTEUR_LOCAL])
        self.assertNotIn("Premier message du passé", contents)
        self.assertNotIn("Première réponse du passé", contents)

    def test_reglage_persiste_et_relu_apres_rechargement(self):
        """Sauvegarde + récupération lors d'un tour ultérieur (points 2-3-6
        de la consigne) : le réglage écrit via le mécanisme réel de
        persistance (auth.write_user_settings, identique à /api/settings)
        est bien relu par le pipeline au tour suivant, sans action
        supplémentaire — pas de valeur mise en cache qui empêcherait sa
        prise en compte après "rechargement"."""
        import auth
        auth.write_user_settings(self.user["id"], {"chatbot": {"historyEnabled": False}})
        reloaded = auth.read_user_settings(self.user["id"])
        self.assertFalse(reloaded["chatbot"]["historyEnabled"])

        with patch.object(cm, "check_and_increment_quota", return_value=1):
            with patch.object(cm, "build_messages", wraps=cm.build_messages) as spy:
                "".join(cm.stream_reply(self.user, self.conv_id, self.MESSAGE_HORS_MOTEUR_LOCAL))
        spy.assert_called_once()
        contents = [m["content"] for m in spy.call_args[0][0]]
        self.assertEqual(contents, [self.MESSAGE_HORS_MOTEUR_LOCAL])


if __name__ == "__main__":
    unittest.main()
