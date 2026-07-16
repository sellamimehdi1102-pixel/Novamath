# NovaMath v1.62

**Date** : 2026-07-14

**Nom de la mise à jour** : RecommendationEngine : carte "Revoir ce chapitre" basée sur le chapitre le plus faible réel

Phase S (dernière phase) du chantier v2.12 : `action_cards_service.py` (déjà le rôle de "RecommendationEngine" demandé par le cahier des charges) propose désormais une carte d'action concrète quand la réponse portait sur la progression ou les statistiques — pointant vers le vrai chapitre le plus faible de l'élève (`{chapitre_le_plus_faible}`, Phase O), pas une suggestion générique.

## Nouveautés
- `action_cards_service._weak_chapter_card(chapter_id)` : construit une carte "Revoir ce chapitre" (type `course`, réutilise `chatbot_card_review_weak`, déjà une clé i18n existante) à partir d'une vraie notion du chapitre indexée par `knowledge_engine` — jamais une donnée inventée.
- `build_cards()` accepte un nouveau paramètre `weak_chapter_id` : quand l'intention de la dernière question était `progression`/`statistique` (Phase O), `conversation_manager.attach_action_cards()` calcule le chapitre le plus faible réel via `variable_resolver.resolve()` (même source que la réponse déjà composée) et le transmet.

## Corrections
- (aucune — extension d'une fonctionnalité existante)

## Optimisations
- (aucune)

## Fichiers modifiés
- `webapp/chatbot/services/action_cards_service.py`, `webapp/chatbot/conversation_manager.py`

## Bugs connus
- Vérifié en Python direct : une demande "Quels chapitres dois-je revoir ?" sur un compte avec un chapitre faible réel (Chapitre_5, 33% de réussite) produit bien une carte "Revoir ce chapitre" pointant vers Chapitre_5.

## Temps estimé de développement
- ~25min

---

## Clôture du chantier v2.12

Ce chantier (v1.60 → v1.62) inverse la priorité IA/local du chatbot NovaMath conformément à la demande explicite : le LLM devient un filet de sécurité, jamais le premier réflexe. Un moteur compositionnel (intention → variables réelles → templates avec variantes → habillage mode/longueur) répond désormais localement, sans appel au fournisseur IA, à toutes les demandes de progression, statistiques, dashboard, profil, paramètres, séries et exercices scopés par chapitre — vérifié par comptage réel des appels au fournisseur (0 appel pour ces intentions, fallback LLM conservé pour toute question ouverte ou inédite). Toutes les mentions "@" chargent désormais de vraies données ; une mention seule produit une réponse 100% locale. Les cartes de recommandation s'appuient sur les mêmes données réelles que les réponses composées.
