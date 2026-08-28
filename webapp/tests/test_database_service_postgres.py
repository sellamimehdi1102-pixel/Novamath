"""
Suite ARCH-02 : intégration RÉELLE avec un serveur PostgreSQL — jamais un
serveur externe permanent requis. Se désactive proprement (skip) si
`DATABASE_URL` n'est pas positionnée vers un PostgreSQL réellement joignable.

Deux façons de fournir ce serveur, toutes deux documentées dans
DEPLOYMENT.md :
- CI (.github/workflows/ci.yml, job "postgres-tests") : conteneur PostgreSQL
  éphémère fourni nativement par GitHub Actions (`services: postgres:`),
  détruit à la fin du job — c'est la stratégie principale, exécutée à
  chaque push/pull request ;
- local : `docker compose --profile postgres up -d db` puis
  `DATABASE_URL=postgresql://novamath:novamath@localhost:5432/novamath pytest
  tests/test_database_service_postgres.py`.

Sans l'une de ces deux options, cette suite se désactive intégralement
(aucun échec, un skip explicite par test) — jamais un serveur PostgreSQL
externe à installer/maintenir manuellement.
"""
import os
import random
import unittest

import config
import database_service as ds
import db

_DATABASE_URL = os.environ.get("DATABASE_URL")


def _postgres_reachable():
    if not _DATABASE_URL or not _DATABASE_URL.lower().startswith(("postgres://", "postgresql://")):
        return False
    try:
        conn = ds.get_connection(sqlite_path="unused", sqlite_data_dir="unused", database_url=_DATABASE_URL)
        conn.close()
        return True
    except Exception:
        return False


_REACHABLE = _postgres_reachable()
_SKIP_REASON = (
    "DATABASE_URL absente/non-PostgreSQL/serveur injoignable — voir DEPLOYMENT.md "
    "(docker compose --profile postgres, ou CI job postgres-tests)."
)


def _unique(prefix):
    return f"{prefix}{random.randint(1_000_000, 9_999_999)}"


@unittest.skipUnless(_REACHABLE, _SKIP_REASON)
class PostgresTestCase(unittest.TestCase):
    """Bascule `config.DATABASE_URL` vers le serveur PostgreSQL de test pour
    la durée de la suite, applique le schéma une fois (idempotent), puis
    laisse chaque test créer ses propres données identifiées par des valeurs
    aléatoires uniques (même convention que _fake_ip()/emails aléatoires
    utilisée ailleurs dans le projet — jamais de TRUNCATE global entre
    tests, qui empêcherait toute parallélisation future)."""

    @classmethod
    def setUpClass(cls):
        cls._url_backup = config.DATABASE_URL
        config.DATABASE_URL = _DATABASE_URL
        ds.reset_pool()
        db.init_db()

    @classmethod
    def tearDownClass(cls):
        config.DATABASE_URL = cls._url_backup
        ds.reset_pool()


class TestConnexionReelle(PostgresTestCase):
    def test_get_connection_renvoie_un_wrapper_postgres(self):
        conn = db.get_connection()
        try:
            self.assertIsInstance(conn, ds._PostgresConnection)
        finally:
            conn.close()

    def test_select_1_fonctionne(self):
        conn = db.get_connection()
        try:
            row = conn.execute("SELECT 1 AS un").fetchone()
            self.assertEqual(row["un"], 1)
        finally:
            conn.close()

    def test_engine_of_reconnait_postgresql(self):
        conn = db.get_connection()
        try:
            self.assertEqual(ds.engine_of(conn), ds.ENGINE_POSTGRESQL)
        finally:
            conn.close()

    def test_plusieurs_connexions_successives(self):
        for _ in range(5):
            conn = db.get_connection()
            conn.execute("SELECT 1")
            conn.close()


