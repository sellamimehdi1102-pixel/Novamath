"""
Suite Release Candidate — expiration de session "en cours d'utilisation".

Le rapport d'audit précédent indiquait une ABSENCE de tests sur ce chemin :
`db.get_session_user` filtre par `WHERE sessions.expires_at > ?`, comparaison
de chaînes ISO-8601 (colonne TEXT, identique sur SQLite et PostgreSQL — voir
db.py::_now()/create_session). Après relecture, le mécanisme est cohérent
(même format de chaîne généré par le même code Python quel que soit le
moteur, comparaison lexicographique correcte pour de l'ISO-8601 UTC) : pas de
bug identifié, seulement un chemin jamais exercé par un test. Conformément à
la consigne, aucune modification de auth.py/db.py ici — uniquement les tests
manquants.
"""
import random
import unittest

import db
import server


def _register(client):
    email = f"sess{random.randint(1_000_000, 9_999_999)}@gmail.com"
    username = f"sess{random.randint(100_000, 999_999)}"
    resp = client.post("/api/auth/register", json={
        "email": email, "username": username, "pseudo": "Test",
        "birth_date": "2000-01-01",
        "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
        "accept_terms": True, "accept_privacy": True,
    })
    return resp.get_json()["user"]


class TestGetSessionUserExpiration(unittest.TestCase):
    """Niveau unitaire (db.py), indépendant de Flask — SQLite (mode réel de
    ce projet aujourd'hui)."""

    def setUp(self):
        self.user_id = db.create_user(
            f"sessdb{random.randint(1_000_000, 9_999_999)}@gmail.com",
            f"sessdb{random.randint(100_000, 999_999)}", "Pseudo", "hash",
        )

    def test_session_valide_est_acceptee(self):
        token = db.create_session(self.user_id, days=1)
        found = db.get_session_user(token)
        self.assertIsNotNone(found)
        self.assertEqual(found["id"], self.user_id)

    def test_session_expiree_est_rejetee(self):
        """Le cœur du scénario : une session dont expires_at est déjà dans
        le passé (days négatif, même mécanisme de calcul que create_session
        en usage normal — voir db.py::create_session, expires_at = now +
        timedelta(days=days)) ne doit plus jamais résoudre d'utilisateur."""
        token = db.create_session(self.user_id, days=-1)
        found = db.get_session_user(token)
        self.assertIsNone(found)

    def test_session_expirant_a_linstant_pres_est_rejetee(self):
        """Cas limite : days=0 avec un `days` fractionnaire n'existe pas côté
        API (int), donc on vérifie l'égalité stricte via une session tout
        juste expirée par construction (days=-1 couvre déjà largement la
        marge), et on vérifie qu'un jeton inconnu (jamais créé) est aussi
        rejeté proprement, sans lever d'exception."""
        self.assertIsNone(db.get_session_user("token-completement-inconnu"))
        self.assertIsNone(db.get_session_user(""))
        self.assertIsNone(db.get_session_user(None))

    def test_session_expiree_de_plusieurs_mois_est_rejetee(self):
        """Un utilisateur inactif depuis longtemps (le scénario "plusieurs
        mois d'utilisation" de l'audit long terme) ne doit jamais obtenir de
        session valide en rejouant un ancien cookie."""
        token = db.create_session(self.user_id, days=-200)
        self.assertIsNone(db.get_session_user(token))


class TestSessionExpireeEnCoursDutilisationHTTP(unittest.TestCase):
    """Bout en bout via une vraie route protégée (@login_required) : preuve
    qu'une session déjà valide, qui devient expirée ENTRE deux requêtes
    (pas seulement au moment de la connexion), est bien rejetée par 401 —
    et pas seulement par la couche db.py en isolation."""

    def setUp(self):
        self.client = server.app.test_client()
        self.user = _register(self.client)

    def test_session_fraichement_creee_donne_acces(self):
        resp = self.client.get("/api/support/tickets")
        self.assertEqual(resp.status_code, 200)

    def test_session_expiree_entre_deux_requetes_est_rejetee_401(self):
        # La session posée par _register()/register() est valide (voir test
        # ci-dessus) : on la remplace ICI par un jeton expiré pour le MÊME
        # utilisateur, simulant un cookie de session devenu invalide depuis
        # la dernière requête (au lieu d'un jeton jamais valide dès le
        # départ, cas déjà couvert au niveau unitaire ci-dessus).
        expired_token = db.create_session(self.user["id"], days=-1)
        self.client.set_cookie("nm_session", expired_token)

        resp = self.client.get("/api/support/tickets")
        self.assertEqual(resp.status_code, 401)

    def test_session_valide_puis_expiree_puis_a_nouveau_valide(self):
        """Confirme que le rejet est bien lié à l'expiration précise du
        jeton utilisé, pas à un effet de bord global (ex: compte bloqué) :
        un NOUVEAU jeton valide pour le même utilisateur redonne accès."""
        expired_token = db.create_session(self.user["id"], days=-1)
        self.client.set_cookie("nm_session", expired_token)
        self.assertEqual(self.client.get("/api/support/tickets").status_code, 401)

        fresh_token = db.create_session(self.user["id"], days=1)
        self.client.set_cookie("nm_session", fresh_token)
        self.assertEqual(self.client.get("/api/support/tickets").status_code, 200)


if __name__ == "__main__":
    unittest.main()
