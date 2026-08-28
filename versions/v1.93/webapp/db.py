"""
Couche base de données pour le système de comptes NovaMath.

SQLite par défaut (fichier local, DATA_DIR/DB_PATH ci-dessous), PostgreSQL si
`config.DATABASE_URL` est positionnée (ARCH-02) — l'ouverture des connexions,
la détection du moteur et les quelques différences de syntaxe SQL entre les
deux sont ENTIÈREMENT déléguées à `database_service.py` (voir sa docstring) :
toutes les fonctions ci-dessous continuent d'écrire du SQL "dialecte SQLite"
(placeholders `?`, `INSERT OR IGNORE`) exactement comme avant ARCH-02, sans
aucune connaissance du moteur réellement actif. Le schéma est créé de façon
idempotente (`CREATE TABLE IF NOT EXISTS`) au démarrage du serveur, donc sûr
à ré-exécuter, sur les deux moteurs.

Ce module ne contient aucune route Flask : uniquement l'accès aux données.
Les routes et la logique métier (validation, hachage, sessions HTTP) vivent
dans `webapp/auth.py`.
"""
import json
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

import database_service

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

-- count_recent_failed_attempts (anti brute-force, webapp/auth.py::login) et
-- record_login_attempt filtrent/écrivent par email à CHAQUE tentative de
-- connexion, cette table n'étant purgée que par delete_login_attempts (à la
-- suppression du compte concerné) — sans cet index, un table scan complet à
-- chaque login, dont le coût grandit indéfiniment avec l'historique
-- accumulé (y compris les tentatives échouées d'un bot, jamais purgées).
CREATE INDEX IF NOT EXISTS idx_login_attempts_email ON login_attempts(email, attempted_at);

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
    cards TEXT,
    mentions TEXT,
    created_at TEXT NOT NULL
);

-- Quota d'appels IA quotidien par utilisateur (sécurité — limite les abus).
CREATE TABLE IF NOT EXISTS chatbot_quota (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, date)
);

-- Idempotence des webhooks Stripe (webapp/stripe_webhook_service.py) : chaque
-- event.id Stripe n'est traité qu'une seule fois, même si Stripe le renvoie
-- plusieurs fois (retries réseau, redélivraison manuelle depuis le Dashboard).
CREATE TABLE IF NOT EXISTS stripe_webhook_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    processed_at TEXT NOT NULL
);

-- Quotas d'utilisation quotidiens génériques (webapp/quota_service.py) — une
-- ligne par (utilisateur, type de quota, jour). Générique et indépendante de
-- `chatbot_quota` ci-dessus (qui reste utilisée telle quelle par le chatbot
-- existant, non touchée par cette table) : toute future limitation
-- (PDF_ANALYSIS, AI_GENERATIONS, CUSTOM_EXERCISES, EXPORTS, ou un nouveau
-- QuotaType) réutilise cette même table, sans migration supplémentaire.
-- La "réinitialisation quotidienne" n'est pas un job à part : une nouvelle
-- date = une nouvelle ligne, donc `count` recommence naturellement à 0 sans
-- aucune purge ni tâche planifiée (voir quota_service.py).
CREATE TABLE IF NOT EXISTS user_daily_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    quota_type TEXT NOT NULL,
    date TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    UNIQUE(user_id, quota_type, date)
);

-- Rate limiting HTTP par fenêtre glissante (webapp/rate_limit_service.py) —
-- table volontairement distincte de user_daily_usage ci-dessus : ici on
-- limite la FRÉQUENCE des requêtes (protection anti-bots/brute-force/coûts
-- API), pas un volume métier quotidien remis à zéro chaque jour. Une ligne =
-- un "bucket" d'1 seconde (window_start = epoch seconds) pour une (clé
-- d'identité "user:<id>"/"ip:<adresse>", endpoint Flask) donnée ; la fenêtre
-- glissante réelle est recalculée à chaque requête en sommant les buckets
-- encore dans la fenêtre (voir rate_limit_service.check()) — jamais un
-- simple compteur remis à zéro sur une minute calendaire.
CREATE TABLE IF NOT EXISTS rate_limit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    window_start INTEGER NOT NULL,
    count INTEGER NOT NULL DEFAULT 0
);

