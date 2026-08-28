"""
Suite ARCH-02 : webapp/database_service.py — détection du moteur, traduction
SQL SQLite<->PostgreSQL, wrapper de connexion/curseur PostgreSQL (testé ici
avec des objets psycopg simulés — aucun serveur PostgreSQL requis pour cette
suite, voir test_database_service_postgres.py pour l'intégration réelle),
configuration, et non-régression complète de webapp/db.py sur SQLite (mode
par défaut, comportement historique).
"""
import importlib
import os
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import psycopg

import config
import database_service as ds
import db


def _reload_config():
    return importlib.reload(config)


ENV_VARS = ("DATABASE_URL", "DATABASE_POOL_SIZE", "DATABASE_MAX_OVERFLOW", "DATABASE_POOL_TIMEOUT", "DATABASE_POOL_RECYCLE")


class _EnvIsolatedTestCase(unittest.TestCase):
    def setUp(self):
        self._saved = {name: os.environ.get(name) for name in ENV_VARS}
        for name in ENV_VARS:
            os.environ.pop(name, None)
        _reload_config()
        ds.reset_pool()

    def tearDown(self):
        for name, value in self._saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        _reload_config()
        ds.reset_pool()


class _SqliteIsolatedTestCase(unittest.TestCase):
    """Même stratégie que tests/test_two_factor_migration.py : base SQLite
    temporaire, jamais la base réelle."""

    def setUp(self):
        self._tmp_dir = tempfile.mkdtemp()
        self._data_dir_backup = db.DATA_DIR
        self._db_path_backup = db.DB_PATH
        db.DATA_DIR = Path(self._tmp_dir)
        db.DB_PATH = db.DATA_DIR / "novamath.db"

    def tearDown(self):
        db.DATA_DIR = self._data_dir_backup
        db.DB_PATH = self._db_path_backup
        shutil.rmtree(self._tmp_dir, ignore_errors=True)


# ── Détection du moteur ──────────────────────────────────────────────────
class TestDetectEngine(_EnvIsolatedTestCase):
    def test_absente_donne_sqlite(self):
        self.assertEqual(ds.detect_engine(None), ds.ENGINE_SQLITE)

    def test_vide_donne_sqlite(self):
        self.assertEqual(ds.detect_engine(""), ds.ENGINE_SQLITE)

    def test_postgresql_scheme(self):
        self.assertEqual(ds.detect_engine("postgresql://u:p@host/db"), ds.ENGINE_POSTGRESQL)

    def test_postgres_scheme_court(self):
        self.assertEqual(ds.detect_engine("postgres://u:p@host/db"), ds.ENGINE_POSTGRESQL)

    def test_sqlite_scheme_explicite(self):
        self.assertEqual(ds.detect_engine("sqlite:///chemin/vers/fichier.db"), ds.ENGINE_SQLITE)

    def test_scheme_insensible_a_la_casse(self):
        self.assertEqual(ds.detect_engine("POSTGRESQL://u:p@host/db"), ds.ENGINE_POSTGRESQL)

    def test_scheme_inconnu_leve_value_error(self):
        with self.assertRaises(ValueError):
            ds.detect_engine("mysql://u:p@host/db")

    def test_lit_config_database_url_par_defaut(self):
        os.environ["DATABASE_URL"] = "postgresql://u:p@host/db"
        _reload_config()
        self.assertEqual(ds.detect_engine(), ds.ENGINE_POSTGRESQL)

    def test_parametre_explicite_prime_sur_config(self):
        os.environ["DATABASE_URL"] = "postgresql://u:p@host/db"
        _reload_config()
        self.assertEqual(ds.detect_engine(None), ds.ENGINE_POSTGRESQL)
        self.assertEqual(ds.detect_engine(""), ds.ENGINE_SQLITE)


class TestEngineOf(_SqliteIsolatedTestCase):
    def test_connexion_sqlite_reconnue(self):
        conn = db.get_connection()
        try:
            self.assertEqual(ds.engine_of(conn), ds.ENGINE_SQLITE)
        finally:
            conn.close()

    def test_connexion_postgres_simulee_reconnue(self):
        wrapper = ds._PostgresConnection(MagicMock(), MagicMock())
        self.assertEqual(ds.engine_of(wrapper), ds.ENGINE_POSTGRESQL)


