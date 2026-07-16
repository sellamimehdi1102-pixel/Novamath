"""
Couche base de données pour le système de comptes NovaMath.

SQLite (fichier local, cohérent avec un projet mono-instance sans serveur de
base de données dédié) via le module standard `sqlite3` — aucune dépendance
supplémentaire. Le schéma est créé de façon idempotente (`CREATE TABLE IF NOT
EXISTS`) au démarrage du serveur, donc sûr à ré-exécuter.

Ce module ne contient aucune route Flask : uniquement l'accès aux données.
Les routes et la logique métier (validation, hachage, sessions HTTP) vivent
dans `webapp/auth.py`.
"""
import sqlite3
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "novamath.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    username TEXT UNIQUE NOT NULL,
    pseudo TEXT NOT NULL,
    password_hash TEXT,
    avatar TEXT,
    auth_provider TEXT NOT NULL DEFAULT 'local',
    created_at TEXT NOT NULL,
    last_login_at TEXT,
    xp INTEGER NOT NULL DEFAULT 0,
    level INTEGER NOT NULL DEFAULT 1,
    accuracy REAL NOT NULL DEFAULT 0,
    progression REAL NOT NULL DEFAULT 0,
    total_time_s INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS oauth_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    provider_user_id TEXT NOT NULL,
    UNIQUE(provider, provider_user_id)
);

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS login_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL,
    attempted_at TEXT NOT NULL,
    success INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS password_resets (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    used INTEGER NOT NULL DEFAULT 0
);

-- Journal des événements de sécurité (connexion, déconnexion, changement de mot
-- de passe, création/suppression de compte) — jamais de mot de passe, token,
-- cookie ou clé : uniquement le type d'événement, l'utilisateur concerné et
-- l'adresse IP, pour la traçabilité/détection d'abus.
CREATE TABLE IF NOT EXISTS security_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    user_id INTEGER,
    ip TEXT,
    created_at TEXT NOT NULL
);

-- Chatbot pédagogique NovaMath (module webapp/chatbot/) : une conversation
-- contient plusieurs messages, relation classique 1-N, d'où l'usage de vraies
-- tables SQL (contrairement aux stats/settings/course-progress qui sont un
-- blob JSON par utilisateur) — nécessaire pour l'historique paginé et la
-- recherche parmi les conversations.
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL DEFAULT 'Nouvelle conversation',
    pinned INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chatbot_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    liked INTEGER,
    created_at TEXT NOT NULL
);

-- Quota d'appels IA quotidien par utilisateur (sécurité — limite les abus).
CREATE TABLE IF NOT EXISTS chatbot_quota (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, date)
);
"""


def get_connection():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
        _migrate_guest_lifecycle_columns(conn)
    finally:
        conn.close()


def _migrate_guest_lifecycle_columns(conn):
    """Ajoute les colonnes de suivi du cycle de vie invité à une base déjà
    existante (CREATE TABLE IF NOT EXISTS ne modifie pas un schéma déjà créé).
    Idempotent : ignore l'erreur si la colonne existe déjà."""
    for ddl in (
        "ALTER TABLE users ADD COLUMN guest_last_seen_at TEXT",
        "ALTER TABLE users ADD COLUMN guest_dashboard_viewed INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE sessions ADD COLUMN user_agent TEXT",
    ):
        try:
            conn.execute(ddl)
            conn.commit()
        except sqlite3.OperationalError:
            pass  # colonne déjà présente


def _now():
    return datetime.now(timezone.utc).isoformat()


# ── Utilisateurs ─────────────────────────────────────────────────────────────
def count_users():
    conn = get_connection()
    try:
        return conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
    finally:
        conn.close()


