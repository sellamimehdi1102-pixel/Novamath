# syntax=docker/dockerfile:1
#
# Image de production pour NovaMath — build multi-étapes :
#   1. "builder" compile/installe les dépendances Python (nécessite gcc, absent
#      de l'image finale) ;
#   2. "frontend-builder" exécute le pipeline Vite (npm ci && npm run build,
#      voir vite.config.js) : produit webapp/static-dist/ (JS/CSS minifiés,
#      hashés pour le cache busting, HTML réécrit) — Node.js n'existe QUE dans
#      cette étape, jamais dans l'image finale ;
#   3. "final" ne contient que l'interpréteur Python, les dépendances déjà
#      installées et le code applicatif (y compris static-dist/ déjà construit)
#      — jamais d'outil de compilation ni de Node.js, image aussi légère que
#      possible. server.py sert automatiquement static-dist/ dès qu'il existe
#      (voir webapp/server.py, sinon repli sur static/ inchangé).
#
# Sert TOUJOURS via Gunicorn (gunicorn.conf.py à la racine) — jamais le
# serveur de développement Flask (`app.run()`, utilisé uniquement par
# `python webapp/server.py` en local, voir README.md).
#
# Construction : docker build -t novamath .
# Exécution    : docker run -p 8000:8000 --env-file .env novamath
# (voir docker-compose.yml pour l'usage recommandé avec volumes persistants)

# ── Étape 1 : builder ────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# build-essential : requis pour compiler les extensions C de certaines
# dépendances (cryptography, argon2-cffi, PyMuPDF, numpy/scikit-learn) sur
# les architectures où aucune roue précompilée n'est disponible sur PyPI.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ── Étape 2 : frontend-builder ───────────────────────────────────────────
FROM node:22-slim AS frontend-builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY vite.config.js ./
COPY webapp/static ./webapp/static
RUN npm run build

# ── Étape 3 : image finale ───────────────────────────────────────────────
FROM python:3.12-slim AS final

# curl : seule dépendance système conservée dans l'image finale, utilisée
# uniquement par HEALTHCHECK ci-dessous (interroge /api/health, déjà exposé
# par webapp/health_service.py — aucune route ajoutée pour ce besoin).
# Utilisateur non-root dédié (jamais root en production).
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 --shell /usr/sbin/nologin novamath

WORKDIR /app

# Dépendances déjà installées par l'étape "builder" (pip install --user =>
# ~/.local) — copiées telles quelles, jamais réinstallées ici.
COPY --from=builder /root/.local /home/novamath/.local

ENV PATH=/home/novamath/.local/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PORT=8000

# Code applicatif — voir .dockerignore pour ce qui est volontairement exclu
# (tests, pipeline archivé, sources PDF, snapshots de versions...).
COPY --chown=novamath:novamath . .

# Frontend déjà construit (JS/CSS minifiés + hashés, voir étape
# "frontend-builder" ci-dessus) — remplace/complète webapp/static/ tel quel,
# server.py le détecte et le sert automatiquement en priorité.
COPY --from=frontend-builder --chown=novamath:novamath /app/webapp/static-dist /app/webapp/static-dist

# data/ et backups/ sont écrits au runtime (base SQLite, stats utilisateurs,
# sauvegardes — voir webapp/db.py/backup_service.py) : créés ici avec les
# bons droits pour que l'utilisateur non-root puisse y écrire, même avant
# tout montage de volume (voir docker-compose.yml).
RUN mkdir -p /app/data /app/backups && chown -R novamath:novamath /app/data /app/backups

USER novamath

# Port réellement configurable (voir gunicorn.conf.py, lit $PORT) — cette
# valeur n'est qu'une métadonnée par défaut pour `docker run -P`/documentation,
# elle ne restreint rien.
EXPOSE 8000

# Sonde de santé Docker native — mêmes trois états que /api/health
# (webapp/health_service.py) : le conteneur est marqué "unhealthy" si
# l'application ne répond plus, permettant à l'orchestrateur (Docker
# Compose/Swarm/Kubernetes/PaaS) de le redémarrer automatiquement.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT}/api/health" || exit 1

# Gunicorn — jamais le serveur de développement Flask. `webapp.server:app`
# suppose une exécution depuis la racine du projet (WORKDIR /app), exactement
# comme documenté pour un déploiement hors conteneur (voir README.md).
CMD ["gunicorn", "-c", "gunicorn.conf.py", "webapp.server:app"]
