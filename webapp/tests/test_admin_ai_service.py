"""
Suite dédiée à admin_ai_service.py — chantier "fiabilité des données
d'analytics IA" (audit 2026-08-27), anomalie #2 : total_tokens
(ai_provider_usage.total_tokens, déjà alimentée par
ai_provider_service.record_llm_usage()) n'était jamais exposée par
list_usage()/get_provider_usage(), alors que le coût affiché (estimated_cost)
inclut déjà les tokens de réflexion Gemini comptés dans ce total. Vérifie
uniquement l'exposition/l'agrégation de la donnée déjà stockée — aucun
changement de estimate_llm_cost()/des tarifs, jamais recalculé ici.
"""
import shutil
import tempfile
import unittest
from pathlib import Path

import admin_ai_service
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
        ai_provider_service.seed_default_providers()
        self.flash_id = ai_provider_service._find_provider_id("gemini", "gemini-3-flash-preview")

    def tearDown(self):
        db.DATA_DIR = self._data_dir_backup
        db.DB_PATH = self._db_path_backup
        shutil.rmtree(self._tmp_dir, ignore_errors=True)


class TestTotalTokensExposeParListUsage(_IsolatedDbTestCase):
    def test_1_total_tokens_present_dans_la_reponse_admin(self):
        usage = {"prompt_tokens": 29, "completion_tokens": 34, "total_tokens": 229}
        ai_provider_service.record_llm_usage("gemini", "gemini-3-flash-preview", usage)

        result = admin_ai_service.list_usage()
        item = next(i for i in result["items"] if i["provider_id"] == self.flash_id)
        self.assertTrue(item["usage"]["available"])
        self.assertEqual(item["usage"]["value"]["total_tokens"], 229)
        # 229 > 29 (input) + 34 (output) : le delta (166) correspond aux
        # tokens de réflexion — total_tokens n'est jamais recalculé ici,
        # simplement transmis tel qu'écrit en base.
        self.assertGreater(item["usage"]["value"]["total_tokens"], 29 + 34)

    def test_2_total_tokens_correctement_agrege_sur_plusieurs_jours(self):
        """increment_ai_provider_usage crée une ligne par (provider_id, jour) —
        _aggregate_usage doit sommer total_tokens sur TOUTES les lignes,
        exactement comme elle le fait déjà pour input_tokens/output_tokens."""
        usage_1 = {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 20}
        usage_2 = {"prompt_tokens": 7, "completion_tokens": 3, "total_tokens": 15}
        ai_provider_service.record_llm_usage("gemini", "gemini-3-flash-preview", usage_1)
        ai_provider_service.record_llm_usage("gemini", "gemini-3-flash-preview", usage_2)

        result = admin_ai_service.get_provider_usage(self.flash_id)
        self.assertTrue(result["available"])
        self.assertEqual(result["value"]["total_tokens"], 35)  # 20 + 15, même jour -> une seule ligne incrémentée
        self.assertEqual(result["value"]["input_tokens"], 17)  # 10 + 7, inchangé par ce chantier
        self.assertEqual(result["value"]["output_tokens"], 8)  # 5 + 3, inchangé par ce chantier

    def test_3_cout_estime_strictement_identique_apres_exposition_de_total_tokens(self):
        """L'exposition de total_tokens ne doit rien changer au calcul du
        coût déjà en place (estimate_llm_cost, jamais modifiée par ce
        chantier)."""
        usage = {"prompt_tokens": 29, "completion_tokens": 10, "total_tokens": 325}
        ai_provider_service.record_llm_usage("gemini", "gemini-3.1-pro-preview", usage)
        pro_id = ai_provider_service._find_provider_id("gemini", "gemini-3.1-pro-preview")

        expected_cost = ai_provider_service.estimate_llm_cost("gemini", "gemini-3.1-pro-preview", 29, 10, 325)
        result = admin_ai_service.get_provider_usage(pro_id)
        self.assertAlmostEqual(result["value"]["estimated_cost"], expected_cost)

    def test_4_input_output_tokens_inchanges(self):
        usage = {"prompt_tokens": 100, "completion_tokens": 40, "total_tokens": 140}
        ai_provider_service.record_llm_usage("gemini", "gemini-3-flash-preview", usage)
        result = admin_ai_service.get_provider_usage(self.flash_id)
        self.assertEqual(result["value"]["input_tokens"], 100)
        self.assertEqual(result["value"]["output_tokens"], 40)

    def test_6_provider_sans_aucune_donnee_reste_available_false_sans_erreur(self):
        """Aucune ligne ai_provider_usage pour ce fournisseur (jamais appelé) :
        get_provider_usage()/list_usage() doivent rester {"available": False}
        — jamais un total_tokens=0 fabriqué qui laisserait croire à un vrai 0."""
        result = admin_ai_service.get_provider_usage(self.flash_id)
        self.assertFalse(result["available"])
        self.assertIsNone(result["value"])

        list_result = admin_ai_service.list_usage()
        item = next(i for i in list_result["items"] if i["provider_id"] == self.flash_id)
        self.assertFalse(item["usage"]["available"])

    def test_daily_rows_contiennent_aussi_total_tokens(self):
        """_serialize_usage_row (détail journalier de la fiche fournisseur)
        expose aussi total_tokens, pas seulement l'agrégat global."""
        usage = {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 12}
        ai_provider_service.record_llm_usage("gemini", "gemini-3-flash-preview", usage)
        result = admin_ai_service.get_provider_usage(self.flash_id)
        self.assertEqual(len(result["value"]["daily"]), 1)
        self.assertEqual(result["value"]["daily"][0]["total_tokens"], 12)


