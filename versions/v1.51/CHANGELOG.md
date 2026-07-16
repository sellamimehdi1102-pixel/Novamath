# NovaMath v1.51

**Date** : 2026-07-14

**Nom de la mise à jour** : Refonte du système de mentions @ : palette robuste, badges, clavier, tolérance aux fautes

Correction demandée après retour utilisateur sur la v1.46 : le système de mentions "@" ne fonctionnait pas correctement (recherche multi-mots directe cassée dès qu'un espace était tapé sans catégorie préalable, aucune tolérance aux fautes de frappe, insertion en texte brut au lieu d'un badge visuel, pas de navigation clavier). Le bug racine identifié : l'ancienne détection de mention exigeait un mot unique sans espace tant qu'aucune catégorie n'avait été sélectionnée — "@Valeurs absolues" (mention directe multi-mots, cas d'usage central du cahier des charges) ne pouvait donc jamais fonctionner. Le système a été repensé en profondeur plutôt que rapiécé.

## Nouveautés
- Nouvelle route unique `GET /api/chatbot/mentions?q=` (`chatbot/services/mentions_service.py`) : sert à la fois les catégories de page réelles (Cours/Exercices/Notions/Séries/Dashboard/Progression/Statistiques/Objectifs/Quiz/Profil/Paramètres/Chatbot, chacune avec une vraie destination ou action) et les ressources (cours/exercices), avec repli flou (`search_service.py`, `difflib`, stdlib) pour les fautes de frappe ("puisance" → "Les puissances"). Renvoie un "Voulez-vous dire : X ?" pour une requête sans correspondance sérieuse (cutoff plus permissif, réservé à cette présentation explicitement incertaine).
- `search_service.py` : cours et exercices interrogés séparément puis fusionnés (au lieu d'un top-N unique) pour qu'une notion couvrant des dizaines d'exercices ne masque plus systématiquement le cours correspondant ; déduplication par titre pour la palette (une notion = une entrée, pas 8 exercices identiques) ; nouvelle fonction `resolve()` (lookup exact, pas une recherche) pour injecter la vraie donnée d'une mention déjà choisie.
- `knowledge_engine.py` : nouveau lookup direct `get_notion(chapter_id, notion_id)` et `all_documents()`, utilisés par le repli flou et la résolution de mention.
- **Composeur de message revu** (`chatbot-composer.js`, nouveau) : le `<textarea>` devient un `<div contenteditable>`, seul moyen d'insérer un vrai badge visuel non-éditable (`.chatbot-mention-chip`) supprimable en un seul Backspace — impossible avec un textarea (texte brut uniquement).
- `chatbot-mentions.js` réécrit : navigation clavier complète (flèches, Entrée, Échap, Tab), une seule source de vérité (l'endpoint backend, plus aucune logique de correspondance côté client), mention multi-mots fonctionnelle sans sélection de catégorie préalable.
- Grounding réel des mentions : `db.py` (colonne `mentions` JSON sur `chatbot_messages`, même schéma que `cards`), `conversation_manager.py`/`prompt_builder.py` injectent la vraie donnée de la ressource mentionnée dans le prompt système (jamais laissée à l'appréciation du LLM), persistée pour que `regenerate` réutilise les mêmes mentions.
- Actions de catégorie réelles (pas de redirection décorative) : Paramètres ouvre le vrai popup de la page, "Chatbot" démarre une vraie nouvelle conversation, Objectifs insère les vrais chiffres du jour (`/api/goals/daily`) dans le message.

## Corrections
- Bug racine : mention multi-mots ("@Valeurs absolues") impossible à taper sans choisir une catégorie au préalable (le menu se fermait dès le premier espace).
- Faux positifs du repli flou (ex. "thales" matchait "Intervalles" à 0.59 par pur hasard de lettres) : cutoff du résultat "confiant" relevé à 0.62 ; les correspondances plus faibles ne sont plus présentées que comme suggestion explicite ("Voulez-vous dire ?").
- `search_service.resolve()` levait une `KeyError: 'score'` sur toute mention résolue (les lookups directs ne passent pas par le chemin qui ajoute ce champ) — détecté en testant le pipeline complet (pas seulement les endpoints de surface), corrigé par un score explicite (1.0, correspondance exacte).

## Optimisations
- (aucune)

## Fichiers modifiés
- `webapp/chatbot/knowledge_engine.py`, `webapp/chatbot/services/search_service.py`, `webapp/chatbot/conversation_manager.py`, `webapp/chatbot/prompt_builder.py`, `webapp/db.py`, `webapp/server.py`
- `webapp/static/js/chatbot.js`, `webapp/static/js/api.js`, `webapp/static/js/i18n.js`, `webapp/static/css/chatbot.css`, `webapp/static/chatbot.html`
- Nouveaux : `webapp/chatbot/services/mentions_service.py`, `webapp/static/js/chatbot-composer.js`
- Réécrit : `webapp/static/js/chatbot-mentions.js`

## Bugs connus
- Comme pour les v1.46/v1.50 : pas de navigateur automatisé disponible dans cette session. Cette fois le pipeline complet a été rejoué directement en Python (au-delà des routes HTTP) pour attraper les erreurs invisibles en surface — ce qui a permis de trouver et corriger un vrai crash serveur (`KeyError: 'score'`) — mais l'interaction clavier/souris réelle du composeur contenteditable (badges, flèches, Backspace) reste à valider manuellement avant diffusion large.

## Temps estimé de développement
- ~3h (refonte backend + composeur contenteditable + tests pipeline complet incluant un bug de production trouvé et corrigé)
