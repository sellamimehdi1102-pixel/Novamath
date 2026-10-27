# Mathadap — instructions projet

Les règles graphify (requêtes `graphify query/path/explain`, `graphify update .` après modification) sont définies dans `../CLAUDE.md` et s'appliquent aussi ici.

## Optimisation des tokens, du temps et des tests

Travailler de manière ciblée et proportionnée à la modification, sans sacrifier la qualité, la sécurité ni la fiabilité.

### Organisation

- Avant de commencer, identifier rapidement les fichiers concernés, l'impact probable et les tests réellement nécessaires.
- Préférer les modifications minimales aux réécritures intégrales.
- Regrouper les modifications cohérentes et lancer les tests au moment pertinent, pas après chaque micro-correction.

### Tests selon le risque

| Niveau | Validation |
|---|---|
| Mineure | Tests directement concernés. Vérification visuelle seulement si l'affichage change. Pas de pytest/Vitest complet sans raison. |
| Intermédiaire | Tests du module et des dépendances susceptibles d'être affectées. Vérification navigateur si le parcours utilisateur change. Suites globales seulement si le risque l'exige. |
| Majeure ou sensible | Tests ciblés + régression + suites complètes pytest/Vitest + build + vérifications fonctionnelles. |

Toujours traiter comme **sensible** : authentification, permissions, Stripe, quotas, publication, services partagés.

Ne jamais réduire les tests en supprimant des protections ou en ignorant un échec.

### Exercices et générateurs mathématiques

- Ne pas recalculer tous les exercices de toutes les classes à chaque modification.
- Générateur inchangé : conserver sa validation existante.
- Générateur modifié : tester les familles affectées.
- Nouveau générateur : validation approfondie avec vérification indépendante.
- Fonction mathématique commune modifiée : élargir aux familles dépendantes.
- Conserver les validations globales avant toute publication ou modification majeure.

### Lectures et sorties

- Recherches ciblées ; lire uniquement les fonctions et passages nécessaires ; ne pas relire ni réafficher les mêmes fichiers.
- Ne pas afficher la sortie complète des tests réussis ; détailler uniquement les échecs.
- Réutiliser la documentation existante.
- Ne pas sacrifier la compréhension des dépendances quand la modification est sensible.

### Rapports

- Messages intermédiaires limités aux découvertes importantes, problèmes et décisions nécessaires.
- Rapport final : modifications effectuées, tests exécutés et résultats, anomalies restantes, points d'attention.
- Rapport détaillé seulement sur demande ou après un chantier important.

### Sécurité — interdits absolus

Ces optimisations ne doivent jamais entraîner : erreur mathématique non contrôlée, régression non détectée, perte de données, publication involontaire, utilisation de Stripe live, suppression de modifications existantes, test déclaré réussi artificiellement.

**Aucun commit, push ou déploiement sans autorisation explicite.**