-- UNIQUE plutôt qu'un simple index : sert à la fois de contrainte (cible de
-- l'UPSERT dans record_rate_limit_event) et d'index couvrant la requête de
-- lecture la plus fréquente (key, endpoint, window_start >= ...), utilisée à
-- chaque requête HTTP décorée par @rate_limit — reste performant même avec
-- plusieurs centaines de milliers d'événements.
CREATE UNIQUE INDEX IF NOT EXISTS idx_rate_limit_events_lookup
    ON rate_limit_events(key, endpoint, window_start);

-- Index dédié à cleanup() (DELETE ... WHERE window_start < ?) : sans lui,
-- purger les fenêtres expirées nécessiterait un scan complet de la table.
CREATE INDEX IF NOT EXISTS idx_rate_limit_events_window_start
    ON rate_limit_events(window_start);

-- Authentification à deux facteurs (webapp/two_factor_service.py, RFC 6238).
-- Défi de connexion en attente de code TOTP/recovery : email+mot de passe déjà
-- validés (voir auth.py::login), mais AUCUNE session n'est créée tant que ce
-- défi n'est pas résolu par /api/auth/2fa/verify ou /2fa/recovery — même
-- pattern que password_resets (token à usage unique, expiration courte),
-- table séparée volontairement (sémantique différente : ceci authentifie une
-- connexion en cours, jamais une réinitialisation de mot de passe).
-- `remember` reporte le choix "se souvenir de moi" fait à l'étape mot de passe
-- jusqu'à la création réelle de la session, une fois le second facteur validé.
CREATE TABLE IF NOT EXISTS two_factor_challenges (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    remember INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

-- Recovery codes 2FA : hachés (jamais en clair, même hachage que les mots de
-- passe — voir auth.py::hash_password/verify_password), à usage unique — une
-- ligne par code, supprimée dès qu'il est consommé (voir
-- two_factor_service.py). Relation 1-N avec users, comme oauth_accounts/
-- sessions/conversations ci-dessus.
CREATE TABLE IF NOT EXISTS two_factor_recovery_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    code_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_two_factor_recovery_codes_user
    ON two_factor_recovery_codes(user_id);

-- Consentement parental RGPD (webapp/consent_service.py) — SEC-04. Un compte
-- créé sous le seuil légal (13 ans) reste `account_status='pending_parental_
-- consent'` (voir colonne dans _PRIVACY_COLUMNS) tant qu'aucune ligne ici
-- n'est passée à `status='accepted'` : aucune session n'est créée pour ce
-- compte (voir auth.py::_finish_login), donc aucun accès nulle part sans
-- duplication de vérification route par route. Un seul jeton "pending" à la
-- fois par utilisateur (les précédents sont marqués 'superseded' par
-- consent_service.resend_consent_email avant qu'un nouveau ne soit créé),
-- même philosophie que two_factor_challenges/password_resets (token opaque,
-- expiration courte, jamais réutilisable une fois résolu).
CREATE TABLE IF NOT EXISTS parental_consent_requests (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    parent_email TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    resolved_at TEXT,
    resolved_ip TEXT
);
CREATE INDEX IF NOT EXISTS idx_parental_consent_requests_user
    ON parental_consent_requests(user_id);

-- Preuve RGPD immuable de chaque décision de consentement (parental,
-- conditions d'utilisation, politique de confidentialité, cookies
-- statistiques/marketing) — CNIL exige de pouvoir démontrer QUI a accepté
-- QUOI, QUAND, avec QUELLE version du texte et depuis QUELLE IP. Séparée de
-- security_events (qui reste un journal opérationnel générique) car son
-- contenu ne doit JAMAIS être supprimé, y compris après suppression du
-- compte (pas de ON DELETE CASCADE sur user_id, contrairement à toutes les
-- autres tables ci-dessus — voir privacy_service.delete_account) : un
-- user_id orphelin après suppression est attendu et normal ici, jamais une
-- anomalie à corriger.
CREATE TABLE IF NOT EXISTS consent_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    consent_type TEXT NOT NULL,
    decision TEXT NOT NULL,
    policy_version TEXT,
    ip TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_consent_records_user
    ON consent_records(user_id);

-- Préférences cookies (bandeau RGPD) des comptes connectés — la catégorie
-- "nécessaires" n'est pas stockée (toujours active, ce n'est pas un choix) ;
-- seules statistiques/marketing sont de vrais consentements. Les visiteurs
-- anonymes gardent leur choix uniquement en localStorage (voir
-- cookieConsent.js) : cette table ne sert qu'à rendre ce choix modifiable
-- depuis la page Paramètres une fois connecté, sans inventer un second
-- mécanisme de suivi anonyme.
CREATE TABLE IF NOT EXISTS cookie_consents (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    statistics INTEGER NOT NULL DEFAULT 0,
    marketing INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);
