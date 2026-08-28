"""
Couche d'abstraction base de données — ARCH-02.

Unique point d'entrée pour :
- l'ouverture des connexions (SQLite fichier local, ou PostgreSQL via un pool
  de connexions) ;
- la détection automatique du moteur à partir de `config.DATABASE_URL` ;
- la gestion des transactions (commit/rollback), y compris le rollback
  automatique d'une connexion PostgreSQL rendue au pool en état transactionnel
  incomplet ;
- les quelques différences de syntaxe SQL entre moteurs (placeholders,
  schéma, `INSERT OR IGNORE`, identifiant auto-incrémenté).

Architecture stricte, identique au reste des services :

    webapp/db.py  →  database_service.py  →  config.py

jamais l'inverse : ce module n'importe JAMAIS db.py (webapp/db.py lui délègue
`get_connection()`/l'application du schéma/les migrations de colonnes, en lui
passant ses propres `DATA_DIR`/`DB_PATH` — évite toute dépendance circulaire
et préserve à l'identique le monkeypatch de `db.DATA_DIR`/`db.DB_PATH` déjà
utilisé par la suite de tests existante).

Aucun autre service (plan_service, quota_service, billing_service,
role_service, rate_limit_service, two_factor_service, logging_service,
metrics_service, backup_service, health_service, ...) n'importe ce module ni
n'a conscience du moteur réellement utilisé : ils continuent d'appeler
`db.py` exactement comme avant, sur des connexions dont l'interface
(`execute`/`executemany`/`executescript`/`commit`/`rollback`/`close`, lignes
accessibles par nom de colonne) est strictement identique quel que soit le
moteur — c'est précisément ce que ce module garantit.

SQLite (par défaut, `DATABASE_URL` absente) : comportement STRICTEMENT
inchangé — une connexion `sqlite3.Connection` brute est renvoyée telle
quelle, jamais enveloppée, pour un risque de régression nul.

PostgreSQL (`DATABASE_URL` commençant par `postgres://`/`postgresql://`) :
`psycopg` (v3) + `psycopg_pool.ConnectionPool` — connexion ouverte via
`pool.getconn()`, rendue via `pool.putconn()` sur `.close()` (jamais
réellement fermée : réutilisée, exactement le même pattern "une connexion
par appel" que SQLite dans `db.py`, juste effectivement mise en pool en
dessous). `psycopg`/`psycopg_pool` restent des dépendances optionnelles :
absentes, tout fonctionne normalement tant que `DATABASE_URL` n'est jamais
positionnée (même philosophie que Stripe/Sentry/2FA ailleurs dans ce
projet) — l'import n'est tenté qu'au moment où une connexion PostgreSQL est
réellement demandée.
"""
import logging
import re
import sqlite3
import threading
from pathlib import Path
from urllib.parse import urlparse

import config

logger = logging.getLogger("database_service")

ENGINE_SQLITE = "sqlite"
ENGINE_POSTGRESQL = "postgresql"


class DatabaseConnectionError(Exception):
    """Levée quand une connexion PostgreSQL ne peut pas être obtenue (serveur
    injoignable, pool épuisé au-delà de DATABASE_POOL_TIMEOUT, identifiants
    invalides...) — jamais une sqlite3.OperationalError brute qui fuiterait
    un détail d'implémentation vers les appelants de db.py."""


# ── Détection du moteur ──────────────────────────────────────────────────
def detect_engine(database_url=None):
    """`database_url=None` (défaut) : lit `config.DATABASE_URL` à l'appel,
    jamais mise en cache — un test qui la modifie (monkeypatch) obtient
    immédiatement le moteur correspondant, sans redémarrage ni rechargement
    de module (même convention que security_headers_service.py)."""
    url = database_url if database_url is not None else config.DATABASE_URL
    if not url:
        return ENGINE_SQLITE
    scheme = urlparse(url).scheme.lower()
    if scheme.startswith("postgres"):
        return ENGINE_POSTGRESQL
    if scheme.startswith("sqlite"):
        return ENGINE_SQLITE
    raise ValueError(
        f"DATABASE_URL non supportée : schéma '{scheme}' — attendu postgres(ql):// "
        "pour PostgreSQL, sqlite:// ou absente pour SQLite (fichier local)."
    )