# ── Durcissement production : PRAGMA SQLite (voir audit "database is
# locked" sous gunicorn multi-worker/thread) ────────────────────────────────
class TestSqliteProductionPragmas(_SqliteIsolatedTestCase):
    def test_journal_mode_wal_sur_fichier_reel(self):
        conn = db.get_connection()
        try:
            mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
            self.assertEqual(mode.lower(), "wal")
        finally:
            conn.close()

    def test_synchronous_normal(self):
        conn = db.get_connection()
        try:
            # NORMAL = 1 (valeur numérique renvoyée par PRAGMA synchronous)
            value = conn.execute("PRAGMA synchronous").fetchone()[0]
            self.assertEqual(value, 1)
        finally:
            conn.close()

    def test_busy_timeout_configure(self):
        conn = db.get_connection()
        try:
            value = conn.execute("PRAGMA busy_timeout").fetchone()[0]
            self.assertEqual(value, 30000)
        finally:
            conn.close()

    def test_wal_sans_effet_sur_base_memoire(self):
        """Une base ':memory:' n'a pas de fichier -WAL possible : SQLite doit
        silencieusement rester en mode 'memory' plutôt que lever une erreur —
        condition nécessaire pour que les tests qui utilisent une DB en
        mémoire continuent de fonctionner sans changement."""
        conn = ds._sqlite_connection(":memory:", self._tmp_dir)
        try:
            mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
            self.assertEqual(mode.lower(), "memory")
        finally:
            conn.close()

    def test_ecritures_concurrentes_ne_levent_jamais_database_is_locked(self):
        """Preuve directe du problème corrigé : sans WAL/busy_timeout, des
        écritures concurrentes sur le même fichier SQLite peuvent lever
        sqlite3.OperationalError('database is locked'). Ici, 20 threads
        écrivent chacun 5 fois dans une table réelle du schéma
        (security_events, via db.log_security_event) sans qu'aucune
        exception ne remonte."""
        import threading
        db.init_db()
        errors = []

        def worker(i):
            try:
                for _ in range(5):
                    db.log_security_event(f"hardening_test_{i}")
            except Exception as e:  # noqa: BLE001 - on veut voir TOUTE exception
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [], f"Écritures concurrentes en échec : {errors}")


# ── Traduction SQL ────────────────────────────────────────────────────────
class TestTranslateSqlPlaceholders(unittest.TestCase):
    def test_un_placeholder(self):
        self.assertEqual(ds._translate_sql_for_postgres("SELECT * FROM t WHERE id = ?"), "SELECT * FROM t WHERE id = %s")

    def test_plusieurs_placeholders_dans_lordre(self):
        sql = ds._translate_sql_for_postgres("UPDATE t SET a = ?, b = ? WHERE id = ?")
        self.assertEqual(sql, "UPDATE t SET a = %s, b = %s WHERE id = %s")

    def test_aucun_placeholder(self):
        self.assertEqual(ds._translate_sql_for_postgres("SELECT COUNT(*) FROM t"), "SELECT COUNT(*) FROM t")

    def test_pourcentage_litteral_echappe(self):
        sql = ds._translate_sql_for_postgres("SELECT * FROM t WHERE x LIKE 'abc%'")
        self.assertEqual(sql, "SELECT * FROM t WHERE x LIKE 'abc%%'")

    def test_pourcentage_et_placeholder_combines(self):
        sql = ds._translate_sql_for_postgres(
            "SELECT COUNT(*) AS n FROM security_events WHERE event_type LIKE 'two_factor%_failed' AND created_at > ?"
        )
        self.assertEqual(
            sql,
            "SELECT COUNT(*) AS n FROM security_events WHERE event_type LIKE 'two_factor%%_failed' AND created_at > %s",
        )


class TestTranslateSqlInsertOrIgnore(unittest.TestCase):
    def test_stripe_webhook_events(self):
        sql = ds._translate_sql_for_postgres(
            "INSERT OR IGNORE INTO stripe_webhook_events (event_id, event_type, processed_at) VALUES (?, ?, ?)"
        )
        self.assertNotIn("OR IGNORE", sql)
        self.assertIn("INSERT INTO stripe_webhook_events", sql)
        self.assertTrue(sql.rstrip().endswith("ON CONFLICT DO NOTHING"))

    def test_oauth_accounts(self):
        sql = ds._translate_sql_for_postgres(
            "INSERT OR IGNORE INTO oauth_accounts (user_id, provider, provider_user_id) VALUES (?, ?, ?)",
            autoincrement_tables={"oauth_accounts"},
        )
        self.assertIn("ON CONFLICT DO NOTHING", sql)
        # jamais les deux en même temps : ON CONFLICT DO NOTHING seul.
        self.assertNotIn("RETURNING", sql)

    def test_user_daily_usage(self):
        sql = ds._translate_sql_for_postgres(
            "INSERT OR IGNORE INTO user_daily_usage (user_id, quota_type, date, count) VALUES (?, ?, ?, 0)"
        )
        self.assertIn("ON CONFLICT DO NOTHING", sql)

    def test_placeholders_toujours_traduits(self):
        sql = ds._translate_sql_for_postgres("INSERT OR IGNORE INTO t (a) VALUES (?)")
        self.assertIn("%s", sql)
        self.assertNotIn("?", sql)


