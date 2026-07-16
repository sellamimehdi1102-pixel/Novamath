# NovaMath v1.59

**Date** : 2026-07-14

**Nom de la mise à jour** : Audit qualité visuelle des bulles : alignement centré, débordement tableau/mots longs

Phase M du chantier v2.11 (dernière phase) : audit ciblé du CSS des bulles de conversation. Un vrai défaut structurel a été identifié en analysant le CSS (vérifiable sans navigateur) : la zone de saisie était centrée (`max-width:780px; margin:0 auto`) mais les bulles de messages ne l'étaient pas — elles s'alignaient au bord du conteneur (assistant à gauche, utilisateur à droite du viewport entier), créant une incohérence visuelle nette avec la barre de saisie centrée juste en dessous.

## Nouveautés
- (aucune — audit/correctifs uniquement)

## Corrections
- **Alignement incohérent** : `.chatbot-messages` n'avait pas `align-items: center`, alors que `.chatbot-input-wrap`/`.chatbot-live-suggestions` sont centrés (`max-width:780px; margin:0 auto`). Résultat : sur un écran large, les bulles de message s'alignaient aux bords du conteneur au lieu de partager la même colonne centrée que la barre de saisie. Corrigé : `.chatbot-messages { align-items: center; }` + `.chatbot-msg { width: 100%; }` (en plus du `max-width:780px` existant) — assistant et utilisateur restent chacun alignés à leur bord (gauche/droite) mais à l'intérieur de la même colonne de lecture centrée que la saisie, comme ChatGPT.
- **Débordement horizontal possible** : un tableau large dans une réponse (`.chatbot-msg-bubble table`) n'avait aucune protection contre le débordement — ajouté `display:block; overflow-x:auto` (même traitement que les blocs de code, déjà protégés).
- **Mots/URLs longs non coupés** : `.chatbot-msg-bubble` n'avait pas `overflow-wrap: break-word` — un token très long (URL, nombre) pouvait dépasser la largeur de la bulle. Ajouté.

## Optimisations
- (aucune)

## Fichiers modifiés
- `webapp/static/css/chatbot.css`

## Bugs connus
- Padding/rayons/police des bulles étaient déjà cohérents et basés sur les tokens du design system (`var(--radius-md)`, tailles uniformes) — aucune incohérence trouvée sur ces points, rien à corriger. Correctifs validés par relecture de code (CSS équilibré, 148 accolades ouvertes/fermées) ; pas de test visuel réel en navigateur (limite déjà documentée) — à valider par l'utilisateur avant diffusion large.

## Temps estimé de développement
- ~30min

---

## Clôture du chantier v2.11

Ce chantier (v1.52 → v1.59) fiabilise le chatbot NovaMath sur les points remontés : moteur d'intention pédagogique, exercices strictement scopés par chapitre, préréponses pédagogiques et paramètres réellement appliqués, mentions "@" qui récupèrent de vraies données, règle de progression centralisée (Maîtrisé = accuracy ≥ 70% et ≥ 10 tentatives), popups premium réutilisables, icône sidebar repositionnée, audit visuel des bulles. Deux bugs de production critiques ont été trouvés et corrigés en testant systématiquement le pipeline complet en Python (pas seulement les routes HTTP) : un bug de retrieval TF-IDF (pluriel/singulier faisait rater des correspondances évidentes) et un bug où le fournisseur par défaut ignorait entièrement le prompt système (rendant invisible tout le mécanisme de grounding depuis la v1.51).
