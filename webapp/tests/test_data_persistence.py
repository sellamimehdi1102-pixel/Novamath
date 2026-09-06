"""
Suite de non-régression "persistance des données utilisateur" (audit
production 2026-09-06) : démontre, au niveau code, que rien dans la couche
DB ne réinitialise ou ne perd les données d'un utilisateur entre deux accès —
y compris en simulant un redémarrage du processus applicatif (fermeture de
connexion + ré-exécution de db.init_db(), exactement l'appel fait par
server.py au boot).

Ce que cette suite PROUVE : le code ne contient aucune réinitialisation
destructive (pas de DROP, pas de recréation de fichier, schéma idempotent).

Ce que cette suite NE PEUT PAS prouver : que le disque sur lequel vit
data/novamath.db est un volume réellement persistant en production (Render).
C'est une question d'infrastructure, hors de portée d'un test unitaire — voir
RENDER_SETUP.md §6 et le rapport de la mission "persistance des données".
"""
import random
import unittest

import config
import db


def _rand_email():
    return f"persist{random.randint(1_000_000, 9_999_999)}@gmail.com"


def _rand_username():
    return f"persist{random.randint(100_000, 999_999)}"


@unittest.skipIf(config.DATABASE_URL is not None, "Suite écrite pour le mode SQLite par défaut (voir db.DB_PATH)")
class TestPersistanceApresRedemarrageSimule(unittest.TestCase):
    def test_utilisateur_et_progression_survivent_a_une_reouverture_de_connexion(self):
        # TEST 1 — créer un utilisateur.
        email = _rand_email()
        user_id = db.create_user(email, _rand_username(), "Ada", "hash-fake")
        self.assertIsNotNone(db.get_user_by_email(email))

        # TEST 2 — modifier ses données importantes (progression/statistiques).
        db.update_stats_cache(user_id, xp=1234, level=7, accuracy=0.82, progression=0.55, total_time_s=9999)

        # TEST 3 — fermer/rouvrir la connexion (chaque fonction db.py ouvre et
        # ferme déjà la sienne, donc aucune connexion "vivante" ne subsiste
        # entre deux appels) PUIS ré-exécuter db.init_db() — l'appel exact que
        # server.py fait à chaque démarrage du process, schéma idempotent
        # (CREATE TABLE IF NOT EXISTS) : simule un redémarrage réel du serveur
        # sans recréer/supprimer le fichier.
        db.init_db()

        # TEST 4 — relire les données : doivent être identiques.
        user = db.get_user_by_id(user_id)
        self.assertIsNotNone(user)
        self.assertEqual(user["email"], email.lower())
        self.assertEqual(user["xp"], 1234)
        self.assertEqual(user["level"], 7)
        self.assertAlmostEqual(user["accuracy"], 0.82)
        self.assertAlmostEqual(user["progression"], 0.55)
        self.assertEqual(user["total_time_s"], 9999)

    def test_oauth_account_et_conversation_chatbot_survivent_au_redemarrage_simule(self):
        """Couvre les autres catégories de données réellement persistées par
        Mathadap au-delà du profil utilisateur : liaison OAuth (webapp/auth.py)
        et historique de conversation chatbot (webapp/chatbot/) — pas de
        catégorie inventée, seulement ce qui existe réellement dans le
        schéma (voir db.SCHEMA)."""
        email = _rand_email()
        user_id = db.create_user(email, _rand_username(), "Ada", None, auth_provider="google")
        db.link_oauth_account(user_id, "google", f"sub-{random.randint(10_000_000, 99_999_999)}")
        conv_id = db.create_conversation(user_id, title="Ma conversation")
        db.add_message(conv_id, "user", "Bonjour")

        db.init_db()  # redémarrage simulé, voir test ci-dessus

        self.assertIsNotNone(db.get_user_by_id(user_id))
        conversations = db.list_conversations(user_id)
        self.assertTrue(any(c["id"] == conv_id for c in conversations))
        messages = db.list_messages(conv_id)
        self.assertTrue(any(m["content"] == "Bonjour" for m in messages))

    def test_db_path_est_bien_sous_data_dir_partage_avec_les_secrets(self):
        """Ancrage explicite : DB_PATH doit rester sous DATA_DIR (même
        répertoire que les secrets .flask_secret_key/.admin_key, voir
        server.py::_get_or_create_secret) — c'est ce répertoire unique qui
        doit être monté sur un disque persistant en production (voir
        RENDER_SETUP.md §6). Un futur changement qui déplacerait DB_PATH hors
        de DATA_DIR romprait silencieusement cette hypothèse."""
        self.assertEqual(db.DB_PATH.parent, db.DATA_DIR)


if __name__ == "__main__":
    unittest.main()
