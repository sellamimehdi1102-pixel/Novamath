"""
Chantier "formules brutes et réponses hors demande" (2026-10-18) — test de
régression bout en bout, reproduisant précisément le bug réel signalé :

    "Soient A(1 ; 2) et B(4 ; 6). Calcule les coordonnées du vecteur AB,
    puis la distance AB. Détaille les calculs avec les formules
    mathématiques."

Cause racine réelle (confirmée en lisant le code, pas supposée) : ce message
matche `intent_service.REFORMULATION_RE` ("détaille" seul) — un déclencheur
pensé pour un VRAI suivi ("détaille-moi ça", après une explication déjà
donnée) — alors qu'il s'agit d'une demande FRAÎCHE et autonome contenant des
données numériques concrètes. `response_strategy.decide_strategy()` routait
alors vers `ENGINE_KNOWLEDGE` (knowledge_response_composer.py), qui répond
avec la notion de cours "Milieu et distance" (chapitre_5.json) — exactement
la capture fournie, "milieu d'un segment" non demandé inclus — plutôt que de
calculer la réponse réelle. Modifier `BASE_SYSTEM_PROMPT` (chantier
précédent, 2026-10-18 matin) n'avait donc aucun effet : ce chemin ne passe
jamais par le LLM ni par `prompt_builder.py`.

Corrigé à deux niveaux :
1. `response_strategy._requires_real_computation` écarte désormais
   REFORMULATION du routage local quand le message contient à la fois un
   verbe d'opération mathématique ET un chiffre (voir
   test_response_strategy.py pour les tests unitaires détaillés du routage).
2. `knowledge_response_composer._ensure_math_delimited` délimite désormais
   systématiquement `calcul[].expr` (jamais délimité dans course_content/
   **/*.json, à la différence de `enonce`/`reponse`) — corrige TOUS les
   chemins qui répondent légitimement via Knowledge Engine (ex: "Donne-moi
   un exemple sur..."), pas seulement ce cas précis (voir
   test_knowledge_response_composer.py).

Ce fichier vérifie le comportement RÉEL de bout en bout
(`conversation_manager.stream_reply`), avec `FakeProvider` (aucun appel
payant) sur une base SQLite temporaire isolée — même pattern que
`test_perimetre_pedagogique.py`.
"""
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import db
from chatbot import cache as llm_cache, conversation_manager as cm
from chatbot.services import knowledge_response_composer as krc, pipeline_metrics


class TestDemandeFraicheAvecDonneesEviteLeGabaritLocal(unittest.TestCase):
    MESSAGE_SIGNALE = (
        "Soient A(1 ; 2) et B(4 ; 6). Calcule les coordonnées du vecteur AB, "
        "puis la distance AB. Détaille les calculs avec les formules "
        "mathématiques."
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

        user_id = db.create_user("vecteur@test.local", "vecteur_user", "Vecteur Test", "x")
        self.user = {"id": user_id, "pseudo": "Vecteur Test", "level": 1}
        conv = cm.create_conversation(self.user["id"], "Test vecteur AB")
        self.conv_id = conv["id"]
        self.addCleanup(lambda: cm.delete_conversation(self.user["id"], self.conv_id))

    def tearDown(self):
        pipeline_metrics.reset()
        llm_cache.clear()

    def test_le_message_signale_natterit_plus_sur_le_gabarit_local(self):
        """Le chemin réel de génération sélectionné ne doit plus être
        knowledge_response_composer (ENGINE_NAME) pour ce message précis —
        c'est tout le bug : le gabarit local répondait avec une notion de
        cours générique au lieu de calculer la réponse réelle."""
        with patch.object(cm, "check_and_increment_quota", return_value=1) as quota_mock:
            text = "".join(cm.stream_reply(self.user, self.conv_id, self.MESSAGE_SIGNALE))
        self.assertTrue(text.strip())

        messages = db.list_messages(self.conv_id)
        self.assertEqual(messages[-1]["role"], "assistant")
        self.assertNotEqual(messages[-1]["engine"], krc.ENGINE_NAME)
        # Le filet de sécurité LLM consomme du quota (contrairement au
        # gabarit local, qui n'en consomme jamais par conception) — un appel
        # de plus que le seul appel systématique en amont de stream_reply
        # confirmerait qu'un moteur local gratuit a répondu à la place.
        self.assertEqual(quota_mock.call_count, 1)

    def test_compatible_avec_lhistorique_une_vraie_reformulation_ensuite(self):
        """Compatibilité avec les conversations historiques (section 4) :
        une vraie reformulation de suivi, immédiatement après, doit
        continuer à fonctionner normalement (aucune régression introduite
        par le correctif sur le tour précédent)."""
        with patch.object(cm, "check_and_increment_quota", return_value=1):
            "".join(cm.stream_reply(self.user, self.conv_id, self.MESSAGE_SIGNALE))
        with patch.object(cm, "check_and_increment_quota", return_value=1):
            follow_up = "".join(cm.stream_reply(self.user, self.conv_id, "Explique-moi ça plus simplement"))
        self.assertTrue(follow_up.strip())

        messages = db.list_messages(self.conv_id)
        self.assertEqual([m["role"] for m in messages], ["user", "assistant", "user", "assistant"])


if __name__ == "__main__":
    unittest.main()
