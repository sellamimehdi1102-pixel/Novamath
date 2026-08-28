"""
Suite dédiée au chantier "fiabilité des données d'analytics IA" (audit
2026-08-27) — corrige l'anomalie #1 confirmée par l'audit : les entrées
"(repli)" de ai_providers (ex: "Gemini Flash (repli)", "Gemini Pro (repli
Ultra)") restaient structurellement vides car ai_provider_service.
_find_provider_id() renvoyait toujours le PREMIER fournisseur correspondant
au couple (provider_key, model_name), sans jamais tenir compte de is_fallback
— alors que le catalogue seedé contient volontairement deux lignes distinctes
partageant ce même couple (une "primaire", une "repli").

Ne couvre QUE la résolution du provider_id (ai_provider_service.py) — ne
touche ni provider_manager.py, ni la mécanique de fallback elle-même (déjà
couverte par test_chantier2_routing_fallback.py/test_chantier3_cost_accounting.py).
"""
import shutil
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timezone

import ai_provider_service
import db


class _IsolatedDbTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = tempfile.mkdtemp()
        self._data_dir_backup = db.DATA_DIR
        self._db_path_backup = db.DB_PATH
        db.DATA_DIR = Path(self._tmp_dir)
        db.DB_PATH = db.DATA_DIR / "novamath.db"
        db.init_db()

    def tearDown(self):
        db.DATA_DIR = self._data_dir_backup
        db.DB_PATH = self._db_path_backup
        shutil.rmtree(self._tmp_dir, ignore_errors=True)


def _today():
    return datetime.now(timezone.utc).date().isoformat()


