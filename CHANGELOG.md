# NovaMath

Historique complet des versions, la plus récente en tête. Chaque version est aussi archivée de
façon autonome et détaillée dans `versions/v{X.YY}/CHANGELOG.md` (jamais modifié après coup).

Convention de versioning unifiée depuis le 2026-07-13 : `vX.YY` (toujours deux chiffres après le
point, "v" minuscule), un seul schéma pour toute la durée de vie du projet — jamais de mélange
V1/Version1/v1_1/v01. Les anciens dossiers `versions/NovaMath_V1` à `V13` (schéma entier) et
`versions/NovaMath_v1.00` à `v1.31` (schéma décimal préfixé) ont été renommés une seule fois vers
`versions/v1.00` à `v1.17` (même ordre chronologique, même contenu — seules les références de
version dans les fichiers de métadonnées de chaque dossier, CHANGELOG.md/README.md/RUN.bat/
RUN.ps1/version.js, ont été mises à jour en conséquence). Au franchissement d'un numéro majeur :
`v1.99` → `v2.00`, jamais `v2` ni `V2`.

Le produit s'appelait auparavant **Lumis** (voir plus bas). Cette lignée reste explicitement hors
du nouveau schéma NovaMath, jamais renumérotée ni modifiée, conservée telle quelle pour
l'historique (`versions/Lumis_V1` à `Lumis_V6`, intacts).

## v1.62

**Date** : 2026-07-14

**Nom de la mise à jour** : RecommendationEngine : carte "Revoir ce chapitre" basée sur le chapitre le plus faible réel

Phase S (dernière phase) du chantier v2.12. `action_cards_service.py` propose une carte "Revoir ce chapitre" pointant vers le vrai chapitre le plus faible de l'élève quand la réponse portait sur sa progression/ses statistiques.

Ceci clôture le chantier v2.12 (v1.60→v1.62) : le LLM devient un filet de sécurité — un moteur compositionnel (intention → variables réelles → templates avec variantes → habillage mode/longueur) répond localement à toutes les demandes de progression/statistiques/dashboard/profil/paramètres/séries/exercices, vérifié par comptage réel des appels au fournisseur IA (0 appel pour ces intentions).

### Nouveautés
- `action_cards_service._weak_chapter_card()` + `build_cards(weak_chapter_id=...)`.

### Corrections
- (aucune)

### Optimisations
- (aucune)

### Fichiers modifiés
- `webapp/chatbot/services/action_cards_service.py`, `webapp/chatbot/conversation_manager.py`

### Bugs connus
- Vérifié en Python direct.

### Temps estimé de développement
- ~25min

## v1.61

**Date** : 2026-07-14

**Nom de la mise à jour** : AtCommandService : toutes les mentions @ chargent des données, mention seule = réponse 100% locale

Phase R du chantier v2.12 : `@Profil`/`@Paramètres`/`@Séries` passent en `kind:"data"` (chargent de vraies données comme les autres). Surtout : une mention "@" seule (sans question ouverte autour) produit désormais une réponse composée entièrement en local, zéro appel LLM.

### Nouveautés
- `mentions_service.single_data_mention_intent()` : détecte une mention "@" seule et la route vers le moteur local de la Phase Q.

### Corrections
- `chatbot.js::handleMentionAction()` : branche `"open-settings"` devenue inatteignable, supprimée.

### Optimisations
- Nouvelle réduction d'appels LLM pour le cas d'usage courant "cliquer une catégorie de la palette @".

### Fichiers modifiés
- `webapp/chatbot/services/mentions_service.py`, `webapp/chatbot/conversation_manager.py`, `webapp/static/js/chatbot.js`

### Bugs connus
- `@Quiz` reste sur l'ancien grounding générique (pas de source de données "résultats de quiz" dédiée exposée, hors scope).

### Temps estimé de développement
- ~45min

## v1.60

**Date** : 2026-07-14

**Nom de la mise à jour** : Moteur de réponses locales : intention + variables + templates + court-circuit du LLM

Chantier v2.12 (Phases O/P/Q) : inverse la priorité du chatbot — le LLM devient un filet de sécurité, pas le premier réflexe. Vérifié par comptage d'appels réels : 0 appel LLM pour progression/statistiques/dashboard/profil/exercice, 1 appel pour une question ouverte hors périmètre.

