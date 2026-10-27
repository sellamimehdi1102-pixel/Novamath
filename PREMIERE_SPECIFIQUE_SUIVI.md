# Première spécifique (`premiere_specifique`) — suivi

Historique antérieur (programme de spécialité 2026, séparation d'avec `premiere`) : `PREMIERE_SPECIALITE_SUIVI.md`, non modifié par ce chantier.

## 1. Référence

Manuel fourni par l'utilisateur : « Cours de mathématiques – Première ES/L » (`Cours 1ES-L.pdf`, 40 pages, 9 chapitres). Il correspond à l'**ancienne Première ES/L** : il sert de périmètre pédagogique ; ce n'est pas un programme officiel en vigueur. Ses calculs sont vérifiés (coquilles relevées en §5), son texte n'est pas recopié.

| Ch. | PDF (pages) | Sections |
|---|---|---|
| 1 | Pourcentages (3-5) | proportions ; taux d'évolution (déterminer, appliquer, coefficient multiplicateur) ; taux réciproque ; indices base 100 ; évolutions successives |
| 2 | Fonctions numériques (6-8) | notion de fonction, variations (définitions), représentation graphique ; racine carrée (variations, courbe, symétrie avec x² par rapport à y = x) ; cube (variations, signe, symétrie par rapport à l'origine) |
| 3 | Polynômes du second degré (9-13) | définitions, discriminant ; forme canonique (preuve) ; racines et factorisation (preuve) ; variations, parabole, sommet ; signe ; tableau récapitulatif |
| 4 | Statistiques (14-17) | notation Σ ; mode, moyenne (avec fréquences), médiane ; quartiles ; boîte à moustaches ; variance (deux formules), écart-type, écart interquartile, étendue ; résumer une série |
| 5 | Dérivation (18-22) | taux d'accroissement, nombre dérivé ; tangente (équation, preuve) ; fonction dérivée, dérivées usuelles (k, x, x², 1/x, xⁿ, 1/xⁿ, √x) ; somme, λu, produit, inverse, quotient |
| 6 | Dérivation et variations (23-25) | dérivée d'une fonction monotone (preuve) ; signe de f′ et variations ; extremums locaux |
| 7 | Suites numériques (26-31) | suites explicites, récurrentes ; représentation ; sens de variation ; arithmétiques (terme général, variations, points alignés) ; géométriques (terme général, variations de qⁿ et de u₀qⁿ) |
| 8 | Variables aléatoires (32-34) | événements (∩, ∪, contraire, incompatibles, lois de De Morgan) ; probabilités, P(A ∪ B) ; variable aléatoire, loi ; espérance, variance (deux formules), écart-type ; loi des grands nombres |
| 9 | Loi de Bernoulli et loi binomiale (35-40) | expériences indépendantes ; répétition (produit) ; loi de Bernoulli (E, V, σ) ; schéma de Bernoulli, coefficients binomiaux ; loi binomiale (formule, E = np, V, σ) ; représentation ; intervalle de fluctuation à 95 % et règle de décision |

## 2. Audit différentiel (2026-10-26, avant toute modification)

État initial : 13 chapitres, 57 notions, 1 176 exercices rédigés, 5 854 générés. Progression : **aucune** dans les données réelles (0 fichier de cours, 0 réponse) ; une seule dans les données isolées de prévisualisation (compte de vérification) — renumérotation possible sans migration.

Légende — décisions : CONSERVER, ADAPTER, DÉPLACER, RETIRER (retrait du curriculum actif ; sources conservées), CRÉER ; « INCERTAIN » = conservé provisoirement et signalé.

| Actuel (ch. — notion) | PDF | Décision | Justification | Exercices / générateurs |
|---|---|---|---|---|
| 13 — Évolutions et taux | Ch. 1 II, III, V | DÉPLACER → ch. 1 | taux, coefficient multiplicateur, réciproque, évolutions successives : exactement le manuel | 4 rédigés ; `automatismes` (5 familles) réutilisés |
| — | Ch. 1 I | CRÉER « Proportions » | absente | à créer (banque + générateur) |
| — | Ch. 1 IV | CRÉER « Indices base 100 » | absente | à créer |
| 13 — Fonctions et représentations | Ch. 2 I | DÉPLACER + ADAPTER → « Rappels sur les fonctions » | image, antécédents, courbe, lecture de variations ; ajouter les définitions de (stricte) croissance ; retirer l'équation de droite (Seconde) | 4 rédigés ; familles `image_antecedent`, `lecture_variations` réutilisées, `droite` retirée |
| — | Ch. 2 II | CRÉER « Fonction racine carrée » | absente | à créer |
| — | Ch. 2 III | CRÉER « Fonction cube » | absente (la symétrie de la courbe reprend la notion « fonctions impaires ») | à créer |
| 2 — Fonction polynôme de degré 2 | Ch. 3 I, II, IV | CONSERVER (→ ch. 3) | forme canonique, variations, parabole, sommet | 85 rédigés ; `second_degre_formes` (5 familles) |
| 2 — Équations du second degré | Ch. 3 I, III | CONSERVER (→ ch. 3) | discriminant, racines | 22 rédigés ; `second_degre` : famille `somme_produit` retirée |
| 2 — Propriétés d'un trinôme | Ch. 3 III | ADAPTER (→ ch. 3) | factorisation conservée ; somme et produit des racines hors manuel | 44 rédigés (somme/produit) retirés, 15 conservés ; 4 familles (somme/produit) retirées |
| 2 — Signe du trinôme et inéquations | Ch. 3 IV c | CONSERVER (→ ch. 3) | signe ; les inéquations en sont l'application directe | 30 rédigés ; famille `position_relative` retirée |
| 2 — Modéliser et optimiser | — | RETIRER | problèmes de modélisation absents du manuel | 12 rédigés, 4 familles |
| 13 — Calcul numérique et algébrique | (prérequis du Ch. 3) | **INCERTAIN** — conservé provisoirement en fin de ch. 3 | identités remarquables, produit nul, signe de ax + b : utilisés par les preuves du Ch. 3 mais non enseignés par le manuel | 5 rédigés, 4 familles ; à valider avant tout retrait |
| 13 — Statistiques et probabilités | Ch. 4 II a ; Ch. 8 I | DÉPLACER (scindée) | moyenne, médiane, étendue → ch. 4 ; tableau croisé, contraire → ch. 8 | 4 rédigés ; `statistiques` → ch. 4, `tableau_croise` → ch. 8 |
| — | Ch. 4 I, II a | CRÉER « Notation Σ et indicateurs de tendance centrale » | absente (reprend moyenne, médiane) | à créer |
| — | Ch. 4 II b, c | CRÉER « Quartiles et diagramme en boîte » | absente | à créer |
| — | Ch. 4 II d, e | CRÉER « Indicateurs de dispersion » | absente | à créer |
| 3 — Nombre dérivé. Tangente | Ch. 5 I | CONSERVER (→ ch. 5) | | 37 rédigés ; `tangente`, `derivation_2026` (tangentes) |
| 3 — Fonction dérivée | Ch. 5 II a | CONSERVER (→ ch. 5) | même tableau de dérivées usuelles | 67 rédigés ; `derivatives` : familles composées (√(ax+b), (ax+b)ⁿ) retirées |
| 3 — Opérations et dérivation | Ch. 5 II b-e | CONSERVER (→ ch. 5) | | 91 rédigés : 3 dérivées de (ax+b)ⁿ retirées |
| 3 — Approximation affine et dérivabilité | — | RETIRER | absente du manuel | 9 rédigés, 2 familles |
| 4 — Variations d'une fonction | Ch. 6 I | CONSERVER (→ ch. 6) | | 10 rédigés ; `variations` : `variations_racine` (√(2x), dérivée composée) retirée |
| 4 — Nombre dérivé et extremums locaux | Ch. 6 II | CONSERVER (→ ch. 6) | | 18 rédigés |
| 4 — Fonctions paires et impaires | (Ch. 2 III c) | RETIRER | seule la symétrie de la courbe du cube figure au manuel (reprise dans « Fonction cube ») | 6 rédigés |
| 4 — Inégalités et position relative | — | RETIRER | absente | 6 rédigés |
| 4 — Étude d'une fonction et méthode de Newton | — | RETIRER | absente | 6 rédigés |
| 1 — Généralités sur les suites | Ch. 7 I a-c | CONSERVER (→ ch. 7) | | 31 rédigés |
| 1 — Sens de variation d'une suite | Ch. 7 I d | CONSERVER (→ ch. 7) | | 27 rédigés |
| 1 — Suite arithmétique | Ch. 7 II | CONSERVER (→ ch. 7) | | 13 rédigés (1 somme retirée) ; famille `arith_somme` retirée |
| 1 — Suite géométrique | Ch. 7 III | CONSERVER (→ ch. 7) | | 13 rédigés ; famille `geo_somme` retirée |
| 1 — Calcul de sommes | — | RETIRER | absent (seule la notation Σ figure, au Ch. 4) | 11 rédigés, 5 familles |
| 1 — Notion de limite d'une suite | — | RETIRER | absente | 13 rédigés, 5 familles |
| — | Ch. 8 I | CRÉER « Rappels de probabilités : événements » | absente | à créer ; `tableau_croise` réutilisé |
| 10 — Variables aléatoires réelles | Ch. 8 II a, b | CONSERVER (→ ch. 8) | | 23 rédigés |
| 10 — Espérance – Variance – Écart-type | Ch. 8 II c | ADAPTER (→ ch. 8) | linéarité et V(aX + b) hors manuel | 7 rédigés (Y = aX + b) retirés ; famille `transformation_affine` retirée |
| 10 — Simulation et échantillonnage | Ch. 8 II d | ADAPTER → « Loi des grands nombres et simulation » | le manuel : fréquences et moyenne → probabilités et espérance ; retirer 2σ/√n | 6 rédigés à revoir |
| 9 — Épreuves indépendantes et épreuves de Bernoulli | Ch. 9 I, II | DÉPLACER + ADAPTER → « Expériences indépendantes et loi de Bernoulli » | ajouter E = p, V = p(1 − p) ; retirer marche aléatoire | 10 rédigés |
| — | Ch. 9 III | CRÉER « Schéma de Bernoulli et loi binomiale » | absente | à créer (banque + générateur) |
| — | Ch. 9 IV | CRÉER « Échantillonnage et règle de décision » | absente | à créer |
| 9 — Probabilité conditionnelle, Arbres pondérés, Indépendance | — | RETIRER | absents du manuel (seules les expériences indépendantes y figurent) | 69 rédigés ; `probabilites_conditionnelles` |
| 5 — Fonction exponentielle (7 notions) | — | RETIRER | absente du manuel | 84 rédigés ; `exponentielle` |
| 6 — Trigonométrie (3) | — | RETIRER | absente | 162 rédigés ; `trigonometrie` |
| 7 — Produit scalaire (4) | — | RETIRER | absent | 97 rédigés ; `produit_scalaire` |
| 8 — Géométrie repérée (4) | — | RETIRER | absente | 76 rédigés ; `geometrie_reperee` |
| 11 — Logique et ensembles (4) | — | RETIRER | absents | 20 rédigés ; `logique_ensembles` |
| 12 — Algorithmique, listes (4) | — | RETIRER | absents | 16 rédigés ; `listes_python` |

Fichiers impactés : `webapp/course_content/cours_premiere_specifique/`, `exercises_bank_premiere_specifique.json`, `exercises_generated_premiere_specifique.json`, `tools/premiere_specifique/` (sources), `tools/build_premiere_specifique_*.py`, `tools/generate_premiere_specifique_exercises.py`, `webapp/exercise_generator_premiere_specifique/`, l'entrée `premiere_specifique` de `exercise_generator/registry.py`, tests `test_premiere_specifique_*`, suggestions d'interface. Aucun fichier de `premiere`, `quatrieme`, `troisieme`, `seconde`.

Réutilisation : les sources retirées restent dans `tools/premiere_specifique/reserve/` et les générateurs restent dans leur package (seule leur exposition change).

Écarts entre l'audit et la réalisation : « Indicateurs de dispersion » s'appelle finalement « Variance, écart-type et dispersion » (meilleure orientation du chatbot) ; « Propriétés d'un trinôme » est intitulée « Racines et factorisation d'un trinôme » (identifiant conservé) ; trois exercices de l'ancienne notion « Simulation » (Python) et l'approfondissement 70205 ont aussi été mis hors périmètre ; au chapitre 9, 69408 à 69410 (Monte-Carlo, Python, marche aléatoire) également.

## 3. Réalisation (2026-10-26)

**Sauvegardes** (nouveau dossier, celles du 26/10 matin intactes) : `%USERPROFILE%\Mathadap_sauvegardes\2026-10-26_avant_adaptation_1ESL\` — 82 fichiers de la classe avant adaptation, inventaire SHA-256 vérifié.

**Structure** : 13 chapitres → 9 (ordre du manuel) ; 57 notions → 30.

| Ch. | Titre | Notions (identifiant conservé ou créé) | Exercices rédigés | Générés |
|---|---|---|---|---|
| 1 | Pourcentages | Proportions et pourcentages (créée) ; Évolutions et taux (déplacée, ex-ch. 13) ; Indices base 100 (créée) | 19 | 376 |
| 2 | Fonctions numériques | Rappels sur les fonctions (adaptée, ex-« Fonctions et représentations ») ; Fonction racine carrée (créée) ; Fonction cube (créée) | 19 | 231 |
| 3 | Polynômes du second degré | Fonction polynôme de degré 2 ; Équations du second degré ; Racines et factorisation d'un trinôme (adaptée) ; Signe du trinôme et inéquations ; Calcul numérique et algébrique (**provisoire, INCERTAIN**) | 155 | 475 |
| 4 | Statistiques | Notation Σ et indicateurs de tendance centrale ; Quartiles et diagramme en boîte ; Variance, écart-type et dispersion (créées) | 19 | 272 |
| 5 | Dérivation | Nombre dérivé. Tangente ; Fonction dérivée ; Opérations et dérivation | 192 | 335 |
| 6 | Dérivation et variations | Variations d'une fonction ; Nombre dérivé et extremums locaux | 28 | 371 |
| 7 | Suites numériques | Généralités ; Sens de variation ; Suite arithmétique ; Suite géométrique | 83 | 216 |
| 8 | Variables aléatoires | Rappels de probabilités : événements (créée) ; Variables aléatoires réelles ; Espérance – Variance – Écart-type (adaptée) ; Loi des grands nombres et simulation (adaptée) | 59 | 466 |
| 9 | Loi de Bernoulli et loi binomiale | Expériences indépendantes et loi de Bernoulli (adaptée, ex-ch. 9) ; Schéma de Bernoulli et loi binomiale (créée) ; Échantillonnage et règle de décision (créée) | 23 | 185 |

**Notions** : 20 identifiants conservés (dont 13 sans modification de fond, 5 adaptées, 2 déplacées), 10 créées, 37 retirées du curriculum actif (sources en réserve). Aucune notion « INCERTAINE » supprimée : « Calcul numérique et algébrique » est conservée provisoirement en fin de chapitre 3, à valider.

**Exercices rédigés** : 1 176 → 597. 517 réutilisés sans aucune modification de contenu (rattachés à leur nouveau chapitre ou à leur notion du manuel) ; 80 créés (bloc 80 000 + 1 000 × chapitre, valeurs recalculées en fractions exactes ou par SymPy) ; 659 retirés du curriculum actif (conservés dans les modules : `EXERCICES_HORS_PERIMETRE` ou réserve). Niveaux servis : 1 (202), 2 (236), 3 (127), 4 (32). Chaque notion a son mini-quiz de 3 exercices de niveau ⩽ 2.

**Exercices générés** : 5 854 → 2 927. 1 984 conservés (mêmes identifiants et contenus ; 26 dont l'écriture a été corrigée : « −1t² », « + 0 ») ; 943 créés ; 3 870 retirés (familles hors manuel, non servies).

**Générateurs** :
- réutilisés sans modification : `derivatives`, `tangente`, `derivation_2026`, `variations`, `variables_aleatoires`, `second_degre_formes`, `automatismes` (familles redistribuées dans les ch. 1, 2, 3, 4, 8) ;
- adaptés (écriture seulement, tirages et identifiants inchangés) : `suites`, `second_degre` ;
- créés : `pourcentages_1es`, `fonctions_reference_1es`, `statistiques_1es`, `evenements_1es`, `loi_binomiale_1es` (socle `_commun_1es`), quatre niveaux chacun ;
- table d'adaptation `programme_1es.py` : rattachement de chaque famille conservée à son chapitre et à sa notion ; vues pour la génération à la demande (entrée `premiere_specifique` du registre partagé, seule modifiée) ;
- non exposés (code conservé) : `exponentielle`, `trigonometrie`, `produit_scalaire`, `geometrie_reperee`, `probabilites_conditionnelles`, `logique_ensembles`, `listes_python`, et les familles hors manuel (somme et produit des racines, dérivées composées, approximation affine, sommes et limites de suites, transformation affine, équation de droite…).

**Couverture du PDF** : les 9 chapitres et toutes leurs sections sont couverts (cours + exercices). Points traités plus légèrement : représentation graphique d'une suite (dans « Généralités ») ; usage de la calculatrice pour la loi binomiale (mentionné, sans menus de calculatrice).

**Outils** : `tools/premiere_specifique/chapitres.py` (9 chapitres + réserve) ; construction globale des cours et de la banque avec garde-fous (aucune notion ni aucun exercice ne disparaît sans être déclaré retiré) ; `ids_avant_adaptation.py` fige les identifiants historiques.

## 4. Tests et contrôles

- Tests de la classe : `test_premiere_specifique_1es.py` (sources fidèles, banque, quiz, structure du manuel, aucune famille hors manuel servie, droits Free/Premium/Ultra sur les 9 chapitres en HTTP), `test_premiere_specifique_generateurs_1es.py` (contrat des 5 nouveaux modules, 14 familles recalculées indépendamment, pool servi identique aux tirages), `test_premiere_specifique_derivation_free_coverage.py` (ex-chapitre 3, dérivation désormais ch. 5), `test_premiere_specifique_generateurs_reserve.py` (générateurs en réserve : code toujours vérifié, familles non exposées).
- KaTeX : 0 erreur sur 14 258 formules ; écritures fautives : aucun défaut réel restant (faux positifs : sommes d'écarts « + 0 », substitutions « (3)^2 »).
- Chatbot (orientation des questions) : 13/14.
- Autres classes : Première historique identique à la sauvegarde A ; Seconde, Troisième, Quatrième identiques à la sauvegarde B ; registre des classes : seul ajout le profil `premiere_specifique`.

## 5. Coquilles relevées dans le manuel (non reproduites)

- Ch. 1 p. 3 : « comprise en 0 et 1 » (lire « entre »).
- Ch. 4 p. 17 : « 1×8⁵ » dans le calcul de la variance (lire 1×8²).
- Ch. 5 p. 18 : le calcul de f′(−3) pour la fonction carré donne « 6 + h » et f′(−3) = 6 ; la bonne valeur est −6 (repris correctement p. 19). P. 19 : « 9 = −6×3 + b » (lire −6×(−3)).
- Ch. 6 p. 25 : x² + 2x − 1 admet en x = −1 un **minimum** local égal à −2 (et non un maximum).
- Ch. 7 p. 27 : « strictement décroissante si u_{n+1} ⩽ u_n » (lire « décroissante ») ; p. 29 : « constante si et seulement si r > 0 » (lire r = 0) ; p. 28 : raison et premier terme inversés dans l'exemple u_n = 3 + 5n.
- Ch. 8 p. 34 : « E(X) = Σ pᵢ x₁ » (lire xᵢ).

## 6. Anomalies et points ouverts

- **À valider** : « Calcul numérique et algébrique » (rappel provisoire en fin de chapitre 3) — conserver comme rappel ou retirer.
- « Généralités sur les suites » garde un exemple d'algorithme en Python (outil, pas notion du manuel) — à valider.
- Chatbot : « factoriser un trinôme avec le discriminant » n'est orienté vers aucune notion (score faible, réponse confiée au modèle de langage) ; « comment factoriser un trinôme » est bien orienté.
- Deux notions sans générateur (exercices rédigés seulement) : « Racines et factorisation d'un trinôme » (13 exercices), « Loi des grands nombres et simulation » (6).
- La classe reste non publiée (prévisualisation locale uniquement).

## 7. Corrections finales ciblées (2026-10-26, fin de journée)

Les points ouverts du § 6 ont été traités ainsi (§ 6 conservé tel quel pour l'historique) :

- **Calcul numérique et algébrique** : retirée comme notion (décision utilisateur). Chapitre 3 : 4 notions ; classe : 9 chapitres, 29 notions. Rappels conservés dans les méthodes (identités remarquables, produit nul ; ajout du signe de $ax + b$ dans « Signe du trinôme »). Exercices rédigés : 73201 → « Équations du second degré », 73203 → « Racines et factorisation », 73204 → « Signe du trinôme » ; 73202 (développer) et 73205 (fractions) retournent en réserve. Familles générées : `produit_nul`, `factoriser`, `signe_affine` rattachées aux mêmes notions ; `developper` (32 exercices) hors curriculum actif.
- **Exemple Python des suites** : retiré (absent du chapitre 7 du manuel) ; les autres exemples sont inchangés.
- **Chatbot** : « factoriser un trinôme avec le discriminant » est orienté vers « Racines et factorisation » (phrase-clé ajoutée dans « À retenir » de la notion ; moteur inchangé). 14/14 sur le jeu de questions de la classe.
- **Représentation graphique et calculatrice** : ajout du lien « points de la courbe de $f$ » (suites, manuel ch. 7 I c) et des menus calculatrice TI/Casio du manuel pour les coefficients binomiaux et la loi binomiale (ch. 9).
- **Racines et factorisation** : la famille générée « factoriser un trinôme après avoir déterminé ses racines » (25 exercices), jusque-là rattachée à « Équations du second degré », lui est rattachée, avec la famille `factoriser` (32) : 57 exercices générés, sans nouveau générateur. **Loi des grands nombres** : 6 exercices rédigés + mini-quiz ; pas de générateur (une simulation ne se prête pas à une réponse unique vérifiable).
- **Langage mathématique** : 8 indices des suites générées écrivaient `u_n`, `u_{n+1}` hors formule (corrigés dans `exercise_generator_premiere_specifique/suites.py`) ; l'indice de la famille « Espérance » écrivait `Σ x_i × P(X=x_i)` en texte brut (corrigé dans `variables_aleatoires.py`, copie propre à la classe) ; 2 lignes de calcul de cours (`129{,}45 - 11{,}05^2`, `12x^2 - 96x + 144`) étaient affichées en texte brut (corrigé dans `cours_commun.calc`).

## 8. Complément au plancher de 300 exercices par chapitre (2026-10-27)

Préalable à la publication : quatre chapitres étaient sous la règle de `test_exercise_chapter_balance.py` (au moins 300 exercices servis par chapitre) — ch. 2 (250), ch. 4 (291), ch. 7 (299), ch. 9 (208).

- **Méthode (ajout pur)** : `tools/generate_premiere_specifique_exercises.py`, `_COMPLEMENT_PLANCHER`. Les 2 895 exercices générés existants sont reproduits à l'identique ; des tirages supplémentaires des générateurs existants (graines distinctes) sont débarrassés de tout énoncé déjà servi, puis prélevés famille après famille ; identifiants dans la moitié haute du bloc de chaque famille (`+500`), ou `915 000+` pour `suites`. Aucun exercice existant modifié, aucun nouveau générateur.
- **Volume** : +186 exercices (2 895 → 3 081 générés ; total servi 3 490 → 3 676) — ch. 2 : 250 → 310 (Rappels sur les fonctions, racine carrée, cube) ; ch. 4 : 291 → 310 (11 familles) ; ch. 7 : 299 → 310 (11 familles) ; ch. 9 : 208 → 304.
- **Ch. 9, limite des générateurs existants** : quatre familles sont épuisées (`bernoulli`, `coefficients`, `cumul`, `bornes` : tout leur espace d'énoncés est déjà servi). Les ajouts de `proba_binomiale` (35) et `decision` (36) sont plafonnés (`_COMPLEMENT_PLAFONDS`) pour que le patron d'énoncé dominant reste sous 20 % (19,7 %). Pour gagner en diversité, il faudrait de nouvelles familles (calcul de $P(X \leqslant k)$, reconnaissance d'un schéma de Bernoulli en contexte…).
- **Vérifications** : 175 ajouts recalculés indépendamment (vérificateur du projet et vérificateur dédié : sympy, fractions exactes, statistics) et 11 exercices de suites relus un à un : aucune erreur ; `test_pool_servi_identique_aux_tirages` vérifie désormais que chaque ajout est un tirage à l'identique ; rendu KaTeX strict sans erreur ; tests de volume, diversité et patrons textuels réussis avec la classe servie.
- **Statut** : la classe reste non publiée.