class TestResolutionProviderIdPrimaireVsRepli(_IsolatedDbTestCase):
    """Catalogue par défaut réel (seed_default_providers) : "Gemini Flash"
    (priority 0) / "Gemini Flash (repli)" (priority 4) partagent
    ("gemini", "gemini-3-flash-preview") ; "Gemini Pro" (priority 1) /
    "Gemini Pro (repli Ultra)" (priority 3) partagent
    ("gemini", "gemini-3.1-pro-preview")."""

    def setUp(self):
        super().setUp()
        ai_provider_service.seed_default_providers()
        self.flash_primary_id = ai_provider_service._find_provider_id("gemini", "gemini-3-flash-preview")
        self.pro_primary_id = ai_provider_service._find_provider_id("gemini", "gemini-3.1-pro-preview")
        self.flash_fallback_id = ai_provider_service._find_provider_id(
            "gemini", "gemini-3-flash-preview", is_fallback=True,
        )
        self.pro_fallback_id = ai_provider_service._find_provider_id(
            "gemini", "gemini-3.1-pro-preview", is_fallback=True,
        )

    def test_gemini_flash_primaire_et_repli_sont_deux_ids_distincts(self):
        self.assertNotEqual(self.flash_primary_id, self.flash_fallback_id)
        names = {p["id"]: p["name"] for p in ai_provider_service.list_providers()}
        self.assertEqual(names[self.flash_primary_id], "Gemini Flash")
        self.assertEqual(names[self.flash_fallback_id], "Gemini Flash (repli)")

    def test_gemini_pro_primaire_et_repli_sont_deux_ids_distincts(self):
        self.assertNotEqual(self.pro_primary_id, self.pro_fallback_id)
        names = {p["id"]: p["name"] for p in ai_provider_service.list_providers()}
        self.assertEqual(names[self.pro_primary_id], "Gemini Pro")
        self.assertEqual(names[self.pro_fallback_id], "Gemini Pro (repli Ultra)")

    def test_1_appel_gemini_flash_primaire_ecrit_dans_lentree_primaire(self):
        ai_provider_service.record_llm_usage(
            "gemini", "gemini-3-flash-preview", {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            is_fallback=False,
        )
        primary_row = db.get_ai_provider_usage(self.flash_primary_id, _today())
        fallback_row = db.get_ai_provider_usage(self.flash_fallback_id, _today())
        self.assertIsNotNone(primary_row)
        self.assertEqual(primary_row["requests"], 1)
        self.assertIsNone(fallback_row)  # jamais créée par un appel primaire

    def test_2_appel_gemini_flash_fallback_ecrit_dans_lentree_repli(self):
        ai_provider_service.record_llm_usage(
            "gemini", "gemini-3-flash-preview", {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            is_fallback=True,
        )
        primary_row = db.get_ai_provider_usage(self.flash_primary_id, _today())
        fallback_row = db.get_ai_provider_usage(self.flash_fallback_id, _today())
        self.assertIsNone(primary_row)  # jamais créée par un appel fallback
        self.assertIsNotNone(fallback_row)
        self.assertEqual(fallback_row["requests"], 1)

    def test_3_appel_gemini_pro_primaire_ecrit_dans_gemini_pro(self):
        ai_provider_service.record_llm_usage(
            "gemini", "gemini-3.1-pro-preview", {"prompt_tokens": 20, "completion_tokens": 8, "total_tokens": 28},
            is_fallback=False,
        )
        primary_row = db.get_ai_provider_usage(self.pro_primary_id, _today())
        fallback_row = db.get_ai_provider_usage(self.pro_fallback_id, _today())
        self.assertIsNotNone(primary_row)
        self.assertIsNone(fallback_row)

    def test_4_appel_gemini_pro_fallback_ecrit_dans_repli_ultra(self):
        ai_provider_service.record_llm_usage(
            "gemini", "gemini-3.1-pro-preview", {"prompt_tokens": 20, "completion_tokens": 8, "total_tokens": 28},
            is_fallback=True,
        )
        primary_row = db.get_ai_provider_usage(self.pro_primary_id, _today())
        fallback_row = db.get_ai_provider_usage(self.pro_fallback_id, _today())
        self.assertIsNone(primary_row)
        self.assertIsNotNone(fallback_row)

    def test_5_compteurs_primaire_et_repli_ne_se_melangent_jamais_sur_plusieurs_appels(self):
        for _ in range(3):
            ai_provider_service.record_llm_usage(
                "gemini", "gemini-3-flash-preview", {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                is_fallback=False,
            )
        for _ in range(2):
            ai_provider_service.record_llm_usage(
                "gemini", "gemini-3-flash-preview", {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                is_fallback=True,
            )
        primary_row = db.get_ai_provider_usage(self.flash_primary_id, _today())
        fallback_row = db.get_ai_provider_usage(self.flash_fallback_id, _today())
        self.assertEqual(primary_row["requests"], 3)
        self.assertEqual(fallback_row["requests"], 2)

    def test_6_provider_sans_doublon_comportement_inchange_quel_que_soit_is_fallback(self):
        """Claude n'a qu'UNE seule ligne (aucun rôle "repli" dans le
        catalogue par défaut) : is_fallback=True ne doit jamais rediriger
        vers une entrée inexistante ni en créer une fantôme — comportement
        strictement identique à avant ce chantier."""
        claude_id_primary = ai_provider_service._find_provider_id("anthropic", "claude-sonnet-5", is_fallback=False)
        claude_id_fallback = ai_provider_service._find_provider_id("anthropic", "claude-sonnet-5", is_fallback=True)
        self.assertEqual(claude_id_primary, claude_id_fallback)

        ai_provider_service.record_llm_usage(
            "anthropic", "claude-sonnet-5", {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10},
            is_fallback=True,
        )
        row = db.get_ai_provider_usage(claude_id_primary, _today())
        self.assertIsNotNone(row)
        self.assertEqual(row["requests"], 1)


class TestProviderPersonnaliseNonRedirigeArbitrairement(_IsolatedDbTestCase):
    """§7 de la demande : un fournisseur ajouté par l'admin, seul sur son
    (provider_key, model_name) (aucun doublon volontaire), ne doit jamais
    être basculé vers une entrée fallback qui n'existe pas — même si
    is_fallback=True est transmis (ex: ce fournisseur personnalisé est
    utilisé en 2e position dans une chaîne configurée par l'admin)."""

    def test_fournisseur_personnalise_seul_reste_stable(self):
        provider_id = ai_provider_service.create_provider(
            "Mistral Perso", "ollama", "mistral", enabled=True, priority=10,
        )
        resolved_primary = ai_provider_service._find_provider_id("ollama", "mistral", is_fallback=False)
        resolved_fallback = ai_provider_service._find_provider_id("ollama", "mistral", is_fallback=True)
        self.assertEqual(resolved_primary, provider_id)
        self.assertEqual(resolved_fallback, provider_id)

    def test_deux_fournisseurs_personnalises_dupliques_respectent_lordre_de_priorite(self):
        """Un admin qui configure lui-même deux lignes pour le même modèle
        (même logique que le seed par défaut) doit bénéficier de la même
        désambiguïsation, sans dépendre du nom "(repli)" codé en dur."""
        primary_id = ai_provider_service.create_provider(
            "Mon modèle A", "ollama", "llama3", enabled=True, priority=20,
        )
        fallback_id = ai_provider_service.create_provider(
            "Mon modèle A (secours)", "ollama", "llama3", enabled=True, priority=21,
        )
        self.assertEqual(
            ai_provider_service._find_provider_id("ollama", "llama3", is_fallback=False), primary_id,
        )
        self.assertEqual(
            ai_provider_service._find_provider_id("ollama", "llama3", is_fallback=True), fallback_id,
        )


if __name__ == "__main__":
    unittest.main()