class TestTransactionsEtRollback(PostgresTestCase):
    def test_commit_persiste_les_donnees(self):
        email = _unique("commit") + "@example.com"
        uid = db.create_user(email, _unique("user"), "Pseudo", "hash")
        self.assertIsNotNone(db.get_user_by_id(uid))

    def test_rollback_explicite_annule_linsertion(self):
        conn = db.get_connection()
        try:
            email = _unique("rollback") + "@example.com"
            conn.execute(
                "INSERT INTO users (email, username, pseudo, password_hash, auth_provider, created_at) "
                "VALUES (?, ?, ?, ?, 'local', ?)",
                (email, _unique("user"), "Pseudo", "hash", "2026-01-01T00:00:00"),
            )
            conn.rollback()
        finally:
            conn.close()
        self.assertIsNone(db.get_user_by_email(email))

    def test_close_sans_commit_annule_la_transaction(self):
        """Reproduit le pattern `finally: conn.close()` d'un appel db.py
        interrompu par une exception AVANT commit() — la transaction ne
        doit jamais survivre (voir _PostgresConnection.close())."""
        email = _unique("interrupted") + "@example.com"
        conn = db.get_connection()
        try:
            conn.execute(
                "INSERT INTO users (email, username, pseudo, password_hash, auth_provider, created_at) "
                "VALUES (?, ?, ?, ?, 'local', ?)",
                (email, _unique("user"), "Pseudo", "hash", "2026-01-01T00:00:00"),
            )
            # Pas de commit() ici — simule une exception levée juste après.
        finally:
            conn.close()
        self.assertIsNone(db.get_user_by_email(email))

    def test_isolation_deux_connexions_distinctes(self):
        """Une transaction non commitée sur une connexion n'est jamais
        visible depuis une AUTRE connexion (isolation READ COMMITTED,
        comportement par défaut de PostgreSQL — jamais reconfiguré)."""
        email = _unique("isolation") + "@example.com"
        conn_a = db.get_connection()
        conn_b = db.get_connection()
        try:
            conn_a.execute(
                "INSERT INTO users (email, username, pseudo, password_hash, auth_provider, created_at) "
                "VALUES (?, ?, ?, ?, 'local', ?)",
                (email, _unique("user"), "Pseudo", "hash", "2026-01-01T00:00:00"),
            )
            row = conn_b.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            self.assertIsNone(row)
            conn_a.commit()
        finally:
            conn_a.close()
            conn_b.close()
        self.assertIsNotNone(db.get_user_by_email(email))


class TestPoolDeConnexions(PostgresTestCase):
    def test_connexions_reutilisees_par_le_pool(self):
        pool = ds._get_pool()
        initial_stats = pool.get_stats()
        for _ in range(10):
            conn = db.get_connection()
            conn.execute("SELECT 1")
            conn.close()
        stats = pool.get_stats()
        # Le pool ne doit jamais avoir ouvert 10 connexions distinctes pour
        # 10 appels séquentiels — la réutilisation est le point même du pool.
        self.assertLessEqual(stats.get("connections_num", 0), config.DATABASE_POOL_SIZE + config.DATABASE_MAX_OVERFLOW)

    def test_reset_pool_puis_reconnexion(self):
        """Reconnexion propre après une coupure simulée (fermeture forcée du
        pool) — le pool suivant doit fonctionner normalement."""
        conn = db.get_connection()
        conn.execute("SELECT 1")
        conn.close()
        ds.reset_pool()
        conn2 = db.get_connection()
        try:
            row = conn2.execute("SELECT 1 AS un").fetchone()
            self.assertEqual(row["un"], 1)
        finally:
            conn2.close()

    def test_pool_respecte_min_size(self):
        pool = ds._get_pool()
        self.assertEqual(pool.min_size, config.DATABASE_POOL_SIZE)


