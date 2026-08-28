# NovaMath v1.80

**Date** : 2026-07-20

**Nom de la mise à jour** : OAuth Google réel, audit des intégrations externes, correctifs critiques

## Nouveautés
- OAuth Google entièrement implémenté (`webapp/auth.py`) : échange réel code → token → userinfo, protection CSRF par `state` signé en session, email vérifié par Google exigé. Trois chemins : compte déjà lié (connexion directe), email correspondant à un compte local existant (liaison automatique), email inconnu (nouvelle route `POST /api/auth/<provider>/complete-signup` avec collecte obligatoire de la date de naissance et consentement parental RGPD si mineur).
- Refactor `_finish_login` → `_create_authenticated_session`, réutilisé par le flux OAuth sans dupliquer la logique de session déjà utilisée par `login()`/`verify_2fa()`.
- 41 nouveaux tests : `test_server_oauth_google.py` (18), `test_ollama_provider.py` (13, dont 2 d'intégration réelle contre un serveur Ollama local), `test_anthropic_provider.py` (10, dont 1 de connectivité réelle contre l'API Anthropic officielle).

## Corrections
- Incident critique : 1617 fichiers du dépôt supprimés du disque en cours d'audit (hors git) — restaurés intégralement via `git checkout` ciblé.
- `webapp/static/assets/backgrounds/hero-wave.png` (jamais suivie par git) perdue lors du même incident, retrouvée intacte dans un ancien dossier de build et restaurée à l'identique (1 495 962 octets) — le design V4 s'affiche de nouveau correctement.
- Décalage de version `esbuild` dans `node_modules` résolu par `npm ci`.
- URL d'autorisation OAuth mal encodée (`scope` non échappé) corrigée avec l'implémentation réelle.
- 23 imports morts supprimés (`ruff --fix --select F401`), aucun changement de comportement.

## Optimisations
- `.dockerignore` : exclusion du dossier de sauvegarde de build `webapp/static-dist.bak-*/`.

## Fichiers modifiés
- `webapp/auth.py`, `.dockerignore`, 23 fichiers avec import mort supprimé.

## Fichiers créés
- `webapp/tests/test_server_oauth_google.py`, `webapp/tests/test_ollama_provider.py`, `webapp/tests/test_anthropic_provider.py`.

## Bugs connus
- Suite e2e Stripe (92 tests) désactivée : `STRIPE_WEBHOOK_SECRET` reste un placeholder (clé secrète et Price ID confirmés valides par ailleurs).
- Provider Anthropic non testé en génération réelle (pas de clé valide fournie).
- SMTP réel non testé (aucun identifiant fourni).
- Root cause de l'incident de suppression de masse non formellement identifiée.

## Temps estimé de développement
- Session unique, ~3h.
