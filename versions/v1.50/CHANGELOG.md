# NovaMath v1.50

**Date** : 2026-07-14

**Nom de la mise à jour** : Chatbot premium : suggestions temps réel + clôture du chantier assistant pédagogique central

Phase F, dernière étape du chantier "chatbot premium, assistant pédagogique central de NovaMath" lancé en v1.43. Bilan du chantier complet (v1.43 → v1.50) : le chatbot connaît désormais automatiquement l'élève (prénom, objectif du jour, notions faibles), peut chercher dans le contenu réel du site (cours + exercices), propose des cartes d'action et des suggestions en temps réel basées sur de vraies correspondances, et dispose d'une palette de commandes `@` ainsi que d'une Command Palette `Ctrl+K` disponible sur toute l'application — le tout sur une architecture provider-agnostique inchangée (`ChatProvider`) et sans aucune donnée fictive.

## Nouveautés
- `chatbot.js` : pendant la frappe (hors mode `@`), débounce 350ms sur `/api/search` (sans scope) — jusqu'à 4 suggestions réelles (cours/exercices) affichées en chips discrets au-dessus de la barre de saisie, cliquables (navigation directe vers le cours, ou vers une série ciblée pour un exercice via le pattern `localStorage "lumis:pending_series"` déjà utilisé ailleurs sur le site).
- Nouvelle zone `#chatbot-live-suggestions` dans `chatbot.html`, masquée à l'envoi du message ou si le champ est vide/trop court/commence par `@` (pas de conflit avec la palette de commandes de la Phase D).

## Corrections
- (aucune — fonctionnalité additive)

## Optimisations
- (aucune)

## Fichiers modifiés
- `webapp/static/js/chatbot.js`, `webapp/static/css/chatbot.css`, `webapp/static/chatbot.html`

## Bugs connus
- Comme pour la v1.46 : tests réalisés via curl/relecture manuelle du JS, pas de navigateur automatisé disponible dans cette session — recommander un passage manuel (clavier/clic réels) avant diffusion large de l'ensemble du chantier v1.43-v1.50.

## Temps estimé de développement
- ~1h (implémentation + tests serveur)
