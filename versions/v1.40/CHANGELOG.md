# NovaMath v1.40

**Date** : 2026-07-13

**Nom de la mise à jour** : Chatbot pédagogique premium : Ollama/Mistral local, Math Engine, Knowledge/RAG Engine, pipeline hybride

## Nouveautés
- **Fournisseur Ollama** (`webapp/chatbot/providers/ollama_provider.py`) : le chatbot utilise désormais par défaut un modèle local via Ollama (Mistral), sans aucun appel à une API cloud — `stream_chat()` (streaming HTTP `/api/chat`), `health()` (test `/api/tags`), `available_models()` (détection dynamique des modèles installés). Le provider Anthropic (Claude), déjà présent, reste disponible en secours ; changer de fournisseur ne modifie aucune autre couche (`provider_manager.py`).
- **Bannière de disponibilité** : si Ollama n'est pas démarré, un bandeau clair apparaît sur la page Chatbot (« Le moteur d'intelligence artificielle local n'est pas démarré ») avec les actions Réessayer / Continuer sans le chatbot — testé automatiquement au chargement de la page et à chaque échec d'envoi (nouvelle route `/api/chatbot/health`).
- **Math Engine** (`webapp/chatbot/math_engine.py`, sympy) : résout de façon déterministe — sans jamais appeler le LLM — les demandes de calcul (résoudre une équation, simplifier une fraction ou une racine, développer, factoriser, calculer un pourcentage ou une expression), avec une explication method + résultat déjà formatés en LaTeX (rendu KaTeX). Robuste aux accents omis dans les verbes déclencheurs (« resous » aussi bien que « résous »).
- **Knowledge Engine / RAG léger** (`webapp/chatbot/knowledge_engine.py`, TF-IDF scikit-learn sur les cours NovaMath) : répond directement (sans LLM) aux demandes de définition/rappel sans ambiguïté (« c'est quoi... », « définition de... ») en retrouvant la notion de cours correspondante ; sinon, injecte quelques notions pertinentes comme contexte compact dans le prompt système du LLM, pour des réponses ancrées dans le cours réel sans jamais y envoyer les cours en entier.
- **Pipeline hybride** (`conversation_manager.py::_try_internal_answer`) : Rule Engine (salutations/identité) → Math Engine → Knowledge Engine → LLM en dernier recours seulement — la majorité des questions factuelles/calculatoires sont désormais résolues sans appel au modèle IA.
- **Paramètres → Chatbot** : sélecteur de fournisseur (Ollama par défaut, Claude en option), liste de modèles détectés dynamiquement pour le fournisseur actif (`/api/chatbot/models`), température, longueur de réponse, niveau d'explication, streaming, historique, mémoire — déjà présents en Phase 1, mis à jour pour refléter Ollama/Mistral par défaut.
- **Pièce jointe PDF réelle** (`webapp/chatbot/attachments.py`, PyMuPDF) : le texte d'un PDF joint est extrait côté serveur (jamais écrit sur disque) et inséré dans le message ; limite de 30 pages / 15 Mo. Les images restent volontairement non analysées automatiquement (le fournisseur par défaut est un modèle texte, sans OCR installé) — le chatbot le dit explicitement à l'élève plutôt que de simuler une capacité absente.

## Corrections
- Aucune (fonctionnalité neuve ; l'essentiel de l'architecture Phase 1 — conversations, streaming, actions par message, quota, contexte NovaMath — était déjà solide et a été étendu sans réécriture).

## Optimisations
- Le contexte RAG (quelques notions de cours, jamais le corpus entier) limite fortement les tokens envoyés au LLM par rapport à l'injection de cours complets.
- Index TF-IDF du Knowledge Engine construit une seule fois en mémoire (paresseux, mis en cache) plutôt qu'à chaque requête.

## Fichiers modifiés
- `webapp/chatbot/providers/ollama_provider.py` (nouveau), `providers/base.py` (contrat étendu : health/available_models/current_model)
- `webapp/chatbot/provider_manager.py` (Ollama enregistré, détection dynamique des modèles, health_check)
- `webapp/chatbot/math_engine.py` (nouveau), `knowledge_engine.py` (nouveau), `attachments.py` (nouveau)
- `webapp/chatbot/conversation_manager.py` (pipeline hybride, contexte RAG)
- `webapp/chatbot/prompt_builder.py` (injection du contexte RAG)
- `webapp/auth.py` (chatbot par défaut : `provider: "ollama"`, `model: "mistral"`)
- `webapp/server.py` (routes `/api/chatbot/health`, `/api/chatbot/models`, `/api/chatbot/attachments/pdf`, gestion d'erreur `OllamaConnectionError`)
- `webapp/static/js/settings.js` (fournisseurs/modèles dynamiques), `webapp/static/js/chatbot.js` (bannière de santé, pièce jointe PDF réelle, limite image explicite), `webapp/static/js/api.js` (nouveaux appels)
- `webapp/static/chatbot.html`, `webapp/static/css/chatbot.css` (bannière)
- `requirements.txt` (sympy, PyMuPDF, requests)

## Bugs connus
- Le Knowledge Engine (TF-IDF) n'a pas la finesse d'un vrai moteur sémantique : sur une question ambiguë entre deux notions proches (ex: « racine carrée » comme opération vs comme fonction de référence), il peut hésiter — dans ce cas il choisit délibérément de ne PAS répondre seul et laisse le LLM trancher avec le contexte des deux notions.
- Les images jointes ne sont pas analysées (pas de vision, pas d'OCR local) — clairement annoncé à l'élève, pas une régression mais une limite assumée de cette première version 100% locale.

## Temps estimé de développement
- Session unique, longue durée : audit de l'architecture Phase 1 déjà en place (découverte d'un chatbot partiellement construit), ajout du provider Ollama et bascule du fournisseur par défaut, conception et implémentation du Math Engine (sympy) et du Knowledge/RAG Engine (TF-IDF), intégration au pipeline hybride, section Paramètres, pièce jointe PDF, débogage itératif (accents, exposants composés, ambiguïtés de retrieval), vérification bout en bout dans un navigateur réel avec un vrai appel Ollama/Mistral.