"""


database_service.register_schema(lambda: SCHEMA)


def get_connection():
    return database_service.get_connection(sqlite_path=DB_PATH, sqlite_data_dir=DATA_DIR)


def init_db():
    conn = get_connection()
    try:
        database_service.init_schema(conn, SCHEMA)
        _migrate_guest_lifecycle_columns(conn)
    finally:
        conn.close()


# Colonnes ajoutées à une base déjà existante (CREATE TABLE IF NOT EXISTS ne
# modifie pas un schéma déjà créé) — (table, colonne, définition SQL de la
# colonne). Idempotent sur les deux moteurs via
# database_service.add_column_if_missing() (voir sa docstring : IF NOT
# EXISTS nativement côté PostgreSQL, capture d'exception côté SQLite qui ne
# le supporte pas).
_GUEST_LIFECYCLE_COLUMNS = (
    ("users", "guest_last_seen_at", "TEXT"),
    ("users", "guest_dashboard_viewed", "INTEGER NOT NULL DEFAULT 0"),
    ("sessions", "user_agent", "TEXT"),
    # Cartes d'action (Phase C, "cartes intelligentes") : JSON nullable,
    # absent des bases créées avant cette version.
    ("chatbot_messages", "cards", "TEXT"),
    # Mentions "@" résolues (système de mentions revu) : JSON nullable.
    ("chatbot_messages", "mentions", "TEXT"),
    # Abonnement Stripe (webapp/stripe_service.py) : customer_id est créé dès
    # le premier passage en Checkout, subscription_id/plan ne sont renseignés
    # qu'après confirmation (webhook checkout.session.completed).
    ("users", "stripe_customer_id", "TEXT"),
    ("users", "stripe_subscription_id", "TEXT"),
    ("users", "plan", "TEXT NOT NULL DEFAULT 'free'"),
    # Statut brut de l'abonnement Stripe (active/trialing/past_due/canceled/
    # unpaid/incomplete/incomplete_expired) — distinct de `plan` : un
    # abonnement `past_due` (paiement en échec, en cours de nouvelle
    # tentative par Stripe) garde son `plan` jusqu'à confirmation de
    # l'annulation, mais ce statut permet d'avertir l'utilisateur.
    ("users", "stripe_subscription_status", "TEXT"),
    # Rôle d'équipe (webapp/role_service.py) : gouverne l'accès aux routes
    # internes/admin (ex: /api/dev/dashboard), indépendamment du plan
    # d'abonnement (`plan` ci-dessus). Défaut 'user' appliqué aussi bien
    # aux comptes déjà existants (ALTER TABLE ADD COLUMN ... DEFAULT porte
    # sur les lignes déjà en base) qu'aux nouveaux (INSERT INTO users ne
    # référence pas cette colonne, comme pour `plan`).
    ("users", "role", "TEXT NOT NULL DEFAULT 'user'"),
    # Authentification à deux facteurs (webapp/two_factor_service.py) —
    # SEC-03. two_factor_secret est TOUJOURS chiffré (jamais en clair, voir
    # two_factor_service._encrypt_secret) et reste NULL tant que
    # two_factor_enabled=0 (généré par /2fa/setup, confirmé par /2fa/enable,
    # effacé par /2fa/disable). two_factor_last_counter mémorise le dernier
    # pas TOTP (fenêtre de 30s) accepté avec succès pour CE compte — rejette
    # un code déjà utilisé (rejeu) même s'il reste mathématiquement valide
    # dans sa fenêtre de validité (voir two_factor_service.verify_totp_code).
    ("users", "two_factor_enabled", "INTEGER NOT NULL DEFAULT 0"),
    ("users", "two_factor_secret", "TEXT"),
    ("users", "two_factor_enabled_at", "TEXT"),
    ("users", "two_factor_last_counter", "INTEGER"),
    # Conformité RGPD / protection des mineurs (webapp/consent_service.py,
    # webapp/privacy_service.py) — SEC-04. birth_date sert UNIQUEMENT à
    # calculer l'âge (jamais affiché tel quel, jamais demandé directement
    # "quel âge as-tu") ; account_status gouverne l'accès complet au compte
    # (voir auth.py::_finish_login) — 'active' (comportement historique,
    # défaut appliqué aussi aux comptes déjà existants avant ce chantier),
    # 'pending_parental_consent' (mineur en attente d'accord parental) ou
    # 'parental_consent_refused' (accès définitivement bloqué). Les colonnes
    # *_accepted_version/*_accepted_at journalisent la dernière version des
    # CGU/politique de confidentialité acceptée par CE compte, comparée à
    # consent_service.TERMS_VERSION/PRIVACY_VERSION pour exiger une nouvelle
    # acceptation après publication d'une nouvelle version.
    ("users", "birth_date", "TEXT"),
    ("users", "account_status", "TEXT NOT NULL DEFAULT 'active'"),
    ("users", "terms_accepted_version", "TEXT"),
    ("users", "terms_accepted_at", "TEXT"),
    ("users", "privacy_accepted_version", "TEXT"),
    ("users", "privacy_accepted_at", "TEXT"),
)


def _migrate_guest_lifecycle_columns(conn):
    for table, column, coltype in _GUEST_LIFECYCLE_COLUMNS:
        database_service.add_column_if_missing(conn, table, column, coltype)
    # stripe_customer_id n'existe qu'après la migration ci-dessus (colonne
    # ajoutée par ALTER TABLE, absente du CREATE TABLE users de SCHEMA) :
    # cet index doit donc être créé ici, jamais dans SCHEMA. Voir
    # get_user_by_stripe_customer_id, appelée à chaque webhook Stripe reçu
    # (webapp/stripe_webhook_service.py) — sans cet index, chaque événement
    # Stripe ferait un scan complet de la table users, dont le coût grandit
    # avec le nombre de comptes. Colonne non UNIQUE (NULL pour tout compte
    # n'ayant jamais eu de client Stripe), donc un index simple.
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_stripe_customer_id ON users(stripe_customer_id)")
    conn.commit()


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


def get_user_by_stripe_customer_id(customer_id):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE stripe_customer_id = ?", (customer_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def set_stripe_customer_id(user_id, customer_id):
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE users SET stripe_customer_id = ? WHERE id = ?", (customer_id, user_id)
        )
        conn.commit()
    finally:
        conn.close()


def set_stripe_subscription(user_id, subscription_id, plan, status=None):
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE users SET stripe_subscription_id = ?, plan = ?, stripe_subscription_status = ? WHERE id = ?",
            (subscription_id, plan, status, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def set_user_role(user_id, role):
    """Écrit la valeur brute (str) d'un Role (voir role_service.py) — ce
    module ne connaît pas l'Enum Role, uniquement la colonne SQL, même
    séparation que set_stripe_subscription/plan_service.Plan."""
    conn = get_connection()
    try:
        conn.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
        conn.commit()
    finally:
        conn.close()


def set_stripe_subscription_status(user_id, status):
    """Met à jour uniquement le statut brut (ex: 'past_due' après un paiement
    en échec), sans toucher à plan/stripe_subscription_id — utilisé quand
    l'abonnement reste actif en base mais que Stripe signale un problème de
    paiement en cours de nouvelle tentative."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE users SET stripe_subscription_status = ? WHERE id = ?", (status, user_id)
        )
        conn.commit()
    finally:
        conn.close()


