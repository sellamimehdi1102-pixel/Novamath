# NovaMath v1.42

**Date** : 2026-07-13

**Nom de la mise à jour** : Architecture chatbot indépendante du fournisseur IA : FakeProvider par défaut, RetrievalEngine séparé, cache

## Nouveautés
- **FakeProvider** (`webapp/chatbot/providers/fake_provider.py`, nouveau fournisseur par défaut) : le chatbot fonctionne désormais **sans aucune API** dès l'installation. Il respecte exactement le même contrat `ChatProvider` que les fournisseurs IA (Anthropic, Ollama) — assemble une réponse à partir des cours NovaMath réels (via le Knowledge Engine) quand une correspondance nette existe, et l'admet honnêtement (sans jamais inventer) quand ce n'est pas le cas, avec une suggestion concrète (reformuler, consulter l'onglet Cours, activer Claude/Ollama).
- **RetrievalEngine séparé du Knowledge Engine** (`webapp/chatbot/retrieval_engine.py`, nouveau) : la mécanique de recherche générique (TF-IDF + cosinus) est désormais un module à part entière, sans aucune connaissance métier — il indexe et recherche des "documents" fournis par un appelant. `knowledge_engine.py` ne fait plus que savoir *où* chercher (cours NovaMath) et déléguer la recherche elle-même à ce moteur générique ; l'API publique (`search`, `try_answer_definition`, `context_block`) est inchangée pour le reste de la chaîne.
- **Cache mémoire** (`webapp/chatbot/cache.py`, nouveau) : si la même question est reposée par le même utilisateur avec le même fournisseur/modèle actif, la réponse déjà générée est réutilisée immédiatement (évite de refaire une recherche ou un appel IA identique) — LRU borné à 200 entrées, en mémoire process, intégré dans `conversation_manager.py` (`stream_reply` et `regenerate_last`).
- **Provider Manager étendu** (`webapp/chatbot/provider_manager.py`, `webapp/auth.py`) : `"fake"` enregistré comme fournisseur par défaut (`CHATBOT_PROVIDER` / réglage `provider`) ; Anthropic et Ollama restent des options activables sans aucun changement de code, exactement comme prévu par l'architecture en couches Frontend → ChatController (routes `webapp/server.py`) → ConversationManager → PromptBuilder → ContextBuilder → KnowledgeEngine/RuleEngine/MathEngine → RetrievalEngine → ProviderManager → fournisseur actif.
- **Paramètres → Chatbot** : "Aucun (moteur NovaMath, par défaut)" apparaît en premier et coché par défaut ; Claude et Ollama restent sélectionnables comme mises à niveau, sans redémarrage.

## Corrections
- Aucune (architecture neuve ; les moteurs Rule/Math/Knowledge et les providers Anthropic/Ollama existants n'ont pas changé de comportement).

## Optimisations
- Le cache évite de refaire une recherche TF-IDF ou un appel réseau (Anthropic/Ollama) pour une question déjà posée dans les mêmes conditions.

## Fichiers modifiés
- `webapp/chatbot/providers/fake_provider.py` (nouveau)
- `webapp/chatbot/retrieval_engine.py` (nouveau), `knowledge_engine.py` (refactorisé pour déléguer la recherche)
- `webapp/chatbot/cache.py` (nouveau)
- `webapp/chatbot/provider_manager.py` (fournisseur par défaut : `fake`)
- `webapp/chatbot/conversation_manager.py` (intégration du cache)
- `webapp/auth.py` (`DEFAULT_SETTINGS.chatbot` : `provider: "fake"`, `model: "moteur-novamath"`)
- `webapp/server.py` (commentaire de section : rôle de ChatController explicité)
- `webapp/static/js/settings.js` (option "Aucun" par défaut dans Paramètres → Chatbot)

## Bugs connus
- Un bug de seuil de confiance a été trouvé et corrigé pendant le développement (pas livré en l'état) : le premier seuil choisi pour le FakeProvider (0.10) laissait passer des correspondances non pertinentes (ex : une question totalement hors-sujet obtenait tout de même une réponse assemblée à partir d'un chapitre sans rapport). Calé sur 0.20 (même seuil que `knowledge_engine.try_answer_definition`, déjà validé), il admet désormais honnêtement ne pas savoir plutôt que de citer un cours sans rapport — au prix de refuser aussi quelques questions réellement couvertes mais formulées de façon trop vague.
- Limites déjà documentées en v1.40/v1.41 (retrieval TF-IDF non sémantique, pas d'analyse d'image) inchangées.

## Temps estimé de développement
- Session moyenne : conception de l'architecture en couches complète (FakeProvider, RetrievalEngine séparé, cache), refactor du Knowledge Engine sans changer son API publique, calibrage empirique du seuil de confiance du FakeProvider par des tests de scores TF-IDF réels sur des questions couvertes et hors-sujet, vérification bout en bout dans un navigateur réel (salutation, calcul, définition directe, question ouverte couverte, question hors-sujet, panneau Paramètres).
