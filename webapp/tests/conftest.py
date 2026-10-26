"""
Isolation SQLite + fichiers utilisateurs pour pytest (chantier "isolation
SQLite", 2026-10-17) — garantit qu'aucun test automatisé ne peut écrire dans
la vraie base `data/novamath.db` ni dans les vrais dossiers utilisateurs
(`data/user_stats`, `data/user_settings`, `data/user_course_progress`), ni
dans les fichiers auxiliaires réels (`data/.flask_secret_key`,
`data/.admin_key`, `data/reviews.json`, `data/stats_store.json`).

Diagnostic ayant motivé ce fichier (lecture seule, confirmé par exécution) :
43 fichiers de tests font `import server` au niveau module. Pytest importe
TOUS les fichiers de test pendant la collecte, avant qu'aucune fixture ne
puisse s'exécuter — une fixture `conftest.py` classique (basée sur `yield`)
arrive donc trop tard : `server.py` a déjà, à son propre import, appelé
`db.init_db()` (ligne 567) et écrit potentiellement de vraies données dès
qu'un test appelle ensuite `test_client().post("/api/auth/register", ...)`.

Seule une redirection effectuée au NIVEAU MODULE de ce conftest.py (exécuté
par pytest avant la collecte des fichiers test_*.py du même dossier, quel
que soit le sous-ensemble de tests lancé) intervient suffisamment tôt.

Deux mécanismes, les deux nécessaires :

1. Redirection des chemins, AVANT tout import de server.py/auth.py.
   `db.get_connection()` relit `db.DATA_DIR`/`db.DB_PATH` à CHAQUE appel
   (liaison tardive, vérifié par lecture du code) — la redirection de ces
   deux attributs suffit pour toute la couche SQLite de db.py. En revanche
   `auth.py` calcule `USER_STATS_DIR`/`USER_SETTINGS_DIR`/`USER_COURSE_DIR`/
   `LEGACY_STATS_PATH` UNE SEULE FOIS à l'import, à partir de son propre
   `DATA_DIR` indépendant de celui de db.py — ces constantes doivent donc
   être redirigées individuellement. Même chose pour `server.DATA_DIR`/
   `server.REVIEWS_PATH` et `admin_user_profile_service.REVIEWS_PATH`
   (chemins indépendants, eux aussi figés à l'import).

   Cas particulier : `_get_or_create_secret()` (server.py) lit d'abord
   `os.environ.get(...)` et ne touche au disque QUE si absent — positionner
   NOVAMATH_SECRET_KEY/NOVAMATH_ADMIN_KEY avant `import server` évite tout
   accès à `data/.flask_secret_key`/`data/.admin_key` (appelés au niveau
   module de server.py, donc avant qu'un simple patch post-import de
   `server.DATA_DIR` ne puisse les intercepter).

2. Garde-fou global sur `sqlite3.connect()` — ne jamais supposer que la
   redirection des variables suffit à couvrir TOUS les appelants :
   `backup_service.py` appelle `sqlite3.connect()` directement à 3 endroits
   (restauration/vérification de sauvegarde), indépendamment de
   `database_service.py`. Toute tentative de connexion SQLite vers un
   chemin hors du répertoire temporaire alloué échoue immédiatement avec un
   message explicite, plutôt que d'écrire silencieusement dans la vraie
   base — ceci couvre aussi tout futur appelant non encore identifié.

`config.DATABASE_URL` est neutralisée pour la durée du processus pytest
(jamais restaurée, le processus se termine avec pytest) : si une
configuration locale venait à pointer vers une base externe (PostgreSQL),
elle ne doit jamais être utilisée par des tests sans isolation propre à
cette base, hors du périmètre de ce chantier (SQLite uniquement).

Nettoyage : le répertoire temporaire est supprimé en fin de session
(`pytest_sessionfinish` + filet `atexit`), et UNIQUEMENT lui — jamais un
chemin du projet lui-même.

Chantier "sécurisation contre les appels API réels" (2026-10-17) — ajoute
deux protections supplémentaires, indépendantes de l'isolation SQLite
ci-dessus :

A. Neutralisation des clés réelles (ANTHROPIC_API_KEY/GEMINI_API_KEY/
   STRIPE_SECRET_KEY/STRIPE_WEBHOOK_SECRET/STRIPE_PRICE_*), positionnée
   AVANT le premier `import config` de ce fichier : `config.py` les capture
   UNE SEULE FOIS à son import (`STRIPE_SECRET_KEY = os.environ.get(...)`),
   donc toute neutralisation faite après serait trop tardive pour `config`
   (bien qu'elle resterait efficace pour anthropic_provider.py/
   gemini_provider.py, qui relisent `os.environ` à l'instanciation, pas à
   l'import). `load_dotenv()` (appelé par server.py) n'écrase JAMAIS une
   variable déjà présente dans `os.environ` (comportement par défaut,
   confirmé par le commentaire de server.py lui-même) — positionner ces
   variables ICI, avant tout import du projet, les protège donc durablement
   pour tout le processus pytest, quel que soit l'ordre d'import réel.

   Remplacées par un PLACEHOLDER non vide et syntaxiquement plausible,
   jamais une chaîne vide — essai initial (chaîne vide) corrigé après avoir
   cassé 2 tests préexistants : `provider_manager.select_llm_for_user()`
   (chaîne MODEL_CHAIN_BY_PLAN) ne passe au candidat suivant que si
   `has_credentials()` (qui teste SEULEMENT `bool(api_key)`) renvoie False
   pour le candidat courant — une clé vide fait donc basculer TOUS les
   utilisateurs sur "fake" quel que soit leur plan, qui déclenche dans
   llm_fallback_service._stream_chunks() un raccourci "mode dégradé" AVANT
   même d'appeler `provider_manager.get_provider()` — ignorant totalement
   le mock de `get_provider()` posé par test_chantier9_streaming_
   navigation_fix.py/test_chantier6_streaming_fix.py, qui vérifient
   volontairement le comportement réel de sélection/repli des fournisseurs
   (confirmé : échec reproductible, corrigé en repassant à un placeholder
   présent). Une valeur FACTICE mais PRÉSENTE restaure un comportement de
   sélection identique à "avant" (clé réelle = également présente), sans
   jamais exposer la vraie valeur — le garde-fou réseau (B, ci-dessous)
   reste la protection réelle contre un appel effectif, indépendante de la
   présence/absence de la clé.

B. Garde-fou réseau de dernier recours, AU NIVEAU TRANSPORT HTTP plutôt
   qu'au niveau SDK — pour couvrir aussi un test qui contournerait le
   routage habituel (clé passée explicitement en argument, clé chargée
   depuis la base via ai_provider_key_service...). Anthropic ET Gemini
   (google-genai) utilisent tous les deux `httpx` en interne (vérifié :
   `anthropic.Anthropic()._client` est un sous-type direct de
   `httpx.Client`, idem pour `genai.Client()._api_client._httpx_client` —
   aucun des deux ne surcharge `.send()`, le patch de la méthode de base
   suffit). Stripe utilise `requests` par défaut (`stripe._http_client.
   RequestsClient`, confirmé). Patché au niveau `httpx.Client.send`/
   `httpx.AsyncClient.send`/`requests.Session.send` — le point unique par
   lequel passent TOUTES les variantes d'appel de chaque bibliothèque
   (`requests.get`/`.post()` créent une Session éphémère puis appellent
   `.send()` dessus ; `client.get()/.post()/.request()` idem côté httpx).
   Seul l'hôte local (127.0.0.1/localhost/::1, pour Ollama — jamais une API
   payante) reste autorisé ; tout le reste échoue immédiatement avec un
   message explicite. Un test qui mocke directement `requests.post`/
   `stripe_service.stripe`/`provider_manager.get_provider` (déjà la norme
   dans ce projet, voir test_server_oauth_google.py/test_stripe_service.py/
   test_chantier5_llm_budget.py) ne passe jamais par ce garde-fou : le mock
   remplace l'appel avant qu'il n'atteigne la couche transport.
"""
import atexit
import os
import secrets
import shutil
import sqlite3
import tempfile
from pathlib import Path
from urllib.parse import urlparse