# ── Idempotence des webhooks Stripe ────────────────────────────────────────────
def has_processed_stripe_event(event_id):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT 1 FROM stripe_webhook_events WHERE event_id = ?", (event_id,)
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def mark_stripe_event_processed(event_id, event_type):
    """Réserve cet event_id avant traitement (voir
    stripe_webhook_service.handle_event, qui appelle cette fonction AVANT
    d'exécuter le handler, pas après) : INSERT OR IGNORE sur la PRIMARY KEY
    event_id fait que si deux requêtes concurrentes traitent le même event_id
    (double livraison quasi simultanée), une seule des deux insertions réussit
    réellement — l'autre est ignorée sans erreur au lieu de violer la
    contrainte, et son appelant sait grâce à la valeur de retour qu'il ne doit
    pas exécuter le handler. Renvoie True si cet appel vient de réserver
    l'event_id (jamais vu avant, le handler peut s'exécuter), False s'il était
    déjà enregistré (doublon, à ignorer)."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT OR IGNORE INTO stripe_webhook_events (event_id, event_type, processed_at) VALUES (?, ?, ?)",
            (event_id, event_type, _now()),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def unmark_stripe_event_processed(event_id):
    """Annule la réservation faite par mark_stripe_event_processed : appelée
    uniquement quand le handler d'un event_id fraîchement réservé lève une
    exception, pour que Stripe puisse le redélivrer plus tard et qu'il soit
    retraité normalement au lieu de rester bloqué en doublon fantôme."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM stripe_webhook_events WHERE event_id = ?", (event_id,))
        conn.commit()
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