class TestTranslateSqlReturningId(unittest.TestCase):
    TABLES = frozenset({"users", "conversations", "chatbot_messages"})

    def test_ajoute_returning_sur_table_autoincrement(self):
        sql = ds._translate_sql_for_postgres(
            "INSERT INTO users (email) VALUES (?)", self.TABLES,
        )
        self.assertTrue(sql.rstrip().endswith("RETURNING id"))

    def test_najoute_pas_sur_table_non_autoincrement(self):
        sql = ds._translate_sql_for_postgres(
            "INSERT INTO sessions (token) VALUES (?)", self.TABLES,
        )
        self.assertNotIn("RETURNING", sql)

    def test_najoute_pas_si_deja_present(self):
        original = "INSERT INTO users (email) VALUES (?) RETURNING id"
        sql = ds._translate_sql_for_postgres(original, self.TABLES)
        self.assertEqual(sql.count("RETURNING"), 1)

    def test_najoute_pas_sur_upsert_on_conflict(self):
        sql = ds._translate_sql_for_postgres(
            "INSERT INTO user_daily_usage (user_id, quota_type, date, count) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(user_id, quota_type, date) DO UPDATE SET count = count + excluded.count",
            frozenset({"user_daily_usage"}),
        )
        self.assertNotIn("RETURNING", sql)

    def test_najoute_pas_sans_table_reconnue(self):
        sql = ds._translate_sql_for_postgres("INSERT INTO unknown_table (a) VALUES (?)", self.TABLES)
        self.assertNotIn("RETURNING", sql)

    def test_conversations(self):
        sql = ds._translate_sql_for_postgres(
            "INSERT INTO conversations (user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?)", self.TABLES,
        )
        self.assertTrue(sql.rstrip().endswith("RETURNING id"))

    def test_chatbot_messages(self):
        sql = ds._translate_sql_for_postgres(
            "INSERT INTO chatbot_messages (conversation_id, role, content, cards, mentions, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)", self.TABLES,
        )
        self.assertTrue(sql.rstrip().endswith("RETURNING id"))

    def test_select_jamais_touche(self):
        sql = ds._translate_sql_for_postgres("SELECT * FROM users WHERE id = ?", self.TABLES)
        self.assertNotIn("RETURNING", sql)

    def test_update_jamais_touche(self):
        sql = ds._translate_sql_for_postgres("UPDATE users SET plan = ? WHERE id = ?", self.TABLES)
        self.assertNotIn("RETURNING", sql)

    def test_delete_jamais_touche(self):
        sql = ds._translate_sql_for_postgres("DELETE FROM users WHERE id = ?", self.TABLES)
        self.assertNotIn("RETURNING", sql)


class TestTranslateSchemaForPostgres(unittest.TestCase):
    def test_autoincrement_traduit_en_serial(self):
        translated = ds._translate_schema_for_postgres("id INTEGER PRIMARY KEY AUTOINCREMENT,")
        self.assertIn("SERIAL PRIMARY KEY", translated)
        self.assertNotIn("AUTOINCREMENT", translated.upper())

    def test_toutes_les_occurrences_traduites(self):
        schema = "\n".join([f"CREATE TABLE t{i} (id INTEGER PRIMARY KEY AUTOINCREMENT);" for i in range(5)])
        translated = ds._translate_schema_for_postgres(schema)
        self.assertEqual(translated.count("SERIAL PRIMARY KEY"), 5)

    def test_texte_sans_autoincrement_inchange(self):
        schema = "CREATE TABLE t (token TEXT PRIMARY KEY, user_id INTEGER NOT NULL);"
        self.assertEqual(ds._translate_schema_for_postgres(schema), schema)

    def test_schema_reel_du_projet(self):
        translated = ds._translate_schema_for_postgres(db.SCHEMA)
        self.assertNotIn("AUTOINCREMENT", translated.upper())
        # SEC-04 a ajouté consent_records (id INTEGER PRIMARY KEY AUTOINCREMENT) :
        # 9 tables historiques + 1 nouvelle = 10 (voir TestAutoincrementTables
        # ci-dessous pour la liste complète).
        self.assertEqual(translated.count("SERIAL PRIMARY KEY"), 10)

    def test_insensible_a_la_casse(self):
        translated = ds._translate_schema_for_postgres("id integer primary key autoincrement,")
        self.assertIn("SERIAL PRIMARY KEY", translated)


class TestSplitStatements(unittest.TestCase):
    def test_deux_instructions(self):
        stmts = ds._split_statements("CREATE TABLE a (id INT); CREATE TABLE b (id INT);")
        self.assertEqual(len(stmts), 2)

    def test_ignore_les_fragments_vides(self):
        stmts = ds._split_statements("CREATE TABLE a (id INT);;;  ;")
        self.assertEqual(len(stmts), 1)

    def test_chaine_vide(self):
        self.assertEqual(ds._split_statements(""), [])

    def test_une_seule_instruction_sans_point_virgule_final(self):
        stmts = ds._split_statements("CREATE TABLE a (id INT)")
        self.assertEqual(len(stmts), 1)

    def test_schema_reel_du_projet_se_decoupe(self):
        translated = ds._translate_schema_for_postgres(db.SCHEMA)
        stmts = ds._split_statements(translated)
        self.assertGreater(len(stmts), 10)
        for stmt in stmts:
            self.assertTrue(stmt.upper().startswith(("CREATE TABLE", "CREATE INDEX", "CREATE UNIQUE INDEX", "--")) or "CREATE" in stmt.upper())