class TestMigrationsIdempotentes(PostgresTestCase):
    def test_init_db_rejouable_plusieurs_fois(self):
        db.init_db()
        db.init_db()
        db.init_db()

    def test_colonnes_de_migration_presentes(self):
        email = _unique("migcols") + "@example.com"
        uid = db.create_user(email, _unique("user"), "Pseudo", "hash")
        user = db.get_user_by_id(uid)
        for column in (
            "guest_last_seen_at", "guest_dashboard_viewed", "stripe_customer_id", "stripe_subscription_id",
            "plan", "stripe_subscription_status", "role", "two_factor_enabled", "two_factor_secret",
            "two_factor_enabled_at", "two_factor_last_counter",
        ):
            self.assertIn(column, user)

    def test_add_column_if_missing_est_idempotent(self):
        conn = db.get_connection()
        try:
            ds.add_column_if_missing(conn, "users", "role", "TEXT NOT NULL DEFAULT 'user'")
            ds.add_column_if_missing(conn, "users", "role", "TEXT NOT NULL DEFAULT 'user'")
        finally:
            conn.close()

    def test_toutes_les_tables_du_schema_existent(self):
        conn = db.get_connection()
        try:
            rows = conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            ).fetchall()
            tables = {r["table_name"] for r in rows}
        finally:
            conn.close()
        for table in (
            "users", "oauth_accounts", "sessions", "login_attempts", "password_resets", "security_events",
            "conversations", "chatbot_messages", "chatbot_quota", "stripe_webhook_events", "user_daily_usage",
            "rate_limit_events", "two_factor_challenges", "two_factor_recovery_codes",
        ):
            self.assertIn(table, tables)


class TestCompatibiliteUpsert(PostgresTestCase):
    def test_increment_chatbot_quota(self):
        uid = db.create_user(_unique("quota") + "@example.com", _unique("user"), "Pseudo", "hash")
        first = db.increment_chatbot_quota(uid, "2026-02-01")
        second = db.increment_chatbot_quota(uid, "2026-02-01")
        self.assertEqual(first, 1)
        self.assertEqual(second, 2)

    def test_increment_daily_usage(self):
        uid = db.create_user(_unique("daily") + "@example.com", _unique("user"), "Pseudo", "hash")
        first = db.increment_daily_usage(uid, "PDF_ANALYSIS", "2026-02-01", amount=4)
        second = db.increment_daily_usage(uid, "PDF_ANALYSIS", "2026-02-01", amount=1)
        self.assertEqual(first, 4)
        self.assertEqual(second, 5)

    def test_record_rate_limit_event(self):
        key = _unique("rl")
        first = db.record_rate_limit_event(key, "/api/x", 5000)
        second = db.record_rate_limit_event(key, "/api/x", 5000)
        self.assertEqual(first, 1)
        self.assertEqual(second, 2)

    def test_upsert_decrement_negatif(self):
        uid = db.create_user(_unique("neg") + "@example.com", _unique("user"), "Pseudo", "hash")
        db.increment_daily_usage(uid, "EXPORTS", "2026-02-02", amount=3)
        total = db.increment_daily_usage(uid, "EXPORTS", "2026-02-02", amount=-1)
        self.assertEqual(total, 2)


class TestCompatibiliteInsertOrIgnore(PostgresTestCase):
    def test_mark_stripe_event_processed_idempotent(self):
        event_id = _unique("evt")
        self.assertFalse(db.has_processed_stripe_event(event_id))
        db.mark_stripe_event_processed(event_id, "checkout.session.completed")
        db.mark_stripe_event_processed(event_id, "checkout.session.completed")
        self.assertTrue(db.has_processed_stripe_event(event_id))

    def test_link_oauth_account_idempotent(self):
        uid = db.create_user(_unique("oauth") + "@example.com", _unique("user"), "Pseudo", "hash")
        provider_id = _unique("sub")
        db.link_oauth_account(uid, "google", provider_id)
        db.link_oauth_account(uid, "google", provider_id)
        found = db.get_user_by_oauth("google", provider_id)
        self.assertEqual(found["id"], uid)

    def test_ensure_daily_usage_row_idempotent(self):
        uid = db.create_user(_unique("ensure") + "@example.com", _unique("user"), "Pseudo", "hash")
        db.ensure_daily_usage_row(uid, "AI_GENERATIONS", "2026-02-03")
        db.ensure_daily_usage_row(uid, "AI_GENERATIONS", "2026-02-03")
        self.assertEqual(db.get_daily_usage(uid, "AI_GENERATIONS", "2026-02-03"), 0)


