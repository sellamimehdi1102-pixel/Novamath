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

import config
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

-- LEGACY (Chantier Quotas/IA, 2026-08-25) : table historique, plus alimentée
-- par le chatbot depuis la migration vers `user_daily_usage`/quota_service.py
-- ci-dessous (seul système de quotas réellement actif aujourd'hui — voir
-- increment_daily_usage()). `increment_chatbot_quota()`/`get_chatbot_quota()`
-- restent définies (utilisées uniquement par des tests de non-régression qui
-- vérifient explicitement que cette table reste à 0, voir
-- test_chatbot_quota_integration.py::test_ancienne_table_chatbot_quota_nest_plus_alimentee)
-- mais aucun appelant applicatif ne les invoque plus. Conservée pour ne pas
-- casser une base existante (DROP TABLE hors du périmètre de ce chantier),
-- jamais utilisée pour une décision de quota.
CREATE TABLE IF NOT EXISTS chatbot_quota (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, date)
);

-- Idempotence des webhooks Stripe (webapp/stripe_webhook_service.py) : chaque
-- event.id Stripe n'est traité qu'une seule fois, même si Stripe le renvoie
-- plusieurs fois (retries réseau, redélivraison manuelle depuis le Dashboard).
-- completed_at (NULL tant que le handler n'a pas terminé avec succès) permet
-- de distinguer une réservation "en cours" d'une réservation "terminée" — si
-- le process est tué (SIGKILL, restart Fly.io) avant de pouvoir la marquer
-- complétée, mark_stripe_event_processed() la considère abandonnée après
-- STRIPE_WEBHOOK_CLAIM_TIMEOUT_SECONDS et autorise un nouveau traitement réel
-- au prochain retry Stripe (voir sa docstring).
CREATE TABLE IF NOT EXISTS stripe_webhook_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    processed_at TEXT NOT NULL,
    completed_at TEXT
);

-- Quotas d'utilisation quotidiens génériques (webapp/quota_service.py) — une
-- ligne par (utilisateur, type de quota, jour). SEULE source de vérité des
-- quotas chatbot réels (CHAT_MESSAGES/LLM_CALLS inclus) — `chatbot_quota`
-- ci-dessus est un résidu legacy jamais lu ni écrit par le pipeline actuel.
-- Toute future limitation
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

-- Fournisseurs IA configurables (infrastructure de préparation, voir
-- webapp/ai_provider_service.py) — une ligne = un couple (fournisseur,
-- modèle) avec son état d'activation et sa priorité, en vue d'une future
-- migration du choix du fournisseur IA depuis la base plutôt que depuis les
-- constantes en dur de webapp/chatbot/provider_manager.py (PROVIDERS/MODELS/
-- MODEL_CHAIN_BY_PLAN). PAS ENCORE branchée au chatbot : aucun appelant ne
-- lit cette table à ce jour, le comportement actuel reste donc strictement
-- inchangé (voir docstring de ai_provider_service.py).
CREATE TABLE IF NOT EXISTS ai_providers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    provider_key TEXT NOT NULL,
    model_name TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    priority INTEGER NOT NULL DEFAULT 0,
    fallback_provider_id INTEGER REFERENCES ai_providers(id) ON DELETE SET NULL,
    -- Métadonnées d'affichage pour la future interface d'administration
    -- (voir _AI_PROVIDER_METADATA_COLUMNS ci-dessous pour la migration
    -- additive d'une base déjà créée avant l'introduction de ces colonnes) :
    -- jamais lues par le chatbot, uniquement destinées à un futur écran
    -- d'admin (liste/badge/icône/couleur d'un fournisseur).
    code TEXT,
    description TEXT,
    badge TEXT,
    icon TEXT,
    color TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ai_providers_priority ON ai_providers(enabled, priority);

-- Association abonnement -> fournisseur IA configurable (même infrastructure
-- de préparation, non branchée). `subscription` reprend les valeurs de
-- plan_service.Plan ("free"/"premium"/"ultra") en texte plutôt qu'une
-- contrainte FOREIGN KEY : ce module n'importe jamais plan_service, même
-- règle d'architecture stricte que le reste de db.py (aucune dépendance vers
-- un service applicatif).
CREATE TABLE IF NOT EXISTS subscription_ai_mapping (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subscription TEXT NOT NULL,
    provider_id INTEGER NOT NULL REFERENCES ai_providers(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_subscription_ai_mapping_subscription ON subscription_ai_mapping(subscription);

-- Snapshot de santé courant d'un fournisseur IA configurable (infrastructure
-- de préparation pour la future interface d'administration — voir
-- ai_provider_service.py) : UNE ligne par fournisseur, toujours à jour (même
-- principe qu'une ligne par utilisateur dans cookie_consents), jamais un
-- historique d'événements. PAS ENCORE alimentée par aucun appel réel : ni le
-- chatbot (webapp/chatbot/) ni aucun autre module n'écrit ici à ce jour.
CREATE TABLE IF NOT EXISTS ai_provider_health (
    provider_id INTEGER PRIMARY KEY REFERENCES ai_providers(id) ON DELETE CASCADE,
    last_success TEXT,
    last_failure TEXT,
    http_code INTEGER,
    latency_ms INTEGER,
    average_latency REAL,
    total_requests INTEGER NOT NULL DEFAULT 0,
    total_errors INTEGER NOT NULL DEFAULT 0,
    success_rate REAL,
    last_error TEXT,
    updated_at TEXT NOT NULL
);

-- Haute disponibilité IA : plusieurs clés API par fournisseur, avec rotation
-- automatique en cas d'échec (voir ai_provider_key_service.py). `provider_key`
-- reprend la même valeur que ai_providers.provider_key ("gemini"/"anthropic")
-- MAIS n'est PAS une FK vers une ligne ai_providers précise : une clé API
-- appartient au COMPTE fournisseur (elle fonctionne pour tous ses modèles),
-- jamais à un seul (provider_key, model_name). `api_key_encrypted` : jamais
-- en clair, chiffré via Fernet (même mécanisme que
-- two_factor_service._encrypt_secret, réutilisant TWO_FACTOR_SECRET_KEY —
-- voir ai_provider_key_service.py). `priority` : ordre de rotation (plus
-- petit = essayé en premier) parmi les clés `enabled` d'un même
-- provider_key. `quota_exceeded_until` : NULL si la clé est utilisable
-- maintenant, sinon un timestamp ISO — cette clé est ignorée par la
-- rotation jusqu'à cette date (même principe que le cache d'indisponibilité
-- de provider_manager.py, mais PAR CLÉ plutôt que par (provider, modèle)).
-- `request_count`/`failure_count`/`total_response_time_ms` : compteurs
-- cumulés depuis la création de la clé, jamais réinitialisés. `fallback_count`
-- : nombre de fois où un échec sur CETTE clé a réellement déclenché un
-- passage à la clé/au modèle/au fournisseur suivant (distinct de
-- failure_count : un échec survenu APRÈS qu'une réponse partielle ait déjà
-- été diffusée à l'élève ne peut jamais être rejoué, donc n'entraîne aucune
-- bascule — voir llm_fallback_service.generate()).
CREATE TABLE IF NOT EXISTS ai_provider_api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_key TEXT NOT NULL,
    label TEXT NOT NULL,
    api_key_encrypted TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    priority INTEGER NOT NULL DEFAULT 0,
    request_count INTEGER NOT NULL DEFAULT 0,
    failure_count INTEGER NOT NULL DEFAULT 0,
    fallback_count INTEGER NOT NULL DEFAULT 0,
    total_response_time_ms INTEGER NOT NULL DEFAULT 0,
    last_used_at TEXT,
    last_success_at TEXT,
    last_failure_at TEXT,
    last_error TEXT,
    quota_exceeded_until TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ai_provider_api_keys_provider ON ai_provider_api_keys(provider_key, enabled, priority);

-- Consommation quotidienne d'un fournisseur IA configurable — une ligne par
-- (fournisseur, jour), même principe que user_daily_usage
-- (webapp/quota_service.py) : un nouveau jour = une nouvelle ligne, sans
-- tâche de réinitialisation séparée. Alimentée après CHAQUE appel LLM réel
-- (succès ou échec) via ai_provider_service.record_llm_usage(), appelée par
-- webapp/chatbot/conversation_manager.py::_log_llm_call_details — voir
-- docstring de record_llm_usage. Colonnes d'observabilité (total_tokens/
-- success_count/error_count/fallback_count/total_response_time_ms/
-- last_error_*) ajoutées par migration additive, voir
-- _AI_PROVIDER_USAGE_OBSERVABILITY_COLUMNS ci-dessous (absentes du CREATE
-- TABLE historique pour ne jamais casser une base déjà créée).
CREATE TABLE IF NOT EXISTS ai_provider_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_id INTEGER NOT NULL REFERENCES ai_providers(id) ON DELETE CASCADE,
    date TEXT NOT NULL,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    requests INTEGER NOT NULL DEFAULT 0,
    estimated_cost REAL NOT NULL DEFAULT 0,
    UNIQUE(provider_id, date)
);
CREATE INDEX IF NOT EXISTS idx_ai_provider_usage_provider_date ON ai_provider_usage(provider_id, date);

-- Un événement = un fallback réellement déclenché lors d'un appel LLM (le
-- fournisseur initialement sélectionné par provider_manager.py a échoué à
-- l'usage et un autre a pris le relais, voir llm_fallback_service.generate())
-- — table d'événements distincte de ai_provider_usage (qui n'agrège qu'un
-- COMPTEUR quotidien fallback_count par fournisseur) car `reason`/
-- provider_initial/provider_final varient à chaque événement et ne
-- s'agrègent pas utilement dans une seule ligne par jour. Écrite par
-- ai_provider_service.record_provider_fallback(), jamais lue par le
-- chatbot lui-même (même principe d'indépendance que ai_admin_log).
CREATE TABLE IF NOT EXISTS ai_provider_fallback_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    provider_initial TEXT NOT NULL,
    model_initial TEXT NOT NULL,
    provider_final TEXT NOT NULL,
    model_final TEXT NOT NULL,
    reason TEXT,
    time_lost_ms INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_ai_provider_fallback_events_created_at ON ai_provider_fallback_events(created_at);

-- Une ligne = UN appel LLM réel (succès ou échec), rattaché à l'utilisateur
-- et à la conversation qui l'ont déclenché — écrite par
-- ai_request_log_service.record(), appelé par
-- webapp/chatbot/conversation_manager.py::_log_llm_call_details au même
-- endroit que ai_provider_service.record_llm_usage(). Distincte
-- d'ai_provider_usage (agrégat GLOBAL quotidien par fournisseur, jamais par
-- utilisateur, jamais modifiée par ce chantier) : cette table est la SEULE
-- source des statistiques IA affichées sur la fiche d'un utilisateur
-- (Administration -> Utilisateurs -> onglet Chatbot), voir
-- admin_user_profile_service.get_chatbot(). `conversation_id` n'est PAS une
-- contrainte FOREIGN KEY (contrairement à conversations.user_id
-- ci-dessus) : supprimer UNE conversation ne doit jamais faire disparaître
-- les lignes de consommation déjà enregistrées pour cet utilisateur (même
-- raisonnement que ai_admin_log.provider_id, qui n'est pas non plus une
-- FK). `user_id`, en revanche, cascade avec la suppression du compte : ces
-- statistiques n'ont plus de sens une fois le compte supprimé.
CREATE TABLE IF NOT EXISTS ai_request_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    conversation_id INTEGER,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    estimated_cost REAL NOT NULL DEFAULT 0,
    response_time_ms INTEGER NOT NULL DEFAULT 0,
    success INTEGER NOT NULL DEFAULT 1,
    fallback INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ai_request_logs_user_created ON ai_request_logs(user_id, created_at);

-- Journal d'activité IA (module Administration -> Journal, /admin/journal) —
-- historique COMPLET et immuable de chaque action effectuée depuis le
-- panneau d'administration des fournisseurs IA (création/modification/
-- suppression/activation/désactivation/réordonnancement/abonnements/test/
-- health-check), voir admin_ai_log_service.py. Totalement indépendant du
-- fonctionnement du chatbot : aucune table ici n'est jamais lue par
-- webapp/chatbot/, ce journal ne fait qu'OBSERVER des actions déjà
-- effectuées ailleurs.
--
-- `provider_id` n'est PAS une contrainte FOREIGN KEY (contrairement à
-- ai_provider_health/ai_provider_usage) : un fournisseur supprimé ne doit
-- JAMAIS faire disparaître ou invalider les lignes de journal qui le
-- concernent (ON DELETE CASCADE serait un anti-pattern pour un journal
-- d'audit) — `provider_name`/`provider_key`/`model_name` sont donc stockés
-- en clair (photo au moment de l'action), lisibles même si le fournisseur
-- n'existe plus.
--
-- `admin_user_id` référence `users` avec ON DELETE SET NULL (même raison :
-- un compte admin supprimé ne doit jamais effacer l'historique de ses
-- actions) — `admin_name`/`admin_role` sont eux aussi stockés en clair
-- (photo au moment de l'action, jamais recalculés depuis `users` a
-- posteriori).
--
-- `old_values`/`new_values` : JSON texte (même convention que
-- conversations.learning_context/chatbot_messages.cards) — un sous-ensemble
-- des champs réellement modifiés, jamais l'objet entier reconstruit à la
-- lecture.
CREATE TABLE IF NOT EXISTS ai_admin_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    admin_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    admin_name TEXT NOT NULL,
    admin_role TEXT NOT NULL,
    ip TEXT,
    action TEXT NOT NULL,
    provider_id INTEGER,
    provider_name TEXT,
    old_values TEXT,
    new_values TEXT,
    result TEXT NOT NULL,
    error_message TEXT
);
CREATE INDEX IF NOT EXISTS idx_ai_admin_log_created_at ON ai_admin_log(created_at);
CREATE INDEX IF NOT EXISTS idx_ai_admin_log_admin_user_id ON ai_admin_log(admin_user_id);
CREATE INDEX IF NOT EXISTS idx_ai_admin_log_provider_id ON ai_admin_log(provider_id);
CREATE INDEX IF NOT EXISTS idx_ai_admin_log_action ON ai_admin_log(action);

-- Paramètres persistés du module Administration -> Paramètres (/admin/settings).
-- Une ligne = UN paramètre (clé libre, ex: "site_name"/"maintenance_enabled"),
-- valeur toujours stockée en TEXTE (le service settings_service.py se charge
-- de la conversion vers bool/int/etc. selon la clé — jamais de colonne par
-- paramètre, qui obligerait une migration à chaque nouveau réglage). Absence
-- de ligne = paramètre jamais modifié : settings_service.py applique alors sa
-- valeur par défaut documentée, jamais une valeur fabriquée. Ne remplace
-- JAMAIS une variable d'environnement existante (STRIPE_SECRET_KEY,
-- EMAIL_SMTP_HOST...) : cette table ne stocke QUE des réglages qui n'ont
-- structurellement aucune autre source de vérité aujourd'hui.
CREATE TABLE IF NOT EXISTS system_settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TEXT NOT NULL,
    updated_by_admin_id INTEGER REFERENCES users(id) ON DELETE SET NULL
);