class TestAutoincrementTables(unittest.TestCase):
    def test_tables_reelles_du_schema(self):
        tables = ds._autoincrement_tables(db.SCHEMA)
        expected = {
            "users", "oauth_accounts", "login_attempts", "security_events", "conversations",
            "chatbot_messages", "user_daily_usage", "rate_limit_events", "two_factor_recovery_codes",
            # SEC-04 : preuve RGPD immuable (voir consent_service.py/db.py::SCHEMA).
            "consent_records",
        }
        self.assertEqual(tables, expected)

    def test_tables_sans_id_absentes(self):
        tables = ds._autoincrement_tables(db.SCHEMA)
        for table in ("sessions", "password_resets", "chatbot_quota", "stripe_webhook_events", "two_factor_challenges"):
            self.assertNotIn(table, tables)

    def test_resultat_mis_en_cache(self):
        ds._autoincrement_tables_cache.clear()
        first = ds._autoincrement_tables(db.SCHEMA)
        self.assertIn(db.SCHEMA, ds._autoincrement_tables_cache)
        second = ds._autoincrement_tables(db.SCHEMA)
        self.assertEqual(first, second)

    def test_schema_synthetique(self):
        schema = "CREATE TABLE IF NOT EXISTS foo (\n    id INTEGER PRIMARY KEY AUTOINCREMENT,\n    x TEXT\n);"
        self.assertEqual(ds._autoincrement_tables(schema), frozenset({"foo"}))

    def test_schema_sans_autoincrement(self):
        schema = "CREATE TABLE IF NOT EXISTS foo (token TEXT PRIMARY KEY);"
        self.assertEqual(ds._autoincrement_tables(schema), frozenset())


# ── Wrapper PostgreSQL (objets psycopg simulés — aucun serveur requis) ──────
class _FakeCursor:
    def __init__(self, rows=None, rowcount=0, description=None):
        self._rows = rows if rows is not None else []
        self.rowcount = rowcount
        self.description = description if description is not None else ([("id",)] if rows else None)
        self.executed = []
        self.many = None

    def execute(self, sql, params=None):
        self.executed.append((sql, params))
        return self

    def fetchall(self):
        return self._rows

    def executemany(self, sql, seq):
        self.many = (sql, list(seq))

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class TestPostgresCursor(unittest.TestCase):
    def test_lastrowid_present(self):
        cur = ds._PostgresCursor(_FakeCursor(rows=[{"id": 7}], rowcount=1))
        self.assertEqual(cur.lastrowid, 7)

    def test_lastrowid_absent_sans_lignes(self):
        cur = ds._PostgresCursor(_FakeCursor(rows=[], rowcount=0, description=None))
        self.assertIsNone(cur.lastrowid)

    def test_lastrowid_absent_si_pas_de_colonne_id(self):
        cur = ds._PostgresCursor(_FakeCursor(rows=[{"count": 3}], rowcount=1, description=[("count",)]))
        self.assertIsNone(cur.lastrowid)

    def test_fetchone_sequentiel(self):
        cur = ds._PostgresCursor(_FakeCursor(rows=[{"id": 1}, {"id": 2}], rowcount=2, description=[("id",)]))
        self.assertEqual(cur.fetchone(), {"id": 1})
        self.assertEqual(cur.fetchone(), {"id": 2})
        self.assertIsNone(cur.fetchone())

    def test_fetchall(self):
        cur = ds._PostgresCursor(_FakeCursor(rows=[{"id": 1}, {"id": 2}], rowcount=2, description=[("id",)]))
        self.assertEqual(cur.fetchall(), [{"id": 1}, {"id": 2}])

    def test_fetchall_apres_fetchone_partiel(self):
        cur = ds._PostgresCursor(_FakeCursor(rows=[{"id": 1}, {"id": 2}, {"id": 3}], rowcount=3, description=[("id",)]))
        cur.fetchone()
        self.assertEqual(cur.fetchall(), [{"id": 2}, {"id": 3}])

    def test_fetchall_sans_resultat(self):
        cur = ds._PostgresCursor(_FakeCursor(rows=[], rowcount=0, description=None))
        self.assertEqual(cur.fetchall(), [])

    def test_rowcount_delete(self):
        cur = ds._PostgresCursor(_FakeCursor(rows=[], rowcount=3, description=None))
        self.assertEqual(cur.rowcount, 3)

    def test_rowcount_update(self):
        cur = ds._PostgresCursor(_FakeCursor(rows=[], rowcount=1, description=None))
        self.assertEqual(cur.rowcount, 1)

    def test_pas_de_resultat_pour_update_sans_returning(self):
        cur = ds._PostgresCursor(_FakeCursor(rows=[], rowcount=1, description=None))
        self.assertIsNone(cur.fetchone())


