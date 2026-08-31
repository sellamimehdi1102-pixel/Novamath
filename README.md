# Mathadap

Plateforme intelligente d'apprentissage adaptatif des mathématiques.

Mathadap est une plateforme intelligente d'apprentissage des mathématiques utilisant
l'intelligence artificielle pour adapter les exercices au niveau de chaque élève.

## Démarrage

### Développement

```
python webapp/server.py
```

Le site est servi sur `http://127.0.0.1:5050` (debug activé, cookies non
sécurisés autorisés en HTTP local).

### Docker (recommandé pour tester en local ou déployer)

```
cp .env.example .env
docker compose up -d --build
```

Une seule commande : construit l'image (multi-étapes, utilisateur non-root,
Gunicorn — voir `Dockerfile`), persiste les données dans des volumes nommés
et redémarre automatiquement. Voir [DEPLOYMENT.md](DEPLOYMENT.md) pour le
détail complet (Docker, VPS, Railway, Render, Fly.io, Coolify, Azure App
Service, Google Cloud Run, sauvegardes, rollback, mise à jour).

### Base de données

SQLite par défaut (`data/novamath.db`, aucune installation requise).
PostgreSQL en positionnant `DATABASE_URL` — détecté automatiquement par
`webapp/database_service.py`, sans aucun changement de code ni des services
métiers (`plan_service`, `quota_service`, `billing_service`, `role_service`,
...). Voir [DEPLOYMENT.md](DEPLOYMENT.md#base-de-données--sqlite-et-postgresql)
pour le détail complet, y compris l'usage avec `docker compose --profile postgres`.

### Production

Configuration pilotée par `FLASK_ENV` (voir `.env.example` et
`webapp/config.py`) : `FLASK_ENV=production` désactive le debug et force les
cookies de session/CSRF en `Secure` (HTTPS obligatoire). Lancer avec Gunicorn
depuis la racine du projet (`gunicorn.conf.py` centralise workers/timeouts/
logging, entièrement documenté et pilotable par variables d'environnement) :

```
FLASK_ENV=production gunicorn -c gunicorn.conf.py webapp.server:app
```

Voir [DEPLOYMENT.md](DEPLOYMENT.md) pour la matrice complète des
environnements (développement/staging/production) et la liste de toutes les
variables d'environnement par catégorie.

### Authentification à deux facteurs (2FA)

TOTP (RFC 6238, `webapp/two_factor_service.py`), compatible avec Google
Authenticator, Microsoft Authenticator, Authy, 1Password, Bitwarden — aucun
SMS/email. Nécessite `TWO_FACTOR_SECRET_KEY` (voir `.env.example`), qui
chiffre le secret TOTP stocké en base :

```
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Sans cette variable, la 2FA reste indisponible (réponse 501) mais le reste du
site fonctionne normalement — même philosophie que `STRIPE_SECRET_KEY`.

### En-têtes de sécurité HTTP

`webapp/security_headers_service.py` — Content-Security-Policy (script-src
strict par nonce, jamais `unsafe-eval`), HSTS (production + HTTPS
uniquement, jamais en développement), X-Frame-Options, X-Content-Type-Options,
Referrer-Policy, Permissions-Policy, Cross-Origin-Opener-Policy et
Cross-Origin-Resource-Policy. Piloté par `.env.example`
(`ENABLE_SECURITY_HEADERS`, `CSP_REPORT_ONLY`, `ENABLE_HSTS`, `HSTS_MAX_AGE`,
`CSP_ALLOWED_CONNECT`/`_IMAGES`/`_FONTS`) — aucune valeur codée en dur dans
`server.py`.

## Organisation du projet

Depuis le 2026-07-13, Mathadap n'est plus qu'une application web qui exploite des
banques d'exercices et des modèles déjà finalisés (générés sur une autre machine,
puis copiés dans le projet) — aucun script de génération/entraînement ne tourne
plus ici.

- **Application web** — `webapp/` : le site (backend Flask + frontend statique),
  seule partie éditée en continu. Démarrage : `python webapp/server.py`, servi sur
  `http://127.0.0.1:5050`.
- **Données** — à la racine et dans `data/` : banques d'exercices
  (`exercises_bank*.json`, données définitives), `Programme AI.json`, modèles IA
  (`models/*.pkl`), données runtime (`data/`, base SQLite + stats utilisateurs),
  PDF sources du programme (`Chapitres/`) et leur extraction texte (`texts/`).
- **Outils de maintenance** — `tools/` : scripts encore utiles en production
  (`create_version_snapshot.py` à la racine, `audit_script.py`, `clean_json.py`,
  `regenerate_course_content.py`).
- **Outils de développement (archivés)** — `tools/legacy-pipeline/` : l'ancien
  pipeline de génération d'exercices (extraction PDF, génération LLM, validation,
  simulation de données, entraînement du modèle, naturalisation) — conservé pour
  l'historique, plus utilisé ni référencé par le site (voir son propre README).
- **Versions** — `versions/v{X.YY}/` archive un instantané autonome de `webapp/` à
  chaque version (schéma décimal unifié `vX.YY`, deux chiffres après le point,
  depuis v1.00 — voir `VERSION` à la racine pour la version courante), avec son
  propre `CHANGELOG.md`. Une version archivée n'est jamais modifiée après coup.
  `versions/Lumis_V1` à `Lumis_V6` sont des archives historiques du produit sous
  son nom précédent (Lumis), hors de ce schéma, conservées telles quelles.
- **Documentation** — `README.md`, [DEPLOYMENT.md](DEPLOYMENT.md)
  (installation, Docker, production, variables d'environnement, déploiement
  par plateforme, sauvegardes, rollback, mise à jour), `CHANGELOG.md`
  (dernière version), `TODO.md` (améliorations envisagées), `VERSION`, à la
  racine.
- **Infrastructure de déploiement** (ARCH-03/ARCH-05) — `Dockerfile`
  (multi-étapes — build frontend Node.js, dépendances Python, image finale
  non-root, Gunicorn), `docker-compose.yml`, `gunicorn.conf.py`,
  `.github/workflows/ci.yml` (installation, lint, tests, vérification des
  imports, build frontend, build Docker — ne déploie jamais), et des
  fichiers de configuration optionnels par plateforme (`railway.json`,
  `render.yaml`, `fly.toml`). Détails complets dans
  [DEPLOYMENT.md](DEPLOYMENT.md).
- **Build frontend** — `package.json`, `vite.config.js`, `eslint.config.js`,
  `.prettierrc` (racine du projet) : pipeline de build/lint/tests de
  `webapp/static/js/`, voir "Frontend : build, lint, tests" ci-dessus et
  [DEPLOYMENT.md](DEPLOYMENT.md#frontend--build-lint-et-tests).
- **Base de données** (ARCH-02) — `webapp/database_service.py` : couche
  d'abstraction SQLite/PostgreSQL, seul point d'entrée pour les connexions
  et les transactions ; `webapp/db.py` lui délègue l'ouverture de connexion
  et les migrations de schéma, tout le reste (le SQL métier) est inchangé.

## Frontend : build, lint, tests

`webapp/static/js/` dispose d'une véritable chaîne de build (Vite),
d'un lint bloquant (ESLint) et d'une suite de tests (Vitest) — voir
[DEPLOYMENT.md](DEPLOYMENT.md#frontend--build-lint-et-tests) pour le détail
complet (scripts npm, cache busting, pipeline de build).

```
npm install
npm run dev      # serveur de développement Vite (sourcemaps natifs)
npm run build    # production : webapp/static-dist/ (JS/CSS minifiés et hashés)
npm run lint
npm test
```

## Intégration continue

`.github/workflows/ci.yml` s'exécute sur chaque push/pull request : lint et
tests frontend (npm), lint Python, vérification des imports, suite de tests
Python complète, puis validation que l'image Docker se construit (le build
frontend est intégré au Dockerfile, voir "Frontend : build, lint, tests"
ci-dessus). Ne déploie jamais automatiquement — le déploiement reste une
action manuelle documentée dans [DEPLOYMENT.md](DEPLOYMENT.md).

## Tests End-to-End Stripe

`webapp/tests/test_stripe_e2e.py` — suite dédiée qui appelle réellement
l'API Stripe Test Mode (Checkout, abonnements, upgrade/downgrade,
résiliation, factures, paiements refusés, renouvellement via Test Clocks,
webhooks signés) — **jamais de mock**. Se désactive automatiquement en
l'absence de clés Stripe Test Mode valides. Voir
[DEPLOYMENT.md](DEPLOYMENT.md#tests-end-to-end-stripe) pour la configuration
complète.