def get_user_by_email(email):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email.lower(),)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_user_by_username(username):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_user_by_id(user_id):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def create_guest_user(guest_key):
    """Compte invité éphémère : réutilise entièrement l'infrastructure existante
    (sessions, stats par utilisateur, page gating) au lieu d'un système parallèle
    — email/username générés (uniques, jamais affichés), sans mot de passe.
    `auth_provider='guest'` permet de le distinguer partout où c'est nécessaire
    (restrictions, badge, nettoyage)."""
    conn = get_connection()
    try:
        email = f"guest_{guest_key}@guest.novamath.local"
        username = f"guest_{guest_key}"
        cur = conn.execute(
            """INSERT INTO users (email, username, pseudo, password_hash, auth_provider, created_at)
               VALUES (?, ?, ?, NULL, 'guest', ?)""",
            (email, username, "Invité", _now()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def cleanup_expired_guests(max_idle_hours=2):
    """Purge les comptes invités inactifs depuis trop longtemps (et, en cascade,
    leurs sessions). Basé sur la dernière activité réelle (`guest_last_seen_at`,
    repli sur `created_at` si jamais touché) plutôt que sur la seule date de
    création : un invité toujours actif ne doit jamais être coupé en cours de
    session. Appelé à chaque nouvelle entrée en mode invité et à chaque requête
    d'un invité déjà expiré (voir auth.py::get_current_user) — pas de tâche
    planifiée disponible dans ce projet, un nettoyage paresseux suffit large-
    ment au volume attendu. Retourne la liste des ids supprimés (pour purger
    aussi leurs fichiers de stats, qui vivent hors de SQLite)."""
    conn = get_connection()
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=max_idle_hours)).isoformat()
        rows = conn.execute(
            """SELECT id FROM users
               WHERE auth_provider = 'guest'
               AND COALESCE(guest_last_seen_at, created_at) < ?""",
            (cutoff,),
        ).fetchall()
        ids = [r["id"] for r in rows]
        if ids:
            conn.executemany("DELETE FROM users WHERE id = ?", [(i,) for i in ids])
            conn.commit()
        return ids
    finally:
        conn.close()


def is_guest_expired(user, max_idle_minutes):
    """Un invité est considéré comme une session terminée (donc à recréer de
    zéro) dès que sa dernière activité connue dépasse ce seuil d'inactivité —
    couvre le cas "quitte le site, revient plusieurs heures plus tard" même si
    le cookie de session (lui-même non persistant, voir _set_session_cookie)
    a survécu parce que le navigateur n'a jamais été réellement fermé."""
    last_seen = user.get("guest_last_seen_at") or user.get("created_at")
    if not last_seen:
        return False
    try:
        last_seen_dt = datetime.fromisoformat(last_seen)
    except ValueError:
        return False
    return datetime.now(timezone.utc) - last_seen_dt > timedelta(minutes=max_idle_minutes)


def touch_guest_activity(user_id):
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE users SET guest_last_seen_at = ? WHERE id = ? AND auth_provider = 'guest'",
            (_now(), user_id),
        )
        conn.commit()
    finally:
        conn.close()


def mark_guest_dashboard_viewed(user_id):
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE users SET guest_dashboard_viewed = 1 WHERE id = ? AND auth_provider = 'guest'",
            (user_id,),
        )
        conn.commit()
    finally:
        conn.close()


def create_user(email, username, pseudo, password_hash, auth_provider="local"):
    conn = get_connection()
    try:
        cur = conn.execute(
            """INSERT INTO users (email, username, pseudo, password_hash, auth_provider, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (email.lower(), username, pseudo, password_hash, auth_provider, _now()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_last_login(user_id):
    conn = get_connection()
    try:
        conn.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (_now(), user_id))
        conn.commit()
    finally:
        conn.close()


def update_profile(user_id, pseudo=None, avatar=None, avatar_explicit=False):
    conn = get_connection()
    try:
        if pseudo is not None:
            conn.execute("UPDATE users SET pseudo = ? WHERE id = ?", (pseudo, user_id))
        if avatar_explicit:
            conn.execute("UPDATE users SET avatar = ? WHERE id = ?", (avatar, user_id))
        conn.commit()
    finally:
        conn.close()


def update_stats_cache(user_id, xp, level, accuracy, progression, total_time_s):
    conn = get_connection()
    try:
        conn.execute(
            """UPDATE users SET xp = ?, level = ?, accuracy = ?, progression = ?, total_time_s = ?
               WHERE id = ?""",
            (xp, level, accuracy, progression, total_time_s, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def set_password_hash(user_id, password_hash):
    conn = get_connection()
    try:
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))
        conn.commit()
    finally:
        conn.close()


# ── Comptes liés (OAuth), prêt pour Google/Microsoft/Apple/GitHub ─────────────
def get_user_by_oauth(provider, provider_user_id):
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT users.* FROM users
               JOIN oauth_accounts ON oauth_accounts.user_id = users.id
               WHERE oauth_accounts.provider = ? AND oauth_accounts.provider_user_id = ?""",
            (provider, provider_user_id),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def link_oauth_account(user_id, provider, provider_user_id):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO oauth_accounts (user_id, provider, provider_user_id) VALUES (?, ?, ?)",
            (user_id, provider, provider_user_id),
        )
        conn.commit()
    finally:
        conn.close()