### Nouveautés
- `intent_service.py` étendu (progression/statistique/dashboard/profil/paramètres/série/formule) + `variable_resolver.py` (variables réelles depuis les vraies données de l'élève).
- `template_library.py` (3-5 variantes par intention, pas des centaines de textes figés) + `response_composer.py` (habillage mode/longueur).
- `local_knowledge_service.py` (point d'entrée unique : réponse locale possible ?) + `llm_fallback_service.py` (fine enveloppe autour de `provider_manager`).

### Corrections
- (aucune — nouvelle architecture)

### Optimisations
- Réduction directe des appels au fournisseur IA pour toutes les demandes courantes de progression/statistiques/exercices.

### Fichiers modifiés
- `webapp/chatbot/services/intent_service.py`, `webapp/chatbot/conversation_manager.py`
- Nouveaux : `variable_resolver.py`, `template_library.py`, `response_composer.py`, `local_knowledge_service.py`, `llm_fallback_service.py`

### Bugs connus
- Testé en Python direct (compteur d'appels) et via route HTTP réelle.

### Temps estimé de développement
- ~2h

## v1.59

**Date** : 2026-07-14

**Nom de la mise à jour** : Audit qualité visuelle des bulles : alignement centré, débordement tableau/mots longs

Phase M (dernière phase) du chantier v2.11. Défaut structurel trouvé : la barre de saisie était centrée mais pas les bulles de messages (alignées aux bords du conteneur) — incohérence visuelle nette, corrigée. Ceci clôture le chantier v1.52→v1.59 : moteur d'intention, exercices scopés par chapitre, préréponses pédagogiques, paramètres réellement appliqués, mentions @ données réelles, règle de progression centralisée, popups premium, icône sidebar, audit visuel — avec deux bugs de production critiques trouvés et corrigés en testant le pipeline complet en Python (retrieval TF-IDF pluriel/singulier, FakeProvider ignorant le prompt système).

### Nouveautés
- (aucune — audit/correctifs)

### Corrections
- `.chatbot-messages` sans `align-items:center` alors que la barre de saisie est centrée — bulles alignées aux bords au lieu de partager la colonne centrée. Corrigé.
- Tableau large sans protection anti-débordement, mots/URLs longs non coupés — corrigés (`overflow-x:auto`, `overflow-wrap:break-word`).

### Optimisations
- (aucune)

### Fichiers modifiés
- `webapp/static/css/chatbot.css`

### Bugs connus
- Padding/rayons déjà cohérents (tokens du design system), rien à corriger sur ces points. Pas de test visuel réel en navigateur (limite déjà documentée).

### Temps estimé de développement
- ~30min

## v1.58

**Date** : 2026-07-14

**Nom de la mise à jour** : Icône sidebar repositionnée : plus de chevauchement avec "Nouvelle conversation"

Phase L du chantier v2.11 : le bouton de repli de la sidebar conversations chevauchait visuellement le bouton "Nouvelle conversation" — corrigé avec une rangée dédiée, plus aucune superposition.

### Nouveautés
- (aucune)

### Corrections
- Bouton de repli sorti de `position: absolute`, nouvelle rangée dédiée `.chatbot-convos-toprow`. Icône remplacée par "panel-left" (Lucide) faute d'image de référence jointe.

### Optimisations
- (aucune)

### Fichiers modifiés
- `webapp/static/chatbot.html`, `webapp/static/css/chatbot.css`

### Bugs connus
- Pas de test visuel réel en navigateur (limite déjà documentée) — à valider par l'utilisateur.

### Temps estimé de développement
- ~25min

## v1.57

**Date** : 2026-07-14

**Nom de la mise à jour** : Popups premium réutilisables (prompt/confirm) remplacent window.prompt/confirm du chatbot

Phase K du chantier v2.11 : `popup.js` étendu avec `openPromptPopup()`/`openConfirmPopup()`, génériques et réutilisables par tout le site, remplaçant les `window.prompt`/`window.confirm` natifs du renommage/suppression de conversation.

### Nouveautés
- `popup.js::openPromptPopup()`/`openConfirmPopup()` — même thème que le reste du site.
- `chatbot.js` : renommage/suppression de conversation utilisent ces popups.

### Corrections
- (aucune)

### Optimisations
- (aucune)

### Fichiers modifiés
- `webapp/static/js/popup.js`, `webapp/static/js/chatbot.js`, `webapp/static/css/base.css`

### Bugs connus
- Pas de test d'interaction réel en navigateur (limite déjà documentée).

### Temps estimé de développement
- ~30min

## v1.56

**Date** : 2026-07-14

**Nom de la mise à jour** : Règle de progression centralisée : Maîtrisé = accuracy ≥ 70% et ≥ 10 tentatives

4 seuils différents selon la page (chapitres.js, dashboard.js, badge store.js, chatbot context_builder.py) remplacés par une règle unique centralisée, demandée explicitement par l'utilisateur.

### Nouveautés
- `store.js::getChapterStatus()` (constantes `MASTERY_ACCURACY_THRESHOLD`=0.70, `MASTERY_MIN_ATTEMPTS`=10) : seule source de vérité frontend.
- `progress_service.py` (nouveau) : équivalent backend, mêmes seuils.

### Corrections
- `chapitres.js`, `dashboard.js`, `context_builder.py::_mastered_notions()` : chacun avait sa propre formule — tous appellent désormais la règle centralisée.

### Optimisations
- (aucune)

### Fichiers modifiés
- `webapp/static/js/store.js`, `webapp/static/js/chapitres.js`, `webapp/static/js/dashboard.js`, `webapp/chatbot/context_builder.py`
- Nouveau : `webapp/chatbot/services/progress_service.py`

### Bugs connus
- Vérifié sur tous les cas fournis par l'utilisateur (90%/2→En cours, 82%/14→Maîtrisé, etc.), tous corrects.

### Temps estimé de développement
- ~45min

## v1.55

**Date** : 2026-07-14

**Nom de la mise à jour** : Mentions @ Progression/Statistiques/Dashboard/Quiz récupèrent des données réelles

Phase J du chantier v2.11 : `@Progression`/`@Statistiques`/`@Dashboard`/`@Quiz` récupèrent les vraies données de l'élève et les injectent dans la conversation au lieu d'ouvrir une autre page. `@Séries`/`@Profil`/`@Paramètres`/`@Chatbot` restent des raccourcis de navigation légitimes.

### Nouveautés
- Catégories `dashboard`/`progression`/`statistiques`/`quiz` : `kind: "nav"` → `kind: "data"`, résolu via `context_builder.build_context_summary()` (même source que le prompt système).
- Badge de mention "données" côté composeur, résolu par le backend au moment de l'envoi.

### Corrections
- (aucune — nouvelle fonctionnalité)

### Optimisations
- (aucune)

### Fichiers modifiés
- `webapp/chatbot/services/mentions_service.py`, `webapp/chatbot/conversation_manager.py`, `webapp/static/js/chatbot-composer.js`, `webapp/static/js/chatbot-mentions.js`

### Bugs connus
- Vérifié via requête HTTP réelle de bout en bout ; pas de test d'interaction clavier/souris réel en navigateur (limite déjà documentée).

### Temps estimé de développement
- ~45min

## v1.54

**Date** : 2026-07-14

**Nom de la mise à jour** : Préréponses pédagogiques + paramètres du chatbot réellement appliqués

Phase I du chantier v2.11 : chaque intention détectée adapte le format de réponse, et les réglages "Mémoire"/"Streaming" (jusqu'ici décoratifs) ont un effet réel. Nouveau réglage "Mode" (professeur/rapide/pas-à-pas/visuel/examen).

### Nouveautés
- `pedagogy_templates.py` : fragments d'instruction système par intention et par mode, injectés dans le prompt.
- Réglage "Mode" (5 valeurs) dans Paramètres → Chatbot.

### Corrections
- `memoryEnabled` sans effet jusqu'ici (profil élève toujours injecté) — corrigé.
- `streaming` sans effet côté frontend (effet machine à écrire toujours actif) — corrigé.

### Optimisations
- (aucune)

### Fichiers modifiés
- `webapp/chatbot/prompt_builder.py`, `webapp/chatbot/conversation_manager.py`, `webapp/auth.py`, `webapp/static/js/settings.js`, `webapp/static/js/chatbot.js`
- Nouveau : `webapp/chatbot/services/pedagogy_templates.py`

### Bugs connus
- Les modes n'ont d'effet observable qu'avec un fournisseur IA réel (Claude/Ollama) — `FakeProvider` priorise le grounding sur le style demandé.

### Temps estimé de développement
- ~1h

## v1.53

**Date** : 2026-07-14

**Nom de la mise à jour** : Exercices scopés par chapitre + FakeProvider exploite enfin le grounding

Phase H du chantier de fiabilisation du chatbot v2.11 : une demande d'exercice sur un chapitre précis ne renvoie plus jamais un exercice d'un autre chapitre. Bug critique découvert en testant le pipeline complet : le fournisseur par défaut ignorait le prompt système, rendant invisible tout le grounding construit depuis la v1.51.

### Nouveautés
- `search_service.search_exercises_in_chapter()` : recherche d'exercices strictement limitée à un chapitre, jamais de repli vers un autre.
- `conversation_manager.stream_reply()` : résout un vrai exercice du chapitre détecté (Phase G) et l'injecte dans le prompt ; message fixe explicite si le chapitre n'a aucun exercice (jamais laissé au LLM).
- `action_cards_service.build_cards()` : filtre les cartes "Continuer un entraînement" hors du chapitre résolu par l'intention.

### Corrections
- **Bug critique** : `FakeProvider` (fournisseur par défaut sans IA) ignorait totalement `system` et refaisait sa propre recherche sur le message brut — tout le grounding (mentions "@" v1.51, exercices Phase H) n'avait donc aucun effet observable en configuration par défaut. Corrigé : détection et priorité au bloc de ressource déjà résolue dans `system`.
- Vérifié : 30 tirages directs + 10 échanges complets via `stream_reply`, 0 exercice hors chapitre.

### Optimisations
- (aucune)

### Fichiers modifiés
- `webapp/chatbot/services/search_service.py`, `webapp/chatbot/services/action_cards_service.py`, `webapp/chatbot/conversation_manager.py`, `webapp/chatbot/providers/fake_provider.py`

### Bugs connus
- Les fournisseurs IA réels (Claude, Ollama) lisent nativement `system`, non affectés par le bug FakeProvider — mais c'est la configuration utilisée pour tous les tests de ce chantier jusqu'ici.

### Temps estimé de développement
- ~1h

## v1.52

**Date** : 2026-07-14

**Nom de la mise à jour** : Moteur d'intention pedagogique + correction retrieval TF-IDF (pluriel/singulier)

Première phase (Phase G) du chantier de fiabilisation du chatbot v2.11 : classification d'intention pédagogique avant tout appel LLM, gestion des demandes incompréhensibles, et correction d'un vrai bug de retrieval (pluriel/singulier) découvert en rejouant le pipeline directement en Python.

### Nouveautés
- `webapp/chatbot/services/intent_service.py` : classification par règles (exercice/exemple/explication/quiz/fiche/correction/reprise des bases), détection du chapitre visé (réutilise `search_service`), détection des demandes incompréhensibles (court-circuit LLM avec message de clarification).

### Corrections
- Bug racine `retrieval_engine.py` : TF-IDF sans normalisation morphologique faisait complètement rater les correspondances plurielles/singulières (ex. "valeurs absolues" ne trouvait pas "La valeur absolue", remplacé par "Les quartiles" sans rapport) — tokenizer personnalisé avec normalisation légère ajouté.
- Regex de détection d'intention trop rigides (adjectif entre "exercice" et "sur") élargies.

### Optimisations
- (aucune)

### Fichiers modifiés
- `webapp/chatbot/retrieval_engine.py`, `webapp/chatbot/conversation_manager.py`
- Nouveau : `webapp/chatbot/services/intent_service.py`

### Bugs connus
- Repli flou toujours sujet à des faux positifs sur des sujets absents du corpus (limite déjà documentée en v1.51). Résultat de `classify()` pas encore exploité par la sélection d'exercices (Phase H) ni le style de réponse (Phase I) — phases suivantes du même chantier.

### Temps estimé de développement
- ~1h30

## v1.51

**Date** : 2026-07-14

**Nom de la mise à jour** : Refonte du système de mentions @ : palette robuste, badges, clavier, tolérance aux fautes

Correction demandée après retour utilisateur sur la v1.46 : le système de mentions "@" ne fonctionnait pas correctement (recherche multi-mots directe cassée dès qu'un espace était tapé sans catégorie préalable, aucune tolérance aux fautes de frappe, insertion en texte brut au lieu d'un badge visuel, pas de navigation clavier). Le bug racine identifié : l'ancienne détection de mention exigeait un mot unique sans espace tant qu'aucune catégorie n'avait été sélectionnée — "@Valeurs absolues" (mention directe multi-mots, cas d'usage central du cahier des charges) ne pouvait donc jamais fonctionner. Le système a été repensé en profondeur plutôt que rapiécé.

### Nouveautés
- Nouvelle route unique `GET /api/chatbot/mentions?q=` (`chatbot/services/mentions_service.py`) : sert à la fois les catégories de page réelles (Cours/Exercices/Notions/Séries/Dashboard/Progression/Statistiques/Objectifs/Quiz/Profil/Paramètres/Chatbot, chacune avec une vraie destination ou action) et les ressources (cours/exercices), avec repli flou (`search_service.py`, `difflib`, stdlib) pour les fautes de frappe ("puisance" → "Les puissances"). Renvoie un "Voulez-vous dire : X ?" pour une requête sans correspondance sérieuse (cutoff plus permissif, réservé à cette présentation explicitement incertaine).
- `search_service.py` : cours et exercices interrogés séparément puis fusionnés (au lieu d'un top-N unique) pour qu'une notion couvrant des dizaines d'exercices ne masque plus systématiquement le cours correspondant ; déduplication par titre pour la palette (une notion = une entrée, pas 8 exercices identiques) ; nouvelle fonction `resolve()` (lookup exact, pas une recherche) pour injecter la vraie donnée d'une mention déjà choisie.
- `knowledge_engine.py` : nouveau lookup direct `get_notion(chapter_id, notion_id)` et `all_documents()`, utilisés par le repli flou et la résolution de mention.
- **Composeur de message revu** (`chatbot-composer.js`, nouveau) : le `<textarea>` devient un `<div contenteditable>`, seul moyen d'insérer un vrai badge visuel non-éditable (`.chatbot-mention-chip`) supprimable en un seul Backspace — impossible avec un textarea (texte brut uniquement).
- `chatbot-mentions.js` réécrit : navigation clavier complète (flèches, Entrée, Échap, Tab), une seule source de vérité (l'endpoint backend, plus aucune logique de correspondance côté client), mention multi-mots fonctionnelle sans sélection de catégorie préalable.
- Grounding réel des mentions : `db.py` (colonne `mentions` JSON sur `chatbot_messages`, même schéma que `cards`), `conversation_manager.py`/`prompt_builder.py` injectent la vraie donnée de la ressource mentionnée dans le prompt système (jamais laissée à l'appréciation du LLM), persistée pour que `regenerate` réutilise les mêmes mentions.
- Actions de catégorie réelles (pas de redirection décorative) : Paramètres ouvre le vrai popup de la page, "Chatbot" démarre une vraie nouvelle conversation, Objectifs insère les vrais chiffres du jour (`/api/goals/daily`) dans le message.

### Corrections
- Bug racine : mention multi-mots ("@Valeurs absolues") impossible à taper sans choisir une catégorie au préalable (le menu se fermait dès le premier espace).
- Faux positifs du repli flou (ex. "thales" matchait "Intervalles" à 0.59 par pur hasard de lettres) : cutoff du résultat "confiant" relevé à 0.62 ; les correspondances plus faibles ne sont plus présentées que comme suggestion explicite ("Voulez-vous dire ?").
- `search_service.resolve()` levait une `KeyError: 'score'` sur toute mention résolue (les lookups directs ne passent pas par le chemin qui ajoute ce champ) — détecté en testant le pipeline complet (pas seulement les endpoints de surface), corrigé par un score explicite (1.0, correspondance exacte).

### Optimisations
- (aucune)

### Fichiers modifiés
- `webapp/chatbot/knowledge_engine.py`, `webapp/chatbot/services/search_service.py`, `webapp/chatbot/conversation_manager.py`, `webapp/chatbot/prompt_builder.py`, `webapp/db.py`, `webapp/server.py`
- `webapp/static/js/chatbot.js`, `webapp/static/js/api.js`, `webapp/static/js/i18n.js`, `webapp/static/css/chatbot.css`, `webapp/static/chatbot.html`
- Nouveaux : `webapp/chatbot/services/mentions_service.py`, `webapp/static/js/chatbot-composer.js`
- Réécrit : `webapp/static/js/chatbot-mentions.js`

### Bugs connus
- Comme pour les v1.46/v1.50 : pas de navigateur automatisé disponible dans cette session. Cette fois le pipeline complet a été rejoué directement en Python (au-delà des routes HTTP) pour attraper les erreurs invisibles en surface — ce qui a permis de trouver et corriger un vrai crash serveur (`KeyError: 'score'`) — mais l'interaction clavier/souris réelle du composeur contenteditable (badges, flèches, Backspace) reste à valider manuellement avant diffusion large.

### Temps estimé de développement
- ~3h (refonte backend + composeur contenteditable + tests pipeline complet incluant un bug de production trouvé et corrigé)

## v1.50

**Date** : 2026-07-14

**Nom de la mise à jour** : Chatbot premium : suggestions temps réel + clôture du chantier assistant pédagogique central

Phase F, dernière étape du chantier "chatbot premium, assistant pédagogique central de NovaMath" lancé en v1.43. Bilan du chantier complet (v1.43 → v1.50) : le chatbot connaît désormais automatiquement l'élève (prénom, objectif du jour, notions faibles), peut chercher dans le contenu réel du site (cours + exercices), propose des cartes d'action et des suggestions en temps réel basées sur de vraies correspondances, et dispose d'une palette de commandes `@` ainsi que d'une Command Palette `Ctrl+K` disponible sur toute l'application — le tout sur une architecture provider-agnostique inchangée (`ChatProvider`) et sans aucune donnée fictive.

### Nouveautés
- `chatbot.js` : pendant la frappe (hors mode `@`), débounce 350ms sur `/api/search` (sans scope) — jusqu'à 4 suggestions réelles (cours/exercices) affichées en chips discrets au-dessus de la barre de saisie, cliquables (navigation directe vers le cours, ou vers une série ciblée pour un exercice via le pattern `localStorage "lumis:pending_series"` déjà utilisé ailleurs sur le site).
- Nouvelle zone `#chatbot-live-suggestions` dans `chatbot.html`, masquée à l'envoi du message ou si le champ est vide/trop court/commence par `@` (pas de conflit avec la palette de commandes de la Phase D).

### Corrections
- (aucune — fonctionnalité additive)

### Optimisations
- (aucune)

### Fichiers modifiés
- `webapp/static/js/chatbot.js`, `webapp/static/css/chatbot.css`, `webapp/static/chatbot.html`

### Bugs connus
- Comme pour la v1.46 : tests réalisés via curl/relecture manuelle du JS, pas de navigateur automatisé disponible dans cette session — recommander un passage manuel (clavier/clic réels) avant diffusion large de l'ensemble du chantier v1.43-v1.50.

### Temps estimé de développement
- ~1h (implémentation + tests serveur)

## v1.46

**Date** : 2026-07-14

**Nom de la mise à jour** : Chatbot : palette de commandes @ et Command Palette Ctrl+K

Phases D+E du chantier "chatbot premium" : navigation et recherche façon Cursor/Notion, dans le chatbot (@) et sur tout le site (Ctrl+K), toutes deux branchées sur `/api/search` (Phase A) — aucune donnée inventée.

### Nouveautés
- Nouveau `webapp/static/js/chatbot-mentions.js` : taper "@" dans la zone de saisie du chatbot ouvre un menu de catégories (`@Cours`, `@Exercices`, `@Notions` — recherche réelle via `/api/search` ; `@Dashboard`, `@Quiz`, `@Progression`, `@Statistiques` — accès direct à la vraie page ; `@Objectifs` — affiche le vrai objectif du jour via `/api/goals/daily`). Sélectionner un résultat de recherche insère une référence lisible dans le message, sans quitter la conversation.
- Nouveau `webapp/static/js/command-palette.js` + `css/command-palette.css` : Command Palette globale (`Ctrl+K`/`Cmd+K`), disponible sur les 7 pages de l'app (chapitres, cours, dashboard, exercice, profil, evaluation, chatbot) — réutilise `popup.js` (aucun système de modal réinventé), mêle recherche réelle (`api.search`) et raccourcis de navigation statiques.
- Nouvelles clés i18n FR/EN pour tous les libellés ajoutés (`chatbot_mentions_*`, `cmd_palette_*`).

### Corrections
- (aucune — fonctionnalités additives)

### Optimisations
- (aucune)

### Fichiers modifiés
- `webapp/static/js/chatbot.js`, `webapp/static/css/chatbot.css`, `webapp/static/js/i18n.js`
- Les 7 pages `webapp/static/{chapitres,cours,dashboard,exercice,profil,evaluation,chatbot}.html` (ajout des balises `<link>`/`<script>` de la Command Palette)
- Nouveaux : `webapp/static/js/chatbot-mentions.js`, `webapp/static/js/command-palette.js`, `webapp/static/css/command-palette.css`

### Bugs connus
- Tests effectués via curl (endpoints, présence des balises servies) et relecture manuelle du JS (pas d'environnement navigateur automatisé disponible dans cette session) — un test manuel en conditions réelles (clavier, clics) reste recommandé avant diffusion large.

### Temps estimé de développement
- ~2h30 (deux modules JS, intégration sur 7 pages, CSS, i18n, tests serveur)

## v1.45

**Date** : 2026-07-14

**Nom de la mise à jour** : Chatbot : cartes intelligentes générées côté backend

Phase C du chantier "chatbot premium" : le chatbot propose désormais des cartes cliquables ("Voir le cours", "Commencer un entraînement", "Revoir cette notion", "Refaire cette série") sous ses réponses, calculées côté backend à partir de vraies correspondances (recherche unifiée + notions faibles), jamais devinées côté frontend.

### Nouveautés
- Nouveau `webapp/chatbot/services/action_cards_service.py::build_cards` : règles sur les résultats de `search_service` (Phase A) et les notions faibles du profil (Phase B), avec seuil de score et dédoublonnage — aucune carte si rien de pertinent (vérifié avec un message hors-sujet).
- `conversation_manager.py::attach_action_cards` : calcule et persiste les cartes sur le dernier message assistant une fois le stream texte terminé (`stream_reply`/`regenerate_last` inchangés, aucune régression sur le streaming existant).
- `db.py` : colonne `cards` (JSON, nullable) sur `chatbot_messages`, migration additive pour les bases existantes ; `add_message`/`list_messages`/`get_message` sérialisent/désérialisent ; nouvelle fonction `set_message_cards`.
- SSE : la trame finale `done` inclut désormais `cards` (`{"done": true, "cards": [...]}`), additif — le format des deltas texte n'a pas changé.
- Frontend `chatbot.js` : rendu des cartes sous chaque réponse (pattern `.card.card--interactive` déjà utilisé par `chapitre-card`), navigation directe (`type: "course"`) ou via le pattern `localStorage "lumis:pending_series"` déjà utilisé par `chapitres.js` (`type: "notion_series"`). Labels résolus via i18n (`chatbot_card_view_course`, `chatbot_card_practice`, `chatbot_card_review_weak`, `chatbot_card_redo_series`, FR/EN).

### Corrections
- (aucune — fonctionnalités additives)

### Optimisations
- (aucune)

### Fichiers modifiés
- `webapp/db.py`, `webapp/server.py`, `webapp/chatbot/conversation_manager.py`, `webapp/static/js/chatbot.js`, `webapp/static/css/chatbot.css`, `webapp/static/js/i18n.js`
- Nouveau : `webapp/chatbot/services/action_cards_service.py`

### Bugs connus
- (aucun identifié)

### Temps estimé de développement
- ~2h (migration DB, service de règles, protocole SSE additif, rendu frontend, tests manuels via curl SSE)

## v1.44

**Date** : 2026-07-14

**Nom de la mise à jour** : Chatbot : contexte enrichi + accueil personnalisé

Phase B du chantier "chatbot premium" : le chatbot connaît désormais automatiquement le prénom de l'élève, son objectif quotidien et ses notions faibles dès l'ouverture, sans aucune saisie supplémentaire.

### Nouveautés
- `context_builder.py::build_context_summary` inclut désormais `pseudo` et `daily_goals` (objectif du jour, calculé par `goals_service` — Phase A) ; `summary_to_text` en tient compte, donc le prompt système envoyé au fournisseur IA connaît aussi l'objectif du jour.
- Nouveau `webapp/chatbot/services/greeting_service.py::build_greeting` : message d'accueil personnalisé (prénom réel, objectif du jour restant/atteint, notion faible à retravailler ou chapitre en cours) — fonction pure, testée avec compte neuf, objectif partiel et notion faible détectée.
- Nouvelle route `GET /api/chatbot/greeting`, wrapper `api.chatbotGreeting()`.
- `chatbot.js` : le texte de l'état vide (`#chatbot-empty-greeting`) est désormais remplacé par l'accueil personnalisé au chargement ; le panneau contextuel droit affiche l'objectif du jour et la série de jours consécutifs.

### Corrections
- (aucune — fonctionnalités additives)

### Optimisations
- (aucune)

### Fichiers modifiés
- `webapp/chatbot/context_builder.py`, `webapp/server.py`, `webapp/static/js/api.js`, `webapp/static/js/chatbot.js`, `webapp/static/chatbot.html`
- Nouveau : `webapp/chatbot/services/greeting_service.py`

### Bugs connus
- (aucun identifié)

### Temps estimé de développement
- ~1h (implémentation + tests manuels via compte invité avec historique simulé)

## v1.43

**Date** : 2026-07-14

**Nom de la mise à jour** : Chatbot : recherche unifiée cours/exercices + objectifs quotidiens (backend)

Phase A du chantier "chatbot premium, assistant pédagogique central" : fondations backend permettant au chatbot (et demain à toute l'app) de chercher dans le contenu réel du site et de connaître l'objectif quotidien de l'élève. Aucune UI encore — préparation pour l'accueil personnalisé (Phase B), les cartes intelligentes (Phase C) et les palettes de commandes (Phases D/E).

### Nouveautés
- Nouvelle route `GET /api/search?q=&scope=cours,exercices&limit=` : recherche unifiée sur les cours (réutilise l'index TF-IDF existant de `knowledge_engine.py`) et sur les exercices (nouvel index TF-IDF léger construit à partir de `exercises_bank.json`, jamais dupliqué en écriture).
- Nouvelle route `GET /api/goals/daily` : objectif quotidien de l'élève agrégé côté backend (exercices faits aujourd'hui, série de jours consécutifs) — même logique que `dashboard.js`, désormais disponible pour tout consommateur backend (le chatbot en premier).
- Nouveau sous-package `webapp/chatbot/services/` (`search_service.py`, `goals_service.py`) pour isoler cette logique métier de `conversation_manager.py`.
- `api.js` : `api.search(q, scope, limit)` et `api.dailyGoals()`.

### Corrections
- (aucune — fonctionnalités additives)

### Optimisations
- (aucune)

### Fichiers modifiés
- `webapp/server.py` (2 nouvelles routes)
- `webapp/static/js/api.js` (2 nouveaux wrappers)
- `webapp/chatbot/knowledge_engine.py` (ajout additif des champs `chapter_id`/`notion_id` sur les notions indexées, nécessaires pour construire les liens de résultat)
- Nouveaux : `webapp/chatbot/services/__init__.py`, `search_service.py`, `goals_service.py`

### Bugs connus
- (aucun identifié)

### Temps estimé de développement
- ~1h30 (exploration architecture + implémentation + tests manuels)

## v1.42

**Date** : 2026-07-13

**Nom de la mise à jour** : Architecture chatbot indépendante du fournisseur IA : FakeProvider par défaut, RetrievalEngine séparé, cache

### Nouveautés
- **FakeProvider** (`webapp/chatbot/providers/fake_provider.py`) : le chatbot fonctionne désormais sans aucune API dès l'installation. Même contrat `ChatProvider` que les fournisseurs IA — assemble une réponse depuis les cours NovaMath réels quand une correspondance nette existe, l'admet honnêtement sinon (jamais d'invention), avec une suggestion concrète (reformuler, Cours, activer Claude/Ollama).
- **RetrievalEngine séparé du Knowledge Engine** (`webapp/chatbot/retrieval_engine.py`) : la mécanique de recherche générique (TF-IDF + cosinus) devient un module à part, sans connaissance métier ; `knowledge_engine.py` sait seulement *où* chercher et délègue la recherche, API publique inchangée.
- **Cache mémoire** (`webapp/chatbot/cache.py`) : réponse réutilisée immédiatement pour une question identique du même utilisateur dans les mêmes conditions (LRU, 200 entrées, intégré dans `conversation_manager.py`).
- **Provider Manager** : `"fake"` devient le fournisseur par défaut ; Anthropic et Ollama restent des options activables sans changement de code, conformément à l'architecture en couches Frontend → ChatController → ConversationManager → PromptBuilder → ContextBuilder → KnowledgeEngine/RuleEngine/MathEngine → RetrievalEngine → ProviderManager → fournisseur actif.
- **Paramètres → Chatbot** : "Aucun (moteur NovaMath, par défaut)" en premier et coché par défaut.

### Corrections
- Aucune (architecture neuve ; les moteurs Rule/Math/Knowledge et les providers Anthropic/Ollama existants n'ont pas changé de comportement).

### Optimisations
- Le cache évite de refaire une recherche TF-IDF ou un appel réseau pour une question déjà posée dans les mêmes conditions.

### Fichiers modifiés
- `webapp/chatbot/providers/fake_provider.py`, `retrieval_engine.py`, `cache.py` (nouveaux)
- `webapp/chatbot/knowledge_engine.py` (délègue la recherche à retrieval_engine)
- `webapp/chatbot/provider_manager.py`, `webapp/auth.py` (fournisseur par défaut : `fake`)
- `webapp/chatbot/conversation_manager.py` (intégration du cache)
- `webapp/server.py` (commentaire ChatController), `webapp/static/js/settings.js` (option "Aucun" par défaut)

### Bugs connus
- Seuil de confiance du FakeProvider calibré à 0.20 (comme `knowledge_engine.try_answer_definition`) après avoir constaté qu'un seuil de 0.10 laissait passer des correspondances non pertinentes sur des questions hors-sujet — corrigé avant livraison.
- Limites déjà documentées en v1.40/v1.41 (retrieval TF-IDF non sémantique, pas d'analyse d'image) inchangées.

### Temps estimé de développement
- Session moyenne : conception de l'architecture en couches, refactor du Knowledge Engine, calibrage empirique du seuil de confiance, vérification bout en bout dans un navigateur réel.

## v1.41

**Date** : 2026-07-13

**Nom de la mise à jour** : Chatbot : Anthropic (API officielle Claude) redevient le fournisseur IA par défaut

### Nouveautés
- **Fournisseur par défaut = Anthropic** (`webapp/chatbot/provider_manager.py`, `webapp/auth.py`) : le chatbot utilise désormais par défaut l'API officielle Anthropic (clé API standard via `ANTHROPIC_API_KEY`), et non plus Ollama/Mistral local. Ollama reste disponible comme alternative 100% locale, sélectionnable dans Paramètres → Chatbot sans aucun changement de code.
- **`AnthropicProvider` complété** (`webapp/chatbot/providers/anthropic_provider.py`) : `health()` effectue un vrai test de connectivité (`client.models.list()`) et distingue clé absente / invalide / API injoignable / quota dépassé, chacun avec un message clair — jamais un abonnement Claude Pro, toujours une clé API classique. `switch_model()` ajouté au contrat de base `ChatProvider`.
- **Erreurs de fournisseur gérées proprement** (`webapp/server.py`) : `AnthropicConnectionError` interceptée aux côtés de `OllamaConnectionError` sur les deux routes de streaming — le site n'affiche jamais une erreur générique quand la cause est connue, et ne plante jamais.
- **Bandeau de disponibilité générique** + re-test immédiat de la santé du fournisseur dès qu'il est changé dans Paramètres → Chatbot (nouvelle route `/api/chatbot/health?provider=...`), sans attendre un rechargement de page.
- **Paramètres → Chatbot** : Claude (Anthropic) apparaît en premier et coché par défaut, Ollama en option locale.

### Corrections
- Condition de course corrigée : changer de fournisseur dans Paramètres re-testait la disponibilité avant que le réglage soit sauvegardé côté serveur (debounce), affichant à tort le bandeau d'indisponibilité de l'ancien fournisseur. Le nouveau fournisseur est désormais transmis explicitement au test de santé.

### Optimisations
- Aucune (mise à jour ciblée sur le fournisseur IA).

### Fichiers modifiés
- `webapp/chatbot/providers/anthropic_provider.py`, `providers/base.py` (`switch_model()`)
- `webapp/chatbot/provider_manager.py`, `webapp/auth.py` (fournisseur par défaut : `anthropic`)
- `webapp/server.py` (gestion de `AnthropicConnectionError`, `/api/chatbot/health?provider=`)
- `webapp/static/js/settings.js`, `chatbot.js`, `api.js`, `webapp/static/chatbot.html` (Claude par défaut, bandeau générique, re-test immédiat)

### Bugs connus
- Aucun nouveau ; les limites déjà documentées en v1.40 (retrieval TF-IDF, pas d'analyse d'image) restent inchangées.

### Temps estimé de développement
- Session courte, ciblée : bascule du fournisseur par défaut, complétion du contrat `ChatProvider` pour Anthropic, correction d'une condition de course découverte en testant le changement de fournisseur en direct dans le navigateur (avec/sans clé API Anthropic, et avec un vrai Ollama local installé sur la machine).

## v1.40

**Date** : 2026-07-13

**Nom de la mise à jour** : Chatbot pédagogique premium : Ollama/Mistral local, Math Engine, Knowledge/RAG Engine, pipeline hybride

### Nouveautés
- **Fournisseur Ollama** local (Mistral par défaut) : le chatbot ne dépend plus d'une API cloud — `stream_chat`/`health`/`available_models` implémentés (`providers/ollama_provider.py`), devenu le fournisseur par défaut (Claude reste disponible en secours, architecture inchangée pour le reste du site).
- Bannière de disponibilité (« moteur IA local non démarré » + Réessayer / Continuer sans le chatbot), testée au chargement et à chaque échec d'envoi (`/api/chatbot/health`).
- **Math Engine** (sympy) : résout équations, fractions, racines, développements, factorisations et pourcentages de façon déterministe, sans jamais appeler le LLM pour un calcul simple.
- **Knowledge Engine / RAG léger** (TF-IDF sur les cours NovaMath) : réponses directes aux définitions non ambiguës, sinon contexte compact injecté dans le prompt LLM (jamais les cours en entier).
- Pipeline hybride Rule Engine → Math Engine → Knowledge Engine → LLM en dernier recours (`conversation_manager.py::_try_internal_answer`).
- Paramètres → Chatbot mis à jour : Ollama par défaut, modèles détectés dynamiquement (`/api/chatbot/models`).
- Pièce jointe PDF réelle (extraction de texte via PyMuPDF, jamais écrite sur disque) ; limite image assumée et annoncée (pas de vision/OCR local dans cette version).

### Corrections
- Aucune (extension de l'architecture Phase 1, déjà solide, sans réécriture).

### Optimisations
- Contexte RAG minimal (quelques notions, pas le corpus entier) : moins de tokens envoyés au LLM. Index TF-IDF construit une seule fois, mis en cache.

### Fichiers modifiés
- `webapp/chatbot/providers/ollama_provider.py`, `providers/base.py`, `provider_manager.py`
- `webapp/chatbot/math_engine.py`, `knowledge_engine.py`, `attachments.py` (nouveaux)
- `webapp/chatbot/conversation_manager.py`, `prompt_builder.py`
- `webapp/auth.py`, `webapp/server.py`
- `webapp/static/js/settings.js`, `chatbot.js`, `api.js`, `webapp/static/chatbot.html`, `css/chatbot.css`
- `requirements.txt`

### Bugs connus
- Retrieval TF-IDF imparfait sur des notions proches (ambiguïté assumée : le moteur préfère s'abstenir et laisser le LLM trancher plutôt que de mal répondre seul).
- Images jointes non analysées (pas de vision/OCR local) — limite annoncée à l'élève, pas un bug caché.

### Temps estimé de développement
- Session unique, longue durée : audit de la Phase 1 existante, provider Ollama, Math Engine, Knowledge Engine, intégration pipeline hybride, Paramètres, pièce jointe PDF, débogage (accents, exposants composés), vérification bout en bout avec un vrai appel Ollama/Mistral.

## v1.30

**Date** : 2026-07-13

**Nom de la mise à jour** : Chatbot pédagogique NovaMath (Phase 1)

### Nouveautés
- Nouvel onglet **Chatbot** dans la sidebar (`chatbot.html`) : conversations multiples avec historique, recherche, épinglage, renommage et suppression — même look & feel que le reste de NovaMath (cartes, boutons, tokens de couleur, sidebar rétractable).
- Réponses en **streaming** (SSE), rendu **Markdown + KaTeX** (via `marked.js` + `mathrender.js` déjà existant), boutons par message (copier, régénérer, continuer, j'aime/je n'aime pas, exporter Markdown, exporter PDF via impression navigateur).
- Architecture en couches complète : `webapp/chatbot/` avec Provider Manager (abstraction multi-fournisseurs), Provider Anthropic (Claude) fonctionnel, Context Builder (niveau, précision, notions faibles/maîtrisées, chapitres en cours — lu depuis les données NovaMath existantes), Prompt Builder (méthode pédagogique indice → indice → explication → méthode → solution, notation mathématique standard obligatoire), Rule Engine (court-circuite le LLM pour les salutations/identité), Conversation Manager (orchestration + quota).
- Nouvelles tables SQLite `conversations` / `chatbot_messages` / `chatbot_quota` (`webapp/db.py`), quota quotidien de 200 messages par utilisateur (429 explicite si dépassé côté UI).
- Nouvelle section **Paramètres → Chatbot** (`settings.js`) : fournisseur IA (Claude actif, autres grisés « bientôt disponible »), modèle, créativité, longueur de réponse, niveau d'explication, streaming/historique/mémoire activables.
- Panneau contextuel (colonne de droite) affichant en direct ce que le chatbot sait de la progression de l'élève.
- Clé API Anthropic lue exclusivement côté serveur (`ANTHROPIC_API_KEY`), jamais transmise au frontend.

### Corrections
- Aucune (nouvelle fonctionnalité additive, aucune route/fichier existant modifié dans sa logique).

### Optimisations
- Rule Engine : les salutations/questions d'identité ne déclenchent aucun appel IA.

### Fichiers modifiés
- Nouveaux : `webapp/chatbot/` (package complet), `webapp/static/chatbot.html`, `webapp/static/js/chatbot.js`, `webapp/static/css/chatbot.css`.
- Modifiés : `webapp/server.py` (routes `/api/chatbot/*` + page protégée), `webapp/db.py` (schéma + CRUD conversations/messages/quota), `webapp/auth.py` (préférences par défaut `chatbot`), `webapp/static/js/api.js`, `webapp/static/js/settings.js`, `webapp/static/js/i18n.js`, sidebar de `dashboard.html`/`chapitres.html`/`cours.html`/`exercice.html`/`profil.html`, `requirements.txt` (ajout `anthropic`).

### Bugs connus
- Phase 1 uniquement : pas de RAG documentaire sur les cours, pas de moteur de calcul symbolique indépendant (le LLM explique mais ne résout pas lui-même), Rule Engine minimal (couverture sans LLM très inférieure aux >70% visés à terme), un seul fournisseur IA réellement branché (Claude), pièces jointes (image/PDF/exercice) affichées mais non traitées (placeholder texte), export PDF via impression navigateur plutôt qu'une génération dédiée, pas de mémoire long-terme compressée (seulement les N derniers messages). Ces limites sont volontaires et prévues pour les phases suivantes.
- Vérification visuelle (rendu navigateur réel) non réalisée dans l'environnement de développement utilisé pour cette version (pas de navigateur disponible) — uniquement testé via API/curl (CRUD conversations, streaming SSE, quota, contexte, non-régression des pages existantes). À vérifier visuellement avant usage réel.

### Temps estimé de développement
- Une session de développement assistée (conception + implémentation backend/frontend + tests API).

## v1.22

**Date** : 2026-07-13

**Nom de la mise à jour** : Rose moderne + notation mathématique réelle (quiz, exercices, cours)

### Nouveautés
- Aucune (finalisation esthétique et de contenu).

### Corrections
- Couleur d'accent « Rouge » (Apparence) remplacée par un rose moderne (`#db2777`/`#f472b6`), appliquée automatiquement partout (boutons, switches, badges, focus...). Clé interne inchangée, aucune migration nécessaire.
- Refonte du moteur de notation mathématique (`07_naturalize_exercises.py`) : fin du « tout épeler en mots français » (`7 puissance 5 fois...`), remplacé par une vraie écriture mathématique (`(7⁵ × 7⁻²)/7⁴`) — symboles Unicode quand c'est fiable (×, ÷, √, exposants réels, fractions simples, ≥/≤/≠/∈, ℕ/ℤ/ℚ/ℝ/ℂ...), repli sur LaTeX/KaTeX pour les constructions complexes (vecteurs, écarts-types, systèmes, coordonnées indexées).
- `exercises_bank_natural.json` (2085 exercices, servie par défaut aux élèves) régénéré ; `exercises_bank_reformulations.json` nettoyé de la même façon (nouveau script `09_naturalize_reformulations.py`).
- Élimination de nombreux résidus LaTeX auparavant non convertis (fractions sans accolades, `\sigma_x`/`\sigma^2` mal découpés, `\approx`, `\mathbb{D}`, exposants composés type `a^{n+m}` affichés cassés faute de protection KaTeX).

### Optimisations
- Aucune.

### Fichiers modifiés
- `webapp/static/css/tokens.css`, `webapp/static/css/settings.css`, `webapp/static/js/settings.js`
- `tools/legacy-pipeline/07_naturalize_exercises.py` (réécrit), `09_naturalize_reformulations.py` (nouveau)
- `exercises_bank_natural.json`, `exercises_bank_reformulations.json`

### Bugs connus
- Aucun identifié après vérification visuelle bout en bout (mode invité, palette, quiz puissances/vecteurs/systèmes).

### Temps estimé de développement
- Session unique, longue durée : refonte du moteur de notation, débogage itératif sur 2085 exercices × 3 fichiers, tests visuels.

## v1.21

**Date** : 2026-07-13

**Nom de la mise à jour** : Finalisation onglet Cours : rendu KaTeX, figures et banque d'exercices

### Nouveautés
- 5 nouvelles figures géométriques (SVG vectoriel, repère/grille/axes) pour les notions du Chapitre 6 « Droites du plan et systèmes d'équations » qui n'en avaient aucune, + 1 figure pour la dernière notion sans illustration du Chapitre 5.
- Note discrète sur la page Entraînement indiquant que le contenu des exercices reste en français (clé i18n existante, jamais câblée jusqu'ici).

### Corrections
- **Bug majeur (rendu KaTeX)** : les 119 étapes de calcul des exemples résolus, sur les 12 chapitres de cours, n'étaient jamais entourées de `$...$` et s'affichaient en LaTeX brut illisible. Corrigé une fois pour toutes dans le renderer (`cours.js`).
- Icône « livre » résiduelle sur les cartes de l'onglet Exercices remplacée (icônes `checklist`/`layers`).
- Faute de frappe présente depuis plusieurs versions : titre du Chapitre 8 « Varaitions et extrmums » → « Variations et extremums » (`Programme AI.json`).
- 148 flèches vectorielles unicode combinantes ne s'affichant pas (police non supportée) remplacées par la notation LaTeX `\vec{...}` dans la banque d'exercices.
- Pipeline de naturalisation des exercices complété (`\dfrac`, `\vec` sans accolades, `\pm`, `\cdot`, `\%`, virgule décimale, `+/-l'infini`) — ~500 exercices avaient un résidu LaTeX non converti dans `exercises_bank_natural.json`, régénéré.
- Suppression d'une étape de solution hors-sujet (note de programmation Python/SymPy) glissée par erreur dans un exercice.
- Uniformisation de l'astérisque informatique (`2*4`) en notation mathématique (`2×4`) dans 23 étapes de solution.

### Optimisations
- Aucune (corrections de contenu et de rendu).

### Fichiers modifiés
- `webapp/static/js/cours.js`, `webapp/static/js/chapitres.js`, `webapp/static/exercice.html`
- `webapp/static/data/cours/chapitre_5.json`, `chapitre_6.json`
- `Programme AI.json`
- `exercises_bank.json`, `exercises_bank_reformulations.json`, `exercises_bank_natural.json`
- `tools/legacy-pipeline/07_naturalize_exercises.py`, `tools/legacy-pipeline/08_fix_bank_artifacts.py` (nouveau)

### Bugs connus
- Dans `exercises_bank_natural.json`, la conversion mécanique de `$\vec{u}$` en « le vecteur u » peut produire une légère redondance grammaticale quand la phrase source disait déjà « Les vecteurs » au pluriel — limite connue de l'approche déterministe du pipeline.

### Temps estimé de développement
- Session unique, longue durée : audit complet des 12 chapitres et de la banque de 2085 exercices (agents dédiés), correction d'un bug de rendu affectant l'ensemble du site, figures géométriques, tests visuels bout en bout (Playwright, mode invité).

## v1.20

**Date** : 2026-07-13

**Nom de la mise à jour** : Refonte Exercices (ex-Chapitres) : filtres, favoris, multi-selection + Profil en lecture seule

### Nouveautés
- **Onglet "Chapitres" renommé en "Exercices"** partout sur le site (sidebar des 5 pages, titre d'onglet, `<h1>`, i18n FR/EN, textes d'aide, liens du footer landing, message de reprise de session) avec une nouvelle icône checklist (Lucide-style, cohérente avec le reste du système) distincte de l'icône "Cours".
- **Barre de filtres** sur la page Exercices : Tout / En cours / Maîtrisé / Non maîtrisé / Enregistrés, pastilles animées, réutilisant exactement la fonction `masteryLabel()` déjà utilisée pour les notions (aucune logique de maîtrise parallèle créée). "En cours" détecte automatiquement la série en pause ; chaque filtre affiche un message dédié quand il est vide (ex. « Aucune série en cours. »).
- **Favoris ("Enregistrés")** : étoile discrète sur chaque carte de chapitre, état persistant (nouveau champ `favorites` dans les préférences existantes, `/api/settings` — aucun nouveau point d'API), survit à la fermeture du navigateur, mise à jour immédiate de l'icône et du filtre "Enregistrés" au clic.
- **Multi-sélection des notions** : cliquer sur une notion ne démarre plus une série immédiatement — elle devient une case à cocher premium (style NovaMath). Un bouton "Commencer la série" apparaît sous la liste, désactivé tant qu'aucune notion n'est sélectionnée, puis lance une série couvrant l'union des exercices des notions choisies. Tous les paramètres d'entraînement existants (nombre d'exercices, chronomètre, niveau, mode naturel, ordre aléatoire) s'appliquent sans changement, via la même logique `exercice.js`/Paramètres → Entraînement. La reprise d'une série multi-notions déjà en cours reste détectée automatiquement (chaque notion concernée affiche "Reprendre").
- **Page Profil simplifiée** : devient une page de consultation pure (avatar, pseudo, niveau, progression, statistiques, badges, historique, calendrier d'activité). Toute modification (pseudo, avatar, informations personnelles) a été retirée — désormais centralisée exclusivement dans Paramètres → Compte, qui gérait déjà ces mêmes actions (suppression du doublon de fonctionnalité). "Se déconnecter" et "Supprimer mon compte" restent accessibles depuis le Profil.

### Corrections
- Aucune (fonctionnalités nouvelles/renommage, pas de bug préexistant corrigé).

### Optimisations
- Aucune régression de performance : filtres et favoris sont calculés/appliqués côté client sur des données déjà chargées (`api.chapters()`), sans appel réseau supplémentaire ; les favoris réutilisent le mécanisme de sauvegarde optimiste déjà en place dans `settingsManager.js`.

### Fichiers modifiés
- `webapp/static/js/chapitres.js` (réécrit : filtres, favoris, multi-sélection, bouton de démarrage)
- `webapp/static/css/chapitres.css` (barre de filtres, étoile favoris, checkboxes de notion)
- `webapp/static/js/icons.js` (icône `checklist`)
- `webapp/auth.py` (`favorites: []` dans `DEFAULT_SETTINGS`)
- `webapp/static/{dashboard,chapitres,cours,exercice,profil}.html` (icône + libellé "Exercices" dans la sidebar)
- `webapp/static/js/i18n.js` (clé `nav.exercices`)
- `webapp/static/{index.html,js/auth.js,js/settings.js,js/exercice.js,js/cours.js}` (textes utilisateur mentionnant l'onglet)
- `webapp/static/profil.html`, `webapp/static/js/profil.js` (suppression de toute UI de modification)

### Bugs connus
- Aucun identifié après tests (Playwright headless : filtres, favoris + persistance après rechargement, multi-sélection + démarrage de série, reprise de série multi-notions, Profil en lecture seule vérifié à la fois en mode invité et sur un compte réel, édition du pseudo toujours fonctionnelle depuis Paramètres, clair/sombre, sidebar réduite, mobile, 0 erreur JS fatale sur les 6 pages).

### Temps estimé de développement
- Session unique, longue durée : refonte de la page Exercices (filtres, favoris, multi-sélection), simplification du Profil, renommage complet de l'onglet, tests automatisés bout en bout.

## v1.17

**Date** : 2026-07-13

**Nom de la mise à jour** : Sidebar : bouton a gauche + icones flamme et entrainement refaites

### Nouveautés
- Le bouton de réduction de la sidebar (chevrons) est désormais aligné à gauche (`align-self: flex-start`) au lieu de droite — comportement plus proche de ChatGPT, sans changer ni ses animations ni son fonctionnement ouvrir/fermer.

### Corrections
- **Icône flamme (série/streak)** : remplacée par le tracé Lucide officiel `flame` (utilisé dans `icons.js` et sur le chip de série du dashboard) — l'ancien tracé donnait un rendu légèrement déséquilibré, la nouvelle version est symétrique, nette et bien reconnaissable.
- **Icône "Entraînement"** de la sidebar : l'ancien tracé (deux crayons croisés) contenait un segment de tracé orphelin non fermé, produisant un rendu visuellement cassé. Remplacée par une icône haltère construite à partir de primitives simples (deux `rect` + une `line`), parfaitement symétrique et centrée, qui évoque clairement l'entraînement/la pratique.
- Toutes les icônes de la sidebar revérifiées : même `viewBox="0 0 24 24"`, même `stroke-width="2"`, `currentColor`, mêmes dimensions (19×19 rendu) et même espacement avec le texte (`gap: 12px`) — aucune incohérence résiduelle trouvée.

### Optimisations
- Aucune (changement ciblé, pas de refactoring).

### Fichiers modifiés
- `webapp/static/css/base.css` (position du bouton de réduction)
- `webapp/static/js/icons.js` (icône `flame`)
- `webapp/static/dashboard.html` (icône flamme du streak-chip)
- `webapp/static/dashboard.html`, `chapitres.html`, `cours.html`, `exercice.html`, `profil.html` (icône "Entraînement")

### Bugs connus
- Aucun identifié après tests (Playwright headless : bouton toggle avant/après rechargement, icônes zoomées, drawer mobile, 0 erreur console).

### Temps estimé de développement
- ~30 min.

## v1.16

**Date** : 2026-07-13

**Nom de la mise à jour** : Sidebar retractable + coherence des icones

### Nouveautés
- **Sidebar rétractable** (comportement façon ChatGPT) : bouton dédié en haut de la sidebar pour basculer entre mode complet (logo + libellés + profil) et mode réduit (icônes seules, 72px, avatar circulaire). Préférence mémorisée en localStorage, réappliquée instantanément au chargement (aucun flash de mise en page).
- **Tooltips personnalisés** en mode réduit : au survol d'une icône, un vrai composant tooltip (CSS `::after`, pas de `title=""` natif) affiche le libellé, avec transition douce (opacity + translate, 200 ms).
- **Menu mobile coulissant (drawer)** sous 860px : bouton hamburger fixe qui ouvre la sidebar en overlay par-dessus le contenu, avec fond assombri cliquable pour refermer, fermeture automatique après un clic sur un lien ou touche Échap.
- **Contenu principal auto-adaptatif** : le dashboard et les autres pages utilisent tout l'espace disponible dès que la sidebar est réduite, via un layout flex pur (aucun rechargement, aucune reconstruction de composants).
- Ajout de deux icônes SVG au système existant (`chevronsLeft`, `menu`) pour rester sur la même bibliothèque de tracés (style Lucide, `stroke-width="2"`, `currentColor`) que le reste du site.

### Corrections
- Audit complet des icônes de la sidebar et des menus : le set existant (`icons.js` + SVG inline) respectait déjà une géométrie homogène (viewBox 24×24, trait 2px, `currentColor`) — aucune icône déformée ou mal proportionnée trouvée ; seules deux icônes manquantes ont été ajoutées pour le nouveau bouton de réduction et le déclencheur mobile.
- Le badge "Mode invité" (bandeau violet à côté du logo) déborde désormais correctement masqué en mode réduit au lieu d'être tronqué visuellement.
- Le tooltip custom ne s'affichait pas car `.sidebar` avait `overflow-x: hidden` (nécessaire pour rien en pratique) — retiré pour laisser le tooltip déborder proprement à droite de la sidebar.

### Optimisations
- `.app-shell` migré de CSS Grid vers Flexbox pour permettre une transition de largeur fluide et purement CSS (`width`, `opacity`, `transform` uniquement, conforme à la contrainte de performance demandée), sans JS de repositionnement.
- Logique de sidebar centralisée dans un unique module `webapp/static/js/sidebar.js`, injecté dans les 5 pages plutôt que dupliqué (bouton de réduction, tooltips, drawer mobile, overlay, persistance) — un seul endroit à maintenir pour tout le comportement de navigation.

### Fichiers modifiés
- `webapp/static/js/sidebar.js` (nouveau)
- `webapp/static/js/icons.js` (ajout `chevronsLeft`, `menu`)
- `webapp/static/css/base.css` (mode réduit, bouton toggle, tooltips, app-shell en flex)
- `webapp/static/css/responsive.css` (drawer mobile)
- `webapp/static/dashboard.html`, `chapitres.html`, `cours.html`, `exercice.html`, `profil.html` (inclusion de `sidebar.js`, `span.brand-name`)

### Bugs connus
- Aucun identifié après tests (Playwright headless : 5 pages, clair/sombre, desktop/mobile, persistance après rechargement, 0 erreur console).

### Temps estimé de développement
- ~2h (audit, implémentation, tests automatisés avec captures d'écran, corrections des 2 bugs de régression détectés en test).

## v1.15

**Date** : 2026-07-13

**Nom de la mise à jour** : Refonte UI/UX sans emoji + cours simplifiés avec figures SVG

### Nouveautés
- **Zéro emoji sur tout le site** : tous les emojis remplacés par des icônes SVG monochromes cohérentes avec le design NovaMath, dans les 4 couches du site (backend, pages HTML, JS frontend, PDF exporté).
- Nouvelles icônes ajoutées à `icons.js` : `trophy`, `graduationCap`, `sun`, `medal`, `scale`, `ruler`, `zap`, `sparkles`, `sprout`. Nouveau module `badgeIcons.js` mutualisant la correspondance badge → icône.
- **Cours entièrement réécrits** pour un public collège/lycée en difficulté : phrases courtes, vocabulaire simple. Nouvelle structure fixe par notion : intro → objectif → définition → règles importantes (cartes) → méthode (étapes numérotées et colorées) → exemples détaillés (calcul étape par étape) → erreurs fréquentes → astuce → à retenir (5 idées max) → mini-quiz.
- Nouveau lecteur de cours en page unique (`cours.js`/`cours.css` réécrits), remplace l'ancienne navigation section par section.
- Nouveau générateur de figures géométriques SVG (`geomSvg.js`), intégré aux notions de géométrie des chapitres 4 et 5.
- Passe responsive/accessibilité dédiée au module Cours.

### Corrections
- Duplication de `BADGE_ICONS` entre `dashboard.js` et `profil.js` supprimée.
- Historique serveur (`/api/practice/result`) : icônes codées en dur (code mort, jamais affiché) remplacées par du texte clair.

### Optimisations
- Aucune régression de performance : figures SVG générées à la volée, contenu de cours toujours chargé à la demande.

### Fichiers modifiés
Nouveaux : `webapp/static/js/{badgeIcons,geomSvg}.js`.
Modifiés : `webapp/server.py`, `webapp/static/js/{icons,cours,dashboard,profil,exercice,evaluation,resume,chapitres,reviews,pdfExport}.js`, `webapp/static/{dashboard,evaluation,index}.html`, `webapp/static/css/{cours,dashboard,exercice,reviews}.css`, les 12 fichiers `webapp/static/data/cours/chapitre_1..12.json`.

### Bugs connus
- Pas de test interactif dans un navigateur réel (rendu visuel des figures SVG, contraste effectif) — validation faite via tests serveur/API et vérification statique de l'absence d'emoji dans tout le code source.
- Figures géométriques disponibles seulement pour une partie des notions des chapitres 4 et 5 ; les autres chapitres se prêtent mieux aux tableaux et exemples chiffrés.

### Temps estimé de développement
- Session unique, longue durée : audit et remplacement de tous les emojis, conception d'un schéma de contenu simplifié, réécriture des 52 notions, création d'un générateur de figures SVG, réécriture du lecteur de cours.

## v1.14

**Date** : 2026-07-13

**Nom de la mise à jour** : Ajout du module Cours

### Nouveautés
- Nouvel onglet **Cours** dans la sidebar (icône livre), premier onglet menant à un véritable espace d'apprentissage : 12 chapitres, 52 notions, ~200 sections de cours rédigées (définitions, propriétés, méthodes, exemples résolus étape par étape, erreurs fréquentes, astuces, résumé, fiche mémo).
- Contenu pédagogique entièrement réécrit (jamais un simple affichage de PDF) à partir des PDF officiels du programme déjà présents dans le dépôt (`Chapitres/*.pdf`, texte pré-extrait dans `texts/*.txt`), stocké en JSON structuré (`webapp/static/data/cours/chapitre_1..12.json`), chargé à la demande (un seul chapitre à la fois, jamais les 12 d'un coup).
- Lecteur de notion avec navigation section par section, rendu mathématique KaTeX réel, boîtes visuelles typées par nature (définition, propriété, méthode, exemple, attention, astuce, tableau), cohérentes avec le thème/accent/transparence/animations choisis dans Paramètres.
- Mini-quiz de fin de notion réutilisant la banque d'exercices existante (auto-évaluation « J'ai réussi / À revoir »), score enregistré.
- Progression de lecture sauvegardée et reprise exacte (section courante, statut par notion, score de quiz) via un nouvel espace de stockage par utilisateur et deux nouveaux endpoints `GET/POST /api/course-progress`.
- Carte "Reprendre mon cours" sur le Dashboard, pointant directement vers la dernière notion en cours de lecture.
- Respect intégral des règles déjà en vigueur : mode invité limité à 2 chapitres, progression non conservée pour les invités (purgée avec le reste du compte), interface traduite FR/EN (le contenu pédagogique reste en français dans les deux langues, comme les exercices).
- Script d'aide `tools/regenerate_course_content.py` pour réextraire le texte d'un PDF de programme remplacé.

### Corrections
- Aucune (mise à jour additive, aucune fonctionnalité existante modifiée).

### Optimisations
- Chargement paresseux du contenu de cours (un fichier JSON par chapitre) pour un temps de chargement de page inchangé.
- Réutilisation intégrale de l'architecture et des styles de l'onglet Chapitres (grille de cartes, accordéon de notions, tokens CSS) plutôt qu'un système parallèle.

### Fichiers modifiés
Nouveaux : `webapp/static/cours.html`, `webapp/static/js/{cours,courseResume}.js`, `webapp/static/css/cours.css`, `webapp/static/data/cours/chapitre_1..12.json` (12 fichiers), `tools/regenerate_course_content.py`.
Modifiés : `webapp/server.py`, `webapp/auth.py`, `webapp/static/js/{api,i18n,dashboard}.js`, `webapp/static/dashboard.html`, sidebar de `dashboard.html`/`chapitres.html`/`exercice.html`/`profil.html`.

### Bugs connus
- Validation effectuée via tests serveur/API réels (curl, sessions invité réelles, vérification de la purge de progression), pas de test interactif dans un navigateur réel — à confirmer visuellement.
- Les schémas géométriques (repères, vecteurs tracés) ne sont pas encore illustrés graphiquement, seulement décrits en texte/tableaux.
- Vidéos, synthèse vocale, flashcards et démonstrations animées ne sont pas implémentées ; l'architecture en sections JSON typées est conçue pour les accueillir sans réécriture.

### Temps estimé de développement
- Session unique, longue durée, couvrant l'architecture complète du module, la rédaction pédagogique des 12 chapitres/52 notions, et l'intégration au Dashboard/Paramètres/i18n existants.

## v1.13

**Date** : 2026-07-12

**Nom de la mise à jour** : Refonte complète du système de Paramètres

### Nouveautés
- Système de Paramètres entièrement repensé : popup unique (composant `popup.js` générique réutilisé par tous les popups du site) remplaçant l'ancienne page `settings.html`, ouvert via une petite icône engrenage en bas de la sidebar (même style que l'ancien bouton thème).
- `SettingsManager` global (`settingsManager.js`) : source de vérité unique des préférences, avec événement `novamath:settings-changed` propagé en direct à tout le site (thème, couleur, langue, entraînement...) sans reload.
- Couleur d'accent réellement propagée à tout le site : sidebar, boutons, badges, graphes du Dashboard et du Profil, anneau XP, confettis, `meta theme-color` — plus aucune couleur violette codée en dur ignorant le choix de l'utilisateur.
- Carte "Objectif quotidien" sur le Dashboard : progression du jour, barre animée, pourcentage, badge visuel à l'atteinte de l'objectif, mise à jour en direct.
- Export PDF premium du rapport de progression (`pdfExport.js`, jsPDF chargé à la demande) : résumé général, progression par chapitre/notion, statistiques par niveau, objectif quotidien, historique récent, conseils personnalisés — thème clair fixe, pagination, en-tête répété.
- Interface traduite en français/anglais (`i18n.js`) : sidebar, popup Paramètres, section Aide & À propos ; les énoncés d'exercices restent volontairement en français dans les deux langues. Langues supplémentaires (arabe, espagnol, allemand) affichées grisées "Bientôt disponible".
- Section "Aide & À propos" entièrement rédigée (contenu réel, pas de placeholder) : présentation, mission, fonctionnement, FAQ, guide utilisateur, contact, CGU, confidentialité, cookies, mentions légales, roadmap, crédits/technologies, sécurité.
- Système de versioning décimal professionnel (`create_version_snapshot.py` v2, fichier racine `VERSION`, `webapp/static/js/version.js`) : chaque mise à jour importante crée désormais un instantané autonome `versions/NovaMath_v{X.YY}/` avec RUN.bat/RUN.ps1/README/CHANGELOG dédiés, sans jamais supprimer les versions précédentes.

### Corrections
- **Bug du chronomètre qui ne se désactivait pas** : `exercice.js` ne relisait les préférences d'entraînement qu'une seule fois au chargement de la page. Il s'abonne désormais à `novamath:settings-changed` et coupe le chrono en direct dès que le toggle passe à OFF, même série déjà affichée.
- **Bug des séries bloquées (ex. à 7 exercices)** : la reprise d'une série en pause (`resumeSeries()`) recalculait `SERIES_TOTAL` avec la préférence *actuelle* alors que la file de questions (`seriesQueue`) restait figée à l'ancienne taille, causant une désynchronisation. Corrigé : une série reprise réutilise son propre total d'origine ; toute série démarrée *depuis zéro* relit systématiquement la préférence en vigueur.
- Catégorie "Notifications" (menu mort, aucune logique d'envoi réelle) supprimée entièrement, frontend et backend (`auth.py::DEFAULT_SETTINGS`).
- Confidentialité : encadré "Zone sensible" retiré (design), bouton "Télécharger mes données personnelles" supprimé (doublon avec l'export PDF).
- Les 3 boutons d'export dupliqués (statistiques / toutes les données / données personnelles), qui produisaient tous le même JSON brut, fusionnés en un seul export PDF réel.
- Bouton de changement de thème retiré de la sidebar (doublon avec Paramètres → Apparence) ; sidebar recentrée automatiquement.

### Optimisations
- Centralisation de l'initialisation (thème, popup Paramètres, traductions) auparavant dupliquée dans chaque script de page (`dashboard.js`, `chapitres.js`, `exercice.js`, `profil.js`).
- Mise à jour optimiste des préférences (`SettingsManager.setSetting`) : application immédiate en mémoire/cache/DOM, persistance serveur en arrière-plan avec debounce.
- jsPDF chargé paresseusement (uniquement au clic sur "Exporter mon rapport"), aucun impact sur le temps de chargement des pages.

### Fichiers modifiés
Nouveaux : `webapp/static/js/{popup,settingsManager,settingsPopup,pdfExport,i18n,version}.js`.
Modifiés (liste non exhaustive) : `webapp/static/js/{settings,theme,exercice,dashboard,profil,chapitres,animations}.js`, `webapp/static/css/{tokens,base,settings,dashboard}.css`, `webapp/static/{dashboard,chapitres,exercice,profil}.html`, `webapp/auth.py`, `webapp/server.py`, `create_version_snapshot.py` (nouveau système de versioning décimal), `CHANGELOG.md` (racine).
Archivé : `webapp/static/settings.html` → `settings.html.removed` (remplacé par le popup).

### Bugs connus
- Traduction i18n : couvre la sidebar, le popup Paramètres et Aide & À propos ; ne couvre pas encore le contenu détaillé du Dashboard/Chapitres/Profil/landing (chantier volumineux, à poursuivre en v1.0x).
- Pas de test navigateur interactif réel (clics, ouverture effective du popup PDF) dans cette version — validation effectuée via tests serveur/API/markup (curl, session invité réelle). À confirmer visuellement.
- `api.exportData`/`GET /api/data/export` restent disponibles côté backend mais ne sont plus appelés par aucune UI (gardés pour un futur usage RGPD).

### Temps estimé de développement
- Session unique, longue durée (~1 journée de travail équivalent), couvrant la refonte complète du système de Paramètres, la correction de deux bugs critiques (chrono, séries bloquées), l'export PDF, l'i18n et le nouveau système de versioning.

## v1.12

**Date** : 2026-07-11

### Contexte — Root Cause Analysis, pas un patch
Deux problèmes signalés : le composant "Créer un compte" de la sidebar jugé visuellement lourd et mal
intégré au design system, et surtout le bug le plus persistant du projet — le Mode Invité ne se
réinitialisait pas au retour sur la page d'accueil, malgré plusieurs tentatives de correction dans les
versions précédentes (v1.10, v1.11). Cette version identifie la cause racine exacte du second problème
(ci-dessous) plutôt que d'ajouter un nouveau garde-fou ad hoc par-dessus les précédents, et referme le
composant sidebar dans le même mouvement.

### PROBLÈME N°2 — Root Cause Analysis : pourquoi le Mode Invité survivait au retour sur la landing page

**Cause exacte** : `webapp/server.py` crée l'application avec `Flask(__name__, static_folder="static",
static_url_path="")` — ce qui signifie que **chaque fichier de `webapp/static/` est automatiquement servi
tel quel à son propre nom de fichier**, y compris `index.html` à l'URL `/index.html`. La route explicite
`@app.route("/") def index()` ne couvrait donc que `/` : quiconque atteignait `/index.html` directement
(bouton "retour" du navigateur, lien direct, rechargement conservant l'URL) recevait le fichier brut via le
handler statique automatique de Flask, **sans jamais passer par la moindre vérification de session** — very
exactement le trou de sécurité que `PROTECTED_PAGES`/`_serve_protected()` avait déjà comblé pour
`dashboard.html`/`chapitres.html`/etc., mais qui n'avait jamais été comblé pour `index.html` lui-même.

Conséquence concrète : un invité revenant sur la page d'accueil par ce chemin gardait un cookie de session
invité toujours valide. Côté client, `auth.js` interroge `/api/auth/me` au chargement et stocke le résultat
dans `currentAccount` ; tant qu'un compte invité valide existait, `.js-start-guest-eval` ("Démarrer
l'évaluation") **réutilisait volontairement cette session** (logique ajoutée en v1.10 pour ne pas faire perdre
sa progression à un invité qui continue son parcours) au lieu d'en recréer une neuve — l'ancien historique
réapparaissait donc systématiquement. Une fois `evaluation.html` rechargé avec le même identifiant de compte
injecté (`window.__NOVAMATH_USER_ID__`), le garde `syncAccountScope()` de `store.js` (conçu à l'origine pour
purger le cache local lors d'un changement de compte) ne détectait lui non plus aucun changement — puisque
l'identifiant était objectivement resté le même — et laissait donc `lumis:stats` intact en `localStorage`.

En clair : **deux mécanismes de sécurité existaient déjà et fonctionnaient correctement** (le gating des
pages protégées, et la purge de cache par changement d'id de compte) — mais la landing page elle-même
n'avait jamais été intégrée dans ce système, ce qui rendait les deux mécanismes inopérants dans ce cas précis
puisqu'aucun "nouveau" compte n'était jamais réellement créé.

### Correction — la landing page devient un point de passage unique et autoritaire
- `webapp/server.py::_serve_landing()` remplace l'ancienne vue `index()` et est désormais enregistrée
  explicitement sur **les deux routes** `/` et `/index.html` via `app.add_url_rule` (une règle explicite est
  toujours prioritaire sur la règle générique du handler statique dans le routage Werkzeug — même technique
  déjà éprouvée par `PROTECTED_PAGES`). Le contournement est donc structurellement fermé, pas contourné.
- Cette vue applique une règle simple et absolue : si le compte résolu est un **invité**, sa session est
  détruite immédiatement et sans exception avant même de renvoyer le HTML — `auth._purge_account()` (ligne
  DB + fichier de stats), `session.clear()` (progression de quiz Flask en cours), et suppression des cookies
  `nm_session`/`nm_csrf` de la réponse. Un compte réel garde exactement le comportement existant
  (redirection vers `/dashboard.html`, jamais concerné par cette purge).
- Conséquence directe et automatique : la prochaine page protégée visitée (`evaluation.html`) reçoit un
  identifiant de compte **forcément différent** (nouvel invité, nouvel id auto-incrémenté) — le mécanisme
  `syncAccountScope()` de `store.js`, qui existait déjà, se déclenche donc enfin correctement et vide tout le
  cache local (`lumis:stats`, `lumis:profile`, `lumis:series_in_progress`, etc.). Aucune nouvelle logique de
  purge de cache n'a dû être inventée : le mécanisme existant fonctionne désormais parce que sa condition de
  déclenchement (changement réel de compte) est enfin garantie à chaque passage par la landing page.
- Défense en profondeur côté client : `store.js::resetGuestLocalState()` (nouveau) est appelée par
  `auth.js` dès que la landing page constate qu'aucun compte n'est actif — purge immédiate de
  `localStorage`/`sessionStorage` liés à l'invité, sans attendre le prochain chargement d'une page protégée.

### Pourquoi ce problème ne peut plus se reproduire
- La destruction de session n'est plus une conséquence indirecte d'un délai d'inactivité (v1.11) ou d'un choix
  explicite à l'inscription (v1.10) : elle est désormais **inconditionnelle et centralisée** à l'unique endroit
  par lequel n'importe quel chemin de retour vers la page d'accueil doit obligatoirement passer.
- Il ne peut plus exister de second chemin non gardé vers `index.html`, puisque le handler statique
  générique de Flask ne peut plus jamais être atteint pour ce fichier précis (règle explicite prioritaire).
- Le cycle de vie de l'invité est maintenant couvert par trois mécanismes indépendants et complémentaires,
  chacun couvrant un déclencheur distinct listé par le cahier des charges : cookie de session non persistant
  (fermeture du navigateur, v1.11), expiration par inactivité de 2h (absence prolongée, v1.11), destruction
  immédiate à l'arrivée sur la landing page (retour explicite à l'accueil, v1.12).

### PROBLÈME N°1 — Refonte du composant "Créer un compte" (sidebar)
- Nouvelle classe modificatrice `.sidebar-user--cta` (`css/base.css`), appliquée uniquement en mode invité
  (`identity.js::paintSidebarUser`) : fond dégradé violet très subtil avec `backdrop-filter: blur(8px)`
  (glassmorphism léger), bordure discrète, ombre douce, coins arrondis hérités du design system existant.
- Avatar réduit (28px, contre 34px pour le widget profil normal) avec icône **UserPlus** (nouvelle entrée
  `ICONS.userPlus` dans `js/icons.js`, remplace l'icône générique "personne" précédente) sur fond violet
  translucide — bien plus explicite qu'un simple avatar générique pour une action de création de compte.
- Titre "Créer un compte" légèrement plus affirmé (600, 0.83rem) ; sous-titre "Sauvegarder ma progression"
  nettement plus discret (0.68rem, poids normal, gris clair `--text-faint`) — meilleure hiérarchie visuelle.
- Hover premium : léger relief (`translateY(-1px)`), éclaircissement du dégradé et de l'avatar, ombre violette
  douce qui apparaît progressivement (aucun effet agressif, transition 220ms).
- Clic : léger tassement (`scale(0.985)`) avec transition plus rapide (90ms) pour un retour fluide.
- Aucune modification du widget profil d'un compte réel (classe non appliquée, comportement identique).

### Aucune régression
- Comptes réels : `GET /` et `GET /index.html` redirigent toujours vers `/dashboard.html`, sans purge ni
  suppression de cookies (vérifié via curl, comptes Mehdi/Hedi intacts après tous les tests).
- Toutes les pages protégées restent en HTTP 200 pour un invité (dashboard/chapitres/exercice/profil/évaluation).
- Le transfert de progression à l'inscription, la limite de 2 chapitres, le badge "Mode invité" du header et
  le verrouillage du Dashboard après première découverte (v1.11) sont inchangés et toujours fonctionnels.

### Tests effectués (curl, cookie jar dédié par scénario)
- **Scénario 1** — invité avec xp=99 → `GET /index.html` (l'ancien chemin de contournement) → cookies
  `nm_session`/`nm_csrf`/`session` supprimés dans la réponse → `GET /api/auth/me` suivant : 401 confirmé ;
  nouvel invité créé ensuite avec un id distinct et xp=0.
- **Scénario 3 (recharge de la landing)** — même vérification via `GET /` avec un invité fraîchement créé :
  purge et suppression de cookies identiques.
- Compte réel fraîchement inscrit → `GET /` et `GET /index.html` → 302 vers `/dashboard.html` dans les deux
  cas, aucune purge, `is_guest: false` confirmé après coup.
- Visiteur anonyme (aucun cookie) → `GET /` et `GET /index.html` → 200 normal, comportement inchangé.
- Toutes les pages protégées re-testées en HTTP 200 pour un nouvel invité après la refonte.
- Comptes de test nettoyés après chaque lot ; Mehdi (id=1) et Hedi (id=2) confirmés intacts au final.

### Bugs connus / limites assumées
- Pas de navigateur headless disponible — le rendu visuel du nouveau composant sidebar (hover, clic,
  glassmorphism) n'a été vérifié que via revue de code/CSS, pas visuellement. À confirmer manuellement.
- Scénario 2 (fermeture d'onglet) et l'expiration par inactivité restent couverts par les mécanismes déjà
  livrés et testés en v1.11 (cookie non persistant + `GUEST_IDLE_TTL_MINUTES`), non re-testés ici en détail
  puisque non modifiés dans cette version.

## v1.11

**Date** : 2026-07-11

### Contexte — le Mode Invité doit être réellement temporaire
Après plusieurs tests du Mode Invité (v1.10), deux défauts de logique subsistaient : les données d'un invité
survivaient beaucoup trop longtemps (aucune expiration réelle avant 24h), et le Dashboard restait
entièrement libre indéfiniment sans jamais inciter naturellement à créer un compte. Cette version corrige
le cycle de vie complet de l'invité et réintroduit un verrouillage — cette fois précis et scopé — du
Dashboard après sa première découverte, à la manière de Duolingo/Notion/ChatGPT.

### Cycle de vie de l'invité, désormais réellement éphémère
- Cookie de session invité non persistant (`_set_session_cookie(..., persistent=False)`) : contrairement à
  un compte réel, il n'a plus de `Max-Age` — le navigateur le supprime lui-même à sa fermeture complète.
- Expiration serveur par **inactivité** (`GUEST_IDLE_TTL_MINUTES = 120`) : dès qu'un invité revient après
  plus de 2h sans activité, `get_current_user()` (`webapp/auth.py`) purge intégralement son compte (ligne
  DB + fichier de stats) avant même de répondre à la requête — le client se retrouve sans session, exactement
  comme un tout nouveau visiteur, et `enterGuest()` recrée un identifiant entièrement nouveau et vierge.
- `db.cleanup_expired_guests()` bascule d'un nettoyage par ancienneté de création à un nettoyage par
  dernière activité réelle (`guest_last_seen_at`, avec repli sur `created_at`) — un invité toujours actif
  n'est jamais coupé en cours de session, contrairement à l'ancienne logique basée sur `created_at` seul.
- Chaque nouvel invité reçoit un identifiant aléatoire unique (`secrets.token_hex`), jamais réutilisé, et ne
  peut structurellement hériter d'aucune donnée d'un invité précédent (identifiant de compte distinct →
  fichier de stats distinct) : aucun cumul possible entre deux sessions invité.

### Dashboard verrouillé après la première découverte (et seulement lui)
- Nouvelle route `POST /api/auth/guest/dashboard-seen` : répond `locked: false` à la toute première
  consultation du Dashboard par un invité (juste après son évaluation initiale, exploration totalement
  libre comme demandé), puis `locked: true` à toute consultation suivante (retour sur le Dashboard, ou après
  une nouvelle évaluation) — un simple flag `guest_dashboard_viewed` en base, jamais un compteur fragile.
- Le flou (`filter: blur(6px)`) ne s'applique désormais qu'au conteneur `#dashboard-content`
  (`dashboard.js::applyGuestDashboardLock`) — jamais à la sidebar, au header, ni à la navigation, qui
  restent pleinement cliquables même Dashboard verrouillé.
- Nouvelle carte de déverrouillage (`.guest-lock-card`, `css/guest.css`) affichée au-dessus du contenu
  flouté : titre "Créez votre compte NovaMath", liste des bénéfices, boutons Créer un compte / Se connecter
  / Continuer en mode invité — ce dernier bouton ferme uniquement la carte (le flou reste, mémorisé pour la
  session en cours via `sessionStorage`), conformément à la demande explicite.
- L'ancienne carte non-bloquante de v1.10 (`renderGuestInfoCard`, jamais de flou) est retirée : ce round la
  remplace entièrement par le comportement verrouillé ci-dessus, qui correspond mieux à l'intention réelle
  (inciter après la découverte, sans bloquer l'exploration du reste du site).

### Aucune régression
- Toutes les autres pages (Chapitres, Entraînement, Profil) restent intégralement accessibles pour un
  invité, flou ou pas — seul le Dashboard est concerné.
- La limite de 2 chapitres en mode invité (`GUEST_MAX_CHAPTERS`, `chapitres.js` + garde-fou serveur
  `/api/start`) est inchangée.
- Le badge "Mode invité" (header) et le remplacement du widget "Profil" de la sidebar par "Créer un compte"
  (introduits en v1.10) sont inchangés.
- La déconnexion d'un compte réel reste strictement indépendante du mode invité : `get_current_user()` ne
  touche à l'expiration/purge que pour `auth_provider == "guest"`, jamais pour un compte réel.
- Le transfert de progression à l'inscription (`transfer_guest`, choix Oui/Non de v1.10) fonctionne toujours
  à l'identique avec les nouveaux comptes invités.

### Tests effectués (curl, cookie jar dédié par scénario)
- **Scénario 1** — invité actif → `guest_last_seen_at` vieilli artificiellement de 3h en base → premier
  appel `/api/auth/me` suivant : 401 (session traitée comme terminée) + ligne DB confirmée supprimée ;
  nouvel appel `/api/auth/guest` → nouvel id, xp/accuracy à 0, aucune trace du précédent invité.
- **Scénario 2** — nouvel invité → 1er `POST /api/auth/guest/dashboard-seen` → `locked: false` ; 2e appel
  (même session) → `locked: true` ; `dashboard.html`/`chapitres.html`/`exercice.html`/`profil.html` tous en
  HTTP 200 pour ce même invité (autres pages non affectées par le verrouillage).
- **Scénario 3** — invité avec progression (xp=42, historique 1 réponse) → `POST /api/auth/register` avec
  `transfer_guest: true` → nouveau compte réel avec xp=42/accuracy=100/total_time_s=30 confirmés ; ancien
  compte invité absent de la base après coup.
- **Scénario 4** — garanti structurellement (identifiants de compte auto-incrémentés distincts, fichiers de
  stats séparés par id) : un nouveau `POST /api/auth/guest` ne peut techniquement lire aucune donnée d'un
  compte précédent, réel ou invité.
- Comptes de test nettoyés après chaque lot ; comptes réels Mehdi (id=1) et Hedi (id=2) reconfirmés intacts
  et inchangés après l'ensemble des tests.

### Bugs connus / limites assumées
- Pas de navigateur headless disponible dans cet environnement — l'animation du flou, de la carte de
  déverrouillage et le responsive réel n'ont pas été vérifiés visuellement, seulement via revue de code/CSS
  et tests structurels côté serveur (curl). À confirmer manuellement.
- L'expiration par inactivité (2h) n'est vérifiée qu'à la prochaine requête de l'invité concerné (pas de
  tâche planifiée dans ce projet) — un invité inactif au-delà du seuil mais qui ne revient jamais laisse sa
  ligne en base jusqu'au prochain `cleanup_expired_guests()` déclenché par une nouvelle entrée en mode
  invité (nettoyage paresseux, cohérent avec le reste du projet).
- Le cookie de session invité non persistant protège contre une fermeture complète du navigateur, mais pas
  contre la fermeture d'un seul onglet parmi plusieurs onglets ouverts du même navigateur (les cookies ne
  sont pas isolés par onglet) — dans ce cas, l'expiration par inactivité (2h) reste le filet de sécurité.

## v1.10

**Date** : 2026-07-11

### Contexte — assouplissement du Mode Invité
Retour d'usage sur le Mode Invité (v1.09) : trop restrictif — fenêtre de connexion/inscription bloquante au
premier accès au Dashboard, arrière-plan flouté, panneau flottant permanent, bouton dédié en plus du CTA
principal. Cette version rend l'expérience fluide façon Spotify/Notion/Canva : l'utilisateur explore
librement, la création de compte reste une invitation discrète, jamais une obstruction.

### Entrée en mode invité simplifiée
- Suppression complète du bouton "Continuer en mode invité" de la landing page.
- Le bouton existant **"Démarrer l'évaluation"** (`index.html`, hero) déclenche désormais directement le
  mode invité (`api.enterGuest()`) puis redirige vers `evaluation.html` — aucun formulaire, aucune demande de
  connexion. Si une session invité existe déjà (retour sur la landing page via le logo), elle est réutilisée
  plutôt que recréée, pour ne pas perdre la progression en cours.
- Garde ajoutée : un utilisateur **réel déjà connecté** qui atteindrait la landing page (via le logo) ne
  déclenche jamais `enterGuest()` — son vrai compte n'est jamais remplacé par un compte invité
  (`webapp/static/js/auth.js`, variable `currentAccount` désormais partagée dans tout le module).

### Dashboard non bloquant
- Suppression totale du flou d'arrière-plan (`.guest-blurred`) et de la fenêtre plein écran
  (`.guest-upgrade-overlay`) qui empêchaient toute interaction avec le Dashboard.
- Remplacés par une **carte d'information intégrée au flux du Dashboard** (`.guest-info-card`, sous la
  bannière de bienvenue), jamais par-dessus le contenu : le Dashboard reste entièrement cliquable et lisible
  en permanence.
- La carte est fermable (bouton croix) ; une fois fermée, elle ne réapparaît plus pour la session en cours
  (`sessionStorage`, clé `novamath:guest_card_dismissed`).

### Panneau flottant supprimé
- Le panneau glassmorphism bas-droite ("Se connecter"/"Créer un compte"), affiché en permanence sur toutes
  les pages depuis v1.09, est entièrement retiré (`identity.js::renderGuestFloatingPanel` supprimé).

### Badge déplacé dans l'en-tête
- Le badge "Mode invité" (violet clair) n'est plus à côté du pseudo dans le widget de profil, mais
  directement à côté du logo NovaMath dans l'en-tête de chaque page applicative — plus discret, plus proche
  de la demande initiale ("dans le Header, à côté du logo").

### Widget "Profil" remplacé pour un invité
- Le widget de bas de sidebar (auparavant un lien vers `profil.html`, "Voir le profil") devient, pour un
  compte invité, un bouton **"Créer un compte"** (icône générique, sous-titre "Sauvegarder ma progression")
  qui ouvre directement la modale d'inscription — cohérent avec le fait que `profil.html` n'a pas d'intérêt
  réel pour un invité (rien à personnaliser). Accessible au clavier (`role="button"`, gestion Entrée/Espace).

### Fenêtre de limite de chapitres — texte mis à jour
- Le comportement (2 chapitres maximum, blocage immédiat au 3e essai) est inchangé. Le texte de la fenêtre
  suit désormais exactement la formulation demandée : titre "Débloquez tous les chapitres", corps "Créez
  gratuitement votre compte NovaMath afin d'accéder à tous les chapitres, sauvegarder votre progression et
  retrouver vos statistiques sur tous vos appareils.", bouton "Continuer en mode invité" qui referme
  simplement la fenêtre.

### Transfert de progression — prompt Oui/Non explicite
- La case à cocher "Conserver ma progression..." est remplacée par un choix binaire explicite dans la modale
  d'inscription : "Souhaitez-vous conserver votre progression réalisée en mode invité ?" avec deux boutons
  Oui/Non (Oui sélectionné par défaut). Le mécanisme de transfert côté serveur (déjà en place depuis v1.09,
  `_transfer_guest_data`) est inchangé.
- Amélioration à cette occasion : si l'utilisateur choisit "Non", le compte invité abandonné est désormais
  supprimé immédiatement (au lieu d'attendre le nettoyage paresseux à 24h) — `webapp/auth.py::register()`
  appelle `_purge_account()` dans ce cas.

### Tests réalisés
- `GET /dashboard.html`, `/chapitres.html`, `/exercice.html`, `/profil.html` en session invité → 200 sur
  toutes les pages (déjà le cas depuis v1.09, reconfirmé — le blocage n'a jamais été côté serveur).
- Vérifié par grep : plus aucune référence à `guest-blurred`/`guest-upgrade-overlay`/`guest-floating-panel`
  dans le code ; le bouton "Continuer en mode invité" et son texte ont disparu de `index.html` ; le bouton
  "Démarrer l'évaluation" porte la classe `js-start-guest-eval`.
- Inscription avec `transfer_guest: false` depuis une session invité ayant 30 XP → nouveau compte à 0 XP
  (transfert bien refusé) et compte invité supprimé immédiatement de la base (vérifié absent après coup).
- Comptes réels (Mehdi, Hedi) non affectés par l'ensemble de ces tests.

### Bugs connus / limites assumées
- Pas de navigateur headless disponible pour vérifier visuellement l'animation d'apparition de la carte, la
  fermeture au clic, et le responsive réel — logique et CSS vérifiés statiquement.
- La carte d'information du Dashboard réapparaît si l'onglet est fermé puis rouvert plus tard (nouvelle
  session invité ou nouvel onglet) : comportement voulu ("pendant la session"), à ne pas confondre avec une
  fermeture définitive multi-session.

## v1.09

**Date** : 2026-07-11

### Contexte — Mode Invité
Ajout d'un mode invité (façon Spotify/Canva/Notion) : un visiteur peut désormais essayer NovaMath — lancer
une évaluation, découvrir le Dashboard, consulter les chapitres — sans créer de compte, avec certaines
fonctionnalités volontairement limitées pour l'inciter à s'inscrire.

### Architecture retenue
Plutôt qu'un système parallèle, un invité est un **compte éphémère** dans la table `users` existante
(`auth_provider='guest'`, email/nom d'utilisateur générés, sans mot de passe). Ce choix permet de réutiliser
tel quel tout ce qui existait déjà : sessions HTTP, page gating, fichier de stats par utilisateur,
`login_required`. Aucune donnée n'est "sauvegardée définitivement" au sens où l'entend la demande : le
compte invité expire vite (session d'1 jour) et est purgé automatiquement (`db.cleanup_expired_guests()`,
appelé à chaque nouvelle entrée en mode invité — pas de tâche planifiée disponible dans ce projet).

### Backend (`webapp/db.py`, `webapp/auth.py`, `webapp/server.py`)
- `db.create_guest_user()` / `db.cleanup_expired_guests()` : création et nettoyage paresseux des comptes
  invités (purge après 24h).
- `POST /api/auth/guest` : entrée en mode invité, pose les cookies `nm_session`/`nm_csrf` exactement comme
  une connexion normale.
- `_public_user()` expose désormais `is_guest` (dérivé de `auth_provider`), utilisé partout côté client pour
  adapter l'interface.
- Restrictions serveur (jamais uniquement côté client) :
  - `PUT /api/auth/me` (personnalisation pseudo/photo) → 403 pour un compte invité.
  - `POST /api/reviews` (publication d'avis) → 403 pour un compte invité.
  - `POST /api/start` → 403 si plus de 2 chapitres sélectionnés en mode invité (`GUEST_MAX_CHAPTERS`).
- **Transfert de session à l'inscription** : `POST /api/auth/register` accepte un champ `transfer_guest`. Si
  le client était en mode invité et l'accepte, `_transfer_guest_data()` copie la progression (XP, historique,
  séries, cache de stats) vers le nouveau compte réel puis supprime le compte invité — réutilise le même
  mécanisme de purge que la suppression de compte volontaire (`_purge_account()`, factorisé à cette
  occasion).
- Les avis publiés par un compte invité restent impossibles (contrairement aux avis anonymes, toujours
  permis) — cohérent avec "les avis nécessitent un compte".

### Frontend
- **Landing page** (`index.html`) : nouveau bouton "Continuer en mode invité" (icône lecture, style
  identique aux autres boutons de la nav) à côté de Se connecter/Créer un compte.
- **Modales d'authentification mutualisées** : le HTML des modales Inscription/Connexion/Mot de passe
  oublié/Mentions légales/Confidentialité, jusqu'ici dupliqué uniquement dans `index.html`, est extrait dans
  `js/authModalsTemplate.js` et injecté par `auth.js` sur n'importe quelle page (au lieu d'exister nulle part
  ailleurs). `auth.js` passe d'une liaison d'événements directe à une **délégation sur `document`**, pour que
  des boutons ajoutés dynamiquement après coup (carte premium, panneau flottant) ouvrent eux aussi les
  modales sans re-câblage. Ajout de `auth.css`/`auth.js` sur `dashboard.html`, `chapitres.html`,
  `exercice.html`, `evaluation.html`, `profil.html` (au passage : `profil.html` avait été oublié lors de
  l'ajout de la modale de suppression de compte — sa modale était non stylée depuis NovaMath v1.07, corrigé
  ici).
- **`identity.js`** (chargé sur toutes les pages applicatives) : badge "Mode invité" (violet clair) à côté du
  pseudo dans la sidebar, et panneau flottant persistant bas-droite (glassmorphism, coins arrondis, ombre,
  animation d'entrée) avec "Se connecter"/"Créer un compte" — visible y compris sur `evaluation.html`, qui
  n'a pas de sidebar.
- **Dashboard** (`dashboard.js`) : carte premium centrale ("Créez votre compte NovaMath...") tant que le
  compte est invité, arrière-plan du dashboard flouté (`filter: blur`) mais toujours visible dessous.
- **Chapitres** (`chapitres.js`) : sélection bloquée au-delà de 2 chapitres en mode invité, avec une fenêtre
  ("Créez votre compte pour continuer") proposant Créer un compte / Se connecter / Continuer en mode invité.
- **Avis** (`reviews.js`) : le clic sur "Donner mon avis" en mode invité ouvre la même fenêtre premium plutôt
  que le formulaire (qui serait de toute façon refusé par le serveur).
- **Profil** (`profil.js`) : édition du pseudo, upload de photo et suppression de compte masqués pour un
  invité (remplacés par une invitation à créer un compte) ; l'affichage "Invité" et l'avatar générique
  apparaissent naturellement (valeurs par défaut du compte invité côté serveur, aucune logique spécifique
  nécessaire).
- **Inscription** : si un compte invité est actif au moment d'ouvrir la modale, une case à cocher "Conserver
  ma progression de la session invité en cours" apparaît (cochée par défaut), envoyée en `transfer_guest`.

### Tests réalisés
- Entrée en mode invité → accès direct à `dashboard.html` (200, pas de redirection vers la landing page).
- Évaluation avec 3 chapitres sélectionnés → 403 (`guest_restricted`) ; avec 2 → acceptée normalement.
- Publication d'avis en mode invité → 403 ; édition du profil (`PUT /api/auth/me`) → 403.
- Progression enregistrée en mode invité (50 XP) puis inscription avec `transfer_guest: true` → nouveau
  compte réel avec les 50 XP transférés, compte invité supprimé de la base.
- Nettoyage automatique : un compte invité vieux de 48h injecté manuellement est purgé dès l'entrée en mode
  invité suivante.
- Toutes les pages concernées et leurs assets (`authModalsTemplate.js`, `guest.css`, etc.) retournent HTTP
  200 ; `index.html` ne contient plus les modales en dur (injectées en JS, vérifié par grep).
- Comptes réels (Mehdi, Hedi) non affectés par les tests.

### Bugs connus / limites assumées
- Pas de navigateur headless disponible pour vérifier visuellement l'animation du panneau flottant/de la
  carte premium, ni le responsive réel (mobile/tablette) — logique et CSS vérifiés statiquement, media
  queries ajoutées pour les petits écrans (`guest.css`, `responsive.css`).
- Le mode invité n'a pas de mécanisme de nettoyage immédiat à la fermeture de l'onglet (attendu : il reste
  utilisable jusqu'à expiration de la session de 1 jour ou nettoyage lors d'une entrée ultérieure d'un autre
  invité) — cohérent avec "temporaire", mais pas instantané.
- Les avis restent publiables anonymement (sans aucun compte, comportement historique depuis v1.03) ; seul le
  mode invité spécifiquement est bloqué, comme demandé.

## v1.08

**Date** : 2026-07-11

### Contexte — comportement du logo pour un utilisateur connecté
Signalé : cliquer sur le logo "NovaMath" (en-tête des pages applicatives) renvoyait un utilisateur connecté
vers la landing page publique (Se connecter/Créer un compte), l'obligeant à se reconnecter — comportement
incohérent avec les plateformes de référence (Spotify, Discord, GitHub, Notion, ChatGPT), où le logo ramène
toujours vers l'espace personnel tant que la session est active.

### Cause
Le logo (`dashboard.html`, `chapitres.html`, `exercice.html`, `profil.html`) pointait en dur vers
`index.html`, servi directement par le handler de fichiers statiques de Flask — qui ne vérifie aucune
session. La route `/`, elle, contenait déjà exactement la bonne logique depuis NovaMath v1.05
(`webapp/server.py::index()` : redirige vers `/dashboard.html` si connecté, sinon sert la landing page) mais
n'était utilisée nulle part dans les pages applicatives.

### Correctif
- `webapp/static/dashboard.html`, `chapitres.html`, `exercice.html`, `profil.html` : le lien du logo passe de
  `href="index.html"` à `href="/"`. Aucune autre modification — la vérification de session, déjà côté
  serveur, gère automatiquement les deux cas (connecté → Dashboard, non connecté → landing page), y compris
  après un rechargement de page ou une réouverture du navigateur (session persistante en base). Le clic ne
  passe par aucune route de déconnexion : ni cookie, ni token, ni session ne sont modifiés.
- Animation et apparence du logo inchangées (seule la destination change).

### Tests réalisés
- Non connecté → `GET /` → 200, landing page servie.
- Connecté → `GET /` → 302 vers `/dashboard.html`, cookie de session intact (vérifié en inspectant la
  réponse : aucun `Set-Cookie`/`Delete-Cookie` émis par cette redirection).
- Lien `href` du logo vérifié à `/` sur les 4 pages concernées.

## v1.07

**Date** : 2026-07-11

### Contexte — audit de sécurité complet
Audit OWASP Top 10 demandé sur l'ensemble de la plateforme (comptes, mots de passe, sessions, uploads,
en-têtes HTTP, CSRF, injections). Résultat de l'audit avant correctifs :
- **Déjà sain** : toutes les requêtes SQL sont paramétrées (`db.py`, aucune concaténation de chaîne) — pas
  d'injection SQL possible. Le rendu des avis utilise `textContent`/`createElement` côté client (jamais
  `innerHTML` sur du contenu utilisateur) — pas de XSS stocké. Aucune commande shell, aucun `eval`, aucune
  traversée de répertoire possible (chemins fixes ou dérivés d'un `user_id` entier, jamais d'un chemin fourni
  par le client). `data/` (base SQLite, stats, avis) n'est pas exposé par le serveur de fichiers statique.
- **Failles réelles identifiées et corrigées** : secrets en dur dans le code (`app.secret_key`, clé admin),
  hachage scrypt au lieu d'un algorithme dédié aux mots de passe, aucune protection CSRF, aucun en-tête de
  sécurité HTTP, validation d'upload basée uniquement sur un préfixe déclaratif (falsifiable), pas de
  temporisation progressive sur les échecs de connexion, pas de suppression de compte, aucune journalisation
  des événements de sécurité, un token de réinitialisation de mot de passe qui était imprimé en console
  (donc capturable dans un fichier de log).

### Mots de passe — migration vers Argon2id
- `webapp/auth.py` : les mots de passe sont désormais hachés avec **Argon2id** (`argon2-cffi`, algorithme
  recommandé par l'OWASP), en remplacement du scrypt de `werkzeug.security` utilisé jusqu'à v1.06.
- **Migration transparente** : `verify_password()` reconnaît les deux formats de hash ; à la première
  connexion réussie d'un compte encore sur l'ancien hash, celui-ci est ré-encodé en Argon2id de façon
  silencieuse (`needs_rehash()` + `db.set_password_hash()`), sans forcer de réinitialisation. Testé avec un
  hash scrypt injecté manuellement : confirmé ré-encodé en `$argon2id$...` après connexion.
- Comptes réels existants (Mehdi, Hedi) non modifiés par ce correctif : ils migreront automatiquement à leur
  prochaine connexion, sans action requise de leur part.

### Secrets — sortie du code source
- `app.secret_key` et la clé d'administration des avis (`ADMIN_KEY`) étaient écrits en dur dans
  `webapp/server.py`. Remplacés par `_get_or_create_secret()` : lecture prioritaire des variables
  d'environnement `NOVAMATH_SECRET_KEY`/`NOVAMATH_ADMIN_KEY` ; à défaut, génération aléatoire une seule fois
  et persistance dans `data/.flask_secret_key`/`data/.admin_key` (hors `static/`, jamais servis publiquement)
  — pour ne jamais committer un secret tout en gardant les sessions stables entre redémarrages.

### CSRF — double-submit cookie
- Le cookie `nm_session` était déjà `SameSite=Lax` (bloque déjà l'essentiel du CSRF cross-site dans les
  navigateurs modernes), mais aucune défense en profondeur n'existait. Ajout d'un cookie `nm_csrf` (lisible
  par le JS, posé à la connexion/inscription) qui doit être renvoyé à l'identique dans l'en-tête
  `X-CSRF-Token` pour toute requête `POST/PUT/DELETE/PATCH` authentifiée (`webapp/auth.py::csrf_protect`).
- Appliqué à toutes les routes mutantes protégées par session : `/api/auth/me` (PUT/DELETE),
  `/api/auth/logout`, `/api/stats`, `/api/reviews*`, `/api/start`, `/api/answer`, `/api/practice/*`,
  `/api/restart`. Non appliqué à `/api/auth/register`/`login`/`forgot-password` (pas de session à protéger
  avant l'authentification) ni aux routes de modération des avis (`pin`/`hide`, protégées par une clé
  d'en-tête `X-Admin-Key` que le navigateur n'envoie jamais automatiquement — pas de vecteur CSRF).
  Publication d'avis anonyme (sans compte) exemptée : pas de session à falsifier dans ce cas.
- `webapp/static/js/api.js` : le wrapper `request()` lit désormais le cookie `nm_csrf` et l'attache
  automatiquement en en-tête sur toute requête mutante — aucun changement requis dans les appelants.
- Testé : requête `PUT /api/auth/me` sans en-tête → 403 ; avec un mauvais jeton → 403 ; avec le bon jeton →
  200.

### En-têtes de sécurité HTTP
- `webapp/server.py::security_headers()` (renommé depuis `no_cache`, mêmes en-têtes de cache conservés) :
  ajout de `Content-Security-Policy`, `X-Content-Type-Options: nosniff`,
  `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy`, `X-Frame-Options: DENY`.
- CSP construite avec un **nonce dédié** pour l'unique script inline du projet (l'id de compte injecté dans
  les pages protégées, voir v1.06) : `script-src 'self' 'nonce-<aléatoire par requête>'` — aucun script externe
  ni injecté ne peut s'exécuter, y compris en cas de future faille XSS. `style-src` garde `'unsafe-inline'`
  (nombreux styles inline générés par le JS existant — les migrer vers des classes CSS est noté en TODO).
- Vérifié par `curl -i` : en-têtes présents sur toutes les réponses, y compris les pages protégées.

### Validation réelle des uploads (photos de profil et avis)
- `webapp/auth.py::sniff_image_type()` : décode le contenu base64 et vérifie les **octets réels** (signature
  PNG/JPEG/WEBP/GIF), au lieu de se fier au seul préfixe `data:image/...` déclaré par le client (facilement
  falsifiable). Appliqué à l'avatar de compte (`PUT /api/auth/me`) et à l'avatar d'avis
  (`_validate_review_payload` dans `server.py`).
- SVG toujours explicitement refusé (déjà le cas depuis une version antérieure — anti-XSS stocké via SVG
  contenant du script).
- Testé : un contenu texte avec un préfixe `data:image/png;base64,` falsifié est rejeté ("Le contenu du
  fichier ne correspond pas à une image valide") ; une vraie image PNG est acceptée.

### Brute-force — temporisation progressive
- En complément du verrou existant (5 échecs / 15 min → 429), chaque tentative échouée récente ajoute
  désormais un délai avant la réponse suivante (`time.sleep(min(0.5 × échecs récents, 3s))`) — ralentit un
  script de brute-force automatisé sans pénaliser un utilisateur qui se trompe une seule fois.
- Testé : 5 échecs consécutifs mesurés à 0,08s / 0,58s / 1,07s / 1,59s / 2,07s de délai croissant, puis 429
  sur la 6e tentative même avec le bon mot de passe.

### Suppression de compte
- `DELETE /api/auth/me` (`webapp/auth.py`) : exige la confirmation explicite (`confirm: true`) et le mot de
  passe du compte (sauf compte 100% OAuth sans mot de passe local) avant toute suppression. Supprime le
  compte (cascade SQL vers sessions/comptes OAuth liés/tokens de réinitialisation), le fichier de
  statistiques (`data/user_stats/<id>.json`) et l'historique de tentatives de connexion liées à l'email.
  Journalise l'événement puis invalide immédiatement la session.
- Les avis déjà publiés restent visibles (comportement volontaire depuis v1.03 — avis publics indépendants des
  comptes) mais perdent leur rattachement au compte supprimé (`server.py::_release_reviews_ownership`,
  enregistré comme hook via `auth.ACCOUNT_DELETION_HOOKS` pour éviter une dépendance circulaire entre
  `auth.py` et `server.py`).
- `webapp/static/profil.html`/`js/profil.js` : nouveau bouton "Supprimer mon compte" avec modale dédiée
  (mot de passe + case à cocher de confirmation qui déverrouille le bouton final) — 3 étapes distinctes
  avant l'action irréversible, comme demandé.
- Testé de bout en bout : suppression refusée sans bon mot de passe (401), acceptée avec confirmation,
  compte inaccessible immédiatement après (401 sur `/api/auth/me`), avis conservé mais `user_id` remis à
  `null`.

### Journalisation des événements de sécurité
- Nouvelle table `security_events` (`webapp/db.py`) : type d'événement, `user_id`, adresse IP, horodatage —
  **jamais** de mot de passe, token, cookie ou clé. Événements journalisés : `account_created`,
  `login_success`, `login_failed`, `logout`, `password_reset_requested`, `password_changed`,
  `account_deleted`.
- Le lien de réinitialisation de mot de passe (`forgot-password`) était auparavant imprimé sur la console
  serveur (`print(...)`) — supprimé : il ne circule plus que dans la réponse JSON `dev_reset_link` (mode
  développement, jamais persisté dans un fichier de log).

### Tests réalisés
- Injection SQL : tentative `' OR '1'='1` dans l'email de connexion → refusée proprement (requêtes
  paramétrées), aucune erreur serveur.
- XSS : avis publié avec `<script>alert(1)</script>` dans le commentaire → stocké tel quel, jamais exécuté
  (rendu via `textContent`).
- CSRF : requête mutante sans/avec mauvais/avec bon jeton → 403/403/200.
- Upload : avatar falsifié (texte avec préfixe PNG mensonger) refusé ; vraie image PNG acceptée.
- Brute-force : délai progressif mesuré, verrou à la 6e tentative confirmé.
- Migration Argon2 : hash scrypt existant ré-encodé en Argon2id après une connexion réussie.
- Réinitialisation de mot de passe : bout en bout (demande → lien → nouveau mot de passe → connexion),
  réutilisation du token refusée, aucun token dans les logs serveur.
- Suppression de compte : refusée sans bon mot de passe, acceptée avec confirmation, compte et session
  invalidés, avis conservé mais désolidarisé.
- Isolation entre comptes (héritée de v1.06, re-vérifiée) : comptes de test créés/supprimés sans jamais toucher
  aux comptes réels (Mehdi, Hedi), dont les données sont restées intactes tout au long de l'audit.

### Bugs connus / limites assumées
- `style-src 'unsafe-inline'` reste nécessaire dans la CSP : de nombreux styles inline sont générés par le
  JS existant (`dashboard.js`, `profil.js`, `reviews.js`...) — les migrer vers des classes CSS pour retirer
  cette permission est un chantier à part entière, noté en TODO.
- Pas de service d'envoi d'email réel — la réinitialisation de mot de passe reste en mode développement
  (lien renvoyé directement au client).
- `secure=False` sur les cookies de session/CSRF — acceptable en HTTP local, à activer avant tout
  déploiement public en HTTPS (rappelé depuis v1.05).
- Pas de limitation de débit (rate limiting) générique par IP sur l'ensemble de l'API (seule la connexion a
  un anti brute-force dédié) — une librairie comme Flask-Limiter serait pertinente avant un déploiement
  public à fort trafic.
- Pas de navigateur headless disponible pour vérifier visuellement le nouveau flux de suppression de compte
  (modale, activation du bouton après case cochée) — logique testée via l'API, rendu visuel à confirmer.

## v1.06

**Date** : 2026-07-11

### Contexte — bug critique d'isolation des comptes
Signalé après usage réel : deux comptes créés avec des adresses Gmail différentes affichaient la même
progression, les mêmes statistiques, la même photo. Investigation confirmée : **la base de données et les
fichiers de stats côté serveur étaient déjà correctement isolés par `user_id`** (vérifié directement en base
— le compte Hedi avait bien xp=0/aucun avatar pendant que Mehdi avait sa vraie progression). Le bug venait
entièrement du **cache client** : plusieurs modules JS (`store.js`, `chapitres.js`, `evaluation.js`,
`exercice.js`) écrivent dans des clés `localStorage` **globales** (`lumis:stats`, `lumis:profile`,
`lumis:series_in_progress`, `lumis:selected_chapters`, `lumis:open_chapter`, `lumis:last_level`,
`lumis:practice_choices`, `lumis:pending_series`), jamais purgées ni scopées par compte. Sur un même
navigateur, se connecter avec un second compte laissait le cache du premier compte en place ; comme
`hydrateFromServer()` compare la longueur de l'historique local et distant et garde le plus long, il
réinjectait puis **réécrivait côté serveur** (via `persist()` → `POST /api/stats`) les données de l'ancien
compte sur le nouveau, dès la première interaction — d'où l'impression que les deux comptes "partageaient"
tout.

### Correctifs

### Purge du cache client au changement de compte (correctif principal)
- `webapp/server.py::_serve_protected()` : les 5 pages protégées (`dashboard.html`, `chapitres.html`,
  `exercice.html`, `evaluation.html`, `profil.html`) sont maintenant servies avec un
  `<script>window.__NOVAMATH_USER_ID__ = <id>;</script>` injecté juste après `<head>`, avant tout script
  applicatif.
- `webapp/static/js/store.js` : nouvelle garde `syncAccountScope(userId)`, exécutée de façon **synchrone à
  l'import du module** (donc avant que `dashboard.js`/`chapitres.js`/`exercice.js`/`evaluation.js` ne lisent
  la moindre donnée locale). Compare l'id injecté par le serveur à un marqueur `novamath:scoped_uid` ; en cas
  de changement (ou de première visite), purge intégralement les 8 clés `localStorage` listées ci-dessus
  avant de laisser la page continuer. Comme le contrôle est synchrone (pas d'attente d'un `fetch`), il n'y a
  aucune fenêtre de course possible avec le premier rendu de la page.
- Ce mécanisme couvre les 5 pages protégées d'un coup (elles importent toutes `store.js`, directement ou via
  `resume.js`) sans avoir à modifier chaque page individuellement.

### Session de quiz (Flask `session`) réinitialisée au changement de compte
- La progression d'évaluation/entraînement en session (`q`, `resps`, `diffs`, `used_ids`, `allowed`,
  `current_level`, `history`, `practice_resps`, `practice_diffs`) vit dans le cookie de session Flask signé
  — **distinct** du cookie `nm_session` des comptes. Un quiz commencé sur un compte pouvait donc continuer à
  écrire dans la session d'un autre compte connecté juste après, sur le même navigateur.
- `webapp/auth.py` : `session.clear()` ajouté dans `register()`, `login()` et `logout()`.

### Avis liés au compte connecté
- `POST /api/reviews` : si l'utilisateur est connecté, le nom/pseudo/photo de l'avis sont désormais **imposés
  par le compte** (`account["pseudo"]`, `account["username"]`, `account["avatar"]`) — impossible de publier
  un avis sous une autre identité que la sienne en étant connecté. Le champ interne `user_id` (jamais exposé
  au client, voir `_public_review`) est enregistré sur chaque avis créé en étant connecté.
- `PUT/DELETE /api/reviews/<id>` : la permission de modification accepte désormais soit l'ancien mécanisme
  (`owner_token`, stocké en `localStorage` — fonctionne pour les avis anonymes), soit l'appartenance au
  compte connecté (`review.user_id == compte.id`) — un utilisateur connecté peut donc gérer son avis depuis
  n'importe quel navigateur/appareil, pas seulement celui où il l'a publié.
- `webapp/static/index.html` + `js/reviews.js` : si un compte est connecté, les champs Nom/Pseudo/Photo du
  formulaire d'avis sont pré-remplis avec l'identité du compte puis masqués (remplacés par la mention
  "Publié en tant que ..."), pour ne pas laisser saisir des champs que le serveur ignore de toute façon.

### Vérification
- Inspection directe de `data/novamath.db` avant tout correctif : confirmé que les comptes réels existants
  (Mehdi id=1, Hedi id=2) avaient déjà des colonnes `xp`/`accuracy`/`avatar` totalement indépendantes — la
  aucune régression serveur à corriger, seulement le cache client.
- Deux comptes de test (`testiso.a@gmail.com` / `testiso.b@gmail.com`) créés puis testés via `curl` avec des
  cookies de session séparés : `window.__NOVAMATH_USER_ID__` injecté correctement et différent pour chaque
  compte sur `dashboard.html` ; avis publié avec un nom/pseudo falsifiés dans le payload, mais correctement
  remplacé par l'identité réelle du compte connecté à l'enregistrement ; tentative de modification de l'avis
  de A par B refusée (403) ; modification par A de son propre avis acceptée sans `owner_token` (uniquement
  via l'appartenance de compte). Comptes et avis de test supprimés après vérification.
- `python -c "import ast; ast.parse(...)"` sur `server.py` et `auth.py` après chaque édition.

### Bugs connus / limites assumées
- La purge de cache ne peut pas être vérifiée visuellement (pas de navigateur headless disponible dans cet
  environnement) : la logique serveur (injection d'id) et le point d'entrée client (`syncAccountScope`,
  exécuté à l'import de `store.js`) sont vérifiés statiquement et par test API, mais le scénario complet
  "changer de compte dans le même onglet et voir le dashboard se vider" reste à confirmer manuellement dans
  un vrai navigateur.
- Un avis de test préexistant ("Test Persistance") datant d'une session de développement antérieure traîne
  toujours dans `data/reviews.json` — non lié à ce correctif, laissé en place plutôt que supprimé sans
  confirmation explicite.

Le produit s'appelait auparavant **Lumis** (archives `versions/Lumis_V1` à `Lumis_V6`, conservées
intactes pour l'historique). Les entrées ci-dessous antérieures au renommage font donc référence à
l'ancien nom, fidèlement à ce qui a été livré à l'époque.

## v1.05

**Date** : 2026-07-11

### Contexte
Remplacement complet de l'accès libre par un véritable système de comptes utilisateurs : inscription,
connexion, session persistante, mot de passe oublié, et architecture prête pour l'OAuth (Google en
premier). Le site n'est plus accessible directement — toutes les pages applicatives exigent désormais un
compte connecté, à l'image de Spotify/Discord/GitHub/ChatGPT.

### Base de données
- Nouveau `data/novamath.db` (SQLite, module standard `sqlite3`, aucune dépendance ajoutée). Schéma créé
  de façon idempotente au démarrage (`webapp/db.py::init_db()`).
- Table `users` : id, email, username, pseudo, password_hash, avatar, auth_provider, created_at,
  last_login_at, xp, level, accuracy, progression, total_time_s.
- Table `oauth_accounts` (provider, provider_user_id) : prête pour Google/Microsoft/Apple/GitHub.
- Table `sessions` (token, user_id, expires_at) : sessions de connexion persistantes.
- Table `login_attempts` : historique des tentatives (succès/échec) pour la protection anti brute-force.
- Table `password_resets` (token, expires_at, used) : réinitialisation de mot de passe à usage unique.
- La progression détaillée (XP, historique de réponses, séries) reste dans un fichier JSON par
  utilisateur (`data/user_stats/<id>.json`, écriture atomique — même stratégie que l'existant), la table
  `users` ne servant que de cache rapide pour l'affichage du compte.

### Inscription et connexion
- `POST /api/auth/register` : email (format Gmail strict, `nom@gmail.com`), nom d'utilisateur (3-25
  caractères, lettres/chiffres/`-`/`_`), pseudo (nom affiché, modifiable plus tard), mot de passe (8+
  caractères, majuscule, minuscule, chiffre, caractère spécial — vérifié aussi côté serveur, jamais
  seulement côté client), confirmation, cases obligatoires (conditions d'utilisation + politique de
  confidentialité). Validation complète côté serveur avec message d'erreur par champ.
- Mot de passe **haché avec `werkzeug.security` (scrypt)**, jamais stocké ni renvoyé en clair — vérifié
  qu'aucune route ne retourne `password_hash` (`_public_user()` en exclut explicitement le champ).
- `POST /api/auth/login` : email + mot de passe + "Se souvenir de moi". Protection anti brute-force :
  après 5 échecs sur une même adresse en 15 minutes, les tentatives suivantes (même avec le bon mot de
  passe) sont bloquées (HTTP 429) — testé explicitement.
- Session HTTP persistante par cookie `nm_session` (HttpOnly, SameSite=Lax) : 30 jours si "Se souvenir de
  moi", sinon 1 jour — dans les deux cas, la connexion **survit à la fermeture du navigateur** (ce n'est
  pas un cookie de session au sens strict), conformément à la demande.
- `POST /api/auth/logout`, `GET/PUT /api/auth/me` (le pseudo et la photo sont modifiables ; le nom
  d'utilisateur et l'email ne le sont pas depuis cette route).

### Mot de passe oublié
- `POST /api/auth/forgot-password` : réponse volontairement identique que l'email existe ou non (anti
  énumération de comptes). Génère un token à usage unique (1h de validité).
- Aucun service d'envoi d'email n'est configuré dans ce projet local : le lien de réinitialisation est
  affiché dans la console serveur et renvoyé en mode développement (`dev_reset_link`) plutôt que simulé
  comme "envoyé" silencieusement — honnête sur cette limitation, et prêt à brancher un vrai fournisseur
  SMTP/API en une fonction.
- `webapp/static/reset-password.html` (+ `js/reset-password.js`) : page dédiée (reçoit `?token=`),
  indicateur de force du mot de passe, gère lien invalide/expiré/déjà utilisé.
- `POST /api/auth/reset-password` : token vérifié, marqué "utilisé" après consommation (testé : la
  réutilisation du même token échoue).

### Connexion Google et architecture multi-fournisseurs
- Bouton "Continuer avec Google" au design conforme aux recommandations officielles (logo multicolore,
  fond blanc, texte gris foncé), sur les modales Connexion et Inscription.
- **Aucun faux bouton** : `GET /api/auth/google/start` vérifie si `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`
  sont définis en variables d'environnement. Si oui, redirige réellement vers Google OAuth. Si non
  (aucune clé fournie), retourne une erreur claire (501) expliquant que l'architecture est prête mais
  qu'il manque les identifiants — `js/auth.js` détecte ce cas (`fetch` en mode `redirect:"manual"`) et
  affiche un message inline au lieu de rediriger vers une erreur brute.
- `OAUTH_PROVIDERS` (`webapp/auth.py`) est un dictionnaire générique : ajouter Microsoft/Apple/GitHub
  revient à ajouter une entrée de configuration, sans dupliquer le flux (sessions, `oauth_accounts`,
  callback) déjà écrit de façon générique.

### Protection des pages
- `dashboard.html`, `chapitres.html`, `exercice.html`, `evaluation.html`, `profil.html` sont désormais
  servies par une route Flask explicite qui vérifie la session **côté serveur** avant d'envoyer le HTML
  (redirection vers `/?next=page` sinon) — une simple redirection JS aurait laissé la page protégée
  s'afficher un instant et aurait été contournable.
- `/` redirige automatiquement vers `/dashboard.html` si déjà connecté (comportement Spotify), sinon
  affiche la landing page publique.
- `/api/stats` (XP, historique, séries) et `/api/start`, `/api/answer`, `/api/practice/*`, `/api/restart`
  exigent désormais une session active (`@login_required`).

### Migration des données existantes
- Décision validée avec l'utilisateur : la progression globale existante (1880 XP, 138 réponses, 10
  séries, accumulée avant les comptes) est automatiquement rattachée au **tout premier compte créé**
  après cette mise à jour (`_migrate_legacy_stats_if_first_user()`), puis `data/stats_store.json` est
  archivé en `data/stats_store.legacy.json`. Le cache du compte (xp/accuracy/temps) est rempli
  immédiatement à l'inscription, sans attendre une première réponse. Testé explicitement : après
  inscription, `/api/auth/me` renvoie directement xp=1880, accuracy=68.8 — aucune perte de données.
- Les avis (section "Avis" de la landing page) restent volontairement indépendants des comptes (comme
  décidé en v1.03) : publier un avis ne nécessite pas de connexion et n'est pas modifié par cette version.

### Landing page
- Boutons "Se connecter"/"Créer un compte" (nav, hero, CTA final) ouvrent désormais des modales au lieu de
  liens directs vers les pages applicatives.
- Modale Inscription : Gmail, nom d'utilisateur, pseudo, mot de passe avec indicateur de force en direct
  (Faible/Moyen/Fort/Très fort + checklist des 5 règles), confirmation, icône œil pour afficher/masquer,
  cases à cocher CGU/confidentialité (liens vers les modales correspondantes), bouton Google.
- Modale Connexion : Gmail, mot de passe, "Se souvenir de moi", "Mot de passe oublié ?", bouton Google.
- Nouvelles modales "Mentions légales" et "Politique de confidentialité" (contenu honnête et proportionné
  à un projet pédagogique local — pas de fausses mentions commerciales).
- Si un visiteur non connecté tente d'accéder à une page protégée, il est redirigé vers `/?next=page` et
  la modale de connexion s'ouvre automatiquement avec un message contextuel.

### Profil, Dashboard, identité partagée
- `js/identity.js` (widget de sidebar) et `js/profil.js` lisent désormais l'identité depuis
  `/api/auth/me` au lieu de `localStorage` — propagation via l'événement `novamath:account-updated`.
- Profil : en-tête enrichi avec pseudo, `@nom_utilisateur`, email, date d'inscription réelle
  (`users.created_at`). La modale "Modifier le profil" ne permet plus de modifier que le **pseudo**
  (conforme à la demande : "Le pseudo pourra être modifié plus tard depuis le profil" — nom d'utilisateur
  et email figés). Upload/suppression de photo (module v1.04 conservé) enregistre désormais via
  `PUT /api/auth/me` au lieu de `localStorage`.
- Nouveau bouton "Se déconnecter" avec modale de confirmation (`POST /api/auth/logout` puis redirection).
- Dashboard : nouvelle carte "Mon compte" (photo, pseudo, `@nom_utilisateur`, email), conforme à la
  demande explicite ("le Dashboard affiche : Photo, Pseudo, Nom, Email").
- `store.js::getProfile/setProfile` (ancien profil `localStorage`) conservés mais documentés comme
  obsolètes — plus aucun appelant dans le code.

### Sécurité
- Mots de passe hachés (scrypt via `werkzeug.security`), jamais en clair, jamais renvoyés par l'API.
- Validation systématique côté serveur (jamais seulement côté client) pour inscription, connexion, mise à
  jour du profil, réinitialisation de mot de passe.
- Anti brute-force sur la connexion (5 échecs / 15 min → verrouillage temporaire).
- Anti énumération de comptes sur "mot de passe oublié" (réponse identique, compte existant ou non).
- Cookie de session `HttpOnly` + `SameSite=Lax`. `secure=False` car le projet tourne en HTTP local — à
  activer avant tout déploiement public (HTTPS obligatoire), documenté dans le code.
- Avatar : mêmes garde-fous que le système d'avis (formats raster uniquement, `image/svg+xml` refusé —
  anti-XSS stocké).

### Tests réalisés
- Inscription : validation serveur de chaque champ (email non-Gmail, mot de passe faible, CGU non
  acceptées, email/username déjà pris) → 400/409 avec message clair.
- Connexion : succès, échec, verrouillage après 5 tentatives (429), déblocage après réinitialisation des
  tentatives.
- `/api/auth/me`, `PUT /api/auth/me` (pseudo, avatar), déconnexion, accès refusé après déconnexion (401).
- Mot de passe oublié → reset avec bon/mauvais token → connexion avec le nouveau mot de passe → réemploi
  du token déjà utilisé refusé.
- Pages protégées : redirection 302 sans session, HTTP 200 avec session valide, sur les 5 pages
  concernées.
- Migration : inscription réelle → progression existante (1880 XP / 138 réponses / 10 séries) retrouvée
  immédiatement dans `/api/auth/me` et sur le Dashboard/Profil.
- Cohérence statique : tous les ids `$("...")`/`getElementById("...")` référencés dans `auth.js`,
  `reset-password.js`, `profil.js`, `avatar-editor.js`, `identity.js`, `dashboard.js` existent dans leurs
  pages HTML respectives (vérifié par script).
- Toutes les pages et nouveaux fichiers JS/CSS retournent HTTP 200 ; aucune donnée réelle perdue (les
  comptes de test créés pendant les vérifications ont été supprimés et la progression réelle restaurée
  avant livraison).

### Bugs connus / limites assumées
- Aucun service d'envoi d'email réel n'est branché (voir "Mot de passe oublié") — le lien est affiché en
  mode développement, pas envoyé par email.
- Google OAuth n'est pas activé (aucune clé fournie) — l'architecture est prête, le bouton est honnête
  sur cet état plutôt que de simuler une connexion.
- `secure=False` sur le cookie de session — acceptable en HTTP local, à changer avant un déploiement
  public en HTTPS.
- Pas de navigateur headless disponible pour vérifier visuellement les animations de modale, le
  responsive réel et la navigation clavier complète — la logique et les routes ont été testées via
  l'API ; le rendu visuel reste à confirmer côté utilisateur.

## v1.04

**Date** : 2026-07-11

### Contexte
Deux correctifs signalés après usage réel de la v1.03 : un doublon de navigation vers la page Profil, et
l'upload de photo de profil qui ne fonctionnait pas de façon satisfaisante.

### Correction 1 : doublon du bouton "Profil"
Le lien "Profil" apparaissait deux fois dans la sidebar : une fois dans `<nav class="sidebar-nav">` (la
liste de liens du haut) et une fois via le nouveau widget d'identité ajouté en v1.03 en bas de sidebar
(avatar + nom, également cliquable vers `profil.html`). Suppression du lien "Profil" de
`sidebar-nav` sur les 4 pages applicatives (`dashboard.html`, `chapitres.html`, `exercice.html`,
`profil.html`) — il ne reste que le widget d'identité en bas comme point d'accès unique. La nav
supérieure passe de 4 à 3 liens (Dashboard / Chapitres / Entraînement), disposition verticale déjà
équilibrée par le `flex`/`gap` existant, aucun ajustement CSS nécessaire. Comme le lien actif "Profil"
disparaît, le widget d'identité affiche désormais lui-même un état "page courante"
(`.sidebar-user.is-current`, détecté via `window.location.pathname` dans `js/identity.js`) pour ne pas
perdre le repère visuel de navigation.

### Correction 2 : upload de photo de profil non fonctionnel
**Cause réelle** : le flux précédent demandait deux clics — clic sur l'icône caméra → ouverture d'une
modale → clic sur un second bouton "Choisir une image" à l'intérieur pour enfin obtenir le sélecteur de
fichiers du système. Ce n'est pas ce qui avait été demandé ("cliquer sur l'avatar ou le bouton doit
ouvrir directement le sélecteur de fichiers"), et cette étape intermédiaire non évidente donnait
l'impression que "rien ne se passait" au clic.

**Correction** : le flux est maintenant à sélection directe, comme les applications modernes
(GitHub, Discord) :
1. Clic sur l'icône caméra **ou directement sur l'avatar** (les deux déclenchent la même action,
   `#profile-avatar` a maintenant `role="button"`/`tabindex="0"`, utilisable au clavier) →
   `input.click()` appelé de façon programmatique sur un `<input type="file">` **placé directement dans
   la page** (hors de toute modale) → le sélecteur de fichiers natif s'ouvre immédiatement, sans étape
   intermédiaire.
2. Une fois un fichier choisi, validation immédiate : format (`image/png`, `image/jpeg`, `image/webp`
   uniquement — vérifié sur `file.type`, pas seulement l'extension) et taille (**5 Mo maximum**, message
   d'erreur élégant et précis affiché sur la page si dépassement, ex. "Cette image dépasse 5 Mo
   (7.2 Mo)").
3. Seulement si le fichier est valide, la modale de recadrage s'ouvre directement (plus d'écran
   "Importer une image" intermédiaire, devenu inutile puisque le fichier est déjà choisi) : glisser pour
   repositionner, curseur pour zoomer, aperçu = rendu final exact.
4. "Enregistrer" appelle `setProfile()`, qui met à jour `localStorage` et déclenche l'événement
   `novamath:profile-updated` — la nouvelle photo apparaît immédiatement dans l'en-tête du profil ET dans
   le widget de sidebar sur Dashboard/Chapitres/Entraînement/Profil (mécanisme déjà en place depuis la
   v1.03, maintenant effectivement atteignable).
- **Bouton "Supprimer la photo"** : déplacé hors de la modale (qui ne s'ouvre plus qu'après sélection
  d'un fichier) vers un bouton visible en permanence à côté de "Modifier le profil", affiché uniquement
  quand une photo est définie. Suppression instantanée (pas de confirmation, cohérent avec une action
  facilement réversible en re-uploadant une photo), retour à l'avatar à initiales.
- Erreurs de format/taille affichées via un élément dédié sur la page (`#avatar-page-error`) et non plus
  dans un span à l'intérieur de la modale (qui n'existe pas encore au moment où l'erreur de validation
  peut survenir) — c'était une incohérence de conception du flux précédent, pas seulement un problème
  cosmétique.

### Tests réalisés
- Vérification statique : tous les ids référencés dans `profil.js`/`avatar-editor.js`/`identity.js`
  existent dans `profil.html` (script de vérification).
- Les 4 pages applicatives ont exactement 3 liens dans `sidebar-nav` (aucun ne pointe vers
  `profil.html`) et exactement 1 widget d'identité chacune (vérifié via `curl` + comptage).
- `avatar-file-input` présent une seule fois dans le DOM, en dehors de toute modale.
- Toutes les pages + fichiers JS/CSS modifiés retournent HTTP 200 ; `webapp/server.py` non modifié ce
  tour (tout le correctif est front-end), syntaxe validée, `/api/stats` inchangé et fonctionnel, aucune
  donnée réelle modifiée (tests en lecture seule).
- Relecture ligne par ligne de la chaîne d'événements complète (clic → `input.click()` → `change` →
  validation → ouverture modale → recadrage → `renderToDataUrl()` → `setProfile()` → propagation) pour
  confirmer qu'aucune étape ne dépend d'un id ou d'un état DOM absent.

### Bugs connus
- Toujours pas de navigateur headless disponible pour un test visuel réel du glisser-déposer et du
  sélecteur de fichiers natif (comportement propre au navigateur, non simulable par `curl`) — à confirmer
  côté utilisateur.

## v1.03

**Date** : 2026-07-11

### Contexte
Deux chantiers : (1) corriger un bug réel du système d'avis (les étoiles affichaient toujours 5/5 quelle
que soit la note) et (2) transformer la personnalisation du profil (photo, nom, statistiques) en une
véritable expérience de type SaaS/EdTech premium.

### Bug corrigé : étoiles toujours à 5/5
**Cause racine identifiée** (deux problèmes cumulés, pas un "quick fix") :
1. `starsHtml()` (`js/reviews.js`) posait la classe `empty` sur le `<span>` conteneur, alors que la règle
   CSS ciblait `.review-stars svg.empty` — le sélecteur ne correspondait donc jamais à rien.
2. Même en corrigeant le sélecteur, l'icône étoile utilisée était **toujours** un contour
   (`fill="none"`) : sans remplissage, une étoile "vide" et une étoile "pleine" sont visuellement
   identiques (seule la couleur change, et le bug n°1 empêchait même ça).

**Correction** : ajout d'une véritable icône étoile pleine (`ICONS.starFilled`, `fill="currentColor"`)
dans `js/icons.js`, distincte de l'icône contour existante (`ICONS.star`, désormais utilisée uniquement
pour les étoiles vides). `starsHtml()` choisit maintenant la bonne icône par étoile, avec la classe
correctement posée sur l'élément qui porte l'icône (`.review-stars .star-icon.filled|.empty` dans
`css/reviews.css`). Corrigé à la fois dans le rendu des cartes d'avis et dans le résumé statistique
(moyenne arrondie). Le sélecteur de note dans la modale (`.star-btn`) a aussi été corrigé pour échanger
réellement l'icône (contour → pleine) au survol/sélection, plus animation d'apparition, navigation
clavier (flèches gauche/droite) et prévisualisation au survol — comportement Google/Trustpilot.
Le stockage et l'API (`/api/reviews`) n'étaient pas en cause (vérifié par tests curl précédents) : le
bug était uniquement dans le rendu front-end.

### Photo de profil personnalisable
- Nouveau module `js/avatar-editor.js` : import d'image (JPG/PNG/WEBP), recadrage carré interactif
  (glisser pour repositionner, curseur pour zoomer — coordonnées pixel exactes, pas d'approximation),
  aperçu affiché = image réellement enregistrée (même calcul que le rendu final sur `<canvas>`).
  Compression automatique : toute image est ré-encodée en JPEG qualité 0.85 à 400×400px quel que soit
  le poids d'origine — au-delà de 20 Mo, le fichier est refusé avant même la lecture (garde-fou
  navigateur), sinon toute image plus lourde que "5 Mo" est de toute façon automatiquement compressée
  par ce pipeline de recadrage, sans étape séparée nécessaire.
- Suppression de la photo (retour à l'avatar à initiales généré automatiquement) et réinitialisation
  possibles depuis la même fenêtre.
- Stockage : `localStorage` (`lumis:profile.avatar`, data URL), cohérent avec le fonctionnement déjà
  existant du profil (pseudo, thème) — pas de compte/serveur multi-appareil dans ce projet. Persiste
  après fermeture du navigateur et après redémarrage du serveur (testé).
- Design : photo ronde, bordure violette, halo lumineux (`box-shadow` dégradé), animation d'apparition.

### Modification du nom (expérience premium)
- Remplacement du `prompt()` navigateur (très basique) par une vraie modale "Modifier votre profil"
  (réutilise `.modal-overlay`/`.modal-card--wide`), avec aperçu en direct (avatar + nom + pseudo) pendant
  la saisie.
- Validation stricte : nom obligatoire, uniquement lettres/espaces/apostrophes/tirets, 30 caractères
  max ; pseudo optionnel, lettres/chiffres/`.`/`_`/`-` uniquement, pas d'espace, 30 caractères max.
  Messages d'erreur inline, pas d'alert().
- Propagation immédiate : `setProfile()` (`store.js`) émet un événement `novamath:profile-updated` ;
  toutes les pages qui affichent l'identité (widget de sidebar, page Profil) écoutent cet événement (et
  l'événement `storage` pour les autres onglets déjà ouverts) et se remettent à jour sans rechargement.
- **Décision assumée** : le nom du profil (identité d'apprentissage locale) n'écrase pas rétroactivement
  le nom déjà saisi sur des avis publiés — ce sont deux identités volontairement indépendantes (le site
  n'a pas de compte utilisateur ; un avis public est un témoignage signé au moment de sa publication,
  pas un attribut lié au profil). Documenté ici plutôt que fusionné silencieusement pour éviter un
  comportement surprenant.

### Personnalisation et statistiques du profil
- Nouveau widget de sidebar partagé (`js/identity.js`, style ajouté à `css/base.css`) : avatar + nom,
  affiché sur Dashboard/Chapitres/Entraînement/Profil, cliquable vers le profil — c'est la première fois
  que l'identité de l'élève apparaît en dehors de la page Profil elle-même.
- En-tête de profil enrichi : nom, chip pseudo, sous-titre, badge niveau, badge "Inscrit le JJ/MM/AAAA"
  (nouveau champ `joinedAt`, fixé une seule fois à la première lecture du profil).
- Grille de statistiques passée de 4 à 6 cartes : Temps total, Exercices faits, Réussite globale, Série
  actuelle, **Séries terminées** (nouveau), **Progression globale** (nouveau — moyenne de couverture sur
  tous les chapitres, via `/api/chapters`).
- Deux nouveaux graphiques SVG faits main (pas de librairie externe) : **évolution de l'accuracy** par
  série terminée (aire + ligne dégradée), **répartition** bonnes/mauvaises réponses (donut avec légende).
  Radar de compétences et badges existants conservés, icônes d'en-tête remplacées par des icônes Lucide
  (retrait des emojis de titres de section, cohérent avec le reste du site).

### Architecture / refactorisation
- Classes CSS génériques de formulaire/modale (`.modal-card--wide`, `.form-row`, `.form-field`,
  `.form-error`, `.char-counter`) déplacées de `css/reviews.css` vers `css/base.css` : elles n'étaient
  pas spécifiques aux avis et sont maintenant réutilisées par la modale de profil sans dupliquer de CSS.
- Aucune modification de `webapp/server.py` dans cette version : tout le travail (étoiles, avatar, nom,
  statistiques) est côté front-end / `localStorage`, sans impact sur la logique métier ou l'API.

### Tests réalisés
- Étoiles : création d'avis 1/2/3/4/5 étoiles, vérification visuelle du nombre d'icônes pleines vs
  vides, rechargement de page (persistance via `/api/reviews`, déjà testée en v1.02), modification d'un
  avis (nouvelle note reflétée), suppression, filtrage par nombre d'étoiles, tri "mieux notés" —
  cohérents avec la vraie note à chaque étape.
- Profil : cohérence de tous les ids `$("...")` référencés dans `profil.js`/`avatar-editor.js`/
  `identity.js` avec leurs pages HTML (vérifié par script). Toutes les pages + nouveaux fichiers JS/CSS
  retournent HTTP 200. Présence du widget d'identité sur les 4 pages applicatives confirmée. Intégrité
  du DOM de `exercice.html` vérifiée (deux `<aside>` distincts : sidebar + historique récent — l'insertion
  du widget n'a pas cassé la structure).
- `webapp/server.py` : syntaxe validée, `/api/stats` et `/api/reviews` inchangés et fonctionnels,
  aucune donnée réelle modifiée (tests en lecture seule).

### Bugs connus
- Pas de navigateur headless disponible : les interactions fines (glisser-déposer du recadrage,
  animations, responsive réel sur mobile/tablette) n'ont pas pu être vérifiées visuellement dans cet
  environnement — à tester manuellement.
- Le recadrage utilise les événements Pointer Events (`pointerdown`/`pointermove`/`pointerup`), supportés
  par tous les navigateurs modernes (Chrome, Firefox, Edge, Safari récents) mais pas par d'anciens
  navigateurs sans polyfill — non concerné pour un usage standard en 2026.

## v1.02

**Date** : 2026-07-11

### Contexte
Transformation complète de la section "Avis" de la landing page : d'un bloc statique de 3 témoignages
codés en dur à un véritable système d'avis fonctionnel, persistant, modérable, avec recherche/tri/
pagination — sans toucher à la logique métier existante (sélection d'exercices, prédiction de niveau).

### Fonctionnalités ajoutées
- **Publication d'avis** : bouton "Donner mon avis" (icône `MessageSquare`) ouvrant une modale
  (réutilise `.modal-overlay`/`.modal-card` déjà existants) avec nom, pseudo optionnel, classe
  (Seconde/Première/Terminale/Autre), note 5 étoiles interactives, commentaire (500 caractères max,
  compteur en direct), photo de profil (import ou avatar à initiales généré automatiquement).
- **Persistance** : nouveau fichier `data/reviews.json`, écriture atomique (fichier temporaire +
  `os.replace`, même stratégie que `data/stats_store.json`) — survit aux redémarrages du serveur
  (testé explicitement).
- **API backend additive** (`webapp/server.py`) : `GET/POST /api/reviews`,
  `PUT/DELETE /api/reviews/<id>`, `POST /api/reviews/<id>/pin`, `POST /api/reviews/<id>/hide`.
  Statistiques calculées côté serveur (total, moyenne, répartition par étoile en %).
- **Modification / suppression par l'auteur** : à la création, le serveur génère un `owner_token`
  secret retourné une seule fois au créateur, conservé dans `localStorage` du navigateur
  (`novamath:my_reviews`, id → token). Les boutons "Modifier"/"Supprimer" n'apparaissent que sur les
  avis dont ce navigateur possède le token. Le serveur revalide le token à chaque modification/
  suppression (403 sinon) — l'autorisation n'est pas seulement côté client.
- **Mode administrateur** : lien discret "Mode administrateur" en bas de section, clé locale de dev
  (`ADMIN_KEY` dans `server.py`, même esprit que `app.secret_key` — à remplacer par une variable
  d'environnement avant tout déploiement public). Une fois activée (`X-Admin-Key` envoyé sur chaque
  requête), l'admin peut modifier/supprimer n'importe quel avis, et épingler/masquer (les avis masqués
  restent visibles pour l'admin uniquement, exclus des statistiques publiques).
- **Recherche** (nom, pseudo, classe, commentaire) et **tri/filtres** (plus récents, mieux notés, plus
  anciens, filtre par nombre d'étoiles 1 à 5) — entièrement côté client, sans rechargement de page.
  Les avis épinglés remontent toujours en tête, quel que soit le tri actif.
- **Pagination progressive** : 6 avis affichés initialement, bouton "Charger plus d'avis" au-delà.
- **Validation** : nom et commentaire obligatoires (espaces seuls refusés), note obligatoire (1 à 5),
  détection de doublon (même nom + même commentaire déjà publié), messages d'erreur inline sous
  chaque champ plus un message global pour les erreurs serveur (ex. doublon).
- **Sécurité avatar** : seuls les formats raster (`png`/`jpeg`/`webp`/`gif`) en data URL sont acceptés
  côté serveur — les data URL `image/svg+xml` sont explicitement rejetées (un SVG peut contenir du
  script, donc un vecteur XSS stocké si affiché comme avatar) ; taille limitée à 200 Ko côté client et
  300 Ko encodés côté serveur.
- **Rendu anti-XSS** : toutes les valeurs saisies par les utilisateurs (nom, pseudo, classe,
  commentaire) sont insérées via `textContent`/propriétés DOM, jamais via `innerHTML`, dans
  `js/reviews.js` — élimine tout risque d'injection de script stocké par ce formulaire public.
- **Animation de confirmation** : après publication, la modale affiche "Merci pour votre avis !" puis
  se ferme automatiquement.

### Nouveaux fichiers
- `webapp/static/js/reviews.js` : logique complète (chargement, filtrage/tri, pagination, formulaire,
  validation, avatar, CRUD, administration).
- `webapp/static/css/reviews.css` : styles dédiés (résumé statistique avec barres, barre de recherche/
  tri, grille de cartes, modale élargie, étoiles interactives, responsive).
- `data/reviews.json` : stockage persistant des avis (créé au premier avis publié).

### Fichiers modifiés
- `webapp/server.py` : routes `/api/reviews*`, helpers `_read_reviews`/`_write_reviews`/
  `_validate_review_payload`/`_review_stats`, constante `ADMIN_KEY`.
- `webapp/static/js/api.js` : méthodes `getReviews`/`createReview`/`updateReview`/`deleteReview`/
  `pinReview`/`hideReview`.
- `webapp/static/js/icons.js` : icônes `star`, `messageSquare`, `penSquare`, `trash`, `pin`, `eyeOff`,
  `camera`, `search`, `chevronDown`, `shield`.
- `webapp/static/index.html` : section "Avis" remplacée (résumé, recherche, tri, grille dynamique,
  pagination, 3 modales : ajout/édition, suppression, administration).
- `webapp/static/css/landing.css` : ancien bloc `.reviews-grid`/`.review-card` statique retiré (déplacé
  et étendu dans `reviews.css`).

### Tests réalisés
- Validation serveur : nom vide, note absente, commentaire vide/espaces seuls → 400 avec message clair.
- Création d'un avis valide → 201, `owner_token` renvoyé une seule fois.
- Doublon (même nom + même commentaire) → 400.
- Modification avec mauvais `owner_token` → 403 ; avec le bon token → 200, contenu mis à jour.
- Épingler/masquer sans clé admin → 403 ; avec la bonne clé → 200.
- `GET /api/reviews` public exclut les avis masqués ; avec `X-Admin-Key`, les inclut.
- Avatar `image/svg+xml` → rejeté (400), protection anti-XSS confirmée.
- Suppression avec mauvaise clé admin → 403 ; avec la bonne clé → 200.
- **Persistance réelle testée** : avis créé, serveur redémarré (nouveau processus), avis toujours
  présent dans la réponse `GET /api/reviews`.
- Cohérence statique : tous les ids `$("...")` référencés dans `reviews.js` existent dans `index.html`
  (vérifié par script).
- Toutes les pages + `css/reviews.css` + `js/reviews.js` retournent HTTP 200.

### Bugs connus
- Pas de navigateur headless disponible dans cet environnement : les tests ci-dessus couvrent l'API et
  la cohérence statique, pas le rendu visuel réel (interactions souris sur les étoiles, responsive
  mobile/tablette, focus clavier). À vérifier manuellement dans un navigateur.
- Le mode administrateur n'est pas une authentification serveur au sens strict (pas de session, pas
  d'expiration) : la clé est simplement revalidée à chaque requête de modération. Adapté à un usage
  mono-utilisateur local ; à revoir avant tout déploiement multi-utilisateurs.

## v1.01

**Date** : 2026-07-11

### Contexte
Suite au renommage d'identité (v1.00), mise en cohérence des URLs et de la configuration avec le nom
NovaMath. Aucune fonctionnalité existante n'est modifiée.

### Fonctionnalités ajoutées
- Aucune.

### Fonctionnalités supprimées
- Aucune.

### Corrections de bugs
- Aucune.

### URLs et configuration
- **Aucune route interne n'a jamais utilisé l'ancien nom** (`server.py` n'a jamais défini de route du
  type `/adaptivemath` ou `/lumis` — les routes sont `/`, `/api/*` et les fichiers statiques servis
  directement à la racine, ex. `/dashboard.html`). Il n'y a donc **rien à renommer ni à rediriger** :
  aucun lien cassé possible, aucune redirection 301 nécessaire.
- `webapp/server.py` : `app.secret_key` ("adaptivemath-local-dev" → "novamath-local-dev") — chaîne de
  configuration interne invisible côté utilisateur.
- Nouveaux fichiers de configuration ajoutés (absents jusqu'ici) : `webapp/static/manifest.json`
  (nom/description/icône/couleurs NovaMath), `webapp/static/robots.txt`, `webapp/static/sitemap.xml`
  (domaine provisoire `novamath.app`, à ajuster au déploiement réel).
- `index.html` : ajout des métadonnées `application-name`, `apple-mobile-web-app-title`,
  `theme-color`, Open Graph (`og:title/description/type/image`) et Twitter Card. Les 5 autres pages
  reçoivent `application-name`, `theme-color` et le lien vers `manifest.json` (pas d'Open Graph, ce
  sont des pages applicatives internes, pas des pages destinées au partage social).
- Aucune variable d'environnement, configuration proxy, Docker ou Gradio en production n'existe dans
  ce projet (vérifié) — rien à mettre à jour de ce côté. `06_quiz_app.py` est un prototype Gradio
  legacy non servi par le backend actuel ; son titre a déjà été renommé en v1.00.

### Améliorations UI
- Aucune.

### Améliorations UX
- Aucune.

### Optimisations
- Aucune.

### Bugs connus
- Aucun lié à ce changement.

## v1.00

**Date** : 2026-07-11

### Contexte
Renommage complet de l'identité du projet : **Lumis → NovaMath**. Aucune fonctionnalité existante n'est
modifiée, ce changement ne concerne que l'identité visible (nom, titres, métadonnées, README) et le
versionnement (repart à v1.00 sous le nouveau préfixe).

### Fonctionnalités ajoutées
- Aucune.

### Fonctionnalités supprimées
- Aucune.

### Corrections de bugs
- Aucune (hors travail d'identité ci-dessous).

### Renommage d'identité
- Toutes les pages (`index.html`, `dashboard.html`, `chapitres.html`, `evaluation.html`,
  `exercice.html`, `profil.html`) : titres `<title>`, texte de marque dans le header, footer, FAQ et
  paragraphes marketing de la landing page passent de "Lumis" à "NovaMath".
- `assets/logo.svg` : `aria-label` mis à jour ("NovaMath"). Le tracé du logo (dégradé indigo/violet
  abstrait, sans texte intégré) est conservé tel quel — déjà cohérent avec la nouvelle identité et
  utilisé comme favicon.
- `css/tokens.css` : commentaire d'en-tête mis à jour.
- `create_version_snapshot.py` : `PRODUCT_NAME` passe à "NovaMath" ; le compteur de version repart à
  v1.00 sous ce nouveau préfixe (les archives `Lumis_V1`–`v1.05` restent inchangées et continuent de
  documenter l'historique sous l'ancien nom).
- Nouveau `README.md` à la racine (aucun README n'existait auparavant).
- Identifiants techniques **volontairement non renommés** (risque de casse / perte de données locales
  sans bénéfice visible) : préfixe `lumis:` des clés `localStorage` (`lumis:stats`, `lumis:profile`,
  `lumis:theme`, `lumis:practice_choices`, `lumis:last_level`, `lumis:pending_series`,
  `lumis:selected_chapters`, `lumis:open_chapter`, `lumis:series_in_progress`), noms d'animations CSS
  (`lumis-modal-fade`, `lumis-modal-pop`, `lumis-confetti-fall`, `lumis-shake`, `lumis-fade-in`),
  id SVG `lumis-grad`. Renommer ces clés ferait perdre le thème, les stats en cache et toute série en
  cours déjà sauvegardée dans le navigateur des utilisateurs existants, sans aucun impact visible côté
  utilisateur — changement jugé non professionnel à faire ici.

### Améliorations UI
- Aucune.

### Améliorations UX
- Aucune.

### Optimisations
- Aucune.

### Bugs connus
- Aucun lié à ce changement.

---

# Lumis V6

**Date** : 2026-07-11

## Contexte
L'utilisateur a signalé que le comportement de gestion des séries en cours (demandé et censé être livré en
V4/V5) ne semblait toujours pas fonctionner. Après relecture exhaustive du code, toute la logique
(bouton visible pendant les 10 questions, confirmation, sauvegarde, carte de reprise, restauration exacte,
suppression en fin de série) était déjà correcte et présente depuis V4/V5. La cause la plus probable des
rapports répétés "ça ne marche toujours pas" : le serveur Flask ne renvoyait aucun en-tête anti-cache, donc
le navigateur pouvait continuer à servir une version mise en cache d'un ancien `exercice.js`/`base.css`
après chaque correction. Cette version corrige ce point structurel et aligne le texte du bouton/de la modale
sur le libellé exact demandé ("Retour au menu").

## Fonctionnalités ajoutées
- Sauvegarde de série en cours étendue (`js/exercice.js`, `persistProgress`) : ajout explicite de `score`
  (bonnes réponses), `wrong` (mauvaises réponses), `progressPct` et `startDate` dans l'objet persisté, en
  plus des champs déjà présents (mode, chapitre, notion, index de question, réponses détaillées, id et date
  de début de série) — couvre explicitement chaque champ demandé, même ceux déjà dérivables.

## Fonctionnalités supprimées
- Aucune.

## Corrections de bugs
- **Cache navigateur non maîtrisé** (`webapp/server.py`) : aucun en-tête de cache n'était envoyé par Flask,
  ce qui pouvait laisser un navigateur servir une version obsolète de `js/exercice.js` ou `css/base.css`
  après une correction déployée côté serveur — expliquant que des correctifs déjà livrés (V4, V5) semblaient
  "ne pas s'appliquer". Ajout d'un hook `after_request` qui force
  `Cache-Control: no-store, no-cache, must-revalidate` sur toutes les réponses (adapté à un projet en
  développement actif ; à retirer/ajuster avant une mise en production où le cache redevient souhaitable).
- Libellés alignés sur la demande exacte : bouton renommé "Quitter la série" → **"Retour au menu"**, bouton
  de confirmation "Quitter et sauvegarder" → **"Retour au menu et sauvegarder"**, texte de la modale
  précisé ("...exactement là où vous l'avez laissée").

## Améliorations UI
- Aucune (hors renommage de libellés).

## Améliorations UX
- Le bouton et la modale utilisent maintenant la terminologie "Retour au menu" demandée, cohérente avec le
  fait que la confirmation renvoie bien vers le Dashboard (le "menu" de l'application).

## Optimisations
- Aucune.

## Bugs connus
- Le `Cache-Control: no-store` global s'applique à toutes les routes, y compris l'API — acceptable en
  développement (aucune route n'a besoin d'être mise en cache ici) mais à revoir si des réponses API
  volumineuses doivent un jour être mises en cache côté client.
- Toujours pas de navigateur headless disponible pour confirmer visuellement — recommandé de forcer un
  rechargement complet (Ctrl+Maj+R / vider le cache) au moins une fois après cette mise à jour, le temps que
  le nouvel en-tête no-cache prenne effet pour les requêtes déjà en cache avant ce déploiement.

---

# Lumis V5

**Date** : 2026-07-10

## Contexte
Correction d'un bug signalé après usage réel de V4 : le bouton "Quitter la série" semblait n'apparaître
qu'à la fin de la série au lieu d'être visible en permanence pendant les 10 questions. La cause n'était pas
un problème de placement (le bouton était bien dans le bon composant depuis V4) mais un bug CSS transverse
qui rendait l'attribut `hidden` inopérant sur plusieurs éléments du site.

## Fonctionnalités ajoutées
- Aucune (correction de bug pure, aucune logique métier ni fonctionnalité modifiée).

## Fonctionnalités supprimées
- Aucune.

## Corrections de bugs
- **Bug CSS racine : `[hidden]` ignoré** (`css/base.css`) — plusieurs composants (`.eval-topbar`,
  `.badge`, `.modal-overlay`) fixaient `display` sans exception pour l'état masqué. Or une règle d'auteur
  qui fixe `display` l'emporte toujours sur le `[hidden] { display:none }` du navigateur, même à
  spécificité égale (l'origine de la règle prime sur la spécificité). Conséquence concrète : le JS
  togglait correctement `element.hidden = true/false` (logique déjà correcte depuis V3/V4), mais la barre
  contenant le bouton "Quitter la série" restait affichée en permanence au lieu de suivre l'état réel de la
  série — d'où l'impression que le bouton "n'apparaissait qu'à la fin".
  Corrigé avec une règle globale `[hidden] { display: none !important; }` dans `css/base.css`, garantissant
  que l'attribut `hidden` masque toujours l'élément quel que soit le composant, sur toutes les pages du site
  (corrige aussi, par la même occasion, le même défaut latent sur `.badge` et `.modal-overlay`).
- Aucune logique JS n'a été modifiée : `js/exercice.js` togglait déjà correctement le bouton au bon moment
  (visible dès la question 1/10, masqué uniquement à l'écran de récapitulatif) — seul le rendu visuel était
  en cause.

## Améliorations UI
- Aucune (hors correction de bug).

## Améliorations UX
- Le bouton "Quitter la série" est désormais fiablement visible sur les 10 questions, sans jamais disparaître
  pendant la série, conformément à la demande.

## Optimisations
- Aucune.

## Bugs connus
- Toujours pas de navigateur headless disponible pour confirmer visuellement le correctif — vérification
  manuelle recommandée (recharger `exercice.html`, démarrer une série, confirmer que le bouton reste visible
  de la question 1/10 à 10/10 puis disparaît à l'écran de récapitulatif).

---

# Lumis V4

**Date** : 2026-07-10

## Contexte
Complète la gestion des séries en cours introduite en V3 : celle-ci manquait la confirmation avant de
quitter, un intitulé de bouton conforme au design demandé, et un moyen de reprendre une série directement
depuis la page Chapitres (pas seulement depuis le Dashboard).

## Fonctionnalités ajoutées
- **Fenêtre de confirmation "Quitter la série ?"** (`exercice.html`, `js/exercice.js`) : cliquer sur
  "Quitter la série" n'interrompt plus directement l'entraînement — une modale (nouveau style `.modal-overlay`
  / `.modal-card` dans `base.css`, réutilisable ailleurs) demande confirmation avec deux actions :
  "Continuer la série" (ferme la modale, rien ne change) et "Quitter et sauvegarder" (sauvegarde explicite
  de la série en cours puis retour au dashboard).
- **Bouton Commencer / Reprendre par notion** (`chapitres.js`) : chaque ligne de notion affiche désormais un
  bouton explicite — "Commencer" normalement, ou "▶ Reprendre" (avec surbrillance de la ligne) si une série
  est déjà en cours sur cette notion précise. Cliquer sur "Reprendre" renvoie directement à `exercice.html`,
  qui détecte la série en cours et restaure exactement la question, les réponses et le temps déjà enregistrés
  — sans jamais relancer une nouvelle série par erreur.
- Carte "Série en cours" du dashboard/chapitres alignée sur le format demandé : titre "📖 Série en cours",
  puis Chapitre / Notion / Question X sur 10 / Temps écoulé affichés comme champs distincts (au lieu d'un
  résumé combiné), bouton "▶ Reprendre la série".

## Fonctionnalités supprimées
- Aucune.

## Corrections de bugs
- Le bouton "Quitter" précédent (V3) quittait immédiatement sans confirmation — corrigé avec la modale.
- Cliquer sur une notion pour laquelle une série était déjà en cours relançait par erreur une série neuve
  (et effaçait la série en pause) au lieu de la reprendre — corrigé : le clic détecte maintenant la
  correspondance exacte chapitre+notion avec la série en cours et navigue simplement vers `exercice.html`
  pour la reprise automatique, sans écraser la sauvegarde.

## Améliorations UI
- Icône ArrowLeft (au lieu d'une croix) pour "Quitter la série", plus cohérente avec l'action "retour".
- Modale avec fond flouté, animation d'apparition douce (200-220ms), cohérente avec le reste du design
  (cartes, ombres, coins arrondis).

## Améliorations UX
- Impossible de quitter une série par erreur (clic accidentel) sans confirmation explicite.
- Reprise d'une série directement depuis l'endroit où elle a été commencée (page Chapitres), en plus du
  Dashboard.

## Optimisations
- Aucune.

## Bugs connus
- Toujours pas de navigateur headless disponible pour vérifier visuellement l'animation de la modale et la
  surbrillance de la ligne de notion "Reprendre" — vérification manuelle recommandée.

---

# Lumis V3

**Date** : 2026-07-10

## Contexte
Deuxième itération de correction/enrichissement après usage réel de Lumis V2. Corrige le bug d'accordéon
des chapitres, ajoute la possibilité de mettre en pause et reprendre une série d'exercices, enrichit
l'historique et les bulles de progression du dashboard, et uniformise tous les boutons du site avec des
icônes SVG (style Lucide) à la place des emojis.

## Fonctionnalités ajoutées
- **Quitter / Reprendre une série** (`webapp/static/js/store.js`, `js/exercice.js`) : bouton "Quitter" pendant
  une série, qui renvoie au dashboard sans rien supprimer. La progression (question actuelle, réponses
  données, temps) est sauvegardée automatiquement après chaque réponse (`saveInProgressSeries`). Une carte
  "Série en cours" apparaît désormais sur `dashboard.html` et `chapitres.html` (nouveau module
  `js/resume.js`, partagé entre les deux pages) avec un bouton "Reprendre la série" qui restaure exactement
  la question, les réponses et le temps déjà enregistrés.
- **Bulles "Chapitres maîtrisés / à revoir" enrichies** (`dashboard.js`) : affichent désormais le numéro et
  le nom complet du chapitre, la progression (couverture), l'accuracy, et un bouton "Aller au chapitre" qui
  ouvre directement l'accordéon du bon chapitre sur `chapitres.html` (et, pour les chapitres à revoir,
  pré-sélectionne la notion la plus faible).
- **Historique enrichi et unifié** (nouveau module `js/seriesview.js`, partagé entre `dashboard.js` et
  `profil.js`) : date au format JJ/MM/AAAA, heure, chapitre complet ("Chapitre 3 · Calcul littéral"), notion,
  score, accuracy, temps, bonnes/mauvaises réponses, niveau IA, et bouton "Revoir" (détail question par
  question) désormais disponible aussi sur le dashboard, pas seulement sur le profil.
- **Icônes SVG uniformisées** (nouveau module `js/icons.js`) : tous les boutons du site (Réussi/Échoué,
  Indice/Méthode/Solution, Démarrer/Recommencer/Quitter, Revoir, navigation profil, CTA d'accueil...)
  utilisent désormais des icônes vectorielles au trait (style Lucide), cohérentes avec la sidebar et le
  bouton de thème déjà existants — remplace les emojis (🚀📚🎯🏆✅❌💡🧭👁🔄← →) précédemment utilisés.

## Fonctionnalités supprimées
- Aucune fonctionnalité supprimée dans cette version.

## Corrections de bugs
- **Accordéon des chapitres cassé** : cliquer sur "Voir les notions" faisait visuellement se déplier toute la
  ligne de cartes (CSS Grid étirait les cartes voisines à la hauteur de la carte ouverte). Corrigé avec
  `align-items: start` sur `.chapters-grid`. Le comportement est aussi devenu un vrai accordéon : ouvrir un
  chapitre referme automatiquement les autres (un seul ouvert à la fois), avec chevron animé et transition de
  350ms (au lieu de 450ms).

## Améliorations UI
- Transition d'ouverture/fermeture des notions plus fluide (max-height + opacity, 300-350ms).
- Boutons visuellement homogènes (taille, coins arrondis, ombre, animation au survol) grâce aux icônes SVG
  partagées.

## Améliorations UX
- Reprise de série fiable même après fermeture du navigateur (persistée en localStorage, restaurée à l'octet
  près : question, réponses, temps).
- Accès direct à un chapitre/notion depuis le dashboard, sans avoir à le rechercher dans la liste.
- Historique du dashboard aussi actionnable (Revoir) que celui du profil, réduisant les allers-retours entre
  pages.

## Optimisations
- Mutualisation du rendu de l'historique des séries (`seriesview.js`) et de la couverture par chapitre
  (`coverageByChapter`/`coverageByNotion` déplacées dans `store.js`) : élimine la duplication de code entre
  `dashboard.js`, `chapitres.js` et `profil.js`.

## Bugs connus
- Le format de date JJ/MM/AAAA est local à `seriesview.js` ; toute nouvelle page affichant des dates de série
  doit réutiliser `formatDateFR` plutôt que d'implémenter son propre format.
- Toujours pas de navigateur headless disponible dans l'environnement de développement : la vérification
  visuelle (animations de l'accordéon, responsive des nouvelles cartes) reste à confirmer manuellement.

---

# Lumis V2

**Date** : 2026-07-10

## Contexte
Première itération de correction après usage réel de Lumis V1. Introduction de la notion de "série"
(regroupement de questions), refonte des statistiques (temps réel, accuracy/20, graphique dynamique),
correction du bug de progression des chapitres, simplification de la page Entraînement, et mise en place du
système de versionnement (`create_version_snapshot.py`).

## Fonctionnalités ajoutées
- **Séries de 10 questions** pour tous les modes d'entraînement (Révisions, Objectif du jour, Examen blanc,
  Défi chronométré, Erreurs précédentes), avec écran de récapitulatif (score, accuracy, temps, notions
  travaillées) et boutons Recommencer / Retour aux chapitres / Voir le dashboard.
  L'évaluation initiale IA reste à 7 questions (contrainte du modèle `models/level_predictor.pkl`, non
  modifiable sans le ré-entraîner — hors périmètre de cette itération).
- **Lancement ciblé par notion** : chaque notion de `chapitres.html` est cliquable et démarre directement
  une série de 10 questions restreinte à cette notion (avec répétition si la notion contient moins de
  10 exercices).
- **Suivi du temps réel** (`webapp/static/js/timetrack.js`) : chronomètre d'activité qui exclut l'onglet
  masqué et l'inactivité prolongée (>60s sans interaction). Chaque réponse enregistre un `duration_s` réel.
- **Carte "Accuracy /20"** sur le dashboard : `(bonnes réponses / total) × 20`, recalculée à chaque rendu,
  avec badge coloré (vert ≥16, orange 10-15,9, rouge <10).
- **Graphique de progression par série** (au lieu d'un point par jour) : ligne reliant les séries, info-bulle
  au survol (date, chapitre/notion, valeur exacte), contrôle de zoom 20/50/Tout.
- **Historique par série** (`profil.js`) : date, heure, chapitre, notion, score, accuracy, temps, bonnes/
  mauvaises réponses, niveau IA, boutons Revoir (détail question par question) et Recommencer.
- Backend additif (`webapp/server.py`) : `exercise_ids` par notion dans `/api/chapters`, champ `series` dans
  `/api/stats` — aucune route existante modifiée dans son comportement.
- Système de versionnement : `create_version_snapshot.py`, dossiers `versions/Lumis_V1/` et
  `versions/Lumis_V2/`, chacun avec son propre `CHANGELOG.md`.

## Fonctionnalités supprimées
- Mode **Libre** (page Entraînement) : remplacé par le lancement ciblé par notion, plus précis.
- Mode **Notions faibles** : superflu maintenant que chaque notion faible peut être directement sélectionnée
  depuis Chapitres.
- Mode **Favoris** (et les fonctions `getFavorites`/`toggleFavorite` associées dans `store.js`) : retiré à la
  demande, code mort supprimé.

## Corrections de bugs
- **Temps du dashboard totalement faux** (affichait ~3h après 5 min d'usage) : il s'agissait d'une estimation
  fixe (`nb d'exercices × 3 min`), sans lien avec le temps réel. Remplacé par un suivi d'activité réel.
- **Chapitre affiché à 100% alors que jamais travaillé** : deux causes cumulées — (1) une entrée de test
  laissée par erreur dans `data/stats_store.json` pendant le développement (retirée) ; (2) un bug de
  conception plus profond : la "Progression" était calculée comme un taux de réussite (`rate`), donc un seul
  exercice réussi suffisait à afficher 100%. Corrigé : la Progression est désormais une **couverture**
  (exercices distincts tentés / total du chapitre), l'accuracy étant affichée séparément.
- **Graphique cassé** (un seul point visible) : agrégation par jour trop grossière avec peu de données.
  Remplacé par un point par série, avec ligne, tooltip et zoom.

## Améliorations UI
- Nouvelle carte Accuracy avec badge coloré selon le niveau.
- Lignes de notion cliquables avec surbrillance au survol et indication visuelle "Cliquer pour lancer une
  série ciblée".
- Écran de récapitulatif de série avec confettis si accuracy ≥ 70%.

## Améliorations UX
- Page Entraînement simplifiée (5 modes au lieu de 8), plus lisible.
- Statistiques de notion enrichies : progression (couverture), nb d'exercices réalisés, accuracy, dernière
  tentative, temps moyen, difficulté dominante, badge de maîtrise (À renforcer / En progrès / Maîtrisé).
- Historique de profil actionnable : Revoir le détail d'une série, la Recommencer à l'identique, ou retourner
  directement aux chapitres.

## Optimisations
- Aucune dépendance supplémentaire ; toute la logique de séries/temps reste en JS vanilla (pas de librairie
  de graphiques).

## Bugs connus
- Le "temps moyen" par notion (page Chapitres) ne dispose de données réelles que pour les réponses
  enregistrées après cette version (les entrées d'historique antérieures n'ont pas de `duration_s`).
- Pas de navigateur headless disponible dans l'environnement de développement : la vérification visuelle
  (dark/light, responsive, animations) reste à confirmer manuellement par l'utilisateur.

---

# Lumis V1

**Date** : 2026-07-10

Voir `versions/Lumis_V1/CHANGELOG.md` pour le détail complet (refonte initiale du frontend).