def create_user(email, username, pseudo, password_hash, auth_provider="local",
                 birth_date=None, account_status="active"):
    conn = get_connection()
    try:
        cur = conn.execute(
            """INSERT INTO users
               (email, username, pseudo, password_hash, auth_provider, created_at,
                birth_date, account_status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (email.lower(), username, pseudo, password_hash, auth_provider, _now(),
             birth_date, account_status),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def set_account_status(user_id, status):
    conn = get_connection()
    try:
        conn.execute("UPDATE users SET account_status = ? WHERE id = ?", (status, user_id))
        conn.commit()
    finally:
        conn.close()


def set_policy_acceptance(user_id, terms_version=None, privacy_version=None):
    """Enregistre la dernière version des CGU/politique de confidentialité
    acceptée par ce compte (voir consent_service.needs_policy_reacceptance) —
    n'écrase que les colonnes réellement fournies, comme update_profile."""
    conn = get_connection()
    try:
        now = _now()
        if terms_version is not None:
            conn.execute(
                "UPDATE users SET terms_accepted_version = ?, terms_accepted_at = ? WHERE id = ?",
                (terms_version, now, user_id),
            )
        if privacy_version is not None:
            conn.execute(
                "UPDATE users SET privacy_accepted_version = ?, privacy_accepted_at = ? WHERE id = ?",
                (privacy_version, now, user_id),
            )
        conn.commit()
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


# ── Authentification à deux facteurs (webapp/two_factor_service.py) ───────────
def set_two_factor_secret(user_id, encrypted_secret):
    """Enregistre le secret TOTP chiffré (voir two_factor_service._encrypt_
    secret — jamais appelé avec une valeur en clair) sans activer la 2FA :
    /2fa/setup peut être rappelée pour régénérer un secret tant que /2fa/enable
    n'a pas confirmé un premier code valide."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE users SET two_factor_secret = ?, two_factor_last_counter = NULL WHERE id = ?",
            (encrypted_secret, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def enable_two_factor(user_id):
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE users SET two_factor_enabled = 1, two_factor_enabled_at = ? WHERE id = ?",
            (_now(), user_id),
        )
        conn.commit()
    finally:
        conn.close()


def disable_two_factor(user_id):
    """Efface aussi le secret et le compteur de rejeu — une future
    réactivation repart d'un /2fa/setup entièrement neuf, jamais d'un secret
    résiduel. Les recovery codes sont supprimés séparément (voir
    delete_all_recovery_codes), appelée par two_factor_service.disable()."""
    conn = get_connection()
    try:
        conn.execute(
            """UPDATE users SET two_factor_enabled = 0, two_factor_secret = NULL,
               two_factor_enabled_at = NULL, two_factor_last_counter = NULL WHERE id = ?""",
            (user_id,),
        )
        conn.commit()
    finally:
        conn.close()


def set_two_factor_last_counter(user_id, counter):
    """Persiste le dernier pas TOTP accepté — voir la colonne dans SCHEMA
    (protection anti-rejeu)."""
    conn = get_connection()
    try:
        conn.execute("UPDATE users SET two_factor_last_counter = ? WHERE id = ?", (counter, user_id))
        conn.commit()
    finally:
        conn.close()


def create_two_factor_challenge(user_id, remember, minutes=5):
    """Même pattern que create_password_reset : token opaque à usage unique,
    courte expiration. `remember` reporte le choix fait à l'étape mot de passe
    jusqu'à la résolution du défi (voir SCHEMA)."""
    conn = get_connection()
    try:
        token = secrets.token_urlsafe(32)
        expires_at = (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()
        conn.execute(
            "INSERT INTO two_factor_challenges (token, user_id, remember, created_at, expires_at) VALUES (?, ?, ?, ?, ?)",
            (token, user_id, int(remember), _now(), expires_at),
        )
        conn.commit()
        return token
    finally:
        conn.close()


def get_two_factor_challenge(token):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM two_factor_challenges WHERE token = ? AND expires_at > ?",
            (token, _now()),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def delete_two_factor_challenge(token):
    """Un défi n'est jamais réutilisable, réussi ou pas : consommé après une
    résolution réussie (voir two_factor_service), et de toute façon voué à
    expirer sinon — pas de colonne `used`, la suppression est immédiate."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM two_factor_challenges WHERE token = ?", (token,))
        conn.commit()
    finally:
        conn.close()


def replace_recovery_codes(user_id, code_hashes):
    """Remplace intégralement les recovery codes de `user_id` par
    `code_hashes` (hachés, voir two_factor_service.py — jamais en clair) —
    une seule transaction (DELETE puis INSERT), pour qu'un /2fa/enable qui
    régénère les codes ne laisse jamais un mélange d'anciens et de nouveaux."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM two_factor_recovery_codes WHERE user_id = ?", (user_id,))
        now = _now()
        conn.executemany(
            "INSERT INTO two_factor_recovery_codes (user_id, code_hash, created_at) VALUES (?, ?, ?)",
            [(user_id, code_hash, now) for code_hash in code_hashes],
        )
        conn.commit()
    finally:
        conn.close()


def get_recovery_codes(user_id):
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, code_hash FROM two_factor_recovery_codes WHERE user_id = ?", (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def consume_recovery_code(user_id, code_hash):
    """Supprime ATOMIQUEMENT le recovery code (user_id, code_hash) s'il
    existe encore, et renvoie True s'il a réellement été supprimé (False s'il
    n'existait déjà plus). Un DELETE conditionnel unique — jamais un
    SELECT puis un DELETE séparés — pour qu'un même recovery code ne puisse
    jamais être consommé deux fois par deux requêtes concurrentes (voir
    two_factor_service.verify_recovery_challenge, même principe que
    quota_service.consume()/rate_limit_service.check() ailleurs dans le
    projet : la donnée sur laquelle porte la décision est retirée dans la
    même opération atomique qui vérifie sa présence)."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "DELETE FROM two_factor_recovery_codes WHERE user_id = ? AND code_hash = ?",
            (user_id, code_hash),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def delete_all_recovery_codes(user_id):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM two_factor_recovery_codes WHERE user_id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()


def count_recovery_codes(user_id):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM two_factor_recovery_codes WHERE user_id = ?", (user_id,)
        ).fetchone()
        return row["n"]
    finally:
        conn.close()


def count_recent_two_factor_failures(user_id, minutes=15):
    """Nombre de tentatives 2FA invalides (verify/recovery/disable) pour
    `user_id` sur les `minutes` dernières minutes — verrouillage temporaire
    (voir two_factor_service.py), même principe que count_recent_failed_
    attempts ci-dessus pour le mot de passe. S'appuie sur les événements déjà
    journalisés par auth.py (event_type se terminant par '_failed'), aucune
    table de compteur dédiée supplémentaire."""
    conn = get_connection()
    try:
        since = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()
        row = conn.execute(
            """SELECT COUNT(*) AS n FROM security_events
               WHERE user_id = ? AND event_type LIKE 'two_factor%_failed' AND created_at > ?""",
            (user_id, since),
        ).fetchone()
        return row["n"]
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


def list_security_events_for_user(user_id):
    """Historique des événements de sécurité d'UN compte (export RGPD, voir
    privacy_service.export_account_data) — distinct de count_security_events
    ci-dessous (agrégat global tous comptes confondus, pour metrics_service.py)."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT event_type, ip, created_at FROM security_events WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def count_security_events(event_type):
    """Nombre total d'événements `event_type` déjà journalisés (voir
    log_security_event ci-dessus) — utilisé par metrics_service.py pour
    dériver des compteurs persistés (connexions, inscriptions, paiements)
    sans dupliquer aucune logique de comptage : auth.py/stripe_webhook_
    service.py journalisent déjà ces événements pour d'autres raisons
    (traçabilité), ce compteur ne fait que les agréger en lecture seule."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM security_events WHERE event_type = ?", (event_type,)
        ).fetchone()
        return row["n"]
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


def count_conversations():
    """Nombre total de conversations chatbot, tous utilisateurs confondus —
    utilisé par metrics_service.py (compteur "conversations IA")."""
    conn = get_connection()
    try:
        return conn.execute("SELECT COUNT(*) AS n FROM conversations").fetchone()["n"]
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
def _deserialize_message(row):
    msg = dict(row)
    for field in ("cards", "mentions"):
        if msg.get(field):
            try:
                msg[field] = json.loads(msg[field])
            except json.JSONDecodeError:
                msg[field] = None
    return msg


def add_message(conversation_id, role, content, cards=None, mentions=None):
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO chatbot_messages (conversation_id, role, content, cards, mentions, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (conversation_id, role, content, json.dumps(cards) if cards else None, json.dumps(mentions) if mentions else None, _now()),
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
        rows = [_deserialize_message(r) for r in rows]
        return rows[-limit:] if limit else rows
    finally:
        conn.close()


def get_message(message_id):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM chatbot_messages WHERE id = ?", (message_id,)).fetchone()
        return _deserialize_message(row) if row else None
    finally:
        conn.close()


def set_message_cards(message_id, cards):
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE chatbot_messages SET cards = ? WHERE id = ?",
            (json.dumps(cards) if cards else None, message_id),
        )
        conn.commit()
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


# ── Quotas d'utilisation génériques (webapp/quota_service.py) ─────────────────
def increment_daily_usage(user_id, quota_type, day_str, amount=1):
    """Incrémente (ou crée) le compteur de `quota_type` pour `user_id`/`day_str`
    de `amount` (peut être négatif, utilisé par quota_service.py pour annuler
    un incrément refusé) et renvoie le nouveau total. Un seul INSERT ...
    ON CONFLICT DO UPDATE : opération atomique unique côté SQLite, jamais un
    lire-puis-écrire séparé — sûr sous appels concurrents (voir
    increment_chatbot_quota ci-dessus, même principe)."""
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO user_daily_usage (user_id, quota_type, date, count) VALUES (?, ?, ?, ?)
               ON CONFLICT(user_id, quota_type, date) DO UPDATE SET count = count + excluded.count""",
            (user_id, quota_type, day_str, amount),
        )
        conn.commit()
        row = conn.execute(
            "SELECT count FROM user_daily_usage WHERE user_id = ? AND quota_type = ? AND date = ?",
            (user_id, quota_type, day_str),
        ).fetchone()
        return row["count"]
    finally:
        conn.close()


