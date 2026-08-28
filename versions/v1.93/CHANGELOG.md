# NovaMath v1.93

**Date** : 2026-07-26

**Nom de la mise à jour** : Refonte structurelle des messages chatbot — deux composants DOM distincts

## Nouveautés
- Aucune (refonte structurelle d'une fonctionnalité déjà livrée, à la demande explicite de l'utilisateur qui pensait que seules les couleurs avaient changé).

## Corrections
- **Restructuration du DOM des messages** (`chatbot.js::appendMessageEl`) : l'ancienne implémentation utilisait une seule structure partagée (`<div class="chatbot-msg user|assistant">`) où l'alignement à droite du message utilisateur reposait sur `flex-direction: row-reverse` combiné à `justify-content: flex-end` — techniquement correct et vérifié à l'écran, mais pas ce que l'utilisateur demandait explicitement ("deux composants différents", "pas seulement changer les couleurs"). Remplacée par deux structures HTML réellement distinctes :
  - **Message utilisateur** (`.chatbot-msg-row.chatbot-msg-row--user`) : conteneur `display:flex; justify-content:flex-end` contenant **uniquement** sa bulle (`.chatbot-msg-bubble--user`) — aucun avatar dans le DOM (pas seulement masqué en CSS comme avant).
  - **Message NovaMath** (`.chatbot-msg-row.chatbot-msg-row--assistant`) : conteneur `display:flex; justify-content:flex-start` contenant l'avatar NovaMath puis une colonne (bulle `.chatbot-msg-bubble--assistant`, actions, cartes "Voir le cours").
  - Chaque bulle porte directement sa propre classe de couleur (`--user`/`--assistant`) au lieu d'un sélecteur composé (`.chatbot-msg.user .chatbot-msg-bubble`), pour que l'alignement et la couleur ne dépendent d'aucune combinaison CSS indirecte.
- Largeur maximale des deux bulles fixée à `70%` de la colonne de conversation (au lieu de 73%), exactement la valeur demandée.
- Vérifié à nouveau intégralement après restructuration : DOM inspecté (aucune trace des anciennes classes `.chatbot-msg.user`/`.chatbot-msg.assistant`), plusieurs échanges dans une même conversation (pas seulement le premier message), mode clair, mode sombre, et mobile (390px) — capture d'écran + `getComputedStyle`/`getBoundingClientRect` à l'appui pour chaque cas.

## Optimisations
- Aucune.

## Fichiers modifiés
- `webapp/static/js/chatbot.js` (`appendMessageEl`, seule fonction qui construit le DOM des messages).
- `webapp/static/css/chatbot.css` (sélecteurs des bulles/lignes/avatar renommés en conséquence).
- `webapp/static-dist/` reconstruit (`npm run build`).

## Bugs connus
- Les 4 échecs de tests préexistants déjà documentés (sans rapport avec ce chantier).
- Il n'existe pas de composants React/Vue dans NovaMath (application HTML/CSS/JS "vanilla", sans framework) : la demande de "vérifier les composants React/Vue" ne s'applique pas à cette architecture — la vérification a porté sur le DOM généré par `chatbot.js`.

## Temps estimé de développement
- Environ 45 min (relecture complète du DOM/CSS existant, restructuration en deux composants distincts, mise à jour de tous les sélecteurs CSS dépendants, vérification visuelle et DOM Playwright clair/sombre/mobile/multi-messages).
