# NovaMath v1.15

**Date** : 2026-07-13

**Nom de la mise à jour** : Refonte UI/UX sans emoji + cours simplifiés avec figures SVG

## Nouveautés
- **Zéro emoji sur tout le site** : tous les emojis (🔥 📚 ✅ 💡 🏆 🎓 🔟 💯 🌟 ⏱ 📝 📌 🕒 🏅 ✨ 👋 🎉 📖 🌱 ⚡ ✓ ✗) remplacés par des icônes SVG monochromes cohérentes avec le design NovaMath (même style Lucide déjà utilisé dans `icons.js`), dans les 4 couches du site : backend (`server.py`), pages HTML, JS frontend, PDF exporté (jsPDF).
- Nouvelles icônes ajoutées à `icons.js` : `trophy`, `graduationCap`, `sun`, `medal`, `scale`, `ruler`, `zap`, `sparkles`, `sprout`.
- Nouveau module `badgeIcons.js` : mutualise la correspondance badge → icône, auparavant dupliquée à l'identique dans `dashboard.js` et `profil.js`.
- **Cours entièrement réécrits** pour un public collège/lycée en difficulté : phrases courtes, une idée par phrase, vocabulaire simple. Nouvelle structure fixe par notion : intro courte → objectif → définition → règles importantes (cartes) → méthode (étapes numérotées et colorées avec icône) → plusieurs exemples détaillés (calcul étape par étape avec flèches) → erreurs fréquentes → astuce → à retenir (5 idées maximum) → mini-quiz.
- Nouveau lecteur de cours en **page unique** (`cours.js`/`cours.css` réécrits) façon Khan Academy/Notion, remplace l'ancienne navigation section par section — plus adapté à un contenu toujours découpé en petites cartes, jamais de gros bloc de texte.
- Nouveau générateur de **figures géométriques SVG** (`geomSvg.js`) : déclaratif (points, segments, vecteurs, polygones, cercles), respecte le thème/accent/transparence, responsive. Figures intégrées aux notions de géométrie du Chapitre 4 (triangle et droite des milieux, vecteurs, translation, Chasles, colinéarité) et du Chapitre 5 (repère, vecteur, milieu/distance).
- Passe responsive/accessibilité dédiée au module Cours : étapes de méthode empilées sur mobile, calculs qui ne débordent plus, contraste et tailles de police vérifiés.

## Corrections
- Duplication de `BADGE_ICONS` entre `dashboard.js` et `profil.js` supprimée (mutualisée dans `badgeIcons.js`).
- Historique serveur (`/api/practice/result`) : les icônes `✅/❌` codées en dur (jamais affichées côté frontend, code mort) remplacées par du texte clair.

## Optimisations
- Aucune régression de performance : les figures SVG sont générées à la volée (pas d'images), le contenu de cours reste chargé à la demande (un chapitre à la fois, comme en v1.14).

## Fichiers modifiés
Nouveaux : `webapp/static/js/{badgeIcons,geomSvg}.js`.
Modifiés : `webapp/server.py` (LEVEL_LABELS, historique practice/result), `webapp/static/js/{icons,cours,dashboard,profil,exercice,evaluation,resume,chapitres,reviews,pdfExport}.js`, `webapp/static/{dashboard,evaluation,index}.html`, `webapp/static/css/{cours,dashboard,exercice,reviews}.css`, les 12 fichiers `webapp/static/data/cours/chapitre_1..12.json` (contenu entièrement réécrit).

## Bugs connus
- Comme pour les versions précédentes : validation effectuée via tests serveur/API réels (curl, sessions invité réelles) et vérification statique de l'absence d'emoji dans tout le code source servi — pas de test interactif dans un navigateur réel (rendu visuel des figures SVG, contraste effectif) à confirmer visuellement.
- Figures géométriques disponibles uniquement pour une partie des notions des chapitres 4 et 5 (celles où un schéma apporte une réelle valeur pédagogique) ; les chapitres de fonctions/statistiques/probabilités n'en ont pas car leurs notions se prêtent mieux aux tableaux et exemples chiffrés.

## Temps estimé de développement
- Session unique, longue durée, couvrant l'audit et le remplacement de tous les emojis du site, la conception d'un nouveau schéma de contenu pédagogique simplifié, la réécriture complète des 52 notions des 12 chapitres, la création d'un générateur de figures SVG, et la réécriture du lecteur de cours en page unique.