class TestPostgresConnectionMocked(unittest.TestCase):
    def _wrapper(self, cursor_rows=None, rowcount=0, description=None):
        raw_conn = MagicMock()
        raw_conn.cursor.return_value = _FakeCursor(rows=cursor_rows, rowcount=rowcount, description=description)
        pool = MagicMock()
        return ds._PostgresConnection(raw_conn, pool, autoincrement_tables={"users"}), raw_conn, pool

    def test_execute_traduit_les_placeholders(self):
        wrapper, raw_conn, _ = self._wrapper()
        wrapper.execute("SELECT * FROM users WHERE id = ?", (1,))
        sql_used = raw_conn.cursor.return_value.executed[0][0]
        self.assertIn("%s", sql_used)

    def test_execute_renvoie_un_postgres_cursor(self):
        wrapper, _, _ = self._wrapper(cursor_rows=[{"id": 5}], rowcount=1)
        cur = wrapper.execute("INSERT INTO users (email) VALUES (?)", ("a@b.com",))
        self.assertIsInstance(cur, ds._PostgresCursor)
        self.assertEqual(cur.lastrowid, 5)

    def test_execute_params_par_defaut_vide(self):
        wrapper, raw_conn, _ = self._wrapper()
        wrapper.execute("SELECT 1")
        self.assertEqual(raw_conn.cursor.return_value.executed[0][1], ())

    def test_executemany_traduit_et_delegue(self):
        wrapper, raw_conn, _ = self._wrapper()
        wrapper.executemany("INSERT INTO t (a) VALUES (?)", [(1,), (2,)])
        sql, seq = raw_conn.cursor.return_value.many
        self.assertIn("%s", sql)
        self.assertEqual(seq, [(1,), (2,)])

    def test_executescript_decoupe_et_execute_chaque_instruction(self):
        wrapper, raw_conn, _ = self._wrapper()
        wrapper.executescript("CREATE TABLE a (id INTEGER PRIMARY KEY AUTOINCREMENT); CREATE TABLE b (id INT);")
        executed_sqls = [call[0] for call in raw_conn.cursor.return_value.executed]
        self.assertEqual(len(executed_sqls), 2)
        self.assertIn("SERIAL PRIMARY KEY", executed_sqls[0])

    def test_commit_delegue(self):
        wrapper, raw_conn, _ = self._wrapper()
        wrapper.commit()
        raw_conn.commit.assert_called_once()

    def test_rollback_delegue(self):
        wrapper, raw_conn, _ = self._wrapper()
        wrapper.rollback()
        raw_conn.rollback.assert_called_once()

    def test_close_rend_la_connexion_au_pool(self):
        wrapper, raw_conn, pool = self._wrapper()
        raw_conn.info.transaction_status = psycopg.pq.TransactionStatus.IDLE
        wrapper.close()
        pool.putconn.assert_called_once_with(raw_conn)

    def test_close_rollback_si_transaction_ouverte(self):
        wrapper, raw_conn, pool = self._wrapper()
        raw_conn.info.transaction_status = psycopg.pq.TransactionStatus.INTRANS
        wrapper.close()
        raw_conn.rollback.assert_called_once()
        pool.putconn.assert_called_once()

    def test_close_pas_de_rollback_si_idle(self):
        wrapper, raw_conn, pool = self._wrapper()
        raw_conn.info.transaction_status = psycopg.pq.TransactionStatus.IDLE
        wrapper.close()
        raw_conn.rollback.assert_not_called()

    def test_close_rend_la_connexion_meme_si_rollback_echoue(self):
        wrapper, raw_conn, pool = self._wrapper()
        raw_conn.info.transaction_status = psycopg.pq.TransactionStatus.INERROR
        raw_conn.rollback.side_effect = RuntimeError("panne simulée")
        with self.assertRaises(RuntimeError):
            wrapper.close()
        pool.putconn.assert_called_once_with(raw_conn)


# ── Pool PostgreSQL (construction, sans connexion réelle) ───────────────────
class TestPoolConstruction(_EnvIsolatedTestCase):
    def test_pool_leve_erreur_claire_si_psycopg_pool_absent(self):
        os.environ["DATABASE_URL"] = "postgresql://u:p@host/db"
        _reload_config()
        with patch.dict("sys.modules", {"psycopg_pool": None}):
            with self.assertRaises(ds.DatabaseConnectionError):
                ds._get_pool()

    def test_pool_construit_avec_les_bons_parametres(self):
        os.environ["DATABASE_URL"] = "postgresql://u:p@host/db"
        os.environ["DATABASE_POOL_SIZE"] = "3"
        os.environ["DATABASE_MAX_OVERFLOW"] = "7"
        os.environ["DATABASE_POOL_TIMEOUT"] = "12"
        os.environ["DATABASE_POOL_RECYCLE"] = "999"
        _reload_config()
        with patch("psycopg_pool.ConnectionPool") as mock_pool_cls:
            mock_pool_cls.return_value = MagicMock()
            ds._get_pool()
            _, kwargs = mock_pool_cls.call_args
            self.assertEqual(kwargs["min_size"], 3)
            self.assertEqual(kwargs["max_size"], 10)
            self.assertEqual(kwargs["timeout"], 12)
            self.assertEqual(kwargs["max_lifetime"], 999)

    def test_pool_est_un_singleton_pour_la_meme_url(self):
        os.environ["DATABASE_URL"] = "postgresql://u:p@host/db"
        _reload_config()
        with patch("psycopg_pool.ConnectionPool") as mock_pool_cls:
            mock_pool_cls.return_value = MagicMock()
            first = ds._get_pool()
            second = ds._get_pool()
            self.assertIs(first, second)
            mock_pool_cls.assert_called_once()

    def test_pool_recree_si_lurl_change(self):
        os.environ["DATABASE_URL"] = "postgresql://u:p@host1/db"
        _reload_config()
        with patch("psycopg_pool.ConnectionPool") as mock_pool_cls:
            mock_pool_cls.side_effect = lambda *a, **k: MagicMock()
            ds._get_pool()
            os.environ["DATABASE_URL"] = "postgresql://u:p@host2/db"
            _reload_config()
            ds._get_pool()
            self.assertEqual(mock_pool_cls.call_count, 2)

    def test_reset_pool_ferme_et_oublie(self):
        os.environ["DATABASE_URL"] = "postgresql://u:p@host/db"
        _reload_config()
        with patch("psycopg_pool.ConnectionPool") as mock_pool_cls:
            fake_pool = MagicMock()
            mock_pool_cls.return_value = fake_pool
            ds._get_pool()
            ds.reset_pool()
            fake_pool.close.assert_called_once()
            self.assertIsNone(ds._pool)

    def test_get_connection_leve_databaseconnectionerror_si_getconn_echoue(self):
        os.environ["DATABASE_URL"] = "postgresql://u:p@host/db"
        _reload_config()
        with patch("psycopg_pool.ConnectionPool") as mock_pool_cls:
            fake_pool = MagicMock()
            fake_pool.getconn.side_effect = RuntimeError("serveur injoignable")
            mock_pool_cls.return_value = fake_pool
            with self.assertRaises(ds.DatabaseConnectionError):
                ds.get_connection(sqlite_path="unused", sqlite_data_dir="unused")

    def test_get_connection_utilise_lurl_explicite_pas_config_database_url(self):
        """Régression : un `database_url` explicite passé à get_connection()
        doit piloter la CONNEXION RÉELLE au pool (pas seulement la
        détection du moteur) — sinon une connexion pourrait être ouverte
        vers `config.DATABASE_URL` au lieu de l'URL réellement demandée par
        l'appelant."""
        # config.DATABASE_URL délibérément différente de l'URL explicite,
        # pour prouver laquelle des deux est effectivement utilisée.
        os.environ["DATABASE_URL"] = "postgresql://u:p@config-host/db"
        _reload_config()
        with patch("psycopg_pool.ConnectionPool") as mock_pool_cls:
            mock_pool_cls.return_value = MagicMock()
            ds.get_connection(
                sqlite_path="unused", sqlite_data_dir="unused",
                database_url="postgresql://u:p@explicit-host/db",
            )
            _, kwargs = mock_pool_cls.call_args
            self.assertEqual(kwargs["conninfo"], "postgresql://u:p@explicit-host/db")