-- Catalogue administrable des abonnements (module Administration ->
-- Abonnements, /admin/subscriptions) — UNE ligne par plan FIXE (free/
-- premium/ultra, reprend exactement plan_service.Plan.value comme clé
-- primaire : ces 3 plans ne se créent/suppriment jamais depuis ce panneau,
-- seul leur contenu catalogue est modifiable). Infrastructure de
-- PRÉSENTATION/CATALOGUE, même statut que ai_providers avant sa migration :
-- PAS ENCORE branchée à plan_service.py/quota_service.py (qui restent
-- l'unique source de vérité des droits/quotas réellement appliqués, via
-- FEATURE_MATRIX/QUOTA_MATRIX) — modifier une ligne ici change ce qui
-- s'affiche dans ce panneau d'administration, jamais ce qui est réellement
-- appliqué au chatbot ni à Stripe. `price_amount_cents`/`currency`/
-- `duration_label` reprennent les valeurs actuellement affichées sur la page
-- publique /abonnement.html (texte statique aujourd'hui, jamais lu depuis
-- Stripe) — les modifier ici ne change ni cette page publique ni le montant
-- réellement facturé par Stripe (toujours piloté par STRIPE_PRICE_PREMIUM/
-- STRIPE_PRICE_ULTRA, voir stripe_service.py, totalement inchangé).
CREATE TABLE IF NOT EXISTS subscription_plans (
    plan TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    price_amount_cents INTEGER,
    currency TEXT,
    duration_label TEXT,
    advantages TEXT,
    limits TEXT,
    quota_daily INTEGER,
    quota_monthly INTEGER,
    quota_chatbot INTEGER,
    display_order INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Module Administration -> Support (/admin/support, voir support_service.py).
-- UN ticket par (utilisateur, motif de contact) — créé par l'utilisateur
-- (voir POST /api/support/tickets, aucune création possible depuis
-- l'administration elle-même : un ticket reflète toujours une vraie demande
-- réelle, jamais fabriqué). `status` : 'open'/'in_progress'/'closed'.
-- `category` : 'bug'/'paiement'/'ia'/'compte'/'technique'/'autre'. `priority' :
-- 'faible'/'normale'/'haute'/'urgente'. `assigned_admin_id` : NULL tant
-- qu'aucun administrateur ne s'est attribué le ticket (voir
-- support_service.assign_admin). `first_admin_response_at` : horodatage de la
-- toute PREMIÈRE réponse admin — sert exclusivement au calcul du "temps moyen
-- de réponse" (distinct de `last_response_at`, mis à jour à CHAQUE message,
-- utilisateur ou admin, pour trier/afficher l'activité récente).
-- `satisfaction_rating` : 1-5, renseigné par l'utilisateur après fermeture
-- (optionnel, NULL si jamais noté — jamais une note fabriquée).
CREATE TABLE IF NOT EXISTS support_tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subject TEXT NOT NULL,
    category TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'normale',
    status TEXT NOT NULL DEFAULT 'open',
    assigned_admin_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    satisfaction_rating INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    closed_at TEXT,
    first_admin_response_at TEXT,
    last_response_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_support_tickets_status ON support_tickets(status);
CREATE INDEX IF NOT EXISTS idx_support_tickets_category ON support_tickets(category);
CREATE INDEX IF NOT EXISTS idx_support_tickets_user ON support_tickets(user_id);
CREATE INDEX IF NOT EXISTS idx_support_tickets_created_at ON support_tickets(created_at);
CREATE INDEX IF NOT EXISTS idx_support_tickets_assigned ON support_tickets(assigned_admin_id);

-- Conversation d'UN ticket — `author_type` 'user'/'admin' distingue qui a
-- écrit (jamais déductible de `author_id` seul : un admin peut aussi être un
-- utilisateur NovaMath par ailleurs). Une réponse admin met à jour
-- support_tickets.first_admin_response_at (si absente) ET last_response_at
-- (voir support_service.add_message) — jamais recalculé ici, cette table ne
-- fait qu'stocker le message brut.
CREATE TABLE IF NOT EXISTS support_ticket_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL REFERENCES support_tickets(id) ON DELETE CASCADE,
    author_type TEXT NOT NULL,
    author_id INTEGER NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_support_ticket_messages_ticket ON support_ticket_messages(ticket_id, created_at);

-- Pièce jointe rattachée à UN message (jamais directement à un ticket) —
-- stockage sur disque (voir support_attachment_service.py), cette table ne
-- garde que les métadonnées + le chemin relatif. Aucun contenu binaire en
-- base (contrairement à chatbot_messages.cards qui reste du JSON léger).
CREATE TABLE IF NOT EXISTS support_ticket_attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER NOT NULL REFERENCES support_ticket_messages(id) ON DELETE CASCADE,
    original_filename TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    content_type TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_support_ticket_attachments_message ON support_ticket_attachments(message_id);

-- Note interne (visible UNIQUEMENT par l'administration, jamais par
-- l'utilisateur) — distincte de support_ticket_messages, jamais mélangée à
-- la conversation réellement envoyée à l'élève.
CREATE TABLE IF NOT EXISTS support_ticket_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL REFERENCES support_tickets(id) ON DELETE CASCADE,
    admin_id INTEGER NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_support_ticket_notes_ticket ON support_ticket_notes(ticket_id);

-- Historique des changements d'état d'UN ticket (statut/assignation) —
-- alimente l'onglet "Historique" de la fiche ticket, jamais déduit après
-- coup : chaque changement réel écrit une ligne au moment où il a lieu (voir
-- support_service.change_status/assign_admin).
CREATE TABLE IF NOT EXISTS support_ticket_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL REFERENCES support_tickets(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    from_value TEXT,
    to_value TEXT,
    actor_admin_id INTEGER,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_support_ticket_history_ticket ON support_ticket_history(ticket_id, created_at);

-- Vues Analytics sauvegardées ("Favoris", /admin/analytics) — un admin peut
-- enregistrer une combinaison de filtres (fenêtre/dates) sous un nom pour la
-- rappliquer en un clic. Distincte de system_settings (réglages globaux,
-- pas par admin) et de ai_admin_log (historique d'actions, pas une
-- collection modifiable). `params_json` : {"window":..., "date_from":...,
-- "date_to":...} sérialisé par admin_analytics_service.py, jamais par ce
-- fichier.
CREATE TABLE IF NOT EXISTS analytics_saved_views (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    params_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_analytics_saved_views_admin ON analytics_saved_views(admin_user_id);

-- Cartes KPI épinglées par administrateur ("Tableau de bord personnalisé",
-- /admin/analytics) — un simple ensemble (admin_user_id, kpi_key), jamais un
-- historique : épingler/désépingler modifie la ligne en place (INSERT/DELETE),
-- contrairement à ai_admin_log qui ne fait jamais aucune suppression.
CREATE TABLE IF NOT EXISTS analytics_pinned_kpis (
    admin_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kpi_key TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (admin_user_id, kpi_key)
);
"""


database_service.register_schema(lambda: SCHEMA)


def get_connection():
    return database_service.get_connection(sqlite_path=DB_PATH, sqlite_data_dir=DATA_DIR)


def sqlite_introspection():
    """Introspection en lecture seule de la base SQLite courante (résultat de
    `PRAGMA integrity_check`, version du moteur SQLite) — utilisée par
    system_health_service.py (page Santé du système) : `integrity` pour
    détecter une corruption (action = restaurer une sauvegarde), `sqlite_version`
    pour la carte "Version" du service SQLite. None si le moteur actif n'est
    PAS SQLite (voir database_service.detect_engine) : ces requêtes (PRAGMA)
    n'ont pas de sens sur PostgreSQL, jamais devinées.

    `tables_count`/`total_rows`/`file_size_bytes` ont été retirés (chantier de
    simplification de la page Santé) : purement décoratifs (aucune décision
    admin n'en dépendait), et `total_rows` coûtait un COUNT(*) sur CHAQUE
    table à chaque actualisation de la page — un coût réel pour une donnée
    jamais actionnable. `file_size_bytes` était en outre un doublon exact de
    storage_info()["database_bytes"] (même `DB_PATH.stat().st_size`)."""
    import sqlite3

    if database_service.detect_engine() != database_service.ENGINE_SQLITE:
        return None
    conn = get_connection()
    try:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        return {
            "integrity": integrity,
            "sqlite_version": sqlite3.sqlite_version,
        }
    finally:
        conn.close()


def get_system_setting(key):
    """Valeur brute (TEXTE) du paramètre `key`, ou None s'il n'a jamais été
    modifié — à l'appelant (settings_service.py) d'appliquer sa valeur par
    défaut documentée dans ce cas, jamais ici."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM system_settings WHERE key = ?", (key,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_system_settings():
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM system_settings").fetchall()
        return {row["key"]: dict(row) for row in rows}
    finally:
        conn.close()


def set_system_setting(key, value, updated_by_admin_id=None):
    """UPSERT — `value` toujours stockée en texte (conversion à la charge de
    settings_service.py)."""
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO system_settings (key, value, updated_at, updated_by_admin_id)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(key) DO UPDATE SET
                   value = excluded.value, updated_at = excluded.updated_at,
                   updated_by_admin_id = excluded.updated_by_admin_id""",
            (key, value, _now(), updated_by_admin_id),
        )
        conn.commit()
    finally:
        conn.close()


def count_admins_with_two_factor(roles):
    """{"total": nombre de comptes dont le rôle est dans `roles`, "enabled":
    ceux avec two_factor_enabled=1} — utilisé uniquement par
    settings_service.py (section Sécurité), jamais par le reste du projet."""
    conn = get_connection()
    try:
        placeholders = ",".join("?" for _ in roles)
        total = conn.execute(
            f"SELECT COUNT(*) AS n FROM users WHERE role IN ({placeholders})", tuple(roles)
        ).fetchone()["n"]
        enabled = conn.execute(
            f"SELECT COUNT(*) AS n FROM users WHERE role IN ({placeholders}) AND two_factor_enabled = 1",
            tuple(roles),
        ).fetchone()["n"]
        return {"total": total, "enabled": enabled}
    finally:
        conn.close()


def init_db():
    conn = get_connection()
    try:
        database_service.init_schema(conn, SCHEMA)
        _migrate_guest_lifecycle_columns(conn)
        _migrate_ai_provider_metadata_columns(conn)
        _migrate_ai_provider_usage_columns(conn)
        _migrate_chatbot_message_engine_columns(conn)
        _migrate_ai_request_log_engine_columns(conn)
        _migrate_stripe_webhook_events_columns(conn)
        _create_admin_user_indexes(conn)
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
    # Current Learning Context (continuité de sujet du chatbot) : JSON
    # nullable {chapter_id, notion_id, topic_label, updated_at} — dernier
    # sujet réellement expliqué dans CETTE conversation, voir
    # webapp/chatbot/conversation_manager.py::_update_learning_context. Permet
    # à un message ambigu ("réexplique", "encore"...) de rester sur la même
    # notion sans jamais deviner via une recherche floue sur un message qui
    # ne contient plus aucun mot-clé exploitable.
    ("conversations", "learning_context", "TEXT"),
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


# Métadonnées d'affichage ajoutées à ai_providers après sa création initiale
# (voir _migrate_guest_lifecycle_columns ci-dessus pour le même principe sur
# `users`/`sessions`/... ) — une base créée avant l'introduction de ces
# colonnes ne les a pas via CREATE TABLE IF NOT EXISTS, d'où cette migration
# additive, idempotente sur les deux moteurs.
_AI_PROVIDER_METADATA_COLUMNS = (
    ("ai_providers", "code", "TEXT"),
    ("ai_providers", "description", "TEXT"),
    ("ai_providers", "badge", "TEXT"),
    ("ai_providers", "icon", "TEXT"),
    ("ai_providers", "color", "TEXT"),
)


def _migrate_ai_provider_metadata_columns(conn):
    for table, column, coltype in _AI_PROVIDER_METADATA_COLUMNS:
        database_service.add_column_if_missing(conn, table, column, coltype)
    # `code` n'existe qu'après la migration ci-dessus sur une base déjà créée
    # (absente du CREATE TABLE ai_providers de SCHEMA dans ce cas) : l'index
    # unique doit donc être créé ici, jamais dans SCHEMA. Plusieurs lignes
    # avec code NULL restent autorisées (NULL n'est jamais égal à NULL dans
    # une contrainte UNIQUE), donc aucun conflit tant qu'un `code` n'est pas
    # explicitement renseigné pour chaque fournisseur.
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_ai_providers_code ON ai_providers(code)")
    conn.commit()


# Colonnes d'observabilité ajoutées à ai_provider_usage (chantier
# d'alimentation réelle par le chatbot) — additives, jamais présentes dans
# le CREATE TABLE historique (voir SCHEMA ci-dessus), donc absentes de toute
# base créée avant ce chantier : ajoutées ici via
# database_service.add_column_if_missing(), jamais un ALTER TABLE direct.
# `total_tokens` : somme du total_token_count RÉEL renvoyé par le fournisseur
# (peut dépasser input_tokens+output_tokens, ex: tokens de raisonnement
# internes non détaillés par l'API Gemini — voir
# ai_provider_service.record_llm_usage). `success_count`/`error_count`/
# `fallback_count` : compteurs quotidiens, jamais recalculés depuis
# `requests` (qui reste le total brut, succès + échecs confondus).
# `total_response_time_ms` : somme des durées réelles (voir
# webapp/chatbot/services/llm_fallback_service.py::generate), divisée par
# `requests` côté lecture (admin_dashboard_service.py) pour obtenir une
# moyenne, jamais stockée pré-calculée (éviterait toute incohérence après
# une accumulation partielle). `last_error_*` : SEULEMENT le dernier échec
# connu pour (fournisseur, jour) — pas un historique complet (voir
# ai_provider_fallback_events pour les événements de fallback détaillés).
_AI_PROVIDER_USAGE_OBSERVABILITY_COLUMNS = (
    ("ai_provider_usage", "total_tokens", "INTEGER NOT NULL DEFAULT 0"),
    ("ai_provider_usage", "success_count", "INTEGER NOT NULL DEFAULT 0"),
    ("ai_provider_usage", "error_count", "INTEGER NOT NULL DEFAULT 0"),
    ("ai_provider_usage", "fallback_count", "INTEGER NOT NULL DEFAULT 0"),
    ("ai_provider_usage", "total_response_time_ms", "INTEGER NOT NULL DEFAULT 0"),
    ("ai_provider_usage", "last_error_type", "TEXT"),
    ("ai_provider_usage", "last_error_message", "TEXT"),
    ("ai_provider_usage", "last_error_at", "TEXT"),
)


def _migrate_ai_provider_usage_columns(conn):
    for table, column, coltype in _AI_PROVIDER_USAGE_OBSERVABILITY_COLUMNS:
        database_service.add_column_if_missing(conn, table, column, coltype)
    conn.commit()


# Traçabilité du moteur ayant réellement produit CHAQUE réponse assistant
# (activité chatbot réelle, indépendante de ai_request_logs qui ne couvre que
# les appels LLM). `engine` reprend l'identifiant déjà utilisé par
# pipeline_metrics.record_response() ("clarification", "math_engine",
# "cache", "llm", ...) ; `provider` n'est renseigné que pour engine="llm"
# (call_info["provider"], ex: "gemini"/"anthropic") — NULL pour toute réponse
# locale. Une base créée avant ce chantier a ces deux colonnes NULL sur ses
# lignes existantes : jamais fabriqué, comptabilisé à part ("non catégorisé").
_CHATBOT_MESSAGE_ENGINE_COLUMNS = (
    ("chatbot_messages", "engine", "TEXT"),
    ("chatbot_messages", "provider", "TEXT"),
)


def _migrate_chatbot_message_engine_columns(conn):
    for table, column, coltype in _CHATBOT_MESSAGE_ENGINE_COLUMNS:
        database_service.add_column_if_missing(conn, table, column, coltype)
    conn.commit()


# Couche de tracking IA UNIQUE et étendue : ai_request_logs ne couvrait à
# l'origine que les vrais appels LLM (Gemini/Claude) — désormais CHAQUE
# réponse assistant (y compris moteur local/cache/clarification) y écrit une
# ligne (voir ai_request_log_service.record_local_response()). `engine` est
# le nom précis du moteur ("math_engine", "cache", "llm", ...), `source` le
# bucket coarse ("local"/"gemini"/"anthropic"/"cache"/"clarification" — même
# valeur que `provider` pour toute ligne écrite après ce chantier, gardée
# séparée pour un nom explicite côté API/frontend). `estimated=1` signale que
# input_tokens/output_tokens/total_tokens sont une ESTIMATION heuristique
# (moteur local, aucun appel API réel) et non un comptage réel fourni par le
# fournisseur — jamais confondu avec les vraies données Gemini/Claude
# (estimated=0). Une ligne écrite avant ce chantier a ces 3 colonnes NULL/0 :
# c'était un vrai appel LLM (l'ancien comportement ne loggait que ça), jamais
# réinterprété autrement.
_AI_REQUEST_LOG_ENGINE_COLUMNS = (
    ("ai_request_logs", "engine", "TEXT"),
    ("ai_request_logs", "source", "TEXT"),
    ("ai_request_logs", "estimated", "INTEGER NOT NULL DEFAULT 0"),
)


def _migrate_ai_request_log_engine_columns(conn):
    for table, column, coltype in _AI_REQUEST_LOG_ENGINE_COLUMNS:
        database_service.add_column_if_missing(conn, table, column, coltype)
    conn.commit()


# Résilience de l'idempotence des webhooks Stripe à un kill brutal du process
# (voir CREATE TABLE stripe_webhook_events ci-dessus) — colonne absente d'une
# base créée avant ce correctif.
_STRIPE_WEBHOOK_EVENTS_COLUMNS = (
    ("stripe_webhook_events", "completed_at", "TEXT"),
)


def _migrate_stripe_webhook_events_columns(conn):
    for table, column, coltype in _STRIPE_WEBHOOK_EVENTS_COLUMNS:
        database_service.add_column_if_missing(conn, table, column, coltype)
    conn.commit()


def _now():
    return datetime.now(timezone.utc).isoformat()


# ── Utilisateurs ─────────────────────────────────────────────────────────────


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
    déjà enregistré (doublon, à ignorer).

    Si l'INSERT échoue (ligne déjà réservée), un second essai tente de
    RE-réserver l'event_id via UPDATE, mais UNIQUEMENT si cette réservation
    n'a jamais été marquée complétée (completed_at IS NULL, voir
    mark_stripe_event_completed) ET qu'elle date de plus de
    STRIPE_WEBHOOK_CLAIM_TIMEOUT_SECONDS (config.py) : c'est le cas d'un
    process tué (SIGKILL, restart Fly.io) en plein traitement, qui n'a jamais
    pu exécuter le handler ni la libérer via unmark_stripe_event_processed.
    Sans ce mécanisme, l'event resterait bloqué en "duplicate_ignored" pour
    toujours, alors que sa logique métier (ex: activation d'un abonnement
    Stripe) n'a jamais réellement été exécutée. Le WHERE de l'UPDATE reste
    atomique (une seule instruction SQL) : si deux requêtes tentent cette
    re-réservation en même temps après expiration du délai, une seule des
    deux UPDATE trouve encore la ligne dans l'état attendu et réussit — même
    garantie qu'à l'INSERT initial, jamais de double exécution du handler."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT OR IGNORE INTO stripe_webhook_events (event_id, event_type, processed_at, completed_at) "
            "VALUES (?, ?, ?, NULL)",
            (event_id, event_type, _now()),
        )
        if cur.rowcount > 0:
            conn.commit()
            return True
        stale_cutoff = (
            datetime.now(timezone.utc) - timedelta(seconds=config.STRIPE_WEBHOOK_CLAIM_TIMEOUT_SECONDS)
        ).isoformat()
        cur = conn.execute(
            "UPDATE stripe_webhook_events SET processed_at = ? "
            "WHERE event_id = ? AND completed_at IS NULL AND processed_at < ?",
            (_now(), event_id, stale_cutoff),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def mark_stripe_event_completed(event_id):
    """Marque la réservation comme terminée avec succès (voir
    stripe_webhook_service.handle_event, appelée juste après un handler qui
    n'a pas levé d'exception) — distingue "traitement en cours/abandonné" de
    "traitement réellement terminé" pour mark_stripe_event_processed
    ci-dessus."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE stripe_webhook_events SET completed_at = ? WHERE event_id = ?", (_now(), event_id)
        )
        conn.commit()
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


def count_security_events_since(event_type, since_iso, until_iso=None):
    """Variante de count_security_events() bornée dans le temps — utilisée
    par admin_subscriptions_service.py pour des compteurs par période
    ("nouveaux abonnés"/"résiliations" sur les 30 derniers jours, par
    exemple), à partir des événements Stripe déjà journalisés par
    stripe_webhook_service.py (stripe_subscription_created/_deleted) : aucune
    nouvelle table, aucune nouvelle écriture, uniquement une lecture bornée
    d'un fait déjà enregistré ailleurs. `until_iso` optionnel (borne
    supérieure, ex: filtre "hier"/"personnalisé" du module Analytics) — les
    appelants existants ne le passent jamais, comportement inchangé."""
    sql = "SELECT COUNT(*) AS n FROM security_events WHERE event_type = ? AND created_at >= ?"
    params = [event_type, since_iso]
    if until_iso is not None:
        sql += " AND created_at < ?"
        params.append(until_iso)
    conn = get_connection()
    try:
        return conn.execute(sql, tuple(params)).fetchone()["n"]
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


def count_conversations_for_user(user_id):
    """Nombre de conversations d'UN compte — distinct de count_conversations()
    ci-dessus (agrégat global). Alimente l'onglet Chatbot de la fiche
    utilisateur admin (voir admin_user_profile_service.py)."""
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT COUNT(*) AS n FROM conversations WHERE user_id = ?", (user_id,)
        ).fetchone()["n"]
    finally:
        conn.close()


def count_messages_for_user(user_id):
    """chatbot_messages n'a pas de user_id direct (voir SCHEMA) — jointure via
    conversations, seule façon de compter les messages d'UN compte."""
    conn = get_connection()
    try:
        return conn.execute(
            """SELECT COUNT(*) AS n FROM chatbot_messages m
               JOIN conversations c ON c.id = m.conversation_id
               WHERE c.user_id = ?""",
            (user_id,),
        ).fetchone()["n"]
    finally:
        conn.close()


def chatbot_engine_breakdown_for_user(user_id):
    """Répartition RÉELLE des réponses assistant d'UN compte par moteur ayant
    effectivement répondu — calculée exclusivement à partir de
    chatbot_messages(engine, provider), jamais depuis ai_request_logs (voir
    conversation_manager.py, chaque db.add_message(role="assistant", ...) y
    renseigne engine/provider). Une réponse locale a engine != "llm" (ou NULL
    pour un message écrit avant ce chantier — non catégorisé, jamais compté
    comme "local" par supposition). Retourne {"local": n, "llm": n,
    "uncategorized": n, "by_bucket": {bucket: n, ...}} où `bucket` est
    "local", "uncategorized" ou le provider LLM réel ("gemini"/"anthropic"/...).
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT m.engine AS engine, m.provider AS provider, COUNT(*) AS n
               FROM chatbot_messages m
               JOIN conversations c ON c.id = m.conversation_id
               WHERE c.user_id = ? AND m.role = 'assistant'
               GROUP BY m.engine, m.provider""",
            (user_id,),
        ).fetchall()
        local_count = 0
        llm_count = 0
        uncategorized_count = 0
        by_bucket = {}
        for row in rows:
            engine, provider, n = row["engine"], row["provider"], row["n"]
            if engine is None:
                uncategorized_count += n
                bucket = "uncategorized"
            elif engine == "llm":
                llm_count += n
                bucket = provider or "llm"
            else:
                local_count += n
                bucket = "local"
            by_bucket[bucket] = by_bucket.get(bucket, 0) + n
        return {
            "local": local_count,
            "llm": llm_count,
            "uncategorized": uncategorized_count,
            "by_bucket": by_bucket,
        }
    finally:
        conn.close()


def chatbot_time_spent_seconds_for_user(user_id):
    """Estimation du temps passé sur le chatbot par UN compte, calculée
    exclusivement à partir des timestamps réels de chatbot_messages/
    conversations (jamais depuis ai_request_logs) : pour chaque conversation,
    durée = dernier message - premier message (une conversation à un seul
    message ne contribue aucune durée, faute de deux points de mesure).
    Retourne 0.0 si l'utilisateur n'a encore aucune conversation avec au moins
    deux messages — jamais None (0 est une valeur réelle ici, pas une donnée
    manquante)."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT MIN(m.created_at) AS first_ts, MAX(m.created_at) AS last_ts, COUNT(*) AS n
               FROM chatbot_messages m
               JOIN conversations c ON c.id = m.conversation_id
               WHERE c.user_id = ?
               GROUP BY m.conversation_id
               HAVING COUNT(*) > 1""",
            (user_id,),
        ).fetchall()
        total_seconds = 0.0
        for row in rows:
            first_ts = datetime.fromisoformat(row["first_ts"])
            last_ts = datetime.fromisoformat(row["last_ts"])
            total_seconds += (last_ts - first_ts).total_seconds()
        return total_seconds
    finally:
        conn.close()


def get_latest_ip_for_user(user_id):
    """Dernière IP connue d'UN compte — security_events est la seule table qui
    lie une IP à un user_id (voir SCHEMA : ni `sessions` ni `login_attempts`
    n'ont de colonne IP). None si aucun événement avec IP n'a jamais été
    journalisé pour ce compte (jamais une IP fabriquée)."""
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT ip, created_at FROM security_events
               WHERE user_id = ? AND ip IS NOT NULL
               ORDER BY created_at DESC LIMIT 1""",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None
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


def get_conversation_learning_context(conversation_id):
    """Current Learning Context de cette conversation (voir
    chatbot/conversation_manager.py) : {chapter_id, notion_id, topic_label,
    updated_at, class_level}, ou None si rien n'a encore été mémorisé
    (conversation neuve, ou aucun sujet précis identifié jusqu'ici).

    `class_level` (chantier "dérive de classe", 2026-08-23) : classe scolaire
    sous laquelle chapter_id/notion_id ont été résolus la dernière fois —
    absente (None) pour tout learning_context écrit avant ce chantier,
    l'appelant doit alors la traiter comme "inconnue" (voir
    conversation_manager._update_learning_context et
    intent_service._detect_chapter), jamais comme une correspondance
    implicite avec la classe courante."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT learning_context FROM conversations WHERE id = ?", (conversation_id,)
        ).fetchone()
    finally:
        conn.close()
    if row is None or not row["learning_context"]:
        return None
    try:
        return json.loads(row["learning_context"])
    except json.JSONDecodeError:
        return None


def set_conversation_learning_context(
    conversation_id, chapter_id, notion_id, topic_label, incomprehension_count=0, approaches_used=None,
    class_level=None, used_exemple_ids=None,
):
    """Mémorise le sujet réellement discuté pour cette conversation — appelé à
    chaque tour où un chapitre/une notion a pu être identifié (fresh ou
    hérité), pour que le prochain message ambigu ("réexplique"...) puisse s'y
    raccrocher plutôt que de retomber sur une recherche floue hasardeuse.

    `incomprehension_count`/`approaches_used` (chantier "escalade
    pédagogique", 2026-08-22) : état pédagogique court terme de CETTE
    conversation — combien de fois l'élève a exprimé une incompréhension sur
    le sujet actuel, et quelles grandes approches (definition/methode/
    exemple/analogie/question_guidee) ont déjà été tentées. Toujours calculé
    par l'appelant (conversation_manager._update_learning_context) — cette
    fonction se contente de persister l'état déjà décidé, jamais de logique
    d'escalade ici.

    `class_level` (chantier "dérive de classe", 2026-08-23) : classe scolaire
    sous laquelle `chapter_id`/`notion_id` ont été résolus CE tour — permet à
    l'appelant, au tour suivant, de détecter qu'un changement de classe active
    a eu lieu depuis et d'invalider l'héritage plutôt que de réutiliser un
    chapter_id résolu sous une autre classe (voir intent_service._detect_
    chapter). Purement informatif ici, aucune logique de comparaison dans
    cette fonction.

    `used_exemple_ids` (chantier "répétition des exemples", 2026-08-23) :
    ids des exemples déjà montrés dans CETTE conversation pour le sujet
    actuel — permet à knowledge_response_composer.compose()/degraded_mode_
    service de les exclure du tirage plutôt que de risquer une répétition
    quasi immédiate. Reset par l'appelant (comme approaches_used) au
    changement de sujet, jamais ici.

    Écrase intégralement l'ancien JSON à chaque appel (le payload complet est
    reconstruit par l'appelant à partir de l'état précédent + de la décision
    de ce tour — voir _update_learning_context pour la logique de reset/
    incrément)."""
    payload = json.dumps({
        "chapter_id": chapter_id, "notion_id": notion_id, "topic_label": topic_label, "updated_at": _now(),
        "incomprehension_count": incomprehension_count, "approaches_used": list(approaches_used or []),
        "class_level": class_level, "used_exemple_ids": list(used_exemple_ids or []),
    })
    conn = get_connection()
    try:
        conn.execute("UPDATE conversations SET learning_context = ? WHERE id = ?", (payload, conversation_id))
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


def add_message(conversation_id, role, content, cards=None, mentions=None, engine=None, provider=None):
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO chatbot_messages (conversation_id, role, content, cards, mentions, engine, provider, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                conversation_id, role, content,
                json.dumps(cards) if cards else None, json.dumps(mentions) if mentions else None,
                engine, provider, _now(),
            ),
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
    """Renvoie True si cet appel a réellement supprimé la ligne, False si elle
    n'existait déjà plus (ex: déjà supprimée par un appel concurrent). DELETE
    par clé primaire est intrinsèquement sérialisé par SQLite/PostgreSQL (un
    seul writer à la fois tient le verrou d'écriture sur cette ligne) : sous
    deux appels concurrents pour le MÊME message_id, un seul peut recevoir
    True — c'est ce que conversation_manager.regenerate_last utilise comme
    "jeton de course" pour garantir qu'une seule des deux requêtes régénère
    réellement une réponse (voir durcissement production : sans ce contrôle,
    deux régénérations concurrentes généraient chacune une réponse assistant
    et décrémentaient chacune le quota, pour une seule intention utilisateur)."""
    conn = get_connection()
    try:
        cur = conn.execute("DELETE FROM chatbot_messages WHERE id = ?", (message_id,))
        conn.commit()
        return cur.rowcount > 0
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


def check_and_record_rate_limit(key, endpoint, window_start, since_window_start, limit):
    """Version atomique de la séquence incrémenter -> lire le total agrégé
    sur la fenêtre glissante -> décrémenter si dépassement, utilisée par
    rate_limit_service.check(). Contrairement à increment_daily_usage/
    record_rate_limit_event (une seule ligne par clé, un UPSERT atomique
    suffit), le rate limiting agrège PLUSIEURS lignes (une par window_start)
    sur la fenêtre : rendre chaque écriture individuelle atomique ne rend pas
    la DÉCISION globale (autorisé/refusé) atomique si les trois étapes
    utilisent des connexions/transactions séparées, comme un audit de
    durcissement production l'a révélé (le passage en mode WAL, qui laisse
    les lecteurs ne plus jamais attendre un writer, a rendu cette fenêtre de
    course inter-requêtes largement plus probable qu'avec le journal SQLite
    par défaut, qui la masquait en pratique en sérialisant plus agressivement
    lecteurs/écrivains).

    Ici, incrément + lecture + décrément compensatoire éventuel se font sur
    LA MÊME connexion, dans LA MÊME transaction (un seul commit final) : la
    lecture voit toujours sa propre écriture, et — SQLite comme PostgreSQL —
    aucune autre transaction concurrente sur ce même bucket ne peut
    s'intercaler entre l'INSERT et le commit (verrou d'écriture posé dès le
    premier INSERT, relâché seulement au commit/rollback).

    Renvoie (allowed: bool, total: int, oldest: int|None)."""
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO rate_limit_events (key, endpoint, window_start, count) VALUES (?, ?, ?, 1)
               ON CONFLICT(key, endpoint, window_start) DO UPDATE SET count = count + 1""",
            (key, endpoint, window_start),
        )
        row = conn.execute(
            """SELECT COALESCE(SUM(count), 0) AS total, MIN(window_start) AS oldest
               FROM rate_limit_events
               WHERE key = ? AND endpoint = ? AND window_start >= ?""",
            (key, endpoint, since_window_start),
        ).fetchone()
        total, oldest = row["total"], row["oldest"]
        allowed = total <= limit
        if not allowed:
            conn.execute(
                """UPDATE rate_limit_events SET count = count - 1
                   WHERE key = ? AND endpoint = ? AND window_start = ?""",
                (key, endpoint, window_start),
            )
            total -= 1
        conn.commit()
        return allowed, total, oldest
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def claim_daily_backup(date_str):
    """Réserve le droit de déclencher LA sauvegarde automatique de `date_str`
    (format "AAAA-MM-JJ") — même mécanisme que mark_stripe_event_processed :
    INSERT OR IGNORE sur une clé unique (system_settings.key), atomique côté
    SQLite/PostgreSQL. Si plusieurs workers gunicorn vérifient en même temps
    s'il faut sauvegarder aujourd'hui (voir backup_scheduler.py), un seul
    obtient True (celui qui déclenche réellement backup_service.backup_
    database()) ; les autres reçoivent False et n'exécutent rien — aucune
    sauvegarde concurrente possible, sans verrou applicatif explicite.
    Une ligne par jour (négligeable, ~365/an) ; jamais nettoyée automatiquement
    (comme les autres clés system_settings), coût de stockage nul en pratique."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """INSERT OR IGNORE INTO system_settings (key, value, updated_at)
               VALUES (?, ?, ?)""",
            (f"backup_auto_claim_{date_str}", date_str, _now()),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def claim_message_retry(message_id):
    """Réserve le droit de relancer la génération pour le message utilisateur
    `message_id` (voir conversation_manager.retry_last) — même mécanisme que
    claim_daily_backup/mark_stripe_event_processed : INSERT OR IGNORE
    atomique. Contrairement à regenerate_last (qui réutilise l'atomicité
    naturelle d'un DELETE par clé primaire sur le message assistant déjà
    existant, voir delete_message), retry_last n'a encore AUCUN message
    assistant à supprimer — cette réclamation explicite joue le même rôle de
    jeton de course. Toujours accompagnée de release_message_retry_claim en
    cas d'échec de la génération (voir retry_last), pour qu'un vrai nouvel
    essai séquentiel reste possible après un hoquet réseau répété."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """INSERT OR IGNORE INTO system_settings (key, value, updated_at)
               VALUES (?, ?, ?)""",
            (f"chatbot_retry_claim_{message_id}", "1", _now()),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def release_message_retry_claim(message_id):
    """Annule la réservation posée par claim_message_retry — appelée
    uniquement quand la génération n'a produit AUCUN message assistant
    (échec), jamais après un succès (voir retry_last)."""
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM system_settings WHERE key = ?",
            (f"chatbot_retry_claim_{message_id}",),
        )
        conn.commit()
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


# ── Fournisseurs IA configurables (webapp/ai_provider_service.py) ─────────────
# Infrastructure de préparation, non branchée au chatbot — voir SCHEMA
# ci-dessus et la docstring de ai_provider_service.py.
def create_ai_provider(name, provider_key, model_name, enabled=True, priority=0, fallback_provider_id=None,
                        code=None, description=None, badge=None, icon=None, color=None):
    """`code`/`description`/`badge`/`icon`/`color` : métadonnées d'affichage
    pour la future interface d'administration, jamais lues par le chatbot
    (voir docstring de SCHEMA). `code` est un identifiant technique unique
    (index UNIQUE créé par _migrate_ai_provider_metadata_columns) — laisser
    None si non applicable, plusieurs fournisseurs peuvent avoir `code=NULL`
    simultanément (NULL n'est jamais égal à NULL dans une contrainte UNIQUE)."""
    conn = get_connection()
    try:
        now = _now()
        cur = conn.execute(
            """INSERT INTO ai_providers
               (name, provider_key, model_name, enabled, priority, fallback_provider_id,
                code, description, badge, icon, color, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, provider_key, model_name, int(enabled), priority, fallback_provider_id,
             code, description, badge, icon, color, now, now),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def backfill_ai_provider_metadata(provider_key, model_name, code, description, badge, icon, color):
    """Remplit `code`/`description`/`badge`/`icon`/`color` UNIQUEMENT là où ces
    colonnes sont encore NULL, pour tout fournisseur existant qui correspond
    à (`provider_key`, `model_name`) — ne modifie JAMAIS une valeur déjà
    renseignée (COALESCE conserve la valeur existante si non NULL). Permet à
    ai_provider_service.seed_default_providers() de compléter les métadonnées
    d'un fournisseur déjà seedé AVANT l'introduction de ces colonnes, sans
    jamais écraser une valeur déjà personnalisée manuellement."""
    conn = get_connection()
    try:
        conn.execute(
            """UPDATE ai_providers
               SET code = COALESCE(code, ?), description = COALESCE(description, ?),
                   badge = COALESCE(badge, ?), icon = COALESCE(icon, ?), color = COALESCE(color, ?)
               WHERE provider_key = ? AND model_name = ?""",
            (code, description, badge, icon, color, provider_key, model_name),
        )
        conn.commit()
    finally:
        conn.close()


def get_ai_provider(provider_id):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM ai_providers WHERE id = ?", (provider_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_ai_providers(enabled_only=False):
    """Triés par priorité croissante (0 = priorité la plus haute), même
    convention que MODEL_CHAIN_BY_PLAN dans provider_manager.py où le premier
    candidat de la liste est celui essayé en premier."""
    conn = get_connection()
    try:
        if enabled_only:
            rows = conn.execute(
                "SELECT * FROM ai_providers WHERE enabled = 1 ORDER BY priority ASC, id ASC"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM ai_providers ORDER BY priority ASC, id ASC"
            ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def update_ai_provider(provider_id, name, provider_key, model_name, enabled, priority, fallback_provider_id=None,
                        code=None, description=None, badge=None, icon=None, color=None):
    """Remplace l'intégralité des champs modifiables — même convention que le
    reste de db.py (jamais de construction dynamique de requête UPDATE, voir
    set_stripe_subscription/set_user_role)."""
    conn = get_connection()
    try:
        conn.execute(
            """UPDATE ai_providers
               SET name = ?, provider_key = ?, model_name = ?, enabled = ?,
                   priority = ?, fallback_provider_id = ?, code = ?, description = ?,
                   badge = ?, icon = ?, color = ?, updated_at = ?
               WHERE id = ?""",
            (name, provider_key, model_name, int(enabled), priority, fallback_provider_id,
             code, description, badge, icon, color, _now(), provider_id),
        )
        conn.commit()
    finally:
        conn.close()


def set_ai_provider_enabled(provider_id, enabled):
    """Bascule d'activation seule, sans toucher aux autres champs — même
    principe que set_stripe_subscription_status."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE ai_providers SET enabled = ?, updated_at = ? WHERE id = ?",
            (int(enabled), _now(), provider_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_ai_provider(provider_id):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM ai_providers WHERE id = ?", (provider_id,))
        conn.commit()
    finally:
        conn.close()


def create_subscription_ai_mapping(subscription, provider_id):
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO subscription_ai_mapping (subscription, provider_id, created_at) VALUES (?, ?, ?)",
            (subscription, provider_id, _now()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_subscription_ai_mapping(mapping_id):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM subscription_ai_mapping WHERE id = ?", (mapping_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_subscription_ai_mappings(subscription=None):
    """Sans argument : toutes les associations. Avec `subscription` : celles
    d'un seul palier (ex: "premium"), triées par priorité du fournisseur
    associé (join sur ai_providers.priority, même convention que
    list_ai_providers)."""
    conn = get_connection()
    try:
        if subscription is not None:
            rows = conn.execute(
                """SELECT subscription_ai_mapping.*
                   FROM subscription_ai_mapping
                   JOIN ai_providers ON ai_providers.id = subscription_ai_mapping.provider_id
                   WHERE subscription_ai_mapping.subscription = ?
                   ORDER BY ai_providers.priority ASC, subscription_ai_mapping.id ASC""",
                (subscription,),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT subscription_ai_mapping.*
                   FROM subscription_ai_mapping
                   JOIN ai_providers ON ai_providers.id = subscription_ai_mapping.provider_id
                   ORDER BY subscription_ai_mapping.subscription ASC, ai_providers.priority ASC"""
            ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def delete_subscription_ai_mapping(mapping_id):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM subscription_ai_mapping WHERE id = ?", (mapping_id,))
        conn.commit()
    finally:
        conn.close()


# ── Santé des fournisseurs IA configurables (webapp/ai_provider_service.py) ───
# Infrastructure de préparation, non alimentée par aucun appel réel à ce jour
# — voir docstring de ai_provider_health dans SCHEMA.
def create_or_update_ai_provider_health(provider_id, last_success=None, last_failure=None, http_code=None,
                                         latency_ms=None, average_latency=None, total_requests=0,
                                         total_errors=0, success_rate=None, last_error=None):
    """UPSERT unique (même principe que set_cookie_consent) : une seule ligne
    par fournisseur, toujours remplacée intégralement — jamais de mise à jour
    partielle implicite, l'appelant fournit systématiquement l'état complet
    qu'il souhaite enregistrer."""
    conn = get_connection()
    try:
        now = _now()
        conn.execute(
            """INSERT INTO ai_provider_health
               (provider_id, last_success, last_failure, http_code, latency_ms, average_latency,
                total_requests, total_errors, success_rate, last_error, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(provider_id) DO UPDATE SET
                   last_success = excluded.last_success,
                   last_failure = excluded.last_failure,
                   http_code = excluded.http_code,
                   latency_ms = excluded.latency_ms,
                   average_latency = excluded.average_latency,
                   total_requests = excluded.total_requests,
                   total_errors = excluded.total_errors,
                   success_rate = excluded.success_rate,
                   last_error = excluded.last_error,
                   updated_at = excluded.updated_at""",
            (provider_id, last_success, last_failure, http_code, latency_ms, average_latency,
             total_requests, total_errors, success_rate, last_error, now),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM ai_provider_health WHERE provider_id = ?", (provider_id,)
        ).fetchone()
        return dict(row)
    finally:
        conn.close()


def get_ai_provider_health(provider_id):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM ai_provider_health WHERE provider_id = ?", (provider_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_ai_provider_health():
    """Santé de tous les fournisseurs qui en ont une (une ligne par
    fournisseur ayant déjà été enregistrée au moins une fois), triée par
    priorité du fournisseur — même convention que list_ai_providers."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT ai_provider_health.*
               FROM ai_provider_health
               JOIN ai_providers ON ai_providers.id = ai_provider_health.provider_id
               ORDER BY ai_providers.priority ASC"""
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def delete_ai_provider_health(provider_id):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM ai_provider_health WHERE provider_id = ?", (provider_id,))
        conn.commit()
    finally:
        conn.close()


# ── Haute disponibilité IA : clés API multiples par fournisseur ────────────
# Voir docstring de ai_provider_api_keys dans SCHEMA — CRUD + comptabilité
# uniquement, aucune logique de rotation ici (voir ai_provider_key_service.py,
# qui décide QUELLE clé utiliser ; ce module ne fait qu'écrire/lire).
def create_ai_provider_api_key(provider_key, label, api_key_encrypted, priority=0):
    conn = get_connection()
    try:
        now = _now()
        cur = conn.execute(
            """INSERT INTO ai_provider_api_keys
               (provider_key, label, api_key_encrypted, priority, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (provider_key, label, api_key_encrypted, priority, now, now),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_ai_provider_api_key(key_id):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM ai_provider_api_keys WHERE id = ?", (key_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_ai_provider_api_keys(provider_key=None):
    """Toutes les clés (tous fournisseurs) triées par provider_key puis
    priorité, ou uniquement celles de `provider_key` si précisé — utilisé à
    la fois par l'écran d'administration (toutes) et par la rotation (un seul
    fournisseur à la fois, voir ai_provider_key_service.available_keys)."""
    conn = get_connection()
    try:
        if provider_key is not None:
            rows = conn.execute(
                "SELECT * FROM ai_provider_api_keys WHERE provider_key = ? ORDER BY priority ASC, id ASC",
                (provider_key,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM ai_provider_api_keys ORDER BY provider_key ASC, priority ASC, id ASC"
            ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def update_ai_provider_api_key(key_id, **fields):
    """Mise à jour partielle (label/enabled/priority uniquement — jamais
    api_key_encrypted, voir ai_provider_key_service.rotate_key pour changer
    la valeur d'une clé, qui passe par une suppression + recréation plutôt
    qu'une modification en place)."""
    if not fields:
        return
    allowed = {"label", "enabled", "priority"}
    set_clauses = []
    params = []
    for key, value in fields.items():
        if key not in allowed:
            continue
        set_clauses.append(f"{key} = ?")
        params.append(int(value) if key in ("enabled", "priority") else value)
    if not set_clauses:
        return
    set_clauses.append("updated_at = ?")
    params.append(_now())
    params.append(key_id)
    conn = get_connection()
    try:
        conn.execute(f"UPDATE ai_provider_api_keys SET {', '.join(set_clauses)} WHERE id = ?", params)
        conn.commit()
    finally:
        conn.close()


def delete_ai_provider_api_key(key_id):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM ai_provider_api_keys WHERE id = ?", (key_id,))
        conn.commit()
    finally:
        conn.close()


def record_ai_provider_api_key_result(key_id, success, response_time_ms=0, error=None, fallback=False,
                                       quota_exceeded_until=None):
    """Comptabilise UNE tentative réelle sur cette clé (succès ou échec) —
    appelée par ai_provider_key_service après chaque appel LLM utilisant une
    clé de la base (voir llm_fallback_service.generate()). `fallback=True`
    signifie que cet échec a réellement déclenché un passage à la clé/au
    modèle/au fournisseur suivant (distinct d'un échec après une réponse déjà
    partiellement diffusée, qui n'entraîne aucune bascule). Un SUCCÈS efface
    toujours un éventuel cooldown en cours (la clé vient de prouver qu'elle
    fonctionne). Un ÉCHEC ne touche au cooldown que si `quota_exceeded_until`
    est explicitement fourni (ISO) — un échec non lié au quota (timeout,
    5xx...) ne doit jamais effacer par erreur un cooldown déjà posé par un
    échec précédent lié au quota, lui."""
    conn = get_connection()
    try:
        now = _now()
        if success:
            quota_clause, quota_params = "quota_exceeded_until = NULL", []
        elif quota_exceeded_until is not None:
            quota_clause, quota_params = "quota_exceeded_until = ?", [quota_exceeded_until]
        else:
            quota_clause, quota_params = "quota_exceeded_until = quota_exceeded_until", []
        conn.execute(
            f"""UPDATE ai_provider_api_keys SET
                   request_count = request_count + 1,
                   failure_count = failure_count + ?,
                   fallback_count = fallback_count + ?,
                   total_response_time_ms = total_response_time_ms + ?,
                   last_used_at = ?,
                   last_success_at = {'?' if success else 'last_success_at'},
                   last_failure_at = {'?' if not success else 'last_failure_at'},
                   last_error = ?,
                   {quota_clause},
                   updated_at = ?
               WHERE id = ?""",
            [
                0 if success else 1, 1 if fallback else 0, round(response_time_ms), now,
                *([now] if success else []),
                *([now] if not success else []),
                None if success else error,
                *quota_params,
                now, key_id,
            ],
        )
        conn.commit()
    finally:
        conn.close()


def clear_ai_provider_api_key_cooldown(key_id):
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE ai_provider_api_keys SET quota_exceeded_until = NULL, updated_at = ? WHERE id = ?",
            (_now(), key_id),
        )
        conn.commit()
    finally:
        conn.close()


# ── Consommation des fournisseurs IA configurables (webapp/ai_provider_service.py) ─
# Alimentée après CHAQUE appel LLM réel (succès ou échec) — voir docstring de
# ai_provider_usage dans SCHEMA et ai_provider_service.record_llm_usage.
def create_ai_provider_usage(provider_id, date, input_tokens=0, output_tokens=0, total_tokens=0, requests=0,
                              estimated_cost=0, success_count=0, error_count=0, fallback_count=0,
                              response_time_ms=0, error_type=None, error_message=None, error_at=None):
    """INSERT simple (pas un upsert) : lève une erreur d'intégrité si
    (`provider_id`, `date`) existe déjà — voir increment_ai_provider_usage
    pour le cas d'accumulation progressive au fil de la journée, seul usage
    réellement utilisé par le chatbot. `response_time_ms` : durée de CET
    appel, stockée directement dans total_response_time_ms (première ligne
    du jour)."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """INSERT INTO ai_provider_usage
               (provider_id, date, input_tokens, output_tokens, total_tokens, requests, estimated_cost,
                success_count, error_count, fallback_count, total_response_time_ms,
                last_error_type, last_error_message, last_error_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (provider_id, date, input_tokens, output_tokens, total_tokens, requests, estimated_cost,
             success_count, error_count, fallback_count, response_time_ms,
             error_type, error_message, error_at),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def increment_ai_provider_usage(provider_id, date, input_tokens=0, output_tokens=0, total_tokens=0, requests=0,
                                 estimated_cost=0, success_count=0, error_count=0, fallback_count=0,
                                 response_time_ms=0, error_type=None, error_message=None, error_at=None):
    """Incrémente (ou crée) la ligne de consommation de `provider_id`/`date` —
    même principe que quota_service.increment_daily_usage : un seul
    INSERT ... ON CONFLICT DO UPDATE, opération atomique unique, jamais un
    lire-puis-écrire séparé. `response_time_ms` (durée de CET appel, pas une
    moyenne) s'ACCUMULE dans total_response_time_ms — la moyenne se calcule
    à la lecture (total_response_time_ms / requests, voir
    admin_dashboard_service.py), jamais stockée pré-calculée.
    `error_type`/`error_message`/`error_at` : uniquement le dernier échec
    connu, ne remplacent la valeur déjà en base QUE si un nouvel échec est
    passé (COALESCE) — un appel réussi (error_type=None) ne doit jamais
    effacer le souvenir du dernier échec du jour."""
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO ai_provider_usage
               (provider_id, date, input_tokens, output_tokens, total_tokens, requests, estimated_cost,
                success_count, error_count, fallback_count, total_response_time_ms,
                last_error_type, last_error_message, last_error_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(provider_id, date) DO UPDATE SET
                   input_tokens = input_tokens + excluded.input_tokens,
                   output_tokens = output_tokens + excluded.output_tokens,
                   total_tokens = total_tokens + excluded.total_tokens,
                   requests = requests + excluded.requests,
                   estimated_cost = estimated_cost + excluded.estimated_cost,
                   success_count = success_count + excluded.success_count,
                   error_count = error_count + excluded.error_count,
                   fallback_count = fallback_count + excluded.fallback_count,
                   total_response_time_ms = total_response_time_ms + excluded.total_response_time_ms,
                   last_error_type = COALESCE(excluded.last_error_type, last_error_type),
                   last_error_message = COALESCE(excluded.last_error_message, last_error_message),
                   last_error_at = COALESCE(excluded.last_error_at, last_error_at)""",
            (provider_id, date, input_tokens, output_tokens, total_tokens, requests, estimated_cost,
             success_count, error_count, fallback_count, response_time_ms,
             error_type, error_message, error_at),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM ai_provider_usage WHERE provider_id = ? AND date = ?", (provider_id, date)
        ).fetchone()
        return dict(row)
    finally:
        conn.close()


def create_ai_provider_fallback_event(provider_initial, model_initial, provider_final, model_final,
                                      reason, time_lost_ms=0):
    """Enregistre UN événement de fallback réellement déclenché (voir
    docstring de ai_provider_fallback_events dans SCHEMA) — appelé par
    ai_provider_service.record_provider_fallback(), jamais directement par
    le chatbot."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """INSERT INTO ai_provider_fallback_events
               (created_at, provider_initial, model_initial, provider_final, model_final, reason, time_lost_ms)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (_now(), provider_initial, model_initial, provider_final, model_final, reason, time_lost_ms),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def count_ai_provider_fallback_events_since(since_iso, until_iso=None):
    """Nombre d'événements de fallback réels sur une période — utilisé par
    admin_analytics_service.py (KPI "fallbacks" filtrable par période),
    distinct de list_ai_provider_fallback_events (qui renvoie les lignes
    complètes, plafonnées par `limit`, pour un historique/graphique) : ici
    uniquement un COUNT, sans limite arbitraire."""
    sql = "SELECT COUNT(*) AS n FROM ai_provider_fallback_events WHERE created_at >= ?"
    params = [since_iso]
    if until_iso is not None:
        sql += " AND created_at < ?"
        params.append(until_iso)
    conn = get_connection()
    try:
        return conn.execute(sql, tuple(params)).fetchone()["n"]
    finally:
        conn.close()


def list_ai_provider_fallback_events(since_iso=None, limit=200):
    """Événements de fallback réels, du plus récent au plus ancien —
    utilisé uniquement par system_health_service.py (page Santé du système,
    historique des incidents + graphique des fallbacks), jamais par le
    chatbot. `since_iso` : borne inférieure optionnelle sur created_at."""
    conn = get_connection()
    try:
        if since_iso:
            rows = conn.execute(
                """SELECT * FROM ai_provider_fallback_events
                   WHERE created_at >= ? ORDER BY created_at DESC LIMIT ?""",
                (since_iso, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM ai_provider_fallback_events ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


# ── Consommation IA PAR UTILISATEUR (ai_request_logs) ───────────────────────
# Distincte de ai_provider_usage (agrégat global, jamais par utilisateur) —
# voir docstring de ai_request_logs dans SCHEMA. Écrite par
# ai_request_log_service.record(), lue par admin_user_profile_service.py
# (onglet Chatbot de la fiche utilisateur), JAMAIS par le reste du chatbot.
def create_ai_request_log(user_id, conversation_id, provider, model, input_tokens=0, output_tokens=0,
                           total_tokens=0, estimated_cost=0, response_time_ms=0, success=True, fallback=False,
                           engine=None, source=None, estimated=False):
    conn = get_connection()
    try:
        cur = conn.execute(
            """INSERT INTO ai_request_logs
               (user_id, conversation_id, provider, model, input_tokens, output_tokens, total_tokens,
                estimated_cost, response_time_ms, success, fallback, engine, source, estimated, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, conversation_id, provider, model, input_tokens, output_tokens, total_tokens,
             estimated_cost, response_time_ms, int(bool(success)), int(bool(fallback)),
             engine, source, int(bool(estimated)), _now()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def list_ai_request_logs_for_user(user_id, limit=20):
    """Historique des appels IA de CET utilisateur, du plus récent au plus
    ancien — alimente la sous-section "Historique des appels IA" de l'onglet
    Chatbot (voir admin_user_profile_service.get_chatbot())."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT * FROM ai_request_logs WHERE user_id = ? ORDER BY created_at DESC LIMIT ?""",
            (user_id, limit),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def list_ai_request_logs_since(since_iso):
    """Lignes ai_request_logs (TOUS utilisateurs confondus) depuis
    `since_iso` — utilisé uniquement par system_health_service.py pour
    calculer la disponibilité réelle (succès/échecs) et les graphiques de
    requêtes/erreurs/latence de la page Santé du système. Distincte de
    list_ai_request_logs_for_user (qui, elle, reste réservée à un seul
    utilisateur, onglet Chatbot de la fiche utilisateur) : jamais lue par le
    chemin normal du chatbot."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT provider, response_time_ms, success, fallback, created_at
               FROM ai_request_logs WHERE created_at >= ? ORDER BY created_at ASC""",
            (since_iso,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def ai_request_logs_stats_since(since_iso, until_iso=None):
    """Agrégat SQL (COUNT/SUM/AVG en une seule requête, jamais un rapatriement
    de toutes les lignes côté Python) sur ai_request_logs pour une période —
    utilisé par admin_analytics_service.py (KPI "appels IA"/"tokens"/"coût"/
    "latence moyenne"/"taux de succès"). Distincte de list_ai_request_logs_since
    (qui renvoie les lignes brutes, utilisées par system_health_service.py
    pour construire des séries journalières) : ici uniquement les totaux.
    None si aucun appel n'existe sur la période (jamais un 0 fabriqué pour
    une moyenne — AVG SQL sur un ensemble vide renvoie déjà NULL nativement).
    `real_requests`/`estimated_requests` : distinction déjà portée par la
    colonne `estimated` (voir ai_request_log_service.py — 0 = vrai appel LLM
    avec tokens/coût réels, 1 = moteur local/cache, tokens estimés par
    heuristique, coût toujours 0) — jamais mélangés silencieusement dans
    l'interface, voir admin_analytics_service.py."""
    sql = """SELECT COUNT(*) AS requests,
                    SUM(CASE WHEN success THEN 1 ELSE 0 END) AS success_count,
                    SUM(CASE WHEN success THEN 0 ELSE 1 END) AS error_count,
                    SUM(CASE WHEN fallback THEN 1 ELSE 0 END) AS fallback_count,
                    SUM(CASE WHEN estimated THEN 0 ELSE 1 END) AS real_requests,
                    SUM(CASE WHEN estimated THEN 1 ELSE 0 END) AS estimated_requests,
                    SUM(total_tokens) AS total_tokens,
                    SUM(estimated_cost) AS estimated_cost,
                    AVG(response_time_ms) AS avg_response_time_ms
             FROM ai_request_logs WHERE created_at >= ?"""
    params = [since_iso]
    if until_iso is not None:
        sql += " AND created_at < ?"
        params.append(until_iso)
    conn = get_connection()
    try:
        row = conn.execute(sql, tuple(params)).fetchone()
        if not row or not row["requests"]:
            return None
        return dict(row)
    finally:
        conn.close()


def ai_request_log_stats_for_user(user_id):
    """Statistiques agrégées calculées EXCLUSIVEMENT sur ai_request_logs pour
    `user_id` — None si ce compte n'a encore déclenché aucun appel LLM réel
    (jamais un 0 fabriqué, voir admin_user_profile_service.get_chatbot()).
    `most_used_provider` : le fournisseur le plus fréquent dans l'historique
    de CET utilisateur (GROUP BY, pas forcément le fournisseur par défaut du
    plan — un changement de fournisseur/fallback peut faire diverger les
    deux). `last_provider`/`last_model`/`last_used_at` : ligne la plus
    récente, indépendamment du fournisseur le plus fréquent."""
    conn = get_connection()
    try:
        totals = conn.execute(
            """SELECT COUNT(*) AS total_requests, COALESCE(SUM(total_tokens), 0) AS total_tokens,
                      COALESCE(SUM(input_tokens), 0) AS input_tokens, COALESCE(SUM(output_tokens), 0) AS output_tokens,
                      COALESCE(SUM(estimated_cost), 0) AS total_cost, COALESCE(AVG(response_time_ms), 0) AS avg_response_time_ms,
                      COALESCE(SUM(CASE WHEN estimated = 1 THEN total_tokens ELSE 0 END), 0) AS estimated_tokens,
                      COALESCE(SUM(CASE WHEN estimated = 1 THEN 1 ELSE 0 END), 0) AS estimated_requests
               FROM ai_request_logs WHERE user_id = ?""",
            (user_id,),
        ).fetchone()
        if totals["total_requests"] == 0:
            return None

        most_used = conn.execute(
            """SELECT provider, COUNT(*) AS n FROM ai_request_logs WHERE user_id = ?
               GROUP BY provider ORDER BY n DESC LIMIT 1""",
            (user_id,),
        ).fetchone()
        last_row = conn.execute(
            """SELECT provider, model, created_at FROM ai_request_logs WHERE user_id = ?
               ORDER BY created_at DESC LIMIT 1""",
            (user_id,),
        ).fetchone()

        return {
            "total_requests": totals["total_requests"],
            "total_tokens": totals["total_tokens"],
            "input_tokens": totals["input_tokens"],
            "output_tokens": totals["output_tokens"],
            "total_cost": totals["total_cost"],
            "avg_response_time_ms": round(totals["avg_response_time_ms"]),
            "most_used_provider": most_used["provider"],
            "last_provider": last_row["provider"],
            "last_model": last_row["model"],
            "last_used_at": last_row["created_at"],
            # Transparence réel/estimé (voir _AI_REQUEST_LOG_ENGINE_COLUMNS) :
            # le total ci-dessus mélange tokens réels (Gemini/Claude) et
            # tokens estimés (moteur local, aucun appel API réel) — jamais
            # présenté comme une seule et même donnée facturée sans distinction.
            "estimated_tokens": totals["estimated_tokens"],
            "real_tokens": totals["total_tokens"] - totals["estimated_tokens"],
            "estimated_requests": totals["estimated_requests"],
            "real_requests": totals["total_requests"] - totals["estimated_requests"],
        }
    finally:
        conn.close()


def ai_request_log_source_breakdown_for_user(user_id):
    """Répartition RÉELLE des requêtes IA de `user_id` par `source`
    ("local"/"gemini"/"anthropic"/"cache"/"clarification"/...) — alimente
    "Répartition par moteur" de la Consommation IA (voir
    admin_user_profile_service.get_chatbot()). Une ligne écrite avant ce
    chantier a `source` NULL (c'était systématiquement un vrai appel LLM,
    voir _AI_REQUEST_LOG_ENGINE_COLUMNS) — bucketée à part sous
    "uncategorized", jamais requalifiée par supposition. Retourne
    {bucket: {"requests": n, "tokens": n, "cost": n}, ...}."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT COALESCE(source, 'uncategorized') AS bucket, COUNT(*) AS n,
                      COALESCE(SUM(total_tokens), 0) AS tokens, COALESCE(SUM(estimated_cost), 0) AS cost
               FROM ai_request_logs WHERE user_id = ? GROUP BY bucket ORDER BY n DESC""",
            (user_id,),
        ).fetchall()
        return {
            row["bucket"]: {"requests": row["n"], "tokens": row["tokens"], "cost": row["cost"]}
            for row in rows
        }
    finally:
        conn.close()


def get_ai_provider_usage(provider_id, date):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM ai_provider_usage WHERE provider_id = ? AND date = ?", (provider_id, date)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_ai_provider_usage(provider_id=None):
    """Sans argument : toute la consommation enregistrée, tous fournisseurs
    confondus. Avec `provider_id` : uniquement la sienne. Triée par date
    croissante dans les deux cas."""
    conn = get_connection()
    try:
        if provider_id is not None:
            rows = conn.execute(
                "SELECT * FROM ai_provider_usage WHERE provider_id = ? ORDER BY date ASC", (provider_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM ai_provider_usage ORDER BY provider_id ASC, date ASC"
            ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def update_ai_provider_usage(usage_id, input_tokens, output_tokens, requests, estimated_cost):
    """Remplace l'intégralité des champs numériques d'une ligne existante, par
    id — même convention que update_ai_provider (jamais de construction
    dynamique de requête UPDATE)."""
    conn = get_connection()
    try:
        conn.execute(
            """UPDATE ai_provider_usage
               SET input_tokens = ?, output_tokens = ?, requests = ?, estimated_cost = ?
               WHERE id = ?""",
            (input_tokens, output_tokens, requests, estimated_cost, usage_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_ai_provider_usage(usage_id):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM ai_provider_usage WHERE id = ?", (usage_id,))
        conn.commit()
    finally:
        conn.close()


# ── Journal d'activité IA (lecture/écriture, webapp/admin_ai_log_service.py) ──
# Voir SCHEMA::ai_admin_log pour la justification des choix de modélisation
# (pas de FOREIGN KEY sur provider_id, ON DELETE SET NULL sur admin_user_id,
# admin_name/admin_role/provider_name stockés en clair).
def create_ai_admin_log(admin_user_id, admin_name, admin_role, ip, action, provider_id, provider_name,
                         old_values, new_values, result, error_message):
    """Écrit UNE ligne de journal — un seul INSERT, une seule transaction
    (voir commit() ci-dessous) : jamais d'écriture partielle possible, chaque
    appel produit soit une ligne complète, soit aucune (exception propagée
    par l'appelant si l'INSERT échoue)."""
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO ai_admin_log
               (created_at, admin_user_id, admin_name, admin_role, ip, action,
                provider_id, provider_name, old_values, new_values, result, error_message)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (_now(), admin_user_id, admin_name, admin_role, ip, action,
             provider_id, provider_name, old_values, new_values, result, error_message),
        )
        conn.commit()
    finally:
        conn.close()


def _ai_admin_log_filter_sql(search, admin_user_id, provider_id, action, result, date_from, date_to,
                              provider_name=None):
    """Whitelist stricte : `action`/`result` sont comparés tels quels (déjà
    validés par une whitelist côté admin_ai_log_service.py, jamais une
    colonne/opérateur SQL construit depuis une entrée libre) — même principe
    que _users_admin_filter_sql ci-dessus. `provider_name` (égalité exacte,
    jamais LIKE) : utilisé par le module Abonnements pour l'onglet
    "Historique" d'un plan (voir admin_subscriptions_service.py), qui
    journalise ses actions avec provider_id=NULL/provider_name="Abonnement
    <plan>" — provider_id seul ne peut donc pas filtrer ces entrées."""
    clauses = []
    params = []
    if search:
        clauses.append("(admin_name LIKE ? OR provider_name LIKE ? OR action LIKE ? OR error_message LIKE ?)")
        like = f"%{search}%"
        params.extend([like, like, like, like])
    if admin_user_id is not None:
        clauses.append("admin_user_id = ?")
        params.append(admin_user_id)
    if provider_id is not None:
        clauses.append("provider_id = ?")
        params.append(provider_id)
    if provider_name is not None:
        clauses.append("provider_name = ?")
        params.append(provider_name)
    if action:
        clauses.append("action = ?")
        params.append(action)
    if result:
        clauses.append("result = ?")
        params.append(result)
    if date_from:
        clauses.append("created_at >= ?")
        params.append(date_from)
    if date_to:
        clauses.append("created_at <= ?")
        params.append(date_to)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return where, params


def count_ai_admin_log(search=None, admin_user_id=None, provider_id=None, action=None, result=None,
                        date_from=None, date_to=None, provider_name=None):
    where, params = _ai_admin_log_filter_sql(
        search, admin_user_id, provider_id, action, result, date_from, date_to, provider_name=provider_name,
    )
    conn = get_connection()
    try:
        return conn.execute(f"SELECT COUNT(*) AS n FROM ai_admin_log {where}", params).fetchone()["n"]
    finally:
        conn.close()


def list_ai_admin_log(search=None, admin_user_id=None, provider_id=None, action=None, result=None,
                       date_from=None, date_to=None, limit=25, offset=0, provider_name=None):
    """Toujours triée par `created_at DESC, id DESC` (le plus récent
    d'abord) — un journal se lit chronologiquement à l'envers, jamais un tri
    personnalisable comme la liste des utilisateurs."""
    where, params = _ai_admin_log_filter_sql(
        search, admin_user_id, provider_id, action, result, date_from, date_to, provider_name=provider_name,
    )
    conn = get_connection()
    try:
        rows = conn.execute(
            f"""SELECT * FROM ai_admin_log {where}
                ORDER BY created_at DESC, id DESC
                LIMIT ? OFFSET ?""",
            (*params, limit, offset),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


# Plafond dur pour un export (CSV/JSON) — évite qu'un export sans filtre sur
# une base de plusieurs centaines de milliers de lignes ne charge tout en
# mémoire d'un coup ; largement au-delà de tout usage réel d'un panneau
# d'administration.
_AI_ADMIN_LOG_EXPORT_LIMIT = 10000


def list_ai_admin_log_for_export(search=None, admin_user_id=None, provider_id=None, action=None, result=None,
                                  date_from=None, date_to=None):
    return list_ai_admin_log(
        search=search, admin_user_id=admin_user_id, provider_id=provider_id, action=action, result=result,
        date_from=date_from, date_to=date_to, limit=_AI_ADMIN_LOG_EXPORT_LIMIT, offset=0,
    )


def list_ai_admin_log_distinct_admins():
    """Couples (admin_user_id, admin_name) réellement présents dans le
    journal, pour peupler le filtre "Administrateur" sans jamais lister un
    compte qui n'a encore rien modifié — jamais une requête sur `users`."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT DISTINCT admin_user_id, admin_name FROM ai_admin_log
               WHERE admin_user_id IS NOT NULL ORDER BY admin_name ASC"""
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def list_ai_admin_log_distinct_providers():
    """Couples (provider_id, provider_name) réellement présents dans le
    journal, pour peupler le filtre "Fournisseur" — inclut les fournisseurs
    déjà supprimés (provider_id non NULL mais absent de ai_providers
    aujourd'hui), volontairement : leur historique reste consultable."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT DISTINCT provider_id, provider_name FROM ai_admin_log
               WHERE provider_id IS NOT NULL ORDER BY provider_name ASC"""
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


# ── Catalogue des abonnements (lecture/écriture, webapp/subscription_plan_service.py) ─
# Voir SCHEMA::subscription_plans pour la justification des choix de
# modélisation (clé primaire = plan_service.Plan.value, catalogue non encore
# branché à l'enforcement réel).
def get_subscription_plan(plan):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM subscription_plans WHERE plan = ?", (plan,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_subscription_plans():
    """Triés par `display_order ASC, plan ASC` — ordre d'affichage
    administrable (voir update_subscription_plan), jamais un tri alphabétique
    brut qui ignorerait ce champ."""
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM subscription_plans ORDER BY display_order ASC, plan ASC").fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def create_subscription_plan(plan, name, description, price_amount_cents, currency, duration_label,
                              advantages, limits, quota_daily, quota_monthly, quota_chatbot,
                              display_order, active):
    conn = get_connection()
    try:
        now = _now()
        conn.execute(
            """INSERT INTO subscription_plans
               (plan, name, description, price_amount_cents, currency, duration_label,
                advantages, limits, quota_daily, quota_monthly, quota_chatbot,
                display_order, active, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (plan, name, description, price_amount_cents, currency, duration_label,
             advantages, limits, quota_daily, quota_monthly, quota_chatbot,
             display_order, 1 if active else 0, now, now),
        )
        conn.commit()
    finally:
        conn.close()


def update_subscription_plan(plan, name, description, price_amount_cents, currency, duration_label,
                              advantages, limits, quota_daily, quota_monthly, quota_chatbot,
                              display_order, active):
    conn = get_connection()
    try:
        conn.execute(
            """UPDATE subscription_plans
               SET name = ?, description = ?, price_amount_cents = ?, currency = ?, duration_label = ?,
                   advantages = ?, limits = ?, quota_daily = ?, quota_monthly = ?, quota_chatbot = ?,
                   display_order = ?, active = ?, updated_at = ?
               WHERE plan = ?""",
            (name, description, price_amount_cents, currency, duration_label,
             advantages, limits, quota_daily, quota_monthly, quota_chatbot,
             display_order, 1 if active else 0, _now(), plan),
        )
        conn.commit()
    finally:
        conn.close()


def set_subscription_plan_active(plan, active):
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE subscription_plans SET active = ?, updated_at = ? WHERE plan = ?",
            (1 if active else 0, _now(), plan),
        )
        conn.commit()
    finally:
        conn.close()


# ── Dashboard Administrateur (lecture seule, webapp/admin_dashboard_service.py) ─
# Aucune écriture ici, uniquement des agrégats de lecture sur des tables déjà
# existantes — voir docstring de admin_dashboard_service.py pour la politique
# "aucune donnée inventée" (None plutôt qu'un 0 fabriqué quand la mesure n'a
# structurellement pas de source). `since_iso`/`day_str` : chaînes ISO 8601 UTC,
# même format que `_now()` déjà utilisé dans toutes les colonnes `created_at`/
# `last_login_at` de ce fichier — jamais un objet datetime construit ici.
def count_users():
    conn = get_connection()
    try:
        return conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
    finally:
        conn.close()


def count_users_active_since(since_iso, until_iso=None):
    """Comptage par `last_login_at` — un compte qui ne s'est jamais connecté
    (last_login_at NULL) n'est jamais compté comme actif. `until_iso`
    optionnel (borne supérieure, ex: filtre "hier"/"personnalisé" du module
    Analytics) — les appelants existants ne le passent jamais, comportement
    inchangé."""
    sql = "SELECT COUNT(*) AS n FROM users WHERE last_login_at IS NOT NULL AND last_login_at >= ?"
    params = [since_iso]
    if until_iso is not None:
        sql += " AND last_login_at < ?"
        params.append(until_iso)
    conn = get_connection()
    try:
        return conn.execute(sql, tuple(params)).fetchone()["n"]
    finally:
        conn.close()


def count_users_created_since(since_iso, until_iso=None):
    sql = "SELECT COUNT(*) AS n FROM users WHERE created_at >= ?"
    params = [since_iso]
    if until_iso is not None:
        sql += " AND created_at < ?"
        params.append(until_iso)
    conn = get_connection()
    try:
        return conn.execute(sql, tuple(params)).fetchone()["n"]
    finally:
        conn.close()


def count_conversations_since(since_iso, until_iso=None):
    sql = "SELECT COUNT(*) AS n FROM conversations WHERE created_at >= ?"
    params = [since_iso]
    if until_iso is not None:
        sql += " AND created_at < ?"
        params.append(until_iso)
    conn = get_connection()
    try:
        return conn.execute(sql, tuple(params)).fetchone()["n"]
    finally:
        conn.close()


def count_messages_since(since_iso, until_iso=None):
    sql = "SELECT COUNT(*) AS n FROM chatbot_messages WHERE created_at >= ?"
    params = [since_iso]
    if until_iso is not None:
        sql += " AND created_at < ?"
        params.append(until_iso)
    conn = get_connection()
    try:
        return conn.execute(sql, tuple(params)).fetchone()["n"]
    finally:
        conn.close()


def count_messages_by_role_since(role, since_iso, until_iso=None):
    """Variante de count_messages_since() filtrée par `role` ("user"/
    "assistant", voir SCHEMA chatbot_messages) — utilisée par
    admin_analytics_service.py pour distinguer "messages utilisateur" de
    "réponses assistant", jamais confondus dans un seul total."""
    sql = "SELECT COUNT(*) AS n FROM chatbot_messages WHERE role = ? AND created_at >= ?"
    params = [role, since_iso]
    if until_iso is not None:
        sql += " AND created_at < ?"
        params.append(until_iso)
    conn = get_connection()
    try:
        return conn.execute(sql, tuple(params)).fetchone()["n"]
    finally:
        conn.close()


def average_total_time_s():
    """None si `users` est vide (AVG SQL sur un ensemble vide renvoie déjà NULL
    nativement — traduit ici en None Python, jamais en 0 : l'absence de compte
    n'est pas la même chose qu'une moyenne mesurée à zéro)."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT AVG(total_time_s) AS avg_s FROM users").fetchone()
        return row["avg_s"]
    finally:
        conn.close()


def count_users_with_failed_payment():
    """Nombre de comptes dont l'abonnement Stripe est en échec de paiement
    (`past_due` : premier échec, en cours de nouvelle tentative ; `unpaid` :
    tentatives épuisées) — colonne réelle déjà écrite par
    stripe_webhook_service.py/billing_service.py (voir
    set_stripe_subscription_status), aucune nouvelle collecte. Utilisé par
    l'alerte "paiements en échec" du Dashboard administrateur (voir
    admin_dashboard_service.py) : `count_users_admin(account_status=...)`
    (admin_users_service.py) ne convient pas ici, cette colonne est
    indépendante de `account_status`."""
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT COUNT(*) AS n FROM users WHERE stripe_subscription_status IN ('past_due', 'unpaid')"
        ).fetchone()["n"]
    finally:
        conn.close()


def count_users_pending_parental_consent():
    """Nombre de comptes bloqués en attente de consentement parental
    (`users.account_status = 'pending_parental_consent'`) — utilisé par
    l'alerte du Dashboard administrateur (voir admin_dashboard_service.py).
    `admin_users_service.count_users_admin(account_status=...)` ne convient
    pas ici : sa valeur "suspended" regroupe TOUTE valeur différente de
    'active' (donc aussi 'parental_consent_refused', voir
    _users_admin_filter_sql), jamais cette seule valeur précise."""
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT COUNT(*) AS n FROM users WHERE account_status = 'pending_parental_consent'"
        ).fetchone()["n"]
    finally:
        conn.close()


def count_users_by_plan():
    """{"free": n, "premium": n, "ultra": n, ...} — une clé par valeur de
    `plan` réellement présente en base (jamais une liste fixe de plans
    codée en dur ici, voir plan_service.Plan pour la liste des plans
    valides côté application)."""
    conn = get_connection()
    try:
        rows = conn.execute("SELECT plan, COUNT(*) AS n FROM users GROUP BY plan").fetchall()
        return {row["plan"]: row["n"] for row in rows}
    finally:
        conn.close()


def users_registered_per_day(since_iso, until_iso=None):
    """Une entrée par jour calendaire (UTC, `substr(created_at, 1, 10)` —
    format "YYYY-MM-DD", identique aux `day_str` de quota_service.py) où au
    moins un compte a été créé depuis `since_iso` — un jour sans inscription
    n'a simplement aucune ligne, à l'appelant de compléter les jours manquants
    à 0 s'il construit une série continue (voir admin_dashboard_service.py).
    `until_iso` optionnel (borne supérieure, module Analytics) — comportement
    inchangé pour les appelants existants qui ne le passent pas."""
    sql = "SELECT substr(created_at, 1, 10) AS day, COUNT(*) AS n FROM users WHERE created_at >= ?"
    params = [since_iso]
    if until_iso is not None:
        sql += " AND created_at < ?"
        params.append(until_iso)
    sql += " GROUP BY day ORDER BY day ASC"
    conn = get_connection()
    try:
        rows = conn.execute(sql, tuple(params)).fetchall()
        return [{"date": row["day"], "count": row["n"]} for row in rows]
    finally:
        conn.close()


def users_registered_per_month(since_iso, until_iso=None):
    """Même convention que users_registered_per_day, agrégée par MOIS
    calendaire (`substr(created_at, 1, 7)` — format "YYYY-MM") — utilisée par
    admin_analytics_service.py pour la courbe de croissance mensuelle."""
    sql = "SELECT substr(created_at, 1, 7) AS month, COUNT(*) AS n FROM users WHERE created_at >= ?"
    params = [since_iso]
    if until_iso is not None:
        sql += " AND created_at < ?"
        params.append(until_iso)
    sql += " GROUP BY month ORDER BY month ASC"
    conn = get_connection()
    try:
        rows = conn.execute(sql, tuple(params)).fetchall()
        return [{"date": row["month"], "count": row["n"]} for row in rows]
    finally:
        conn.close()


def users_registered_per_year(since_iso, until_iso=None):
    """Même convention, agrégée par ANNÉE calendaire (`substr(created_at, 1, 4)`)."""
    sql = "SELECT substr(created_at, 1, 4) AS year, COUNT(*) AS n FROM users WHERE created_at >= ?"
    params = [since_iso]
    if until_iso is not None:
        sql += " AND created_at < ?"
        params.append(until_iso)
    sql += " GROUP BY year ORDER BY year ASC"
    conn = get_connection()
    try:
        rows = conn.execute(sql, tuple(params)).fetchall()
        return [{"date": row["year"], "count": row["n"]} for row in rows]
    finally:
        conn.close()


def conversations_created_per_day(since_iso, until_iso=None):
    """Même convention que users_registered_per_day, sur `conversations`."""
    sql = "SELECT substr(created_at, 1, 10) AS day, COUNT(*) AS n FROM conversations WHERE created_at >= ?"
    params = [since_iso]
    if until_iso is not None:
        sql += " AND created_at < ?"
        params.append(until_iso)
    sql += " GROUP BY day ORDER BY day ASC"
    conn = get_connection()
    try:
        rows = conn.execute(sql, tuple(params)).fetchall()
        return [{"date": row["day"], "count": row["n"]} for row in rows]
    finally:
        conn.close()


def ai_provider_usage_per_day(since_iso):
    """Somme de `total_tokens` (compte RÉEL renvoyé par le fournisseur, voir
    ai_provider_service.record_llm_usage) par jour, tous fournisseurs
    confondus, sur `ai_provider_usage`. `date` y est déjà stockée au format
    "YYYY-MM-DD", donc comparée directement à `since_iso` tronqué aux 10
    premiers caractères plutôt qu'un timestamp complet."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT date, SUM(total_tokens) AS n
               FROM ai_provider_usage WHERE date >= ? GROUP BY date ORDER BY date ASC""",
            (since_iso[:10],),
        ).fetchall()
        return [{"date": row["date"], "count": row["n"]} for row in rows]
    finally:
        conn.close()


def ai_provider_requests_per_day(since_iso):
    """Même convention que ai_provider_usage_per_day, sur `requests` (nombre
    total d'appels LLM réels, succès + échecs confondus) plutôt que les
    tokens — alimente le graphique "Évolution quotidienne des requêtes IA"
    (voir admin_dashboard_service.py)."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT date, SUM(requests) AS n
               FROM ai_provider_usage WHERE date >= ? GROUP BY date ORDER BY date ASC""",
            (since_iso[:10],),
        ).fetchall()
        return [{"date": row["date"], "count": row["n"]} for row in rows]
    finally:
        conn.close()


def ai_provider_usage_daily_totals(since_iso, until_iso=None):
    """Un seul agrégat par jour (requêtes/tokens/coût/succès/échecs/
    fallbacks/latence) sur `ai_provider_usage`, tous fournisseurs confondus —
    utilisé par admin_analytics_service.py pour mutualiser TOUS les
    graphiques "IA par jour" (tokens/coût/appels/latence moyenne/taux de
    succès/fallbacks) en une seule requête, plutôt que 6 requêtes séparées.
    100% des appels réels (Gemini/Claude) — ai_provider_usage n'est jamais
    alimentée par le moteur local/cache (voir ai_provider_service.
    record_llm_usage, seul point d'écriture), donc jamais mélangée à une
    estimation."""
    sql = """SELECT date,
                    SUM(requests) AS requests, SUM(total_tokens) AS total_tokens,
                    SUM(estimated_cost) AS estimated_cost, SUM(success_count) AS success_count,
                    SUM(error_count) AS error_count, SUM(fallback_count) AS fallback_count,
                    SUM(total_response_time_ms) AS total_response_time_ms
             FROM ai_provider_usage WHERE date >= ?"""
    params = [since_iso[:10]]
    if until_iso is not None:
        sql += " AND date < ?"
        params.append(until_iso[:10])
    sql += " GROUP BY date ORDER BY date ASC"
    conn = get_connection()
    try:
        rows = conn.execute(sql, tuple(params)).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def ai_provider_usage_by_provider_since(since_iso, until_iso=None):
    """Agrégat par fournisseur configuré (requêtes/tokens/coût), JOIN
    ai_providers pour exposer `name`/`provider_key`/`model_name` — utilisé
    par admin_analytics_service.py pour "Top fournisseurs"/"Top modèles"/
    "Top coûts"/"Top consommation tokens" (mêmes lignes, agrégées deux
    façons différentes côté service : par provider_key pour "fournisseurs",
    par name/model_name pour "modèles" — jamais une seconde requête)."""
    sql = """SELECT ai_providers.id AS provider_id, ai_providers.name AS name,
                    ai_providers.provider_key AS provider_key, ai_providers.model_name AS model_name,
                    SUM(ai_provider_usage.requests) AS requests,
                    SUM(ai_provider_usage.total_tokens) AS total_tokens,
                    SUM(ai_provider_usage.estimated_cost) AS estimated_cost
             FROM ai_provider_usage
             JOIN ai_providers ON ai_providers.id = ai_provider_usage.provider_id
             WHERE ai_provider_usage.date >= ?"""
    params = [since_iso[:10]]
    if until_iso is not None:
        sql += " AND ai_provider_usage.date < ?"
        params.append(until_iso[:10])
    sql += " GROUP BY ai_providers.id ORDER BY total_tokens DESC"
    conn = get_connection()
    try:
        rows = conn.execute(sql, tuple(params)).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def ai_request_logs_by_engine_since(since_iso, until_iso=None):
    """Répartition par `engine` (ai_request_logs.engine — "llm"/"cache"/
    "clarification"/moteur local, voir ai_request_log_service.py) : nombre
    d'appels + tokens — seule source possible pour "Top moteurs" (ai_provider_
    usage ne connaît que le fournisseur, jamais le moteur/engine)."""
    sql = """SELECT COALESCE(engine, 'inconnu') AS engine, COUNT(*) AS requests, SUM(total_tokens) AS total_tokens
             FROM ai_request_logs WHERE created_at >= ?"""
    params = [since_iso]
    if until_iso is not None:
        sql += " AND created_at < ?"
        params.append(until_iso)
    sql += " GROUP BY engine ORDER BY requests DESC"
    conn = get_connection()
    try:
        rows = conn.execute(sql, tuple(params)).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def ai_request_logs_estimated_per_day(since_iso, until_iso=None):
    """Répartition PAR JOUR entre appels réels (estimated=0, vrai LLM
    Gemini/Claude) et appels estimés (estimated=1, moteur local/cache) —
    seule source possible pour distinguer "réponses IA" de "réponses
    locales" au fil du temps (voir docstring de ai_request_logs dans
    SCHEMA) : ai_provider_usage ne couvre QUE les appels réels, elle ne peut
    donc pas servir cette distinction."""
    sql = """SELECT substr(created_at, 1, 10) AS day,
                    SUM(CASE WHEN estimated THEN 0 ELSE 1 END) AS real_count,
                    SUM(CASE WHEN estimated THEN 1 ELSE 0 END) AS estimated_count
             FROM ai_request_logs WHERE created_at >= ?"""
    params = [since_iso]
    if until_iso is not None:
        sql += " AND created_at < ?"
        params.append(until_iso)
    sql += " GROUP BY day ORDER BY day ASC"
    conn = get_connection()
    try:
        rows = conn.execute(sql, tuple(params)).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def ai_request_logs_top_users_since(since_iso, until_iso=None, limit=10):
    """Classement "Top consommateurs IA" — GROUP BY user_id (seule table qui
    rattache un appel IA à un utilisateur précis, voir docstring de
    ai_request_logs dans SCHEMA : ai_provider_usage reste un agrégat GLOBAL
    par fournisseur/jour, jamais par utilisateur)."""
    sql = """SELECT ai_request_logs.user_id AS user_id, users.pseudo AS pseudo,
                    COUNT(*) AS requests, SUM(ai_request_logs.total_tokens) AS total_tokens,
                    SUM(ai_request_logs.estimated_cost) AS estimated_cost
             FROM ai_request_logs
             JOIN users ON users.id = ai_request_logs.user_id
             WHERE ai_request_logs.created_at >= ?"""
    params = [since_iso]
    if until_iso is not None:
        sql += " AND ai_request_logs.created_at < ?"
        params.append(until_iso)
    sql += " GROUP BY ai_request_logs.user_id, users.pseudo ORDER BY total_tokens DESC LIMIT ?"
    params.append(limit)
    conn = get_connection()
    try:
        rows = conn.execute(sql, tuple(params)).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def chatbot_top_users_since(since_iso, until_iso=None, limit=10):
    """Classement "Top utilisateurs du chatbot" (conversations + messages
    utilisateur sur la période) — réutilise le même JOIN conversations/
    chatbot_messages que le reste du fichier, jamais un second modèle de
    jointure inventé."""
    sql = """SELECT conversations.user_id AS user_id, users.pseudo AS pseudo,
                    COUNT(DISTINCT conversations.id) AS conversation_count,
                    COUNT(chatbot_messages.id) AS message_count
             FROM conversations
             JOIN users ON users.id = conversations.user_id
             LEFT JOIN chatbot_messages
                 ON chatbot_messages.conversation_id = conversations.id AND chatbot_messages.role = 'user'
             WHERE conversations.created_at >= ?"""
    params = [since_iso]
    if until_iso is not None:
        sql += " AND conversations.created_at < ?"
        params.append(until_iso)
    sql += " GROUP BY conversations.user_id, users.pseudo ORDER BY message_count DESC LIMIT ?"
    params.append(limit)
    conn = get_connection()
    try:
        rows = conn.execute(sql, tuple(params)).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def messages_created_per_day_by_role(since_iso, until_iso=None):
    """Une entrée par (jour, rôle) — utilisé par admin_analytics_service.py
    pour le graphique "messages utilisateur vs réponses assistant par jour",
    en une seule requête plutôt que deux (une par rôle)."""
    sql = """SELECT substr(created_at, 1, 10) AS day, role, COUNT(*) AS n
             FROM chatbot_messages WHERE created_at >= ?"""
    params = [since_iso]
    if until_iso is not None:
        sql += " AND created_at < ?"
        params.append(until_iso)
    sql += " GROUP BY day, role ORDER BY day ASC"
    conn = get_connection()
    try:
        rows = conn.execute(sql, tuple(params)).fetchall()
        return [{"date": row["day"], "role": row["role"], "count": row["n"]} for row in rows]
    finally:
        conn.close()


def search_conversations_global(query, limit=20):
    """Recherche de conversations PAR TITRE, TOUS utilisateurs confondus —
    distincte de list_conversations(user_id, search) qui, elle, reste scopée
    à un seul utilisateur (fiche utilisateur). Utilisée uniquement par la
    recherche globale du module Analytics."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT conversations.id AS id, conversations.title AS title,
                      conversations.user_id AS user_id, users.pseudo AS pseudo,
                      conversations.created_at AS created_at
               FROM conversations
               JOIN users ON users.id = conversations.user_id
               WHERE conversations.title LIKE ?
               ORDER BY conversations.updated_at DESC LIMIT ?""",
            (f"%{query}%", limit),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def search_messages_global(query, limit=20):
    """Recherche de messages PAR CONTENU, tous utilisateurs confondus — même
    principe que search_conversations_global(), aucun équivalent global
    n'existait (list_conversations(user_id, search) reste scopé à un titre
    de conversation, jamais au contenu d'un message)."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT chatbot_messages.id AS id, chatbot_messages.role AS role,
                      substr(chatbot_messages.content, 1, 140) AS excerpt,
                      chatbot_messages.conversation_id AS conversation_id,
                      conversations.user_id AS user_id, users.pseudo AS pseudo,
                      chatbot_messages.created_at AS created_at
               FROM chatbot_messages
               JOIN conversations ON conversations.id = chatbot_messages.conversation_id
               JOIN users ON users.id = conversations.user_id
               WHERE chatbot_messages.content LIKE ?
               ORDER BY chatbot_messages.created_at DESC LIMIT ?""",
            (f"%{query}%", limit),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


# ── Vues Analytics sauvegardées ("Favoris") ─────────────────────────────────
def create_analytics_saved_view(admin_user_id, name, params_json):
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO analytics_saved_views (admin_user_id, name, params_json, created_at) VALUES (?, ?, ?, ?)",
            (admin_user_id, name, params_json, _now()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def list_analytics_saved_views(admin_user_id):
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM analytics_saved_views WHERE admin_user_id = ? ORDER BY created_at DESC",
            (admin_user_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def delete_analytics_saved_view(admin_user_id, view_id):
    """Supprime uniquement si la vue appartient à `admin_user_id` — jamais un
    admin qui supprime les favoris d'un autre. Renvoie True si une ligne a
    réellement été supprimée."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "DELETE FROM analytics_saved_views WHERE id = ? AND admin_user_id = ?", (view_id, admin_user_id)
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ── Cartes KPI épinglées ("Tableau de bord personnalisé") ───────────────────
def list_pinned_kpis(admin_user_id):
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT kpi_key FROM analytics_pinned_kpis WHERE admin_user_id = ? ORDER BY created_at ASC",
            (admin_user_id,),
        ).fetchall()
        return [row["kpi_key"] for row in rows]
    finally:
        conn.close()


def pin_kpi(admin_user_id, kpi_key):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO analytics_pinned_kpis (admin_user_id, kpi_key, created_at) VALUES (?, ?, ?)",
            (admin_user_id, kpi_key, _now()),
        )
        conn.commit()
    finally:
        conn.close()


def unpin_kpi(admin_user_id, kpi_key):
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM analytics_pinned_kpis WHERE admin_user_id = ? AND kpi_key = ?", (admin_user_id, kpi_key)
        )
        conn.commit()
    finally:
        conn.close()


def search_security_events_global(query, limit=20):
    """Recherche d'événements de sécurité PAR TYPE ou PAR IP — utilisée
    uniquement par la recherche globale du module Analytics."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT * FROM security_events WHERE event_type LIKE ? OR ip LIKE ?
               ORDER BY created_at DESC LIMIT ?""",
            (f"%{query}%", f"%{query}%", limit),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


# ── Gestion des utilisateurs (Administration, lecture seule) ────────────────
# Alimente GET /api/admin/users (voir admin_users_service.py) — jamais utilisé
# ailleurs. `sort_by`/`sort_dir` sont validés par la couche service AVANT
# d'arriver ici (whitelist stricte, voir admin_users_service._SORT_COLUMNS) :
# ce module ne construit la clause ORDER BY qu'à partir de valeurs déjà sûres,
# jamais depuis une chaîne utilisateur brute (pas d'injection SQL possible).
def _users_admin_filter_sql(search, role, plan, account_status, payment_status=None):
    clauses = []
    params = []
    if search:
        clauses.append("(pseudo LIKE ? OR email LIKE ? OR username LIKE ?)")
        like = f"%{search}%"
        params.extend([like, like, like])
    if role:
        clauses.append("role = ?")
        params.append(role)
    if plan:
        clauses.append("plan = ?")
        params.append(plan)
    if account_status:
        # Égalité directe sur la valeur réelle de account_status ('active',
        # 'pending_parental_consent' ou 'parental_consent_refused' — voir
        # admin_users_service._VALID_ACCOUNT_STATUSES) : plus de bucket
        # "suspended" fourre-tout (Chantier Administrateur "Utilisateurs",
        # Phase 2) — l'appelant a déjà validé cette valeur avant d'arriver
        # ici, jamais une chaîne arbitraire injectée dans la clause.
        clauses.append("account_status = ?")
        params.append(account_status)
    if payment_status == "failed":
        # Statut Stripe RÉEL (users.stripe_subscription_status), une donnée
        # totalement distincte de account_status ou de plan — ne JAMAIS les
        # confondre (voir admin_users_service.py). Mêmes deux valeurs que
        # l'alerte "paiements en échec" du Dashboard (admin_dashboard_service.
        # count_users_with_failed_payment), même principe, filtre SQL ici
        # plutôt qu'un COUNT global.
        clauses.append("stripe_subscription_status IN ('past_due', 'unpaid')")
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return where, params


def count_users_admin(search=None, role=None, plan=None, account_status=None, payment_status=None):
    where, params = _users_admin_filter_sql(search, role, plan, account_status, payment_status)
    conn = get_connection()
    try:
        return conn.execute(f"SELECT COUNT(*) AS n FROM users {where}", params).fetchone()["n"]
    finally:
        conn.close()


def list_users_admin(search=None, role=None, plan=None, account_status=None, payment_status=None,
                      sort_by="created_at", sort_dir="DESC", limit=25, offset=0):
    """`sort_by`/`sort_dir` doivent déjà être validés (whitelist) par l'appelant
    — voir la note au-dessus de _users_admin_filter_sql."""
    where, params = _users_admin_filter_sql(search, role, plan, account_status, payment_status)
    conn = get_connection()
    try:
        rows = conn.execute(
            f"""SELECT id, pseudo, email, avatar, role, plan, account_status,
                       last_login_at, created_at, total_time_s
                FROM users {where}
                ORDER BY {sort_by} {sort_dir}, id DESC
                LIMIT ? OFFSET ?""",
            (*params, limit, offset),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def _create_admin_user_indexes(conn):
    """Index de tri/filtre pour la page Gestion des utilisateurs — sans eux,
    chaque tri par colonne ou filtre par rôle/plan/statut sur une base de
    plusieurs milliers de comptes ferait un scan complet de `users` (voir
    list_users_admin ci-dessus). `plan`/`role`/`account_status` sont des
    colonnes ajoutées par ALTER TABLE (absentes du CREATE TABLE users de
    SCHEMA sur une base déjà existante) : ces index ne peuvent donc être
    créés qu'ici, jamais dans SCHEMA (même principe que
    idx_users_stripe_customer_id ci-dessus)."""
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_plan ON users(plan)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_account_status ON users(account_status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_last_login_at ON users(last_login_at)")
    conn.commit()


# ── Module Administration -> Support (support_tickets et tables liées) ─────
# Voir docstring des tables dans SCHEMA. Whitelist stricte des colonnes
# triables/filtrables (même principe que _users_admin_filter_sql) — jamais
# une chaîne du client injectée directement dans la clause SQL.
def _support_tickets_filter_sql(search, status, category, priority, assigned_admin_id):
    clauses = []
    params = []
    if search:
        clauses.append(
            "(support_tickets.subject LIKE ? OR users.pseudo LIKE ? OR users.email LIKE ?)"
        )
        like = f"%{search}%"
        params.extend([like, like, like])
    if status:
        clauses.append("support_tickets.status = ?")
        params.append(status)
    if category:
        clauses.append("support_tickets.category = ?")
        params.append(category)
    if priority:
        clauses.append("support_tickets.priority = ?")
        params.append(priority)
    if assigned_admin_id is not None:
        clauses.append("support_tickets.assigned_admin_id = ?")
        params.append(assigned_admin_id)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return where, params


def count_support_tickets_created_since(since_iso, until_iso=None):
    """Nombre de tickets CRÉÉS sur une période — utilisé par
    admin_analytics_service.py (KPI "tickets" filtrable par période),
    distinct de support_tickets_overview_stats() (qui, elle, renvoie l'état
    ACTUEL ouverts/fermés, non filtrable par période) et de
    count_support_tickets() (filtres recherche/statut/catégorie, sans borne
    de date)."""
    sql = "SELECT COUNT(*) AS n FROM support_tickets WHERE created_at >= ?"
    params = [since_iso]
    if until_iso is not None:
        sql += " AND created_at < ?"
        params.append(until_iso)
    conn = get_connection()
    try:
        return conn.execute(sql, tuple(params)).fetchone()["n"]
    finally:
        conn.close()


def count_support_tickets(search=None, status=None, category=None, priority=None, assigned_admin_id=None):
    where, params = _support_tickets_filter_sql(search, status, category, priority, assigned_admin_id)
    conn = get_connection()
    try:
        return conn.execute(
            f"""SELECT COUNT(*) AS n FROM support_tickets
                JOIN users ON users.id = support_tickets.user_id {where}""",
            params,
        ).fetchone()["n"]
    finally:
        conn.close()


def list_support_tickets_admin(search=None, status=None, category=None, priority=None, assigned_admin_id=None,
                                sort_by="created_at", sort_dir="DESC", limit=25, offset=0):
    """`sort_by`/`sort_dir` déjà validés (whitelist) par l'appelant — voir
    support_service._clean_sort. Jointure users (pour pseudo/email) et
    assigned (admin assigné, alias distinct) — LEFT JOIN pour assigned car un
    ticket peut n'avoir aucun administrateur assigné."""
    where, params = _support_tickets_filter_sql(search, status, category, priority, assigned_admin_id)
    conn = get_connection()
    try:
        rows = conn.execute(
            f"""SELECT support_tickets.*, users.pseudo AS user_pseudo, users.email AS user_email,
                       assigned.pseudo AS assigned_admin_name
                FROM support_tickets
                JOIN users ON users.id = support_tickets.user_id
                LEFT JOIN users AS assigned ON assigned.id = support_tickets.assigned_admin_id
                {where}
                ORDER BY support_tickets.{sort_by} {sort_dir}, support_tickets.id DESC
                LIMIT ? OFFSET ?""",
            (*params, limit, offset),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def create_support_ticket(user_id, subject, category, priority="normale"):
    conn = get_connection()
    try:
        now = _now()
        cur = conn.execute(
            """INSERT INTO support_tickets
               (user_id, subject, category, priority, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, 'open', ?, ?)""",
            (user_id, subject, category, priority, now, now),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_support_ticket(ticket_id):
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT support_tickets.*, users.pseudo AS user_pseudo, users.email AS user_email,
                      assigned.pseudo AS assigned_admin_name
               FROM support_tickets
               JOIN users ON users.id = support_tickets.user_id
               LEFT JOIN users AS assigned ON assigned.id = support_tickets.assigned_admin_id
               WHERE support_tickets.id = ?""",
            (ticket_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_support_tickets_for_user(user_id):
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM support_tickets WHERE user_id = ? ORDER BY created_at DESC", (user_id,)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def update_support_ticket(ticket_id, **fields):
    """Mise à jour partielle — colonnes whitelistées ici (jamais une colonne
    arbitraire construite depuis l'appelant)."""
    allowed = {
        "status", "priority", "category", "assigned_admin_id", "closed_at",
        "first_admin_response_at", "last_response_at", "satisfaction_rating",
    }
    set_clauses = []
    params = []
    for key, value in fields.items():
        if key not in allowed:
            continue
        set_clauses.append(f"{key} = ?")
        params.append(value)
    if not set_clauses:
        return
    set_clauses.append("updated_at = ?")
    params.append(_now())
    params.append(ticket_id)
    conn = get_connection()
    try:
        conn.execute(f"UPDATE support_tickets SET {', '.join(set_clauses)} WHERE id = ?", params)
        conn.commit()
    finally:
        conn.close()


def create_support_ticket_message(ticket_id, author_type, author_id, body):
    conn = get_connection()
    try:
        now = _now()
        cur = conn.execute(
            """INSERT INTO support_ticket_messages (ticket_id, author_type, author_id, body, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (ticket_id, author_type, author_id, body, now),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_support_ticket_message(message_id):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM support_ticket_messages WHERE id = ?", (message_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_support_ticket_messages(ticket_id):
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM support_ticket_messages WHERE ticket_id = ? ORDER BY created_at ASC, id ASC",
            (ticket_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def create_support_ticket_attachment(message_id, original_filename, stored_path, size_bytes, content_type):
    conn = get_connection()
    try:
        now = _now()
        cur = conn.execute(
            """INSERT INTO support_ticket_attachments
               (message_id, original_filename, stored_path, size_bytes, content_type, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (message_id, original_filename, stored_path, size_bytes, content_type, now),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def list_support_ticket_attachments_for_messages(message_ids):
    if not message_ids:
        return []
    conn = get_connection()
    try:
        placeholders = ",".join("?" * len(message_ids))
        rows = conn.execute(
            f"SELECT * FROM support_ticket_attachments WHERE message_id IN ({placeholders})",
            message_ids,
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_support_ticket_attachment(attachment_id):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM support_ticket_attachments WHERE id = ?", (attachment_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def create_support_ticket_note(ticket_id, admin_id, body):
    conn = get_connection()
    try:
        now = _now()
        cur = conn.execute(
            """INSERT INTO support_ticket_notes (ticket_id, admin_id, body, created_at)
               VALUES (?, ?, ?, ?)""",
            (ticket_id, admin_id, body, now),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def list_support_ticket_notes(ticket_id):
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM support_ticket_notes WHERE ticket_id = ? ORDER BY created_at ASC, id ASC",
            (ticket_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def create_support_ticket_history_event(ticket_id, event_type, from_value, to_value, actor_admin_id):
    conn = get_connection()
    try:
        now = _now()
        cur = conn.execute(
            """INSERT INTO support_ticket_history
               (ticket_id, event_type, from_value, to_value, actor_admin_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (ticket_id, event_type, from_value, to_value, actor_admin_id, now),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def list_support_ticket_history(ticket_id):
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM support_ticket_history WHERE ticket_id = ? ORDER BY created_at ASC, id ASC",
            (ticket_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


# ── Statistiques Support (vue d'ensemble + graphiques) ──────────────────────
def support_tickets_overview_stats():
    """Compteurs réels pour les cartes Dashboard/Analytics — jamais un 0
    fabriqué : chaque valeur est un vrai COUNT SQL, calculé à l'instant de
    l'appel (pas de cache).

    Retirés (chantier de simplification du panneau admin) : today_count/
    week_count/month_count et les AVG (réponse/résolution/satisfaction) —
    3 requêtes COUNT + 3 requêtes AVG exécutées à chaque appel pour un
    résultat qu'aucun appelant ne lisait (grep exhaustif de
    admin_analytics_service.py/admin_dashboard_service.py)."""
    conn = get_connection()
    try:
        counts = conn.execute(
            """SELECT
                   SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) AS open_count,
                   SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) AS in_progress_count,
                   SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END) AS closed_count,
                   COUNT(*) AS total_count
               FROM support_tickets"""
        ).fetchone()
        return {
            "open_count": counts["open_count"] or 0,
            "in_progress_count": counts["in_progress_count"] or 0,
            "closed_count": counts["closed_count"] or 0,
            "total_count": counts["total_count"] or 0,
        }
    finally:
        conn.close()


def support_tickets_count_by_category():
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT category, COUNT(*) AS n FROM support_tickets GROUP BY category ORDER BY n DESC"
        ).fetchall()
        return {row["category"]: row["n"] for row in rows}
    finally:
        conn.close()


def support_tickets_count_by_priority():
    """Même convention que support_tickets_count_by_category() — utilisé par
    admin_analytics_service.py (répartition "tickets par priorité"), jamais
    par le module Support lui-même (qui filtre déjà par priorité via
    _support_tickets_filter_sql, sans avoir besoin d'une répartition
    globale)."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT priority, COUNT(*) AS n FROM support_tickets GROUP BY priority ORDER BY n DESC"
        ).fetchall()
        return {row["priority"]: row["n"] for row in rows}
    finally:
        conn.close()


def support_tickets_by_assigned_admin_since(since_iso, until_iso=None):
    """Classement "Top administrateurs" (nombre de tickets assignés créés sur
    la période + temps moyen de résolution des tickets déjà fermés parmi
    eux) — réutilise le même LEFT JOIN users AS assigned que
    list_support_tickets_admin()/count_support_tickets() (voir
    _support_tickets_filter_sql), jamais un second JOIN inventé. Les tickets
    jamais assignés (assigned_admin_id NULL) sont exclus (aucun
    administrateur à classer)."""
    sql = """SELECT support_tickets.assigned_admin_id AS admin_id, assigned.pseudo AS admin_name,
                    COUNT(*) AS ticket_count,
                    AVG(CASE WHEN support_tickets.status = 'closed' AND support_tickets.closed_at IS NOT NULL
                        THEN (julianday(support_tickets.closed_at) - julianday(support_tickets.created_at)) * 86400
                        ELSE NULL END) AS avg_resolution_seconds
             FROM support_tickets
             LEFT JOIN users AS assigned ON assigned.id = support_tickets.assigned_admin_id
             WHERE support_tickets.assigned_admin_id IS NOT NULL AND support_tickets.created_at >= ?"""
    params = [since_iso]
    if until_iso is not None:
        sql += " AND support_tickets.created_at < ?"
        params.append(until_iso)
    sql += " GROUP BY support_tickets.assigned_admin_id, assigned.pseudo ORDER BY ticket_count DESC"
    conn = get_connection()
    try:
        rows = conn.execute(sql, tuple(params)).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def support_tickets_count_by_day(since_iso, until_iso=None):
    sql = """SELECT substr(created_at, 1, 10) AS day, COUNT(*) AS n
             FROM support_tickets WHERE created_at >= ?"""
    params = [since_iso]
    if until_iso is not None:
        sql += " AND created_at < ?"
        params.append(until_iso)
    sql += " GROUP BY day ORDER BY day ASC"
    conn = get_connection()
    try:
        rows = conn.execute(sql, tuple(params)).fetchall()
        return [{"date": row["day"], "count": row["n"]} for row in rows]
    finally:
        conn.close()