# ── -1. Neutraliser les clés API réelles, AVANT tout import du projet ─────
# Placeholder présent (jamais vide) : préserve le comportement de sélection
# existant (has_credentials() reste True) — voir docstring ci-dessus. Le
# préfixe "sk_test_" est volontairement ÉVITÉ pour STRIPE_SECRET_KEY : le
# garde-fou stripe_e2e_helpers.py (tests/test_stripe_e2e.py) n'exécute sa
# suite QUE si la clé commence par "sk_test_" — un placeholder qui ne
# matche jamais ce préfixe la fait skip proprement, sans même atteindre le
# garde-fou réseau (B, ci-dessous), qui reste la protection de secours.
os.environ["ANTHROPIC_API_KEY"] = "sk-ant-neutralized-for-pytest-not-a-real-key"
os.environ["GEMINI_API_KEY"] = "neutralized-for-pytest-not-a-real-key"
os.environ["STRIPE_SECRET_KEY"] = "neutralized_for_pytest_not_a_real_key"
os.environ["STRIPE_WEBHOOK_SECRET"] = "neutralized_for_pytest_not_a_real_whsec"
# OAuth Google (webapp/auth.py::_provider_configured) : si un développeur a
# configuré de VRAIS identifiants Google OAuth en local (.env) pour tester
# manuellement "Se connecter avec Google", ces deux variables restent dans
# os.environ après load_dotenv() et font croire au provider "google" qu'il
# est configuré pendant toute la suite pytest — alors que les tests qui
# appellent /api/auth/google/callback sans session OAuth valide (ni state ni
# code) s'attendent au contraire à un 501 "Fournisseur non configuré"
# (comportement attendu en l'absence de config). Chaîne vide : `bool("")` est
# déjà False, donc _provider_configured() reste False pour toute la session
# pytest, quelle que soit la valeur réelle dans .env local — jamais un vrai
# appel réseau à Google n'est tenté par ces tests.
os.environ["GOOGLE_CLIENT_ID"] = ""
os.environ["GOOGLE_CLIENT_SECRET"] = ""
# Distincts (jamais la même valeur) : des tests comme test_chantier6_
# streaming_fix.py::test_prix_stripe_inchanges vérifient que le bon Price ID
# est résolu PAR PLAN (stripe_service.resolve_price_id) — une valeur unique
# pour les deux rendrait cette distinction impossible à tester, même avec
# un mock correctement posé sur stripe.Price.retrieve.
os.environ["STRIPE_PRICE_PREMIUM"] = "price_neutralized_for_pytest_premium"
os.environ["STRIPE_PRICE_ULTRA"] = "price_neutralized_for_pytest_ultra"