def get_daily_usage(user_id, quota_type, day_str):
    """Compteur courant de `quota_type` pour `user_id`/`day_str`, 0 si aucune
    ligne n'existe encore (pas encore consommé aujourd'hui, ou nouveau jour —
    aucune tâche de reset séparée n'est nécessaire, voir SCHEMA)."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT count FROM user_daily_usage WHERE user_id = ? AND quota_type = ? AND date = ?",
            (user_id, quota_type, day_str),
        ).fetchone()
        return row["count"] if row else 0
    finally:
        conn.close()


def ensure_daily_usage_row(user_id, quota_type, day_str):
    """Crée la ligne de `quota_type` pour `user_id`/`day_str` à 0 si elle
    n'existe pas encore ; ne fait rien sinon (INSERT OR IGNORE, idempotent).
    Jamais nécessaire avant get_daily_usage/increment_daily_usage (qui gèrent
    déjà l'absence de ligne) — utile pour un appelant qui veut garantir
    explicitement l'existence de la ligne du jour (voir
    quota_service.reset_if_needed)."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO user_daily_usage (user_id, quota_type, date, count) VALUES (?, ?, ?, 0)",
            (user_id, quota_type, day_str),
        )
        conn.commit()
    finally:
        conn.close()


# ── Rate limiting HTTP (webapp/rate_limit_service.py) ──────────────────────────
def record_rate_limit_event(key, endpoint, window_start, amount=1):
    """Incrémente (ou crée) le bucket (key, endpoint, window_start) de
    `amount` (peut être négatif, utilisé par rate_limit_service.check() pour
    annuler un incrément refusé) et renvoie le nouveau total du bucket. Un
    seul INSERT ... ON CONFLICT DO UPDATE : opération atomique unique côté
    SQLite, jamais un lire-puis-écrire séparé — sûr sous appels concurrents
    (même principe que increment_daily_usage ci-dessus)."""
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO rate_limit_events (key, endpoint, window_start, count) VALUES (?, ?, ?, ?)
               ON CONFLICT(key, endpoint, window_start) DO UPDATE SET count = count + excluded.count""",
            (key, endpoint, window_start, amount),
        )
        conn.commit()
        row = conn.execute(
            "SELECT count FROM rate_limit_events WHERE key = ? AND endpoint = ? AND window_start = ?",
            (key, endpoint, window_start),
        ).fetchone()
        return row["count"] if row else 0
    finally:
        conn.close()


def get_rate_limit_usage(key, endpoint, since_window_start):
    """Total consommé et fenêtre la plus ancienne encore active pour
    (key, endpoint) parmi les buckets dont window_start >= since_window_start
    — une seule requête agrégée, servie par idx_rate_limit_events_lookup
    (voir SCHEMA), appelée à chaque requête HTTP décorée par @rate_limit.
    Renvoie (0, None) si aucun bucket n'existe encore dans la fenêtre."""
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT COALESCE(SUM(count), 0) AS total, MIN(window_start) AS oldest
               FROM rate_limit_events
               WHERE key = ? AND endpoint = ? AND window_start >= ?""",
            (key, endpoint, since_window_start),
        ).fetchone()
        return row["total"], row["oldest"]
    finally:
        conn.close()


def cleanup_rate_limit_events(older_than_window_start):
    """Supprime tous les buckets dont window_start < older_than_window_start
    — empêche rate_limit_events de grossir indéfiniment (voir
    rate_limit_service.cleanup()). Renvoie le nombre de lignes supprimées."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "DELETE FROM rate_limit_events WHERE window_start < ?", (older_than_window_start,)
        )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