class TestCompatibiliteReturningId(PostgresTestCase):
    def test_create_user_renvoie_un_id_valide(self):
        uid = db.create_user(_unique("ret1") + "@example.com", _unique("user"), "Pseudo", "hash")
        self.assertIsInstance(uid, int)
        self.assertGreater(uid, 0)

    def test_create_guest_user_renvoie_un_id_valide(self):
        uid = db.create_guest_user(_unique("guest"))
        self.assertIsInstance(uid, int)

    def test_create_conversation_renvoie_un_id_valide(self):
        uid = db.create_user(_unique("ret2") + "@example.com", _unique("user"), "Pseudo", "hash")
        conv_id = db.create_conversation(uid, "Titre")
        self.assertIsInstance(conv_id, int)

    def test_add_message_renvoie_un_id_valide(self):
        uid = db.create_user(_unique("ret3") + "@example.com", _unique("user"), "Pseudo", "hash")
        conv_id = db.create_conversation(uid)
        msg_id = db.add_message(conv_id, "user", "Salut")
        self.assertIsInstance(msg_id, int)

    def test_ids_generes_sont_croissants(self):
        uid1 = db.create_user(_unique("inc1") + "@example.com", _unique("user"), "Pseudo", "hash")
        uid2 = db.create_user(_unique("inc2") + "@example.com", _unique("user"), "Pseudo", "hash")
        self.assertGreater(uid2, uid1)


class TestCompatibiliteBooleen(PostgresTestCase):
    def test_two_factor_enabled_stocke_comme_entier(self):
        uid = db.create_user(_unique("bool1") + "@example.com", _unique("user"), "Pseudo", "hash")
        db.enable_two_factor(uid)
        user = db.get_user_by_id(uid)
        self.assertEqual(user["two_factor_enabled"], 1)
        db.disable_two_factor(uid)
        user = db.get_user_by_id(uid)
        self.assertEqual(user["two_factor_enabled"], 0)

    def test_conversation_pinned_booleen(self):
        uid = db.create_user(_unique("bool2") + "@example.com", _unique("user"), "Pseudo", "hash")
        conv_id = db.create_conversation(uid, "Titre")
        db.update_conversation(conv_id, uid, pinned=True)
        conv = db.get_conversation(conv_id, uid)
        self.assertEqual(conv["pinned"], 1)

    def test_login_attempt_success_booleen(self):
        email = _unique("bool3") + "@example.com"
        db.record_login_attempt(email, True)
        db.record_login_attempt(email, False)
        self.assertEqual(db.count_recent_failed_attempts(email), 1)


class TestGestionDesErreurs(PostgresTestCase):
    def test_email_duplique_leve_une_erreur(self):
        email = _unique("dup") + "@example.com"
        db.create_user(email, _unique("user"), "Pseudo", "hash")
        with self.assertRaises(Exception):
            db.create_user(email, _unique("user2"), "Pseudo 2", "hash2")

    def test_erreur_ne_laisse_pas_le_pool_dans_un_etat_corrompu(self):
        """Après une erreur d'intégrité (contrainte UNIQUE violée), la
        prochaine connexion tirée du pool doit fonctionner normalement —
        preuve que le rollback automatique (voir _PostgresConnection.close())
        empêche bien une transaction avortée de fuiter vers l'appelant
        suivant."""
        email = _unique("dup2") + "@example.com"
        db.create_user(email, _unique("user"), "Pseudo", "hash")
        try:
            db.create_user(email, _unique("user3"), "Pseudo 3", "hash3")
        except Exception:
            pass
        # Le pool doit rester utilisable :
        other_uid = db.create_user(_unique("after") + "@example.com", _unique("user4"), "Pseudo 4", "hash4")
        self.assertIsInstance(other_uid, int)

    def test_database_connection_error_sur_url_invalide(self):
        conn = db.get_connection()
        conn.close()
        broken_url = "postgresql://mauvais_user:mauvais_mdp@127.0.0.1:1/inconnue"
        with self.assertRaises((ds.DatabaseConnectionError, Exception)):
            c = ds.get_connection(sqlite_path="unused", sqlite_data_dir="unused", database_url=broken_url)
            c.close()