# Cloudflare Web Analytics (Phase 2, cloudflare_analytics_service.py) :
# contrairement aux clés ci-dessus, une chaîne VIDE est volontaire ici, pas
# un placeholder non-vide. Ce service n'a pas de mock SDK/client interne à
# contourner : `is_configured()` (os.environ.get(...) or None) est la SEULE
# garde avant un éventuel `requests.post` réel vers l'API Cloudflare — un
# placeholder non-vide la rendrait "configurée" et déclencherait une
# tentative d'appel réel à chaque test qui exerce une route /api/admin/
# frequentation/*, intercepté au mieux par le garde-fou réseau (B,
# ci-dessous) sous forme d'exception non gérée (donc une 500 au lieu du
# comportement "non configuré" attendu), au pire un vrai appel si jamais ce
# garde-fou venait à changer. Une chaîne vide se lit comme absente
# (`"" or None` → None), donc is_configured() reste False pour toute la
# session pytest, quelle que soit la valeur réelle dans .env local.
os.environ["CLOUDFLARE_API_TOKEN"] = ""
os.environ["CLOUDFLARE_ACCOUNT_TAG"] = ""
os.environ["CLOUDFLARE_SITE_TAG"] = ""

# Répertoire temporaire créé ICI (avant `import config`) : voir la section
# "BACKUP_DIRECTORY" ci-dessous, qui doit elle aussi être neutralisée AVANT
# le premier import de config.py.
_TEST_ROOT = Path(tempfile.mkdtemp(prefix="mathadap_pytest_"))
_TEST_DATA_DIR = _TEST_ROOT / "data"
_TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Chantier "sécurisation des tests contre les appels API réels" (suite,
# 2026-10-17) : `config.BACKUP_DIRECTORY = os.environ.get("BACKUP_DIRECTORY",
# <défaut>)` est capturée à CHAQUE import — y compris un `importlib.
# reload(config)`, utilisé par plusieurs fichiers de tests préexistants pour
# leurs propres besoins (test_backup_service.py/test_logging_service.py/
# test_cookie_security.py...), sans aucun rapport avec ce chantier. Un
# simple réassignement de `config.BACKUP_DIRECTORY` APRÈS l'import (comme
# fait plus bas, conservé en redondance) ne résiste pas à un futur reload :
# confirmé, `test_settings_service.py::test_creation_telechargement_
# restauration_suppression` a tenté d'écrire dans `/app/data/backups` (la
# vraie valeur de `BACKUP_DIRECTORY` en `.env`, le point de montage du
# disque Render) après qu'un AUTRE fichier de test ait rechargé `config` —
# bloqué par le garde-fou SQLite (aucune donnée perdue), mais la bonne
# correction est à la source : neutraliser la VARIABLE D'ENVIRONNEMENT
# elle-même, relue identiquement par `config.py` à chaque import ou reload.
os.environ["BACKUP_DIRECTORY"] = str(_TEST_DATA_DIR / "backups")

import httpx  # noqa: E402
import requests  # noqa: E402

import config  # noqa: E402

# ── 0. Neutraliser toute base externe pour la durée du processus pytest ───
if config.DATABASE_URL:
    config.DATABASE_URL = None

# ── Garde-fou réseau : seul l'hôte local (Ollama) reste joignable ─────────
_ALLOWED_HOSTS = {"127.0.0.1", "localhost", "::1"}


def _host_allowed(host):
    return (host or "").lower() in _ALLOWED_HOSTS


_real_httpx_send = httpx.Client.send
_real_httpx_async_send = httpx.AsyncClient.send
_real_requests_send = requests.Session.send

# Preuve robuste pour les tests de validation : liste des hôtes ayant
# réellement atteint la couche transport (jamais simplement le texte d'une
# exception, qui peut être ré-enveloppée par le SDK appelant — confirmé avec
# le SDK Anthropic, qui intercepte les erreurs de transport génériques,
# retente 2 fois, puis les enveloppe dans son propre message sans jamais
# laisser filtrer "ISOLATION PYTEST"). Vide = aucun appel réel n'a jamais
# atteint `_real_httpx_send`/`_real_requests_send`, quel que soit ce que le
# SDK appelant a fait de l'exception ensuite.
NETWORK_CALLS_PASSED_THROUGH = []


def _guarded_httpx_send(self, request, *args, **kwargs):
    host = request.url.host
    if not _host_allowed(host):
        raise RuntimeError(
            "ISOLATION PYTEST (webapp/tests/conftest.py) : appel réseau réel bloqué "
            f"(httpx) vers l'hôte {host!r} ({request.url}). Les tests ne doivent "
            "jamais appeler un fournisseur IA réel (Anthropic/Gemini) — utilise "
            "FakeProvider ou un mock explicite."
        )
    NETWORK_CALLS_PASSED_THROUGH.append(("httpx", host))
    return _real_httpx_send(self, request, *args, **kwargs)


async def _guarded_httpx_async_send(self, request, *args, **kwargs):
    host = request.url.host
    if not _host_allowed(host):
        raise RuntimeError(
            "ISOLATION PYTEST (webapp/tests/conftest.py) : appel réseau réel bloqué "
            f"(httpx async) vers l'hôte {host!r} ({request.url})."
        )
    NETWORK_CALLS_PASSED_THROUGH.append(("httpx-async", host))
    return await _real_httpx_async_send(self, request, *args, **kwargs)


def _guarded_requests_send(self, request, *args, **kwargs):
    host = urlparse(request.url).hostname
    if not _host_allowed(host):
        raise RuntimeError(
            "ISOLATION PYTEST (webapp/tests/conftest.py) : appel réseau réel bloqué "
            f"(requests) vers l'hôte {host!r} ({request.url}). Les tests ne doivent "
            "jamais appeler Stripe ou une API externe réelle — utilise un mock "
            "explicite (voir test_stripe_service.py)."
        )
    NETWORK_CALLS_PASSED_THROUGH.append(("requests", host))
    return _real_requests_send(self, request, *args, **kwargs)


httpx.Client.send = _guarded_httpx_send
httpx.AsyncClient.send = _guarded_httpx_async_send
requests.Session.send = _guarded_requests_send

# ── 1. Répertoire temporaire dédié, unique par session pytest ─────────────
# (créé plus haut, avant `import config` — voir le commentaire sur
# BACKUP_DIRECTORY ; `_TEST_ROOT`/`_TEST_DATA_DIR` sont déjà définis ici.)

# Chantier "isolation SQLite" (2026-10-17) : plusieurs fichiers de tests
# existants (test_chantier5_llm_budget.py, test_backup_service.py,
# test_database_service.py...) pratiquent déjà, indépendamment, leur PROPRE
# isolation ad hoc par test — `tempfile.mkdtemp()` dans leur `setUp`, un
# répertoire différent de `_TEST_ROOT` à chaque fois, mais lui aussi situé
# sous le dossier temporaire du système. Un garde-fou limité à `_TEST_ROOT`
# rejetterait à tort ces connexions déjà correctement isolées (confirmé par
# échec massif de test_chantier5_llm_budget.py à la validation progressive).
# Le garde-fou autorise donc tout chemin sous le dossier temporaire du
# système (jamais la vraie base, où qu'un test choisisse d'isoler la
# sienne), pas seulement notre propre sous-répertoire.
_SYSTEM_TMP = Path(tempfile.gettempdir()).resolve()


def _is_inside_test_root(path_str):
    if path_str in (":memory:", "", None):
        return True
    try:
        Path(path_str).resolve().relative_to(_SYSTEM_TMP)
        return True
    except (ValueError, OSError):
        return False


# ── 2. Garde-fou global : aucune connexion SQLite hors du répertoire alloué
_real_sqlite_connect = sqlite3.connect


def _guarded_sqlite_connect(database, *args, **kwargs):
    path_str = database if isinstance(database, str) else str(database)
    if not _is_inside_test_root(path_str):
        raise RuntimeError(
            "ISOLATION PYTEST (webapp/tests/conftest.py) : tentative de connexion SQLite "
            f"hors de tout répertoire temporaire ({_SYSTEM_TMP}). Chemin demandé : "
            f"{path_str!r}. Un test a tenté d'utiliser (ou de créer) une base hors de "
            "l'environnement isolé — vérifier que db.DB_PATH/db.DATA_DIR n'ont pas été "
            "réinitialisés vers un chemin réel après l'import de ce conftest."
        )
    return _real_sqlite_connect(database, *args, **kwargs)


sqlite3.connect = _guarded_sqlite_connect

# ── 3. Secrets de test (avant import de server.py — voir docstring) ───────
os.environ["NOVAMATH_SECRET_KEY"] = secrets.token_urlsafe(32)
os.environ["NOVAMATH_ADMIN_KEY"] = secrets.token_urlsafe(32)

# ── 4. Redirection des chemins, AVANT tout import de server.py/auth.py ────
import db  # noqa: E402

db.DATA_DIR = _TEST_DATA_DIR
db.DB_PATH = _TEST_DATA_DIR / "novamath.db"

import auth  # noqa: E402

auth.DATA_DIR = _TEST_DATA_DIR
auth.USER_STATS_DIR = _TEST_DATA_DIR / "user_stats"
auth.USER_SETTINGS_DIR = _TEST_DATA_DIR / "user_settings"
auth.USER_COURSE_DIR = _TEST_DATA_DIR / "user_course_progress"
auth.LEGACY_STATS_PATH = _TEST_DATA_DIR / "stats_store.json"

config.BACKUP_DIRECTORY = str(_TEST_DATA_DIR / "backups")

# `import server` exécute ici son code de niveau module (db.init_db(),
# seeds par défaut, _get_or_create_secret...) — avec les chemins déjà
# redirigés ci-dessus, donc sans toucher aux vrais fichiers.
import server  # noqa: E402

server.DATA_DIR = _TEST_DATA_DIR
server.REVIEWS_PATH = _TEST_DATA_DIR / "reviews.json"

try:
    import admin_user_profile_service  # noqa: E402

    admin_user_profile_service.REVIEWS_PATH = _TEST_DATA_DIR / "reviews.json"
except ImportError:  # pragma: no cover - module toujours présent dans ce projet
    pass


def _cleanup():
    shutil.rmtree(_TEST_ROOT, ignore_errors=True)


def pytest_sessionfinish(session, exitstatus):  # noqa: ARG001
    _cleanup()


atexit.register(_cleanup)
