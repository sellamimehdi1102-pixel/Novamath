# Déploiement de Mathadap

Ce document couvre tout ce qui n'est pas déjà dans [README.md](README.md) :
installation détaillée, environnements, Docker, production, variables
d'environnement, procédures de déploiement par plateforme, sauvegardes,
rollback et mise à jour. Architecture applicative inchangée par ce chantier
(ARCH-03/ARCH-05) — uniquement de l'infrastructure ajoutée autour du code
existant.

## Sommaire

- [Installation](#installation)
- [Développement](#développement)
- [Docker](#docker)
- [Base de données : SQLite et PostgreSQL](#base-de-données--sqlite-et-postgresql)
- [Tests End-to-End Stripe](#tests-end-to-end-stripe)
- [Frontend : build, lint et tests](#frontend--build-lint-et-tests)
- [Production](#production)
- [Variables d'environnement](#variables-denvironnement)
- [Déploiement par plateforme](#déploiement-par-plateforme)
- [Sauvegardes](#sauvegardes)
- [Rollback](#rollback)
- [Mise à jour](#mise-à-jour)

## Installation

Prérequis : Python 3.12+ (voir `Dockerfile` pour la version exacte utilisée
en production) et, pour un déploiement conteneurisé, Docker + Docker Compose.

```bash
git clone <url-du-dépôt>
cd "Programation AI"
cp .env.example .env          # puis renseigner les valeurs nécessaires
python -m venv .venv
source .venv/bin/activate     # Windows : .venv\Scripts\activate
pip install -r requirements.txt
python webapp/server.py
```

Le site est servi sur `http://127.0.0.1:5050`. Aucune variable n'est
obligatoire pour démarrer : chaque intégration absente (Stripe, 2FA, Sentry,
OAuth...) se désactive proprement plutôt que de faire planter le serveur
(voir la docstring de chaque service concerné).

## Développement

```bash
python webapp/server.py
```

`FLASK_ENV` non défini => `development` (défaut) : débogueur Werkzeug actif,
cookies non-`Secure` autorisés en HTTP local, `RATE_LIMIT_ENABLED`/`ENABLE_HSTS`
désactivés par défaut. Voir `webapp/config.py` pour la liste complète des
valeurs dérivées de `FLASK_ENV`.

## Docker

Un nouveau développeur peut lancer Mathadap avec **une seule commande** :

```bash
cp .env.example .env   # une seule fois
docker compose up -d --build
```

Ce que fait `docker-compose.yml` :
- construit l'image à partir du `Dockerfile` (multi-étapes, utilisateur
  non-root, Gunicorn — jamais le serveur de développement Flask) ;
- expose le port `8000` (personnalisable via `PORT` dans `.env`, sans
  reconstruire l'image) ;
- persiste `data/` (base SQLite + statistiques utilisateurs) et `backups/`
  dans des **volumes Docker nommés**, qui survivent à `docker compose down`
  et aux reconstructions d'image (contrairement à un bind mount, un volume
  nommé vide hérite du contenu initial de l'image à sa création) ;
- redémarre automatiquement le conteneur (`restart: unless-stopped`) et
  applique la même sonde de santé que Docker (`/api/health`).

Commandes utiles :

```bash
docker compose logs -f web        # logs applicatifs (structurés, voir logging_service.py)
docker compose restart web        # redémarrage sans perte de données
docker compose down               # arrêt (les volumes nommés sont conservés)
docker compose down -v            # arrêt ET suppression des volumes (destructif)
```

Construire/lancer l'image sans Compose :

```bash
docker build -t novamath .
docker run -p 8000:8000 --env-file .env -v novamath-data:/app/data novamath
```

## Base de données : SQLite et PostgreSQL

`webapp/database_service.py` (ARCH-02) détecte automatiquement le moteur à
partir de `DATABASE_URL` — `webapp/db.py` et TOUS les services métiers
(`plan_service`, `quota_service`, `billing_service`, `role_service`,
`rate_limit_service`, `two_factor_service`, ...) continuent d'appeler `db.py`
exactement comme avant, sans aucune connaissance du moteur actif.

### SQLite (par défaut)

`DATABASE_URL` absente ou vide : comportement strictement inchangé — fichier
local `data/novamath.db`, aucune installation supplémentaire. C'est le mode
recommandé pour le développement local et convient à un déploiement
mono-instance de taille modeste (VPS, petit conteneur).

### PostgreSQL (montée en charge)

Positionner `DATABASE_URL=postgresql://UTILISATEUR:MOT_DE_PASSE@HOTE:5432/NOM_BASE`
suffit — aucune autre modification de code ou de configuration nécessaire.
Recommandé dès que plusieurs instances de l'application doivent partager la
même base (plusieurs workers Gunicorn sur des machines différentes,
plateforme sans disque persistant comme Cloud Run — voir
[Évolutions futures](#évolutions-futures)) ou que le volume de données dépasse
ce qu'un fichier SQLite local gère confortablement.

Le pool de connexions (`psycopg_pool.ConnectionPool`) est piloté par
`DATABASE_POOL_SIZE`/`DATABASE_MAX_OVERFLOW`/`DATABASE_POOL_TIMEOUT`/
`DATABASE_POOL_RECYCLE` (voir [Variables d'environnement](#variables-denvironnement)) ;
reconnexion automatique en cas de coupure réseau/redémarrage du serveur
PostgreSQL (gérée nativement par `psycopg_pool`), rollback automatique de
toute transaction restée ouverte avant qu'une connexion ne soit rendue au
pool (voir la docstring de `database_service._PostgresConnection.close()`).

### PostgreSQL avec Docker Compose

```bash
cp .env.example .env
# Éditer .env : DATABASE_URL=postgresql://novamath:novamath@db:5432/novamath
#               (+ POSTGRES_DB/POSTGRES_USER/POSTGRES_PASSWORD si personnalisés)
docker compose --profile postgres up -d --build db   # 1. démarre PostgreSQL
# attendre l'état "healthy" : docker compose ps
docker compose --profile postgres up -d --build       # 2. démarre l'application
```

`docker compose up` (sans `--profile postgres`) ne démarre jamais le service
`db` — le mode SQLite par défaut reste garanti disponible sans PostgreSQL
installé. Les données PostgreSQL sont persistées dans le volume nommé
`novamath-postgres` (survit aux redémarrages/rebuilds, comme
`novamath-data`/`novamath-backups`).

### Différences SQLite / PostgreSQL prises en charge

Toutes gérées automatiquement par `database_service.py`, sans jamais changer
le SQL écrit dans `db.py` :

| Différence | SQLite | PostgreSQL | Traduction |
|---|---|---|---|
| Placeholders | `?` | `%s` | Conversion automatique (avec échappement des `%` littéraux, ex. `LIKE 'x%'`) |
| Clé auto-incrémentée | `INTEGER PRIMARY KEY AUTOINCREMENT` | `SERIAL PRIMARY KEY` | Traduction du schéma au chargement |
| Ignorer un conflit | `INSERT OR IGNORE INTO` | `INSERT INTO ... ON CONFLICT DO NOTHING` | Réécriture automatique |
| Upsert | `INSERT ... ON CONFLICT(...) DO UPDATE SET x = excluded.x` | *(identique)* | Aucune — syntaxe standard supportée nativement par les deux moteurs (SQLite 3.24+, PostgreSQL 9.5+) |
| Id généré par un INSERT | `cursor.lastrowid` | `RETURNING id` | Ajouté automatiquement aux `INSERT` sur les tables auto-incrémentées, capturé et exposé comme `cursor.lastrowid` |
| Script multi-instructions | `Connection.executescript()` | absent de psycopg | Découpage + exécution instruction par instruction |
| Colonne ajoutée à une table existante | capture d'exception (non supporté nativement) | `ADD COLUMN IF NOT EXISTS` | Chemin dédié par moteur dans `database_service.add_column_if_missing()` |
| Type booléen/entier | `INTEGER` (0/1) | `INTEGER` (0/1) | Aucune — le schéma n'utilise jamais le type `BOOLEAN` dédié, `INTEGER` est valide et suffisant sur les deux moteurs |

### Hors périmètre

Les sauvegardes (`webapp/backup_service.py`, protégé, non modifié par
ARCH-02) restent spécifiques à SQLite (copie de fichier). Une base
PostgreSQL doit être sauvegardée avec `pg_dump`/les snapshots gérés du
fournisseur (RDS, Cloud SQL, Neon, Supabase, le service `db` géré de
Railway/Render...) — voir [Évolutions futures](#évolutions-futures).

## Tests End-to-End Stripe

`webapp/tests/test_stripe_e2e.py` (109 tests) appelle réellement l'API
Stripe **Test Mode** — jamais un mock, jamais un objet simulé. Complète
(sans dupliquer) les suites existantes basées sur des mocks
(`test_stripe_service.py`, `test_stripe_webhook_service.py`,
`test_billing_service.py`, `test_server_billing.py`), qui restent la
couverture rapide/hors-ligne de la logique pure.

### Activation

Réutilise exactement les 5 variables Stripe déjà documentées ci-dessus
(aucune variable supplémentaire) : `STRIPE_SECRET_KEY`, `STRIPE_PUBLIC_KEY`,
`STRIPE_PRICE_PREMIUM`, `STRIPE_PRICE_ULTRA`, `STRIPE_WEBHOOK_SECRET`. La
suite se désactive automatiquement (skip, jamais une erreur) si l'une
manque, si `STRIPE_SECRET_KEY` n'est pas une clé Test Mode
(`sk_test_...`), ou si le serveur Stripe n'est pas joignable — voir
`webapp/tests/stripe_e2e_helpers.py::_detect_e2e_availability`.

**Sécurité** : cette suite refuse catégoriquement de s'exécuter avec une clé
`sk_live_`, quelle que soit la configuration — aucune donnée réelle, aucun
paiement réel n'est jamais en jeu.

```bash
# Dashboard Stripe > Developers > API keys (mode Test) :
export STRIPE_SECRET_KEY=sk_test_...
export STRIPE_PUBLIC_KEY=pk_test_...
export STRIPE_PRICE_PREMIUM=price_...   # Price ID Test Mode dédié
export STRIPE_PRICE_ULTRA=price_...     # Price ID Test Mode dédié
export STRIPE_WEBHOOK_SECRET=$(stripe listen --print-secret)

python -m pytest webapp/tests/test_stripe_e2e.py -v
```

### Outils Stripe utilisés

- **Stripe Test Mode** : toutes les ressources créées (clients, abonnements,
  factures) sont réelles côté API, dans l'environnement de test du compte —
  jamais de facturation réelle.
- **Moyens de paiement de test officiels** (jamais un numéro de carte
  inventé) : `pm_card_visa` (succès), `pm_card_chargeDeclined`,
  `pm_card_chargeDeclinedInsufficientFunds`,
  `pm_card_chargeDeclinedExpiredCard` — voir
  [la documentation Stripe sur les tests](https://docs.stripe.com/testing).
- **Test Clocks** (`stripe.test_helpers.TestClock`) : seule méthode
  officiellement recommandée par Stripe pour tester un renouvellement ou une
  expiration de période sans attendre de vrais jours — utilisés dans
  `TestRenouvellementAvecTestClock`.
- **Signature webhook réelle** : `webapp/tests/stripe_e2e_helpers.py`
  construit un en-tête `Stripe-Signature` avec le même algorithme
  HMAC-SHA256 que Stripe CLI/les serveurs Stripe
  (`stripe.WebhookSignature`), à partir d'objets réels déjà obtenus depuis
  l'API — la vérification exercée
  (`stripe_service.construct_webhook_event`) est le code réellement utilisé
  en production.
- **Stripe CLI** (`stripe listen --forward-to localhost:5050/api/checkout/webhook`)
  reste l'outil recommandé pour tester manuellement la livraison HTTP réelle
  d'un webhook en développement — complémentaire à cette suite automatisée,
  qui ne dépend d'aucun process interactif externe pour pouvoir tourner en CI.

### Parcours couverts

Checkout (création + lecture de session), abonnement Premium/Ultra
(paiement accepté), paiement refusé/fonds insuffisants/carte expirée,
nouvelle carte après échec, webhooks (signature valide/falsifiée,
`checkout.session.completed`, `customer.subscription.*`, `invoice.*`,
idempotence), Customer Portal, upgrade Premium→Ultra, downgrade
Ultra→Premium (Subscription Schedule), résiliation immédiate et en fin de
période, facturation (moyen de paiement, factures, montants), renouvellement
via Test Clock, et synchronisation locale complète (`plan_service`,
`quota_service`, `billing_service`) après chaque événement réel.

### CI

`.github/workflows/ci.yml`, job `stripe-e2e-tests` : passe les secrets
GitHub Actions `STRIPE_SECRET_KEY`/`STRIPE_PUBLIC_KEY`/
`STRIPE_PRICE_PREMIUM`/`STRIPE_PRICE_ULTRA`/`STRIPE_WEBHOOK_SECRET` en
variables d'environnement si configurés dans le dépôt (Settings > Secrets
and variables > Actions) — la suite s'exécute alors normalement contre
Stripe Test Mode. **Sans ces secrets, le job reste vert** : chaque test se
désactive proprement (skip), jamais un échec.

## Frontend : build, lint et tests

`webapp/static/js/` (41 modules ES) dispose désormais d'une chaîne d'outils
standard : bundling/minification/cache busting (Vite), lint bloquant
(ESLint), formatage (Prettier) et tests (Vitest + axe-core). Configuration à
la racine du dépôt (`package.json`, `vite.config.js`, `eslint.config.js`,
`.prettierrc`) — le code source (`webapp/static/`) n'a pas été déplacé.

### Analyse préalable (modules morts)

Avant toute mise en place, le graphe d'imports complet de `webapp/static/js/`
a été tracé (imports statiques + `import()` dynamiques) depuis les points
d'entrée réellement chargés par chaque page HTML. Un seul module était
orphelin : `avatar-editor.js` (aucun `<script>`, aucun `import`/`import()`
nulle part dans le code actuel — présent uniquement dans `versions/`,
snapshots archivés d'anciennes versions du produit, jamais dans le code
vivant). Supprimé. Tous les 40 autres modules sont réellement utilisés,
directement ou transitivement.

### Scripts npm

```bash
npm install         # installe les dépendances de dev (jamais en production)
npm run dev          # serveur Vite (rechargement à chaud, sourcemaps natifs)
npm run build        # production : webapp/static-dist/ (voir Cache busting)
npm run preview       # sert webapp/static-dist/ localement pour vérification
npm run lint          # ESLint — bloquant en CI
npm run lint:fix      # corrige automatiquement ce qui peut l'être
npm run format        # Prettier — réécrit JS/HTML/CSS
npm run format:check  # Prettier — bloquant en CI, ne réécrit rien
npm test              # Vitest — bloquant en CI
npm run test:watch    # Vitest en mode watch (développement)
npm run coverage      # Vitest avec rapport de couverture (coverage/frontend/)
```

### Pipeline de build (Vite)

`vite.config.js` : les 11 pages HTML réellement servies (voir
`server.py::PROTECTED_PAGES`/landing) sont les points d'entrée. Le build :

- **Bundling + tree shaking** : Rollup (sous Vite) résout le graphe
  d'imports ES réel, élimine le code/les imports/exports jamais utilisés, et
  factorise automatiquement les modules partagés entre plusieurs pages
  (`api.js`, `icons.js`, `curriculumSelector.js`...) en chunks communs
  (bundle splitting), sans configuration manuelle.
- **Minification** : JS (esbuild) et CSS, activée par défaut.
- **Cache busting automatique** : chaque fichier de sortie est nommé
  `assets/<nom>.<hash-du-contenu>.js`/`.css` ; le HTML de sortie est réécrit
  par Vite pour référencer ces noms — **aucun renommage manuel, jamais**. Un
  changement de contenu change le hash, donc l'URL, donc invalide
  automatiquement le cache navigateur/CDN.
- **Sourcemaps en développement uniquement** : `npm run dev` sert les
  modules ES natifs du navigateur avec sourcemaps implicites ; `npm run
  build` (production) ne génère **aucune** sourcemap (`build.sourcemap:
  false`), pour ne jamais exposer de source non minifiée en production.
- **Lazy loading déjà en place, préservé** : `settings.js` charge
  `pdfExport.js` et `popup.js` via `import()` dynamique (export PDF, popups
  différées) — Vite les découpe automatiquement en chunks séparés, chargés
  uniquement quand nécessaire (comportement déjà présent dans le code
  historique, simplement rendu visible/optimisé par le bundler).
- **Assets non bundlés, copiés à l'identique** : `robots.txt`, `sitemap.xml`
  et `data/` (banques de cours, consommées via des URLs `fetch()` littérales)
  conservent un nom de fichier stable, jamais hashé — voir le plugin
  `novamath-copy-unbundled-assets` dans `vite.config.js`.
- **Compression réseau (gzip/brotli)** : déléguée à la plateforme
  d'hébergement/au reverse proxy devant Gunicorn (comportement déjà celui de
  ce projet pour tous les assets statiques existants — voir
  [Déploiement par plateforme](#déploiement-par-plateforme)) plutôt que
  pré-générée dans l'image ; la minification ci-dessus reste le principal
  levier de réduction de taille appliqué par ce chantier.

`webapp/server.py` sert `webapp/static-dist/` en priorité dès qu'il existe
(sinon repli automatique sur `webapp/static/` inchangé — voir
`_STATIC_FOLDER` dans `server.py`) : aucun autre changement de routage,
aucune modification des services métier.

### Lint (ESLint) et formatage (Prettier)

`eslint.config.js` (config plate ESLint 9) : `no-unused-vars`,
`no-debugger`, `no-console` (autorisé en développement, bloquant en
production via `NODE_ENV=production`), `no-unreachable`,
`no-duplicate-imports`/`import/no-duplicates` (imports dupliqués),
`import/no-unresolved` (imports cassés) — bloquant en CI
(`npm run lint`). `.prettierrc`/`.prettierignore` formatent
JS/HTML/CSS sans jamais toucher au Python (voir `.prettierignore`, Ruff
reste seul responsable du code Python — aucun conflit possible).
`.editorconfig` (déjà existant, inchangé) couvre déjà la même indentation.

### Tests (Vitest)

`webapp/static/js/__tests__/` — 252 tests (objectif minimum : 150),
`environment: jsdom`. Structure :

- **Tests unitaires purs** (`api.js`, `features.js`, `store.js`, `theme.js`,
  `i18n.js`, `icons.js`, `popup.js`, `curriculumSelector.js`,
  `chapterTitleByNotions.js`) : logique métier, gestion d'erreurs, quotas,
  calculs de progression, cache localStorage — sans DOM applicatif complet.
- **Tests d'intégration DOM** (`auth.js`, `sidebar.js`, `abonnement.js`,
  `landing.js`, `chatbot.js`, `settings.js`) : chargent le **vrai** corps
  HTML de la page correspondante (`webapp/static/*.html`, jamais une
  approximation — voir `__tests__/testUtils.js::loadPageBody`), mockent
  uniquement `api.js` (aucun appel réseau réel), et exercent le
  comportement réel (soumission de formulaire, authentification,
  changement de plan/upgrade Stripe, changement de classe, reconnexion du
  chatbot après un fournisseur IA indisponible, etc.).
- **Accessibilité** (`a11y.test.js`) : [axe-core](https://github.com/dequelabs/axe-core)
  (outil standard du secteur) sur les composants générés dynamiquement —
  boutons réels (jamais un `<div onclick>`), `aria-label`/`role=dialog`,
  gestion du focus (`openPromptPopup` déplace le focus sur le champ),
  navigation clavier (Échap ferme les popups, Entrée valide/bascule).
- **Toasts** : Mathadap n'a jamais eu de module `toast.js` dédié — les
  notifications toast vivent dans `api.js` (`handleQuotaExceeded`,
  `handleRateLimited`, réutilisées par tout appel API) et localement dans
  `abonnement.js`/`settings.js`. Couverts dans `api.test.js` et
  `abonnement.test.js`.

Non-régression : `webapp/tests/` (Python) n'est ni modifié ni affecté —
les deux suites sont indépendantes (npm vs pytest), exécutées par des jobs
CI distincts.

## Production

Deux façons équivalentes de lancer Mathadap en production — même code,
même comportement (`FLASK_ENV=production` pilote tout, voir
`webapp/config.py`) :

1. **Conteneur** (recommandé) : voir [Docker](#docker) ci-dessus, avec
   `FLASK_ENV=production` dans `.env`.
2. **Hors conteneur** (VPS) : depuis la racine du projet,
   ```bash
   pip install -r requirements.txt
   FLASK_ENV=production gunicorn -c gunicorn.conf.py webapp.server:app
   ```
   `gunicorn.conf.py` (racine du projet) centralise workers/threads/
   timeouts/logging — chaque valeur est surchargeable par variable
   d'environnement, voir le fichier lui-même pour la documentation complète
   de chaque réglage (`WEB_CONCURRENCY`, `GUNICORN_THREADS`,
   `GUNICORN_TIMEOUT`, `GUNICORN_GRACEFUL_TIMEOUT`, `GUNICORN_KEEPALIVE`,
   `GUNICORN_MAX_REQUESTS`, `GUNICORN_MAX_REQUESTS_JITTER`,
   `GUNICORN_LOGLEVEL`, ...).

En production, placer Mathadap derrière un reverse-proxy TLS (Nginx,
Caddy, Traefik, ou le load balancer géré de la plateforme d'hébergement)
qui transmet l'en-tête `X-Forwarded-Proto: https` — nécessaire pour que
HSTS s'active (voir `webapp/security_headers_service.py::_is_https`, qui
lit cet en-tête faute de middleware `ProxyFix` dans ce projet).

### Environnements

| | `development` (défaut) | `staging` | `production` |
|---|---|---|---|
| `FLASK_ENV` | *(absent)* ou `development` | `production` | `production` |
| Débogueur Werkzeug | activé | désactivé | désactivé |
| Cookies `Secure` | non | oui (HTTPS requis) | oui (HTTPS requis) |
| `RATE_LIMIT_ENABLED` | non | oui | oui |
| `ENABLE_HSTS` | non (jamais) | oui, si HTTPS | oui, si HTTPS |
| Serveur | `python webapp/server.py` | Gunicorn | Gunicorn |
| Base de données | fichier SQLite local | SQLite ou PostgreSQL dédié (recommandé) | SQLite ou PostgreSQL dédié |
| `SENTRY_DSN` | absent (optionnel) | recommandé | recommandé |

Mathadap ne définit pas de troisième valeur `FLASK_ENV=staging` distincte :
un environnement de "staging" est simplement un second déploiement
`FLASK_ENV=production` (mêmes garanties de sécurité), pointant vers ses
propres secrets/base de données/domaine — jamais les mêmes que la
production réelle. C'est une convention de déploiement (deux services
distincts sur la plateforme d'hébergement), pas une variable de code
supplémentaire.

## Variables d'environnement

Référence complète : [.env.example](.env.example) (source de vérité, chaque
variable y est documentée en commentaire). Résumé par catégorie :

| Catégorie | Variables | Obligatoire ? |
|---|---|---|
| Environnement | `FLASK_ENV` | non (défaut `development`) |
| Base de données | `DATABASE_URL`, `DATABASE_POOL_SIZE`, `DATABASE_MAX_OVERFLOW`, `DATABASE_POOL_TIMEOUT`, `DATABASE_POOL_RECYCLE` | non (absente => SQLite, comportement historique) |
| Réseau/Gunicorn | `PORT`, `WEB_CONCURRENCY`, `GUNICORN_THREADS`, `GUNICORN_TIMEOUT`, `GUNICORN_GRACEFUL_TIMEOUT`, `GUNICORN_KEEPALIVE`, `GUNICORN_MAX_REQUESTS`, `GUNICORN_MAX_REQUESTS_JITTER`, `GUNICORN_LOGLEVEL`, `GUNICORN_ACCESSLOG`, `GUNICORN_ERRORLOG`, `GUNICORN_WORKER_CLASS`, `GUNICORN_PRELOAD_APP` | non (valeurs par défaut documentées dans `gunicorn.conf.py`) |
| Secrets applicatifs | `NOVAMATH_SECRET_KEY`, `NOVAMATH_ADMIN_KEY` | non (générés et persistés automatiquement si absents — voir `server.py::_get_or_create_secret`) |
| Cookies | `SESSION_COOKIE_SECURE`, `REMEMBER_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SESSION_COOKIE_SAMESITE` | non (dérivées de `FLASK_ENV`) |
| Paiement | `STRIPE_SECRET_KEY`, `STRIPE_PUBLIC_KEY`, `STRIPE_PRICE_PREMIUM`, `STRIPE_PRICE_ULTRA`, `STRIPE_WEBHOOK_SECRET` | oui pour activer les paiements (sinon 501, reste du site inchangé) |
| OAuth | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | oui pour activer "Connexion avec Google" (sinon 501) |
| 2FA | `TWO_FACTOR_SECRET_KEY`, `TWO_FACTOR_ISSUER` | oui pour activer la 2FA (sinon 501) |
| Rôles | `NOVAMATH_ADMIN_EMAILS` | non |
| Rate limiting | `RATE_LIMIT_ENABLED` | non (dérivée de `FLASK_ENV`) |
| Observabilité | `LOG_LEVEL`, `SENTRY_DSN` | non |
| Sauvegardes | `BACKUP_DIRECTORY`, `BACKUP_RETENTION_DAYS` | non |
| En-têtes de sécurité | `ENABLE_SECURITY_HEADERS`, `CSP_REPORT_ONLY`, `ENABLE_HSTS`, `HSTS_MAX_AGE`, `CSP_ALLOWED_CONNECT`, `CSP_ALLOWED_IMAGES`, `CSP_ALLOWED_FONTS` | non |

Aucune variable "obligatoire" ne fait planter le démarrage si absente :
chaque intégration optionnelle se désactive individuellement (réponse `501`
sur ses seules routes) — philosophie constante du projet, voir
`.env.example`.

## Déploiement par plateforme

Toutes les plateformes ci-dessous utilisent le **même** `Dockerfile`, sans
modification de code. Dans chaque cas : créer/renseigner les variables
d'environnement (section précédente) via l'interface de la plateforme —
jamais dans un fichier committé.

### VPS Linux (sans Docker)

```bash
git clone <url> && cd "Programation AI"
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # éditer : FLASK_ENV=production + secrets
FLASK_ENV=production gunicorn -c gunicorn.conf.py webapp.server:app
```
Superviser avec systemd (redémarrage automatique) et placer Nginx/Caddy en
reverse-proxy TLS devant (voir [Production](#production) pour
`X-Forwarded-Proto`).

### Docker / VPS avec Docker

Voir [Docker](#docker) ci-dessus — `docker compose up -d --build`.

### Railway

`railway.json` (racine) détecte automatiquement le `Dockerfile`. `railway up`
ou connecter le dépôt GitHub depuis le tableau de bord Railway ; `PORT` est
injecté automatiquement (lu dynamiquement par `gunicorn.conf.py`), renseigner
le reste des variables (section précédente) dans l'onglet "Variables".

### Render

`render.yaml` (Blueprint) : "New +" > "Blueprint", pointer ce dépôt. Les
variables marquées `sync: false` dans `render.yaml` doivent être saisies
manuellement dans le tableau de bord après la première création.

### Fly.io

```bash
fly launch --no-deploy   # détecte fly.toml + Dockerfile existants
fly secrets set STRIPE_SECRET_KEY=... TWO_FACTOR_SECRET_KEY=... ...
fly deploy
```

### Coolify

Coolify détecte automatiquement un `Dockerfile` à la racine ("Dockerfile"
comme méthode de build) — connecter le dépôt, renseigner les variables
d'environnement dans l'interface, définir `/api/health` comme health check
HTTP. Aucun fichier de configuration dédié requis.

### Azure App Service (conteneurs)

```bash
az acr build --registry <registre> --image novamath:latest .
az webapp create --resource-group <rg> --plan <plan> --name <nom> \
  --deployment-container-image-name <registre>.azurecr.io/novamath:latest
az webapp config appsettings set --resource-group <rg> --name <nom> \
  --settings FLASK_ENV=production WEBSITES_PORT=8000 ...
```
Azure App Service for Containers injecte le trafic sur le port déclaré via
`WEBSITES_PORT` — cohérent avec `PORT`/`EXPOSE 8000` déjà en place.

### Google Cloud Run

```bash
gcloud builds submit --tag gcr.io/<projet>/novamath
gcloud run deploy novamath \
  --image gcr.io/<projet>/novamath \
  --port 8080 \
  --set-env-vars FLASK_ENV=production
```
Cloud Run injecte `PORT` (généralement `8080`) — déjà lu dynamiquement par
`gunicorn.conf.py`, aucune adaptation de code nécessaire. Le stockage de
`data/`/`backups/` sur Cloud Run doit utiliser un volume Cloud Storage FUSE
ou une base de données externe (Cloud Run est sans état persistant local
entre révisions) — voir [Évolutions futures](#évolutions-futures).

## Sauvegardes

`webapp/backup_service.py` (inchangé par ce chantier) écrit dans
`BACKUP_DIRECTORY` (défaut `backups/`, racine du projet) avec rétention
configurable (`BACKUP_RETENTION_DAYS`, défaut 30 jours). En conteneur, ce
dossier est le volume nommé `novamath-backups` (voir `docker-compose.yml`) —
toujours présent après un `docker compose down` (sans `-v`).

Copier une sauvegarde hors du conteneur :

```bash
docker compose cp web:/app/backups ./backups-local
```

Sur un VPS sans Docker, `backups/` est déjà un répertoire local classique —
sauvegarder avec l'outil habituel de l'hébergeur (snapshot disque, rsync
vers un stockage distant, etc.).

## Rollback

1. **Image Docker** : chaque build peut être tagué explicitement
   (`docker build -t novamath:v1.64 .`) — revenir en arrière consiste à
   redéployer le tag précédent, sans toucher aux volumes de données :
   ```bash
   docker compose stop web
   docker run -d --name novamath-web -p 8000:8000 --env-file .env \
     -v novamath-data:/app/data -v novamath-backups:/app/backups \
     novamath:v1.63   # tag précédent
   ```
2. **Code source** : `versions/vX.YY/` (voir README.md, "Organisation du
   projet") conserve un instantané autonome de `webapp/` à chaque version —
   `git checkout vX.YY` (si taggé) ou restaurer depuis `versions/` reste
   toujours possible indépendamment de Docker.
3. **Base de données** : restaurer la sauvegarde SQLite la plus récente
   antérieure au déploiement problématique (voir
   [Sauvegardes](#sauvegardes)) dans le volume `novamath-data` avant de
   redémarrer le conteneur.

Aucun rollback automatique n'est mis en place par ce chantier (voir
[GitHub Actions](#github-actions-ci) : la CI ne déploie jamais) — c'est une
action manuelle et volontaire, cohérente avec l'exigence "jamais de
déploiement automatique".

## Mise à jour

```bash
git pull
docker compose up -d --build   # reconstruit uniquement ce qui a changé
```

Les volumes nommés (`novamath-data`, `novamath-backups`) ne sont **jamais**
affectés par un rebuild — la mise à jour ne perd aucune donnée. Hors
conteneur (VPS) :

```bash
git pull
pip install -r requirements.txt   # dépendances éventuellement mises à jour
sudo systemctl restart novamath   # ou équivalent selon la supervision choisie
```

## GitHub Actions (CI)

`.github/workflows/ci.yml` s'exécute sur chaque push/pull request vers
`main` : job `frontend` (installation npm, ESLint, Prettier, tests Vitest,
build Vite — tous bloquants, voir
[Frontend : build, lint et tests](#frontend--build-lint-et-tests)), lint
Python (erreurs bloquantes uniquement), vérification des imports des
modules critiques, suite de tests Python complète (`webapp/tests/`), puis
validation que l'image Docker se construit (le build frontend est répété à
l'intérieur du Dockerfile, voir son étape `frontend-builder`). **Aucune
étape ne déploie quoi que ce soit** — ni `docker push`, ni appel à une
plateforme d'hébergement : uniquement une validation avant un déploiement
manuel (voir sections ci-dessus).

## Évolutions futures

- **PostgreSQL** : `docker-compose.yml` réserve un service `db` (désactivé,
  `profiles: ["postgres"]`) prêt à activer le jour où `webapp/db.py`
  supportera `DATABASE_URL` en plus de SQLite — non implémenté aujourd'hui
  (hors périmètre de ce chantier, qui ne modifie aucun code métier).
- **Cloud Run / plateformes sans disque persistant** : nécessitera à terme
  soit PostgreSQL managé (voir ci-dessus), soit un volume réseau (Cloud
  Storage FUSE, EFS...) pour `data/`/`backups/` — les autres plateformes
  listées (VPS, Docker, Railway, Render, Fly.io, Coolify, Azure App
  Service) offrent déjà un disque persistant compatible avec SQLite tel
  quel.