def engine_of(conn):
    """Moteur réel derrière une connexion déjà ouverte — utilisé par
    db.py::init_db()/les migrations pour choisir la bonne syntaxe DDL sans
    jamais avoir à connaître `config.DATABASE_URL` elles-mêmes."""
    return ENGINE_SQLITE if isinstance(conn, sqlite3.Connection) else ENGINE_POSTGRESQL


# ── SQLite ─────────────────────────────────────────────────────────────────
def _sqlite_connection(sqlite_path, sqlite_data_dir):
    sqlite_data_dir = Path(sqlite_data_dir)
    sqlite_data_dir.mkdir(parents=True, exist_ok=True)
    # timeout=30 (défaut sqlite3 : 5s) : sous gunicorn (plusieurs
    # workers/threads, chacun avec sa propre connexion, voir audit
    # production), un writer bloque les autres le temps de sa transaction —
    # 5s s'épuise vite dès plusieurs élèves actifs simultanément et remonte
    # en sqlite3.OperationalError("database is locked") non rattrapée. 30s
    # absorbe les pics résiduels sans faire échouer la requête pour autant.
    conn = sqlite3.connect(str(sqlite_path), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    # WAL : autorise des lecteurs concurrents pendant qu'un writer écrit (le
    # rollback-journal par défaut bloque TOUT le monde pendant une écriture).
    # Sans effet sur une base ":memory:" (SQLite l'ignore silencieusement,
    # reste en mode "memory") — donc sûr aussi pour les tests qui utilisent
    # une base en mémoire.
    conn.execute("PRAGMA journal_mode = WAL")
    # NORMAL (au lieu de FULL, le défaut) : en WAL, NORMAL garantit déjà la
    # durabilité au niveau du fichier WAL à chaque commit — seul un crash de
    # l'OS lui-même (pas juste un crash du process) entre deux checkpoints
    # pourrait perdre les tout derniers commits, un risque jugé acceptable
    # ici en échange d'écritures nettement moins bloquantes ; c'est le réglage
    # officiellement recommandé par SQLite pour WAL.
    conn.execute("PRAGMA synchronous = NORMAL")
    # busy_timeout (millisecondes) : filet de sécurité redondant avec
    # timeout= ci-dessus (le paramètre Python définit déjà ce PRAGMA), fixé
    # explicitement pour ne jamais dépendre du défaut de la lib si une
    # connexion venait à être ouverte autrement.
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


def _sqlite_path_from_url(database_url):
    """`sqlite:///chemin/vers/fichier.db` (ou `sqlite:///:memory:`) — support
    minimal pour la cohérence de détection via DATABASE_URL ; le fichier par
    défaut (`db.DB_PATH`) reste le chemin réellement utilisé en pratique tant
    que cette variable n'est pas positionnée."""
    parsed = urlparse(database_url)
    path = parsed.path or ""
    if path.startswith("/") and path != "/:memory:":
        path = path[1:] if not path.startswith("//") else path[1:]
    return ":memory:" if path in ("", ":memory:") else path


# ── PostgreSQL ─────────────────────────────────────────────────────────────
_pool = None
_pool_url = None  # DSN pour lequel _pool a été créé — recréé si elle change
_pool_lock = threading.Lock()


def _get_pool(database_url=None):
    """Pool singleton, recréé automatiquement si l'URL effective change
    (utile en tests : chaque test peut pointer vers une base PostgreSQL
    différente sans redémarrage du process). `database_url=None` (usage
    normal) : lit `config.DATABASE_URL` — un appelant peut forcer une autre
    URL explicitement (voir get_connection())."""
    global _pool, _pool_url
    url = database_url if database_url is not None else config.DATABASE_URL
    with _pool_lock:
        if _pool is not None and _pool_url == url:
            return _pool
        if _pool is not None:
            try:
                _pool.close()
            except Exception:  # pragma: no cover - fermeture best-effort
                logger.warning("Fermeture de l'ancien pool PostgreSQL en échec.", exc_info=True)
        try:
            from psycopg_pool import ConnectionPool
        except ImportError as exc:  # pragma: no cover - dépendance optionnelle absente
            raise DatabaseConnectionError(
                "DATABASE_URL pointe vers PostgreSQL mais psycopg/psycopg_pool ne sont pas "
                "installés — voir requirements.txt (`psycopg[binary,pool]`)."
            ) from exc
        _pool = ConnectionPool(
            conninfo=url,
            min_size=config.DATABASE_POOL_SIZE,
            max_size=config.DATABASE_POOL_SIZE + config.DATABASE_MAX_OVERFLOW,
            timeout=config.DATABASE_POOL_TIMEOUT,
            max_lifetime=config.DATABASE_POOL_RECYCLE,
            open=False,
        )
        _pool.open(wait=False)
        _pool_url = url
        return _pool


def reset_pool():
    """Ferme et oublie le pool courant — jamais appelé en usage normal
    (le pool vit pour la durée du process) ; utilisé par la suite de tests
    pour repartir d'un état propre entre deux configurations PostgreSQL."""
    global _pool, _pool_url
    with _pool_lock:
        if _pool is not None:
            try:
                _pool.close()
            except Exception:  # pragma: no cover
                pass
        _pool = None
        _pool_url = None


# Tables avec `id INTEGER PRIMARY KEY AUTOINCREMENT` dans webapp/db.py::SCHEMA
# — calculé UNE FOIS par introspection du schéma lui-même (jamais une liste
# recopiée à la main, qui pourrait diverger du schéma réel). Seules ces
# tables reçoivent automatiquement `RETURNING id` sur un `INSERT INTO` simple
# côté PostgreSQL (psycopg n'a pas d'équivalent à `cursor.lastrowid`).
_AUTOINCREMENT_RE = re.compile(
    r"CREATE TABLE IF NOT EXISTS (\w+) \(\s*id INTEGER PRIMARY KEY AUTOINCREMENT", re.IGNORECASE,
)
_autoincrement_tables_cache = {}


def _autoincrement_tables(schema_sql):
    cached = _autoincrement_tables_cache.get(schema_sql)
    if cached is None:
        cached = frozenset(_AUTOINCREMENT_RE.findall(schema_sql))
        _autoincrement_tables_cache[schema_sql] = cached
    return cached


_INSERT_INTO_RE = re.compile(r"^\s*INSERT\s+INTO\s+(\w+)", re.IGNORECASE)
_INSERT_OR_IGNORE_RE = re.compile(r"INSERT\s+OR\s+IGNORE\s+INTO", re.IGNORECASE)


def _translate_sql_for_postgres(sql, autoincrement_tables=frozenset()):
    """Traduit une requête écrite dans le dialecte SQLite historique de
    db.py vers une requête équivalente PostgreSQL. Les deux SEULES
    différences syntaxiques réellement rencontrées dans ce projet (voir
    audit complet de webapp/db.py, ARCH-02) :
    - `?` (placeholders positionnels SQLite) -> `%s` (psycopg) ;
    - `INSERT OR IGNORE INTO` (SQLite) -> `INSERT INTO ... ON CONFLICT DO
      NOTHING` (équivalent PostgreSQL, mêmes garanties d'idempotence).
    `INSERT ... ON CONFLICT(...) DO UPDATE SET x = excluded.x` (upsert) est
    déjà une syntaxe standard supportée nativement par SQLite (3.24+) ET
    PostgreSQL (9.5+) — jamais traduite, utilisée telle quelle des deux
    côtés (voir increment_daily_usage/record_rate_limit_event dans db.py)."""
    is_insert_or_ignore = bool(_INSERT_OR_IGNORE_RE.search(sql))
    if is_insert_or_ignore:
        sql = _INSERT_OR_IGNORE_RE.sub("INSERT INTO", sql, count=1)
        sql = sql.rstrip().rstrip(";") + " ON CONFLICT DO NOTHING"
    elif "RETURNING" not in sql.upper() and "ON CONFLICT" not in sql.upper():
        match = _INSERT_INTO_RE.match(sql)
        if match and match.group(1) in autoincrement_tables:
            sql = sql.rstrip().rstrip(";") + " RETURNING id"
    # `%` littéral (ex : LIKE 'two_factor%_failed') doit être doublé AVANT de
    # remplacer `?` par `%s` — psycopg utilise le style de formatage
    # "pyformat" (DB-API 2.0) où `%` est un caractère spécial.
    sql = sql.replace("%", "%%").replace("?", "%s")
    return sql


_AUTOINCREMENT_DDL_RE = re.compile(r"INTEGER PRIMARY KEY AUTOINCREMENT", re.IGNORECASE)


def _translate_schema_for_postgres(schema_sql):
    """Seule différence de DDL entre les deux moteurs dans ce projet : la
    clé primaire auto-incrémentée. Tout le reste du schéma (TEXT, REAL,
    INTEGER, REFERENCES ... ON DELETE CASCADE, UNIQUE, CREATE INDEX/UNIQUE
    INDEX IF NOT EXISTS, clé primaire composite) est déjà une syntaxe SQL
    standard valide sur SQLite ET PostgreSQL, jamais réécrite."""
    return _AUTOINCREMENT_DDL_RE.sub("SERIAL PRIMARY KEY", schema_sql)


def _split_statements(sql_script):
    """Équivalent de `sqlite3.Connection.executescript()` (absent de
    psycopg) : découpe un script en instructions individuelles sur `;` —
    sûr ici car webapp/db.py::SCHEMA ne contient aucun `;` à l'intérieur
    d'un littéral de chaîne ou d'un commentaire (schéma entièrement rédigé
    par ce projet, vérifié)."""
    return [stmt.strip() for stmt in sql_script.split(";") if stmt.strip()]


class _PostgresCursor:
    """Émule le sous-ensemble de l'API sqlite3.Cursor utilisé par
    webapp/db.py (`fetchone`/`fetchall`/`lastrowid`/`rowcount`). Les lignes
    d'un résultat éventuel sont récupérées immédiatement (le volume de
    données de ce projet — mono-instance, pas de streaming nulle part
    ailleurs dans db.py — rend un curseur côté serveur inutile)."""

    def __init__(self, raw_cursor):
        self.rowcount = raw_cursor.rowcount
        self._rows = raw_cursor.fetchall() if raw_cursor.description is not None else None
        self._index = 0

    @property
    def lastrowid(self):
        if self._rows and "id" in self._rows[0]:
            return self._rows[0]["id"]
        return None

    def fetchone(self):
        if not self._rows or self._index >= len(self._rows):
            return None
        row = self._rows[self._index]
        self._index += 1
        return row

    def fetchall(self):
        if not self._rows:
            return []
        remaining = self._rows[self._index:]
        self._index = len(self._rows)
        return remaining


class _PostgresConnection:
    """Émule le sous-ensemble de l'API sqlite3.Connection utilisé par
    webapp/db.py (`execute`/`executemany`/`executescript`/`commit`/
    `rollback`/`close`) — permet à db.py de rester inchangé quel que soit le
    moteur réellement utilisé en dessous."""

    def __init__(self, raw_conn, pool, autoincrement_tables=frozenset()):
        self._conn = raw_conn
        self._pool = pool
        self._autoincrement_tables = autoincrement_tables

    def execute(self, sql, params=()):
        translated = _translate_sql_for_postgres(sql, self._autoincrement_tables)
        cur = self._conn.cursor(row_factory=_dict_row())
        cur.execute(translated, tuple(params))
        return _PostgresCursor(cur)

    def executemany(self, sql, seq_of_params):
        translated = _translate_sql_for_postgres(sql, self._autoincrement_tables)
        with self._conn.cursor() as cur:
            cur.executemany(translated, [tuple(p) for p in seq_of_params])

    def executescript(self, sql_script):
        translated = _translate_schema_for_postgres(sql_script)
        with self._conn.cursor() as cur:
            for statement in _split_statements(translated):
                cur.execute(statement)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        """Ne ferme jamais réellement la connexion réseau : la rend au pool
        (`pool.putconn`), reproduisant le pattern "une connexion par appel"
        déjà utilisé par CHAQUE fonction de db.py (`finally: conn.close()`)
        tout en réutilisant réellement les connexions PostgreSQL sous-jacentes.

        Rollback automatique : si une exception a interrompu un appelant
        entre son `execute()` et son `commit()` (le `finally: conn.close()`
        de db.py s'exécute alors sans commit préalable), la transaction
        PostgreSQL resterait ouverte indéfiniment sur une connexion remise
        au pool — corrompant l'état pour le prochain emprunteur. Vérifié et
        annulé explicitement ici plutôt que de compter sur un comportement
        implicite du pool, pour un rollback garanti et testable."""
        import psycopg

        try:
            if self._conn.info.transaction_status != psycopg.pq.TransactionStatus.IDLE:
                self._conn.rollback()
        finally:
            self._pool.putconn(self._conn)


def _dict_row():
    from psycopg.rows import dict_row
    return dict_row


def _postgres_connection(database_url=None):
    pool = _get_pool(database_url)
    try:
        raw_conn = pool.getconn()
    except Exception as exc:
        raise DatabaseConnectionError(f"Connexion PostgreSQL impossible : {exc}") from exc
    return _PostgresConnection(raw_conn, pool, _autoincrement_tables(_schema_for_autoincrement()))


_schema_provider = None


def _schema_for_autoincrement():
    """`db.py` enregistre son SCHEMA via `register_schema()` au chargement
    du module — évite d'importer db.py depuis ici (dépendance circulaire)
    tout en permettant de dériver dynamiquement les tables auto-incrémentées
    plutôt que de dupliquer leur liste."""
    return _schema_provider() if _schema_provider else ""


def register_schema(schema_provider):
    """Appelée une seule fois par db.py au chargement du module, lui passe
    une fonction renvoyant son SCHEMA — voir _schema_for_autoincrement()."""
    global _schema_provider
    _schema_provider = schema_provider


# ── Point d'entrée public ───────────────────────────────────────────────────
def get_connection(sqlite_path, sqlite_data_dir, database_url=None):
    """Connexion prête à l'emploi, quel que soit le moteur détecté à partir
    de `database_url` (par défaut `config.DATABASE_URL`) : `sqlite3.Connection`
    brute pour SQLite (comportement historique inchangé), connexion tirée
    du pool PostgreSQL sinon. `sqlite_path`/`sqlite_data_dir` sont fournis
    par l'appelant (db.py, via ses propres DATA_DIR/DB_PATH) plutôt que lus
    ici, pour ne jamais importer db.py depuis ce module (voir docstring)."""
    engine = detect_engine(database_url)
    url = database_url if database_url is not None else config.DATABASE_URL
    if engine == ENGINE_SQLITE:
        path = _sqlite_path_from_url(url) if url else sqlite_path
        return _sqlite_connection(path, sqlite_data_dir)
    return _postgres_connection(url)


def init_schema(conn, schema_sql):
    """Applique `schema_sql` (dialecte SQLite, voir db.py::SCHEMA) sur
    `conn` — `conn.executescript()` traduit déjà automatiquement pour
    PostgreSQL (voir _PostgresConnection.executescript), sqlite3.Connection
    l'exécute nativement tel quel : aucune branche par moteur nécessaire ici."""
    conn.executescript(schema_sql)
    conn.commit()


def add_column_if_missing(conn, table, column, coltype):
    """Ajoute `column` à `table` si elle n'existe pas encore — idempotent
    sur les deux moteurs, sans jamais dupliquer le DDL : PostgreSQL (9.6+)
    supporte nativement `ADD COLUMN IF NOT EXISTS` ; SQLite ne le supporte
    pas (vérifié), d'où le repli sur la capture d'exception historique."""
    engine = engine_of(conn)
    if engine == ENGINE_SQLITE:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # colonne déjà présente
    else:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {coltype}")
        conn.commit()