# ── Routage get_connection() ─────────────────────────────────────────────
class TestGetConnectionRouting(unittest.TestCase):
    def setUp(self):
        self._saved = {name: os.environ.get(name) for name in ENV_VARS}
        for name in ENV_VARS:
            os.environ.pop(name, None)
        _reload_config()
        ds.reset_pool()

        self._tmp_dir = tempfile.mkdtemp()
        self._data_dir_backup = db.DATA_DIR
        self._db_path_backup = db.DB_PATH
        db.DATA_DIR = Path(self._tmp_dir)
        db.DB_PATH = db.DATA_DIR / "novamath.db"

    def tearDown(self):
        db.DATA_DIR = self._data_dir_backup
        db.DB_PATH = self._db_path_backup
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

        for name, value in self._saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        _reload_config()
        ds.reset_pool()

    def test_sans_database_url_renvoie_une_connexion_sqlite_brute(self):
        conn = ds.get_connection(sqlite_path=db.DB_PATH, sqlite_data_dir=db.DATA_DIR)
        try:
            self.assertIsInstance(conn, __import__("sqlite3").Connection)
        finally:
            conn.close()

    def test_database_url_postgres_route_vers_le_pool(self):
        os.environ["DATABASE_URL"] = "postgresql://u:p@host/db"
        _reload_config()
        with patch("psycopg_pool.ConnectionPool") as mock_pool_cls:
            fake_pool = MagicMock()
            fake_pool.getconn.return_value = MagicMock()
            mock_pool_cls.return_value = fake_pool
            conn = ds.get_connection(sqlite_path=db.DB_PATH, sqlite_data_dir=db.DATA_DIR)
            self.assertIsInstance(conn, ds._PostgresConnection)

    def test_sqlite_url_explicite_utilise_le_chemin_de_lurl(self):
        tmp = tempfile.mkdtemp()
        try:
            target = str(Path(tmp) / "custom.db")
            conn = ds.get_connection(
                sqlite_path=db.DB_PATH, sqlite_data_dir=db.DATA_DIR, database_url=f"sqlite:///{target}",
            )
            conn.close()
            self.assertTrue(Path(target).exists())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_url_invalide_leve_value_error(self):
        with self.assertRaises(ValueError):
            ds.get_connection(sqlite_path=db.DB_PATH, sqlite_data_dir=db.DATA_DIR, database_url="mysql://x")