class TestSerializeApiKeySuccessCount(_IsolatedDbTestCase):
    """Audit admin (2026-10-20), point 6 : success_count calculé côté
    backend (request_count - failure_count), source unique de vérité —
    avant ce chantier, le frontend recalculait cette soustraction
    localement, exposé à une divergence silencieuse si la définition
    changeait côté serveur sans mise à jour correspondante du JS."""

    def setUp(self):
        super().setUp()
        self.key_id = db.create_ai_provider_api_key("gemini", "Clé de test", "encrypted-placeholder", priority=0)

    def test_success_count_egal_request_moins_failure(self):
        db.record_ai_provider_api_key_result(self.key_id, success=True, response_time_ms=100)
        db.record_ai_provider_api_key_result(self.key_id, success=True, response_time_ms=100)
        db.record_ai_provider_api_key_result(self.key_id, success=False, response_time_ms=100, error="timeout")
        row = db.get_ai_provider_api_key(self.key_id)
        serialized = admin_ai_service._serialize_api_key(row)
        self.assertEqual(serialized["request_count"], 3)
        self.assertEqual(serialized["failure_count"], 1)
        self.assertEqual(serialized["success_count"], 2)

    def test_aucune_tentative_success_count_zero_jamais_negatif(self):
        row = db.get_ai_provider_api_key(self.key_id)
        serialized = admin_ai_service._serialize_api_key(row)
        self.assertEqual(serialized["success_count"], 0)

    def test_list_keys_http_expose_bien_success_count(self):
        import server
        from role_service import Role

        client = server.app.test_client()
        email = "adminaikeys@gmail.com"
        resp = client.post("/api/auth/register", json={
            "email": email, "username": "adminaikeys", "pseudo": "Test",
            "birth_date": "2000-01-01",
            "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
            "accept_terms": True, "accept_privacy": True,
        })
        user_id = resp.get_json()["user"]["id"]
        db.set_user_role(user_id, Role.ADMIN.value)
        csrf = client.get_cookie("nm_csrf").value
        headers = {"X-CSRF-Token": csrf}

        db.record_ai_provider_api_key_result(self.key_id, success=True, response_time_ms=100)
        db.record_ai_provider_api_key_result(self.key_id, success=False, response_time_ms=100, error="boom")

        resp = client.get("/api/admin/ai/keys", headers=headers)
        self.assertEqual(resp.status_code, 200)
        keys = resp.get_json()
        key = next(k for k in keys if k["id"] == self.key_id)
        self.assertEqual(key["success_count"], 1)
        db.delete_user(user_id)


if __name__ == "__main__":
    unittest.main()