# ── Consentement parental RGPD (webapp/consent_service.py) ────────────────────
def create_parental_consent_request(user_id, parent_email, days=30):
    """Même pattern que create_password_reset/create_two_factor_challenge :
    token opaque à usage unique. N'invalide pas les demandes déjà en attente
    pour ce compte — voir supersede_pending_parental_consent_requests, appelée
    séparément par consent_service avant d'en créer une nouvelle."""
    conn = get_connection()
    try:
        token = secrets.token_urlsafe(32)
        expires_at = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
        conn.execute(
            """INSERT INTO parental_consent_requests
               (token, user_id, parent_email, status, created_at, expires_at)
               VALUES (?, ?, ?, 'pending', ?, ?)""",
            (token, user_id, parent_email, _now(), expires_at),
        )
        conn.commit()
        return token
    finally:
        conn.close()


def get_parental_consent_request(token):
    """Lecture brute, quel que soit le statut/l'expiration — c'est à
    consent_service de distinguer jeton inconnu / expiré / déjà résolu pour
    renvoyer le bon message d'erreur."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM parental_consent_requests WHERE token = ?", (token,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def resolve_parental_consent_request(token, status, ip):
    """Passe une demande 'pending' à 'accepted'/'refused' de façon atomique
    (UPDATE conditionné sur status='pending' dans la même requête, jamais un
    SELECT puis UPDATE séparés) — même principe que consume_recovery_code :
    empêche qu'un même lien, ouvert deux fois en parallèle, soit résolu deux
    fois. Renvoie True si cette résolution a bien pris effet."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """UPDATE parental_consent_requests
               SET status = ?, resolved_at = ?, resolved_ip = ?
               WHERE token = ? AND status = 'pending'""",
            (status, _now(), ip, token),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def supersede_pending_parental_consent_requests(user_id):
    """Invalide toute demande encore 'pending' pour ce compte avant l'émission
    d'un nouveau jeton (renvoi d'email) — un seul jeton valide à la fois."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE parental_consent_requests SET status = 'superseded' WHERE user_id = ? AND status = 'pending'",
            (user_id,),
        )
        conn.commit()
    finally:
        conn.close()


