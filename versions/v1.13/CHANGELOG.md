# NovaMath v1.13

**Date** : 2026-07-12

**Nom de la mise à jour** : Refonte complète du système de Paramètres

## Nouveautés
- Système de Paramètres entièrement repensé : popup unique (composant `popup.js` générique réutilisé par tous les popups du site) remplaçant l'ancienne page `settings.html`, ouvert via une petite icône engrenage en bas de la sidebar (même style que l'ancien bouton thème).
- `SettingsManager` global (`settingsManager.js`) : source de vérité unique des préférences, avec événement `novamath:settings-changed` propagé en direct à tout le site (thème, couleur, langue, entraînement...) sans reload.
- Couleur d'accent réellement propagée à tout le site : sidebar, boutons, badges, graphes du Dashboard et du Profil, anneau XP, confettis, `meta theme-color` — plus aucune couleur violette codée en dur ignorant le choix de l'utilisateur.
- Carte "Objectif quotidien" sur le Dashboard : progression du jour, barre animée, pourcentage, badge visuel à l'atteinte de l'objectif, mise à jour en direct.
- Export PDF premium du rapport de progression (`pdfExport.js`, jsPDF chargé à la demande) : résumé général, progression par chapitre/notion, statistiques par niveau, objectif quotidien, historique récent, conseils personnalisés — thème clair fixe, pagination, en-tête répété.
- Interface traduite en français/anglais (`i18n.js`) : sidebar, popup Paramètres, section Aide & À propos ; les énoncés d'exercices restent volontairement en français dans les deux langues. Langues supplémentaires (arabe, espagnol, allemand) affichées grisées "Bientôt disponible".
- Section "Aide & À propos" entièrement rédigée (contenu réel, pas de placeholder) : présentation, mission, fonctionnement, FAQ, guide utilisateur, contact, CGU, confidentialité, cookies, mentions légales, roadmap, crédits/technologies, sécurité.
- Système de versioning décimal professionnel (`create_version_snapshot.py` v2, fichier racine `VERSION`, `webapp/static/js/version.js`) : chaque mise à jour importante crée désormais un instantané autonome `versions/NovaMath_v{X.YY}/` avec RUN.bat/RUN.ps1/README/CHANGELOG dédiés, sans jamais supprimer les versions précédentes.

## Corrections
- **Bug du chronomètre qui ne se désactivait pas** : `exercice.js` ne relisait les préférences d'entraînement qu'une seule fois au chargement de la page. Il s'abonne désormais à `novamath:settings-changed` et coupe le chrono en direct dès que le toggle passe à OFF, même série déjà affichée.
- **Bug des séries bloquées (ex. à 7 exercices)** : la reprise d'une série en pause (`resumeSeries()`) recalculait `SERIES_TOTAL` avec la préférence *actuelle* alors que la file de questions (`seriesQueue`) restait figée à l'ancienne taille, causant une désynchronisation. Corrigé : une série reprise réutilise son propre total d'origine ; toute série démarrée *depuis zéro* relit systématiquement la préférence en vigueur.
- Catégorie "Notifications" (menu mort, aucune logique d'envoi réelle) supprimée entièrement, frontend et backend (`auth.py::DEFAULT_SETTINGS`).
- Confidentialité : encadré "Zone sensible" retiré (design), bouton "Télécharger mes données personnelles" supprimé (doublon avec l'export PDF).
- Les 3 boutons d'export dupliqués (statistiques / toutes les données / données personnelles), qui produisaient tous le même JSON brut, fusionnés en un seul export PDF réel.
- Bouton de changement de thème retiré de la sidebar (doublon avec Paramètres → Apparence) ; sidebar recentrée automatiquement.

## Optimisations
- Centralisation de l'initialisation (thème, popup Paramètres, traductions) auparavant dupliquée dans chaque script de page (`dashboard.js`, `chapitres.js`, `exercice.js`, `profil.js`).
- Mise à jour optimiste des préférences (`SettingsManager.setSetting`) : application immédiate en mémoire/cache/DOM, persistance serveur en arrière-plan avec debounce.
- jsPDF chargé paresseusement (uniquement au clic sur "Exporter mon rapport"), aucun impact sur le temps de chargement des pages.

## Fichiers modifiés
Nouveaux : `webapp/static/js/{popup,settingsManager,settingsPopup,pdfExport,i18n,version}.js`.
Modifiés (liste non exhaustive) : `webapp/static/js/{settings,theme,exercice,dashboard,profil,chapitres,animations}.js`, `webapp/static/css/{tokens,base,settings,dashboard}.css`, `webapp/static/{dashboard,chapitres,exercice,profil}.html`, `webapp/auth.py`, `webapp/server.py`, `create_version_snapshot.py` (nouveau système de versioning décimal), `CHANGELOG.md` (racine).
Archivé : `webapp/static/settings.html` → `settings.html.removed` (remplacé par le popup).

## Bugs connus
- Traduction i18n : couvre la sidebar, le popup Paramètres et Aide & À propos ; ne couvre pas encore le contenu détaillé du Dashboard/Chapitres/Profil/landing (chantier volumineux, à poursuivre en v1.0x).
- Pas de test navigateur interactif réel (clics, ouverture effective du popup PDF) dans cette version — validation effectuée via tests serveur/API/markup (curl, session invité réelle). À confirmer visuellement.
- `api.exportData`/`GET /api/data/export` restent disponibles côté backend mais ne sont plus appelés par aucune UI (gardés pour un futur usage RGPD).

## Temps estimé de développement
- Session unique, longue durée (~1 journée de travail équivalent), couvrant la refonte complète du système de Paramètres, la correction de deux bugs critiques (chrono, séries bloquées), l'export PDF, l'i18n et le nouveau système de versioning.
