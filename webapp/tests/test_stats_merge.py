"""
Suite Release Candidate — correctif priorité 1 : POST /api/stats remplaçait
intégralement l'état de gamification (XP/historique/badges/séries) au lieu de
le fusionner, ce qui effaçait silencieusement la progression d'un
onglet/appareil quand un autre postait un état local plus ancien (voir audit
Release Candidate, server.py::_merge_stats_payload).

Vérifie que la fusion :
- ne perd jamais une entrée d'historique/série déjà persistée ;
- ne duplique jamais une entrée déjà vue (même après plusieurs fusions) ;
- recalcule toujours xp/badges de façon cohérente avec l'historique fusionné ;
- reste stable même si le client renvoie un état plus ancien/partiel.
"""
import random
import unittest

import server


def _register(client):
    email = f"stats{random.randint(1_000_000, 9_999_999)}@gmail.com"
    username = f"stats{random.randint(100_000, 999_999)}"
    resp = client.post("/api/auth/register", json={
        "email": email, "username": username, "pseudo": "Test",
        "birth_date": "2000-01-01",
        "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
        "accept_terms": True, "accept_privacy": True,
    })
    user = resp.get_json()["user"]
    csrf = client.get_cookie("nm_csrf").value
    return user, {"X-CSRF-Token": csrf}


def _entry(ts, xp, chapter="ch1"):
    return {
        "id": f"ex_{ts}", "date": "2026-01-01", "ts": ts, "chapter": chapter,
        "notion": "n1", "difficulty": 1, "correct": True, "mode": "revisions",
        "duration_s": 10, "xp": xp, "class_level": "seconde",
    }


class TestFusionMergeStatsPayload(unittest.TestCase):
    """Test unitaire pur de _merge_stats_payload — pas de round-trip HTTP."""

    def test_union_sans_perte_ni_doublon(self):
        old = {"xp": 10, "history": [_entry(1, 10)], "badges": ["ex_10"], "series": []}
        incoming = {"xp": 15, "history": [_entry(2, 15)], "badges": [], "series": []}
        merged = server._merge_stats_payload(old, incoming)
        self.assertEqual([h["ts"] for h in merged["history"]], [1, 2])
        self.assertEqual(merged["xp"], 25)
        self.assertEqual(merged["badges"], ["ex_10"])

    def test_etat_plus_ancien_nefface_pas_lhistorique_deja_persiste(self):
        """Cas central de l'audit : un onglet B, resynchronisé AVANT que
        l'onglet A n'ait posté ses 2 derniers exercices, poste un état local
        qui ne les contient pas — ces 2 exercices doivent survivre."""
        old = {"xp": 30, "history": [_entry(1, 10), _entry(2, 10), _entry(3, 10)], "badges": [], "series": []}
        stale_incoming = {"xp": 10, "history": [_entry(1, 10)], "badges": [], "series": []}
        merged = server._merge_stats_payload(old, stale_incoming)
        self.assertEqual([h["ts"] for h in merged["history"]], [1, 2, 3])
        self.assertEqual(merged["xp"], 30)

    def test_fusion_repetee_ne_duplique_jamais(self):
        state = {"xp": 10, "history": [_entry(1, 10)], "badges": [], "series": []}
        merged = server._merge_stats_payload(state, state)
        merged = server._merge_stats_payload(merged, state)
        merged = server._merge_stats_payload(merged, merged)
        self.assertEqual(len(merged["history"]), 1)
        self.assertEqual(merged["xp"], 10)

    def test_badges_sont_lunion_jamais_retires(self):
        old = {"xp": 0, "history": [], "badges": ["ex_10", "streak_7"], "series": []}
        incoming = {"xp": 0, "history": [], "badges": ["ex_50"], "series": []}
        merged = server._merge_stats_payload(old, incoming)
        self.assertEqual(set(merged["badges"]), {"ex_10", "streak_7", "ex_50"})

    def test_series_fusionnees_par_id_sans_doublon(self):
        s1 = {"id": "s_1", "startedAt": 1, "questions": []}
        s2 = {"id": "s_2", "startedAt": 2, "questions": []}
        old = {"xp": 0, "history": [], "badges": [], "series": [s1]}
        incoming = {"xp": 0, "history": [], "badges": [], "series": [s1, s2]}
        merged = server._merge_stats_payload(old, incoming)
        self.assertEqual([s["id"] for s in merged["series"]], ["s_1", "s_2"])

    def test_xp_toujours_recalcule_depuis_lhistorique_jamais_celui_du_client(self):
        """Le client pourrait envoyer un xp incohérent (bug frontend, valeur
        manipulée) : le serveur ne doit jamais lui faire confiance tel quel."""
        old = {"xp": 999, "history": [_entry(1, 10)], "badges": [], "series": []}
        incoming = {"xp": -50, "history": [], "badges": [], "series": []}
        merged = server._merge_stats_payload(old, incoming)
        self.assertEqual(merged["xp"], 10)  # somme réelle de l'historique fusionné, pas -50 ni 999


class TestApiStatsRoundTripHTTP(unittest.TestCase):
    """Bout en bout via la vraie route Flask — preuve que le correctif est
    bien branché, pas seulement testé en isolation."""

    def setUp(self):
        self.client = server.app.test_client()
        self.user, self.headers = _register(self.client)

    def test_deux_appareils_divergents_ne_seffacent_pas_lun_lautre(self):
        # "PC" poste 2 exercices.
        self.client.post("/api/stats", json={
            "xp": 20, "history": [_entry(1, 10), _entry(2, 10)], "badges": [], "series": [],
        }, headers=self.headers)

        # "Tablette", partie d'un état local plus ancien (avant que le PC
        # n'ait synchronisé son 2e exercice), poste son propre exercice.
        self.client.post("/api/stats", json={
            "xp": 10, "history": [_entry(1, 10), _entry(3, 10)], "badges": [], "series": [],
        }, headers=self.headers)

        resp = self.client.get("/api/stats", headers=self.headers)
        body = resp.get_json()
        self.assertEqual(sorted(h["ts"] for h in body["history"]), [1, 2, 3])
        self.assertEqual(body["xp"], 30)

    def test_repetition_du_meme_post_est_sans_effet(self):
        payload = {"xp": 10, "history": [_entry(1, 10)], "badges": ["ex_10"], "series": []}
        for _ in range(3):
            self.client.post("/api/stats", json=payload, headers=self.headers)
        resp = self.client.get("/api/stats", headers=self.headers)
        body = resp.get_json()
        self.assertEqual(len(body["history"]), 1)
        self.assertEqual(body["xp"], 10)


if __name__ == "__main__":
    unittest.main()
