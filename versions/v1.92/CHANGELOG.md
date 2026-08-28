# NovaMath v1.92

**Date** : 2026-07-26

**Nom de la mise à jour** : Bulles chatbot — largeur 70-75% et coins uniformément arrondis

## Nouveautés
- Aucune (ajustement visuel d'une fonctionnalité déjà livrée en v1.91).

## Corrections
- Vérification demandée de la disposition des bulles (utilisateur à droite, assistant à gauche, façon ChatGPT/Claude/Messenger/iMessage) : le code déjà en place (v1.91) s'est confirmé correct après nouvelle vérification visuelle complète (capture d'écran clair/sombre/mobile + mesure DOM des couleurs de fond et de la position des bulles) — aucune régression trouvée.
- Largeur maximale des bulles précisée pour correspondre littéralement à la demande ("environ 70 à 75%") : remplacée par `max-width: 73%` (relatif à la colonne de conversation, pas à l'écran entier) au lieu de l'ancienne limite basée sur les caractères (`min(72ch, 100%)`), qui donnait un résultat proche mais pas exactement ce ratio.
- Coins des bulles uniformément très arrondis (22px sur les 4 coins) : suppression du coin légèrement moins arrondi (6px, effet "pointe" façon iMessage) introduit en v1.91, qui n'était pas demandé et pouvait donner l'impression que les coins n'étaient pas "très arrondis" partout.

## Optimisations
- Aucune.

## Fichiers modifiés
- `webapp/static/css/chatbot.css` (`.chatbot-msg-bubble`, `.chatbot-msg.assistant .chatbot-msg-bubble`, `.chatbot-msg.user .chatbot-msg-bubble`).
- `webapp/static-dist/` reconstruit (`npm run build`).

## Bugs connus
- Aucun nouveau (les 4 échecs de tests préexistants, déjà documentés en v1.88-v1.91, sont sans rapport avec ce chantier).

## Temps estimé de développement
- Environ 30 min (relecture du CSS existant, vérification visuelle Playwright clair/sombre/mobile avec mesure DOM, ajustement précis de la largeur et des coins).
