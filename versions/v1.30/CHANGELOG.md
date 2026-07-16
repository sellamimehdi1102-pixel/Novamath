# NovaMath v1.30

**Date** : 2026-07-13

**Nom de la mise à jour** : Chatbot pédagogique NovaMath (Phase 1)

## Nouveautés
- Nouvel onglet **Chatbot** dans la sidebar (`chatbot.html`) : conversations multiples avec historique, recherche, épinglage, renommage et suppression — même look & feel que le reste de NovaMath (cartes, boutons, tokens de couleur, sidebar rétractable).
- Réponses en **streaming** (SSE), rendu **Markdown + KaTeX** (via `marked.js` + `mathrender.js` déjà existant), boutons par message (copier, régénérer, continuer, j'aime/je n'aime pas, exporter Markdown, exporter PDF via impression navigateur).
- Architecture en couches complète : `webapp/chatbot/` avec Provider Manager (abstraction multi-fournisseurs), Provider Anthropic (Claude) fonctionnel, Context Builder (niveau, précision, notions faibles/maîtrisées, chapitres en cours — lu depuis les données NovaMath existantes), Prompt Builder (méthode pédagogique indice → indice → explication → méthode → solution, notation mathématique standard obligatoire), Rule Engine (court-circuite le LLM pour les salutations/identité), Conversation Manager (orchestration + quota).
- Nouvelles tables SQLite `conversations` / `chatbot_messages` / `chatbot_quota` (`webapp/db.py`), quota quotidien de 200 messages par utilisateur (429 explicite si dépassé côté UI).
- Nouvelle section **Paramètres → Chatbot** (`settings.js`) : fournisseur IA (Claude actif, autres grisés « bientôt disponible »), modèle, créativité, longueur de réponse, niveau d'explication, streaming/historique/mémoire activables.
- Panneau contextuel (colonne de droite) affichant en direct ce que le chatbot sait de la progression de l'élève.
- Clé API Anthropic lue exclusivement côté serveur (`ANTHROPIC_API_KEY`), jamais transmise au frontend.

## Corrections
- Aucune (nouvelle fonctionnalité additive, aucune route/fichier existant modifié dans sa logique).

## Optimisations
- Rule Engine : les salutations/questions d'identité ne déclenchent aucun appel IA.

## Fichiers modifiés
- Nouveaux : `webapp/chatbot/` (package complet), `webapp/static/chatbot.html`, `webapp/static/js/chatbot.js`, `webapp/static/css/chatbot.css`.
- Modifiés : `webapp/server.py` (routes `/api/chatbot/*` + page protégée), `webapp/db.py` (schéma + CRUD conversations/messages/quota), `webapp/auth.py` (préférences par défaut `chatbot`), `webapp/static/js/api.js`, `webapp/static/js/settings.js`, `webapp/static/js/i18n.js`, sidebar de `dashboard.html`/`chapitres.html`/`cours.html`/`exercice.html`/`profil.html`, `requirements.txt` (ajout `anthropic`).

## Bugs connus
- Phase 1 uniquement : pas de RAG documentaire sur les cours, pas de moteur de calcul symbolique indépendant (le LLM explique mais ne résout pas lui-même), Rule Engine minimal (couverture sans LLM très inférieure aux >70% visés à terme), un seul fournisseur IA réellement branché (Claude), pièces jointes (image/PDF/exercice) affichées mais non traitées (placeholder texte), export PDF via impression navigateur plutôt qu'une génération dédiée, pas de mémoire long-terme compressée (seulement les N derniers messages). Ces limites sont volontaires et prévues pour les phases suivantes.
- Vérification visuelle (rendu navigateur réel) non réalisée dans l'environnement de développement utilisé pour cette version (pas de navigateur disponible) — uniquement testé via API/curl (CRUD conversations, streaming SSE, quota, contexte, non-régression des pages existantes). À vérifier visuellement avant usage réel.

## Temps estimé de développement
- Une session de développement assistée (conception + implémentation backend/frontend + tests API).
