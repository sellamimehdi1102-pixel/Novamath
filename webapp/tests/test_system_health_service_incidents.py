"""
Suite ciblée de system_health_service.list_incidents() et
ai_provider_service.record_provider_fallback() — audit admin (2026-10-20),
point 5 : un fallback vers "fake" (FakeProvider, le repli ultime quand AUCUN
fournisseur IA réel n'est disponible, voir chatbot/provider_manager.py) ne
doit jamais s'afficher comme un fallback réussi vers un vrai fournisseur
externe — et surtout, son enregistrement ne doit plus échouer silencieusement
(régression réelle trouvée en écrivant ce test : model_final=None, renvoyé
par provider_manager.py pour "fake", violait la contrainte NOT NULL de
ai_provider_fallback_events.model_final — l'incident le plus grave possible
ne laissait alors aucune trace).
"""
import unittest

import ai_provider_service
import db
import system_health_service


class TestRecordProviderFallbackVersFake(unittest.TestCase):
    def test_model_final_none_najamais_echouer_silencieusement(self):
        """Avant le correctif : IntegrityError (NOT NULL) avalée par le
        except Exception, aucune ligne insérée. Après : une ligne réelle
        existe, avec un placeholder explicite jamais confondu avec un vrai
        nom de modèle."""
        before = len(db.list_ai_provider_fallback_events(limit=500))
        ai_provider_service.record_provider_fallback(
            "gemini", "gemini-3-flash-preview", "fake", None,
            "toutes_les_cles_indisponibles", time_lost_ms=120,
        )
        after = db.list_ai_provider_fallback_events(limit=500)
        self.assertEqual(len(after), before + 1)
        self.assertEqual(after[0]["provider_final"], "fake")
        self.assertIsNotNone(after[0]["model_final"])


class TestListIncidentsFallbackVersFake(unittest.TestCase):
    def test_fallback_vers_fake_jamais_presente_comme_un_vrai_fournisseur(self):
        ai_provider_service.record_provider_fallback(
            "gemini", "gemini-3-flash-preview", "fake", None,
            "toutes_les_cles_indisponibles", time_lost_ms=120,
        )
        incidents = system_health_service.list_incidents(window="tous")
        fake_incident = next(i for i in incidents if "dégradé" in i["service"])
        self.assertIn("mode dégradé", fake_incident["service"])
        self.assertNotIn("fake/None", fake_incident["message"])
        self.assertNotIn("fake/aucun", fake_incident["message"])
        self.assertIn("aucune IA externe", fake_incident["message"])
        self.assertEqual(fake_incident["level"], "critical")
        self.assertNotIn("succès", fake_incident["resolution"])

    def test_fallback_vers_un_vrai_fournisseur_reste_inchange(self):
        ai_provider_service.record_provider_fallback(
            "anthropic", "claude-sonnet-5", "gemini", "gemini-3.1-pro-preview",
            "erreur_timeout", time_lost_ms=50,
        )
        incidents = system_health_service.list_incidents(window="tous")
        real_incident = next(i for i in incidents if "gemini" in i["service"] and "dégradé" not in i["service"])
        self.assertEqual(real_incident["service"], "anthropic → gemini")
        self.assertEqual(real_incident["level"], "warning")
        self.assertIn("succès", real_incident["resolution"])


if __name__ == "__main__":
    unittest.main()