def get_latest_parental_consent_request(user_id):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM parental_consent_requests WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_parental_consent_requests(user_id):
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM parental_consent_requests WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ── Preuves de consentement RGPD (webapp/consent_service.py, privacy_service.py) ──
def add_consent_record(user_id, consent_type, decision, policy_version, ip):
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO consent_records (user_id, consent_type, decision, policy_version, ip, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, consent_type, decision, policy_version, ip, _now()),
        )
        conn.commit()
    finally:
        conn.close()


def list_consent_records(user_id):
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM consent_records WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ── Consentement cookies (webapp/consent_service.py) ───────────────────────────
def get_cookie_consent(user_id):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM cookie_consents WHERE user_id = ?", (user_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def set_cookie_consent(user_id, statistics, marketing):
    """UPSERT unique (même principe que increment_chatbot_quota) : une seule
    ligne par utilisateur, toujours à jour."""
    conn = get_connection()
    try:
        now = _now()
        conn.execute(
            """INSERT INTO cookie_consents (user_id, statistics, marketing, updated_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                   statistics = excluded.statistics,
                   marketing = excluded.marketing,
                   updated_at = excluded.updated_at""",
            (user_id, int(statistics), int(marketing), now),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM cookie_consents WHERE user_id = ?", (user_id,)
        ).fetchone()
        return dict(row)
    finally:
        conn.close()