# ── Sessions HTTP (connexion persistante) ──────────────────────────────────────
def create_session(user_id, days=30, user_agent=None):
    conn = get_connection()
    try:
        token = secrets.token_urlsafe(32)
        expires_at = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
        conn.execute(
            "INSERT INTO sessions (token, user_id, created_at, expires_at, user_agent) VALUES (?, ?, ?, ?, ?)",
            (token, user_id, _now(), expires_at, (user_agent or "")[:300]),
        )
        conn.commit()
        return token
    finally:
        conn.close()


def get_session_user(token):
    if not token:
        return None
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT users.* FROM sessions
               JOIN users ON users.id = sessions.user_id
               WHERE sessions.token = ? AND sessions.expires_at > ?""",
            (token, _now()),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def delete_session(token):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
    finally:
        conn.close()


def list_sessions(user_id):
    """Liste des sessions actives (non expirées) d'un compte — base de la
    section « Appareils connectés » des paramètres de sécurité."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT token, created_at, expires_at, user_agent FROM sessions
               WHERE user_id = ? AND expires_at > ? ORDER BY created_at DESC""",
            (user_id, _now()),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def delete_other_sessions(user_id, keep_token):
    """Déconnecte tous les appareils sauf celui à l'origine de la requête
    (« Déconnecter tous les appareils » dans Confidentialité & Sécurité)."""
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM sessions WHERE user_id = ? AND token != ?",
            (user_id, keep_token),
        )
        conn.commit()
    finally:
        conn.close()


def update_email(user_id, email):
    conn = get_connection()
    try:
        conn.execute("UPDATE users SET email = ? WHERE id = ?", (email, user_id))
        conn.commit()
    finally:
        conn.close()


# ── Anti brute-force ──────────────────────────────────────────────────────────
def record_login_attempt(email, success):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO login_attempts (email, attempted_at, success) VALUES (?, ?, ?)",
            (email.lower(), _now(), int(success)),
        )
        conn.commit()
    finally:
        conn.close()


def count_recent_failed_attempts(email, minutes=15):
    conn = get_connection()
    try:
        since = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()
        row = conn.execute(
            """SELECT COUNT(*) AS n FROM login_attempts
               WHERE email = ? AND success = 0 AND attempted_at > ?""",
            (email.lower(), since),
        ).fetchone()
        return row["n"]
    finally:
        conn.close()


# ── Réinitialisation de mot de passe ───────────────────────────────────────────
def create_password_reset(user_id, hours=1):
    conn = get_connection()
    try:
        token = secrets.token_urlsafe(32)
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()
        conn.execute(
            "INSERT INTO password_resets (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (token, user_id, _now(), expires_at),
        )
        conn.commit()
        return token
    finally:
        conn.close()


def get_password_reset(token):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM password_resets WHERE token = ? AND used = 0 AND expires_at > ?",
            (token, _now()),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def mark_reset_used(token):
    conn = get_connection()
    try:
        conn.execute("UPDATE password_resets SET used = 1 WHERE token = ?", (token,))
        conn.commit()
    finally:
        conn.close()


# ── Journal de sécurité ────────────────────────────────────────────────────────
def log_security_event(event_type, user_id=None, ip=None):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO security_events (event_type, user_id, ip, created_at) VALUES (?, ?, ?, ?)",
            (event_type, user_id, ip, _now()),
        )
        conn.commit()
    finally:
        conn.close()


# ── Suppression de compte ──────────────────────────────────────────────────────
def delete_user(user_id):
    """Supprime le compte ; `sessions`/`oauth_accounts`/`password_resets` sont
    supprimés en cascade par les contraintes FK ON DELETE CASCADE du schéma."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()