# ── Configuration (config.py) ───────────────────────────────────────────────
class TestConfigDefaults(_EnvIsolatedTestCase):
    def test_database_url_absente_par_defaut(self):
        self.assertIsNone(config.DATABASE_URL)

    def test_database_url_lue_depuis_lenvironnement(self):
        os.environ["DATABASE_URL"] = "postgresql://u:p@host/db"
        _reload_config()
        self.assertEqual(config.DATABASE_URL, "postgresql://u:p@host/db")

    def test_pool_size_defaut(self):
        self.assertEqual(config.DATABASE_POOL_SIZE, 5)

    def test_max_overflow_defaut(self):
        self.assertEqual(config.DATABASE_MAX_OVERFLOW, 10)

    def test_pool_timeout_defaut(self):
        self.assertEqual(config.DATABASE_POOL_TIMEOUT, 30)

    def test_pool_recycle_defaut(self):
        self.assertEqual(config.DATABASE_POOL_RECYCLE, 3600)

    def test_pool_size_surcharge(self):
        os.environ["DATABASE_POOL_SIZE"] = "20"
        _reload_config()
        self.assertEqual(config.DATABASE_POOL_SIZE, 20)

    def test_max_overflow_surcharge(self):
        os.environ["DATABASE_MAX_OVERFLOW"] = "1"
        _reload_config()
        self.assertEqual(config.DATABASE_MAX_OVERFLOW, 1)

    def test_pool_timeout_surcharge(self):
        os.environ["DATABASE_POOL_TIMEOUT"] = "5"
        _reload_config()
        self.assertEqual(config.DATABASE_POOL_TIMEOUT, 5)

    def test_pool_recycle_surcharge(self):
        os.environ["DATABASE_POOL_RECYCLE"] = "60"
        _reload_config()
        self.assertEqual(config.DATABASE_POOL_RECYCLE, 60)


