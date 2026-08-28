# NovaMath v1.91

**Date** : 2026-07-25

**Nom de la mise à jour** : Refonte UI/UX du Chatbot — bulles, sidebar, suggestions par classe

## Nouveautés
Refonte visuelle complète de la page Chatbot (chatbot.html/css/js), niveau de finition SaaS premium (ChatGPT/Claude/Perplexity) tout en gardant l'identité violette NovaMath.

- **Personnalisation par classe** : les suggestions de questions de l'état vide sont désormais réellement adaptées à la classe sélectionnée (`CLASS_SUGGESTIONS` dans chatbot.js), avec de vraies questions rattachées au programme officiel :
  - Troisième : Pythagore, Thalès, trigonométrie, moyenne/médiane, probabilités, fonctions affines.
  - Seconde : calcul littéral, variations de fonction, inéquations, vecteurs, équation de droite, statistiques descriptives.
  - Première : suites, nombre dérivé, trinôme du second degré, produit scalaire, arbre de probabilités, fonction exponentielle.
  - Le message d'accueil personnalisé (`/api/chatbot/greeting`) et les cartes "Voir le cours" étaient déjà générés côté serveur en fonction de la classe active (`class_level`) : ils s'accordent donc automatiquement avec les nouvelles suggestions.
- **Vraies bulles de conversation** (ChatGPT/Claude/iMessage) : messages utilisateur alignés à droite en bulle violette pleine (`--brand-gradient`) texte blanc, messages assistant alignés à gauche en bulle claire avec bordure et ombre légères — remplace l'ancien rendu "marginalia" (texte de part et d'autre d'un filet central, sans fond). Contraste vérifié en mode sombre (bulle assistant sombre, texte blanc).
- **Panneau de droite ("Ton profil NovaMath") supprimé** : ces informations existent déjà dans le Dashboard. La conversation récupère tout l'espace libéré (colonne élargie de 780px à 880px).
- **Sidebar des conversations repensée** : meilleur espacement, repère de section "CONVERSATIONS", coins plus harmonieux (var(--radius-md)), meilleurs hovers, recherche avec anneau de focus, bouton "Nouvelle conversation" affiné.
- **Barre de saisie** : ombre et anneau de focus renforcés, padding plus généreux, léger effet de levée au focus. Le placeholder ("Pose une question sur ton cours ou ton exercice…") tient désormais sur une seule ligne sur mobile (testé 390/375/360px) via une réduction ciblée de la police et du poids visuel des boutons joindre/envoyer sous 560px puis sous 400px.
- **Cartes "Voir le cours"** : icône passée à un badge dégradé (au lieu d'un simple cercle teinté), padding et rayon augmentés, légère rotation/zoom de l'icône au survol — plus "premium" et interactif.
- **Correctif de fond** : cause racine identifiée et corrigée (voir Corrections) — le décor violet ne semble plus "coupé".

## Corrections
- **Cause racine du défilement de toute la page (bug remonté "la molette fait défiler toute la page")** : `.chatbot-shell`/`.chatbot-convos`/`.chatbot-main` utilisaient `height: 100vh` alors qu'ils vivent à l'intérieur de `.app-shell` (padding 18px haut+bas = 36px, box-sizing:border-box) — exactement la même convention que `.sidebar` (déjà en `calc(100vh - 36px)`). Cette différence de 36px forçait `.app-shell` à grandir au-delà de la fenêtre, faisant défiler le `body` en plus du panneau de conversation. Corrigé en `calc(100vh - 36px)` sur desktop, avec un repli à `100vh` sous 860px (là où `.app-shell` repasse à `padding:0` pour le mode tiroir mobile). Cette même correction résout aussi le décor de fond qui semblait "coupé" : il n'y avait en réalité rien de coupé, c'est la page qui défilait au-delà d'un seul viewport à cause du bug ci-dessus.
- **Chevauchement de deux boutons "hamburger" sur mobile** : sous 860px, le bouton menu principal du site (`#sidebar-mobile-trigger`, fixe, toujours en haut à gauche) se superposait exactement au bouton d'ouverture des conversations du chatbot (`.chatbot-convos-mobile-trigger`), car `.chatbot-topbar` ne fait pas partie de `.main-content` (qui réserve normalement 76px en haut pour ce bouton fixe, voir responsive.css). Corrigé en réservant la même marge sur `.chatbot-topbar`.
- Placeholder de la zone de saisie repassé sur une seule ligne (texte raccourci + ajustements responsive, voir Nouveautés).

## Optimisations
- Aucune.

## Fichiers modifiés
- `webapp/static/chatbot.html` : suppression du panneau contextuel de droite, placeholder raccourci, repère "Conversations" ajouté.
- `webapp/static/js/chatbot.js` : suppression de `loadContextPanel()` et de son appel, ajout de `CLASS_SUGGESTIONS`/`renderSuggestions()`.
- `webapp/static/css/chatbot.css` : correctif de hauteur (cause racine scroll/fond), bulles de message, sidebar, barre de saisie, cartes d'action, correctif hamburger mobile.
- `webapp/static/js/__tests__/chatbot.test.js` : test du panneau contextuel remplacé par un test de suppression + un test des suggestions personnalisées.
- `webapp/static-dist/` reconstruit (`npm run build`).

## Bugs connus
- Les 4 échecs de tests préexistants déjà documentés (sans rapport avec ce chantier) : `test_accesseur_exemple_par_difficulte`, `test_validate_cours_schema`, `test_formules_scaffoldees_depuis_reglesimportantes`, `test_oauth_callback_accessible_avec_headers`.
- La demande mentionnait des exemples pour une classe "Terminale" (Intégration, Exponentielle, Logarithmes...) : cette classe n'existe pas encore dans `curriculum_registry.py` (seules Seconde/Première/Troisième sont enregistrées) — aucun contenu n'a donc été inventé pour une classe qui n'existe pas dans NovaMath.
- Sous ~320px de large (téléphones très anciens, quasi inexistants aujourd'hui), le placeholder repasse sur 2 lignes : réduire encore la police l'aurait rendu illisible. Fonctionne parfaitement de 360px à la 4K.
- L'endpoint backend `/api/chatbot/context-preview` et `api.chatbotContextPreview` (api.js) restent en place (encore testés côté Python) même si plus aucun appelant frontend ne les utilise depuis la suppression du panneau — conservés par prudence plutôt que de supprimer une route d'API testée, en dehors du périmètre demandé (refonte visuelle, pas audit de l'API).

## Temps estimé de développement
- Environ 3h (analyse complète de la page existante, correctif de la cause racine du scroll/fond, refonte des bulles/sidebar/saisie/cartes, personnalisation par classe, vérification visuelle Playwright desktop/tablette/mobile/mode sombre, corrections itératives du placeholder mobile et du chevauchement des boutons, tests de non-régression).