def delete_login_attempts(email):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM login_attempts WHERE email = ?", (email.lower(),))
        conn.commit()
    finally:
        conn.close()


# ── Chatbot : conversations ────────────────────────────────────────────────
def create_conversation(user_id, title="Nouvelle conversation"):
    conn = get_connection()
    try:
        now = _now()
        cur = conn.execute(
            "INSERT INTO conversations (user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (user_id, title, now, now),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def list_conversations(user_id, search=None):
    conn = get_connection()
    try:
        if search:
            rows = conn.execute(
                """SELECT * FROM conversations WHERE user_id = ? AND title LIKE ?
                   ORDER BY pinned DESC, updated_at DESC""",
                (user_id, f"%{search}%"),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM conversations WHERE user_id = ? ORDER BY pinned DESC, updated_at DESC",
                (user_id,),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_conversation(conversation_id, user_id):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM conversations WHERE id = ? AND user_id = ?", (conversation_id, user_id)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_conversation(conversation_id, user_id, title=None, pinned=None):
    conn = get_connection()
    try:
        if title is not None:
            conn.execute(
                "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ? AND user_id = ?",
                (title, _now(), conversation_id, user_id),
            )
        if pinned is not None:
            conn.execute(
                "UPDATE conversations SET pinned = ? WHERE id = ? AND user_id = ?",
                (int(pinned), conversation_id, user_id),
            )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM conversations WHERE id = ? AND user_id = ?", (conversation_id, user_id)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def touch_conversation(conversation_id):
    conn = get_connection()
    try:
        conn.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (_now(), conversation_id))
        conn.commit()
    finally:
        conn.close()


def delete_conversation(conversation_id, user_id):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM conversations WHERE id = ? AND user_id = ?", (conversation_id, user_id))
        conn.commit()
    finally:
        conn.close()


# ── Chatbot : messages ──────────────────────────────────────────────────────
def add_message(conversation_id, role, content):
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO chatbot_messages (conversation_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (conversation_id, role, content, _now()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def list_messages(conversation_id, limit=None):
    conn = get_connection()
    try:
        query = "SELECT * FROM chatbot_messages WHERE conversation_id = ? ORDER BY id ASC"
        rows = conn.execute(query, (conversation_id,)).fetchall()
        rows = [dict(r) for r in rows]
        return rows[-limit:] if limit else rows
    finally:
        conn.close()


def get_message(message_id):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM chatbot_messages WHERE id = ?", (message_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def delete_message(message_id):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM chatbot_messages WHERE id = ?", (message_id,))
        conn.commit()
    finally:
        conn.close()


def set_message_feedback(message_id, liked):
    conn = get_connection()
    try:
        conn.execute("UPDATE chatbot_messages SET liked = ? WHERE id = ?", (liked, message_id))
        conn.commit()
    finally:
        conn.close()


# ── Chatbot : quota quotidien ────────────────────────────────────────────────
def increment_chatbot_quota(user_id, day_str):
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO chatbot_quota (user_id, date, count) VALUES (?, ?, 1)
               ON CONFLICT(user_id, date) DO UPDATE SET count = count + 1""",
            (user_id, day_str),
        )
        conn.commit()
        row = conn.execute(
            "SELECT count FROM chatbot_quota WHERE user_id = ? AND date = ?", (user_id, day_str)
        ).fetchone()
        return row["count"]
    finally:
        conn.close()


def get_chatbot_quota(user_id, day_str):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT count FROM chatbot_quota WHERE user_id = ? AND date = ?", (user_id, day_str)
        ).fetchone()
        return row["count"] if row else 0
    finally:
        conn.close()