# ── Non-régression complète de db.py sur SQLite (mode par défaut) ──────────
class TestDbPyRegressionSQLite(_SqliteIsolatedTestCase):
    def test_init_db_est_idempotent(self):
        db.init_db()
        db.init_db()
        db.init_db()

    def test_get_connection_renvoie_toujours_une_connexion_sqlite(self):
        conn = db.get_connection()
        try:
            import sqlite3
            self.assertIsInstance(conn, sqlite3.Connection)
        finally:
            conn.close()

    def test_create_user_et_lastrowid(self):
        db.init_db()
        uid = db.create_user("a@example.com", "userA", "Pseudo A", "hash")
        self.assertIsInstance(uid, int)
        self.assertGreater(uid, 0)

    def test_create_guest_user_et_lastrowid(self):
        db.init_db()
        uid = db.create_guest_user("guestkey123")
        self.assertIsInstance(uid, int)

    def test_create_conversation_et_lastrowid(self):
        db.init_db()
        uid = db.create_user("b@example.com", "userB", "Pseudo B", "hash")
        conv_id = db.create_conversation(uid, "Titre")
        self.assertIsInstance(conv_id, int)

    def test_add_message_et_lastrowid(self):
        db.init_db()
        uid = db.create_user("c@example.com", "userC", "Pseudo C", "hash")
        conv_id = db.create_conversation(uid)
        msg_id = db.add_message(conv_id, "user", "Salut")
        self.assertIsInstance(msg_id, int)

    def test_get_user_by_id_apres_creation(self):
        db.init_db()
        uid = db.create_user("d@example.com", "userD", "Pseudo D", "hash")
        user = db.get_user_by_id(uid)
        self.assertEqual(user["email"], "d@example.com")
        self.assertEqual(user["plan"], "free")
        self.assertEqual(user["role"], "user")

    def test_toutes_les_colonnes_de_migration_presentes(self):
        db.init_db()
        uid = db.create_user("e@example.com", "userE", "Pseudo E", "hash")
        user = db.get_user_by_id(uid)
        for column in (
            "guest_last_seen_at", "guest_dashboard_viewed", "stripe_customer_id", "stripe_subscription_id",
            "plan", "stripe_subscription_status", "role", "two_factor_enabled", "two_factor_secret",
            "two_factor_enabled_at", "two_factor_last_counter",
        ):
            self.assertIn(column, user)

    def test_upsert_increment_chatbot_quota(self):
        db.init_db()
        uid = db.create_user("f@example.com", "userF", "Pseudo F", "hash")
        first = db.increment_chatbot_quota(uid, "2026-01-01")
        second = db.increment_chatbot_quota(uid, "2026-01-01")
        self.assertEqual(first, 1)
        self.assertEqual(second, 2)

    def test_upsert_increment_daily_usage(self):
        db.init_db()
        uid = db.create_user("g@example.com", "userG", "Pseudo G", "hash")
        first = db.increment_daily_usage(uid, "PDF_ANALYSIS", "2026-01-01", amount=3)
        second = db.increment_daily_usage(uid, "PDF_ANALYSIS", "2026-01-01", amount=2)
        self.assertEqual(first, 3)
        self.assertEqual(second, 5)

    def test_upsert_record_rate_limit_event(self):
        db.init_db()
        first = db.record_rate_limit_event("ip:1.2.3.4", "/api/x", 1000)
        second = db.record_rate_limit_event("ip:1.2.3.4", "/api/x", 1000)
        self.assertEqual(first, 1)
        self.assertEqual(second, 2)

    def test_insert_or_ignore_mark_stripe_event_processed(self):
        db.init_db()
        self.assertFalse(db.has_processed_stripe_event("evt_1"))
        first = db.mark_stripe_event_processed("evt_1", "checkout.session.completed")
        second = db.mark_stripe_event_processed("evt_1", "checkout.session.completed")  # ne doit jamais lever
        self.assertTrue(first)
        self.assertFalse(second)
        self.assertTrue(db.has_processed_stripe_event("evt_1"))

    def test_unmark_stripe_event_processed_permet_une_nouvelle_reservation(self):
        db.init_db()
        db.mark_stripe_event_processed("evt_2", "checkout.session.completed")
        self.assertTrue(db.has_processed_stripe_event("evt_2"))
        db.unmark_stripe_event_processed("evt_2")
        self.assertFalse(db.has_processed_stripe_event("evt_2"))
        self.assertTrue(db.mark_stripe_event_processed("evt_2", "checkout.session.completed"))

    def test_reclaim_refuse_si_reservation_encore_fraiche(self):
        """Une réservation encore dans la fenêtre STRIPE_WEBHOOK_CLAIM_TIMEOUT_
        SECONDS (traitement réellement en cours, pas de kill) reste bloquée —
        le nouveau mécanisme de reprise sur kill ne doit jamais permettre une
        double exécution d'un handler encore réellement en cours."""
        db.init_db()
        self.assertTrue(db.mark_stripe_event_processed("evt_fresh", "checkout.session.completed"))
        self.assertFalse(db.mark_stripe_event_processed("evt_fresh", "checkout.session.completed"))

    def test_reclaim_autorise_apres_expiration_si_jamais_complete(self):
        """Simule un process tué en plein traitement (SIGKILL, restart
        Fly.io) : la réservation existe, n'a jamais été marquée complétée, et
        date de plus de STRIPE_WEBHOOK_CLAIM_TIMEOUT_SECONDS -> un nouveau
        traitement doit être autorisé, sinon l'event resterait bloqué en
        doublon fantôme pour toujours sans que sa logique métier (ex:
        activation d'un abonnement) n'ait jamais réellement été exécutée."""
        db.init_db()
        self.assertTrue(db.mark_stripe_event_processed("evt_stale", "checkout.session.completed"))
        stale_ts = (
            datetime.now(timezone.utc) - timedelta(seconds=config.STRIPE_WEBHOOK_CLAIM_TIMEOUT_SECONDS + 60)
        ).isoformat()
        conn = db.get_connection()
        try:
            conn.execute(
                "UPDATE stripe_webhook_events SET processed_at = ? WHERE event_id = ?", (stale_ts, "evt_stale"),
            )
            conn.commit()
        finally:
            conn.close()

        self.assertTrue(db.mark_stripe_event_processed("evt_stale", "checkout.session.completed"))

    def test_reclaim_toujours_refuse_si_deja_complete_meme_tres_ancien(self):
        """Un event RÉELLEMENT traité avec succès (completed_at renseigné) ne
        doit JAMAIS être ré-exécuté, même très longtemps après — la garantie
        d'idempotence historique doit rester intacte malgré le nouveau
        mécanisme de reprise sur kill (qui ne concerne QUE les réservations
        jamais complétées)."""
        db.init_db()
        db.mark_stripe_event_processed("evt_done", "checkout.session.completed")
        db.mark_stripe_event_completed("evt_done")

        very_old_ts = (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()
        conn = db.get_connection()
        try:
            conn.execute(
                "UPDATE stripe_webhook_events SET processed_at = ? WHERE event_id = ?", (very_old_ts, "evt_done"),
            )
            conn.commit()
        finally:
            conn.close()

        self.assertFalse(db.mark_stripe_event_processed("evt_done", "checkout.session.completed"))

    def test_insert_or_ignore_link_oauth_account(self):
        db.init_db()
        uid = db.create_user("h@example.com", "userH", "Pseudo H", "hash")
        db.link_oauth_account(uid, "google", "google-sub-1")
        db.link_oauth_account(uid, "google", "google-sub-1")  # ne doit jamais lever
        found = db.get_user_by_oauth("google", "google-sub-1")
        self.assertEqual(found["id"], uid)

    def test_executemany_replace_recovery_codes(self):
        db.init_db()
        uid = db.create_user("i@example.com", "userI", "Pseudo I", "hash")
        db.replace_recovery_codes(uid, ["hash1", "hash2", "hash3"])
        codes = db.get_recovery_codes(uid)
        self.assertEqual(len(codes), 3)

    def test_executemany_cleanup_expired_guests(self):
        db.init_db()
        guest_id = db.create_guest_user("expiredguest")
        db.touch_guest_activity(guest_id)
        ids = db.cleanup_expired_guests(max_idle_hours=0)
        # Purge immédiate (idle_hours=0) : le compte invité vient d'être créé,
        # donc potentiellement déjà "expiré" selon la granularité de l'horloge —
        # l'appel ne doit dans tous les cas jamais lever d'exception.
        self.assertIsInstance(ids, list)

    def test_delete_conditionnel_consume_recovery_code(self):
        db.init_db()
        uid = db.create_user("j@example.com", "userJ", "Pseudo J", "hash")
        db.replace_recovery_codes(uid, ["hashX"])
        self.assertTrue(db.consume_recovery_code(uid, "hashX"))
        self.assertFalse(db.consume_recovery_code(uid, "hashX"))

    def test_register_schema_appelle_bien_le_schema_de_db(self):
        self.assertEqual(ds._schema_for_autoincrement(), db.SCHEMA)

    def test_reexecution_migration_colonnes_sans_erreur(self):
        db.init_db()
        conn = db.get_connection()
        try:
            db._migrate_guest_lifecycle_columns(conn)
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