class TestReconnexion(PostgresTestCase):
    def test_operations_apres_reset_pool_fonctionnent(self):
        uid = db.create_user(_unique("recon1") + "@example.com", _unique("user"), "Pseudo", "hash")
        ds.reset_pool()
        user = db.get_user_by_id(uid)
        self.assertIsNotNone(user)

    def test_plusieurs_cycles_reset_reconnexion(self):
        for i in range(3):
            uid = db.create_user(_unique(f"cycle{i}") + "@example.com", _unique("user"), "Pseudo", "hash")
            self.assertIsInstance(uid, int)
            ds.reset_pool()


class TestDbPyRegressionPostgres(PostgresTestCase):
    """Même suite que TestDbPyRegressionSQLite (test_database_service.py)
    mais exécutée contre un VRAI serveur PostgreSQL — preuve que db.py se
    comporte de façon strictement identique quel que soit le moteur."""

    def test_executemany_replace_recovery_codes(self):
        uid = db.create_user(_unique("pgexec") + "@example.com", _unique("user"), "Pseudo", "hash")
        db.replace_recovery_codes(uid, ["h1", "h2", "h3"])
        self.assertEqual(len(db.get_recovery_codes(uid)), 3)

    def test_consume_recovery_code_atomique(self):
        uid = db.create_user(_unique("pgconsume") + "@example.com", _unique("user"), "Pseudo", "hash")
        db.replace_recovery_codes(uid, ["hashY"])
        self.assertTrue(db.consume_recovery_code(uid, "hashY"))
        self.assertFalse(db.consume_recovery_code(uid, "hashY"))

    def test_executemany_cleanup_expired_guests_sans_erreur(self):
        guest_id = db.create_guest_user(_unique("pgguest"))
        ids = db.cleanup_expired_guests(max_idle_hours=24)
        self.assertIsInstance(ids, list)
        self.assertNotIn(guest_id, ids)

    def test_sessions_creation_et_lecture(self):
        uid = db.create_user(_unique("pgsess") + "@example.com", _unique("user"), "Pseudo", "hash")
        token = db.create_session(uid, days=1)
        found = db.get_session_user(token)
        self.assertEqual(found["id"], uid)

    def test_session_expiree_est_rejetee(self):
        """Release Candidate : même vérification que tests/test_session_
        expiration.py côté SQLite — expires_at est une comparaison de
        chaînes ISO-8601 (colonne TEXT sur les deux moteurs, voir db.py::
        _now()), à prouver identique sur un vrai PostgreSQL, pas seulement
        supposée par symétrie du code."""
        uid = db.create_user(_unique("pgsessexp") + "@example.com", _unique("user"), "Pseudo", "hash")
        token = db.create_session(uid, days=-1)
        self.assertIsNone(db.get_session_user(token))

    def test_delete_user_cascade(self):
        uid = db.create_user(_unique("pgcascade") + "@example.com", _unique("user"), "Pseudo", "hash")
        db.create_session(uid)
        db.delete_user(uid)
        self.assertIsNone(db.get_user_by_id(uid))


if __name__ == "__main__":
    unittest.main()
