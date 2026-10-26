# Première spécialité mathématiques — suivi du développement

> **Correction du 2026-10-26 — séparation des deux Premières.** La demande portait sur une NOUVELLE classe indépendante. Le chantier avait, par erreur d'interprétation, réécrit la Première existante (`premiere`) au lieu de la laisser intacte (voir §2, stratégie initiale conservée pour l'historique). Correction appliquée (détails en §10) :
> - **`premiere`** (« Première spécialité Mathématiques », publiée) : restaurée à l'octet près dans son état d'avant le chantier — 10 chapitres, 34 notions, 815 exercices rédigés, 4 281 exercices générés, générateurs d'origine.
> - **`premiere_specifique`** (« Première spécifique », **non publiée**, prévisualisation locale uniquement) : nouvelle classe indépendante portant tout le travail du chantier — 13 chapitres, 57 notions, 1 176 exercices rédigés, 5 854 exercices générés.
> - Les sections 2 à 9 ci-dessous décrivent le chantier tel qu'il a été mené : tout ce qu'elles attribuent à « la Première » concerne désormais `premiere_specifique` (fichiers renommés : voir §10).

Référence : programme de spécialité de mathématiques de première générale, arrêté du 26 février 2026, BO n° 14 du 2 avril 2026 (NOR MENE2602917A), applicable à la rentrée 2026. Annexe officielle téléchargée depuis education.gouv.fr ; texte extrait conservé hors du dépôt (scratchpad de la session, `premiere_src/annexe.txt`).

Le manuel « Cours 1ES-L.pdf » n'est pas disponible dans l'environnement : il n'a pas été utilisé.

## 1. Audit de la Première existante (2026-10-25)

| Élément | Constat |
|---|---|
| Registre | `curriculum_registry.py`, id `premiere`, libellé « Première spécialité Mathématiques », **publiée** (`published=True` par défaut) |
| Cours | `webapp/course_content/cours_premiere/chapitre_1..10.json`, 34 notions, schéma v2, générés depuis la banque (`generate_cours_from_bank.py`) puis audités (tests `test_premiere_audit_final_free_coverage.py`, `test_chapitre3_premiere_free_coverage.py`) |
| Titres de chapitres | JSON « Chapitre N » ; titre affiché déduit des notions (`static/js/chapterTitleByNotions.js`) |
| Banque curée | `exercises_bank_premiere.json`, 815 exercices, id 0 à 2280, difficultés 1 à 5 |
| Pool généré | `exercises_generated_premiere.json`, 4 281 exercices, 186 familles, id 900 000 à 1 008 071 ; modules `webapp/exercise_generator/` (11 modules, `tools/generate_derivative_exercises.py`) |
| Figures | 23 notions sur 34 (geom, bars, pipeline, venn, tree) ; `geomSvg.js` sait tracer des courbes échantillonnées (`curves`), mais aucun tableau de signes ou de variations |
| Progression réelle | 8 fichiers `data/user_course_progress` utilisent des identifiants de Première (Chapitre_1..9, notions slugifiées) : **identifiants à conserver** |
| Tests | 559 tests liés à la Première, tous réussis (base de départ) |

Qualité constatée : contenu correct dans l'ensemble mais inégal (exemple : `-7^2` écrit pour `(-7)^2` et solutions non simplifiées dans « Équations du second degré »), cours parfois courts, figures absentes sur 11 notions, plusieurs notions trop pauvres en exercices (Chapitre 4 : 14 exercices curés ; exponentielle, lien avec les suites : 1).

Écarts avec le programme 2026 :
- **absents** : vocabulaire ensembliste et logique ; notion de liste ; automatismes de première ; approximation affine ; dérivabilité de la valeur absolue et de la racine en 0 ; fonctions paires et impaires ; inégalités et position relative de courbes ; méthode de Newton ; projeté orthogonal d'un point sur une droite ; coordonnées par produits scalaires ; répétition de n ⩽ 4 épreuves de Bernoulli ; linéarité de l'espérance, König-Huygens ; expérimentations (échantillons, écart 2σ/√n) ;
- **hors programme 2026** : dérivée de x ↦ g(ax + b) (notion « Composition de fonctions et dérivation » ; seule la dérivée de t ↦ e^{at} reste au programme) ; étude des fonctions cosinus et sinus (parité, périodicité, courbes — notion « Fonctions cosinus et sinus »).

## 2. Stratégie retenue

- **Aucune nouvelle classe** : enrichissement de la Première existante. Identifiants de chapitres `Chapitre_1..10`, de notions et d'exercices conservés.
- Cours réécrits par des modules sources `tools/premiere/cours_chNN.py` (même constructeur que la Quatrième, contrôles par assertions), écrits par `tools/build_premiere_courses.py`. Le contenu juste des cours existants est réutilisé.
- Banque curée : exercices existants audités et conservés (corrigés s'ils sont faux) ; nouveaux exercices dans un bloc réservé `tools/premiere/banque_chNN.py`, avec contrôles recalculés.
- Générateurs : modules existants audités ; nouvelles familles pour les notions absentes ; vérificateur indépendant (SymPy si utile).
- Notions hors programme : remplacées par les notions du programme 2026 ; exercices concernés réaffectés s'ils restent au programme, retirés de la banque servie sinon (sans supprimer de données de progression).
- Niveaux : 1 à 4 pour les nouveaux exercices ; le niveau 5 historique reste servi.
- Publication : la Première **est déjà publiée** ; son statut n'est pas modifié (le passer à `False` masquerait la classe aux élèves). Rien n'est commité ni déployé : la production reste inchangée tant que l'utilisateur n'a rien autorisé.

## 3. Plan des chapitres

| Chapitre | Titre | Notions (id conservé ou nouveau*) |
|---|---|---|
| 1 | Suites numériques, modèles discrets | généralités (modes de génération, notations, motifs) ; sens de variation ; suite arithmétique ; suite géométrique ; calcul de sommes ; notion de limite (intuitive, seuil) |
| 2 | Second degré (**pilote**) | forme factorisée, racines, somme et produit ; forme canonique et variations ; équation du second degré ; signe du trinôme et inéquations* ; choisir la bonne forme, problèmes* |
| 3 | Dérivation | taux de variation, nombre dérivé, tangente ; approximation affine* ; fonctions dérivées usuelles et dérivabilité ; opérations (somme, produit, inverse, quotient) |
| 4 | Variations et courbes | signe de la dérivée et variations ; extremums et optimisation ; fonctions paires et impaires* ; inégalités et position relative de courbes* ; étude complète, méthode de Newton* |
| 5 | Fonction exponentielle | définition (f' = f, f(0) = 1) ; nombre e et notation e^x ; propriétés algébriques ; signe, variations, courbe ; e^{at}, e^{kt}, e^{-kt} ; lien avec les suites géométriques, modélisation |
| 6 | Trigonométrie | cercle trigonométrique, radian, enroulement ; cosinus et sinus d'un réel, valeurs remarquables, angles associés ; lien avec le triangle rectangle* |
| 7 | Produit scalaire | projection et cosinus, orthogonalité ; bilinéarité, coordonnées, normes ; ‖u ± v‖², Al-Kashi ; transformation de MA·MB, ensembles de points |
| 8 | Géométrie repérée | vecteur normal et équation cartésienne ; projeté orthogonal d'un point* ; équation de cercle |
| 9 | Probabilités conditionnelles | probabilité conditionnelle ; arbres pondérés et probabilités totales ; indépendance ; succession d'épreuves indépendantes, Bernoulli (n ⩽ 4)* |
| 10 | Variables aléatoires réelles | variable aléatoire et loi ; espérance, variance, écart type, linéarité, König-Huygens ; expérimentations et échantillons* |
| 11* | Vocabulaire ensembliste et logique | ensembles et notations ; propositions, connecteurs, quantificateurs, négation ; implication, réciproque, contraposée, CN/CS ; types de raisonnement |
| 12* | Algorithmique et programmation : listes | variables, conditions, boucles, fonctions ; générer une liste ; manipuler, parcourir, itérer ; algorithmes du programme |
| 13* | Automatismes | évolutions et taux ; calcul numérique et algébrique ; fonctions et représentations ; statistiques ; probabilités en tableau ou en arbre |

Les automatismes ne forment pas un chapitre d'enseignement dans le programme ; le chapitre 13 sert d'entraînement transversal (rappelé dans son introduction).

## 4. Matrice de conformité

État : À faire / En cours / Rédigé / Validé.

| Domaine | Capacités et contenus exigés | Ch. | Démonstrations | État |
|---|---|---|---|---|
| Suites | modes de génération (explicite, récurrence, algorithme, motif) ; notations ; passage entre registres ; motifs et dénombrement | 1 | — | Validé |
| Suites | arithmétique : définition, terme général, lien affine, 1 + 2 + … + n | 1 | terme général ; 1 + 2 + … + n | Validé |
| Suites | géométrique : définition, terme général, taux constant, 1 + q + … + qⁿ | 1 | terme général ; 1 + q + … + qⁿ | Validé |
| Suites | sens de variation ; modélisation linéaire / exponentielle ; limite intuitive ; seuil | 1 | — | Validé |
| Suites (algo) | termes, sommes, seuil, factorielle, Syracuse, Fibonacci | 1, 12 | — | Validé |
| Second degré | forme factorisée, racines, signe, somme et produit ; polynômes s'annulant en deux réels | 2 | — | Validé (pilote) |
| Second degré | forme canonique (complétion du carré), discriminant, factorisation, résolution, signe | 2 | résolution de l'équation | Validé (pilote) |
| Second degré | stratégies de factorisation ; choix de la forme (équation, inéquation, optimisation, variations) | 2 | — | Validé (pilote) |
| Dérivation | taux de variation, sécante, nombre dérivé, tangente (équation), approximation affine | 3 | équation de la tangente | Validé |
| Dérivation | dérivées de carré, cube, inverse, racine, xⁿ (n ∈ ℤ) ; racine non dérivable en 0 ; valeur absolue en 0 | 3 | dérivées de carré et inverse ; racine non dérivable en 0 | Validé |
| Dérivation | somme, produit, inverse, quotient | 3 | dérivée d'un produit | Validé |
| Dérivation (algo) | liste des pentes de sécantes pour un pas donné | 3 | — | Validé |
| Variations | fonctions paires, impaires ; signe de f' et variations ; fonctions constantes ; extremum et tangente | 4 | f croissante ⇒ f' ≥ 0 ; extremum ⇒ f'(a) = 0 | Validé |
| Variations | étudier les variations, extremums, optimisation, inégalités, position relative, second degré par dérivation | 4 | parabole au-dessus de ses tangentes | Validé |
| Variations (algo) | méthode de Newton | 4 | formule de Newton | Validé |
| Exponentielle | définition f' = f, f(0) = 1 ; exp(x + y), exp(x)exp(−x) = 1 ; e, eˣ ; signe, variations, courbe ; lien suites géométriques | 5 | unicité, relation fonctionnelle, positivité et croissance (approfondissements) | Validé |
| Exponentielle | transformer des expressions ; dérivée de e^{at} ; tracer e^{kt}, e^{−kt} ; modéliser | 5 | — | Validé |
| Exponentielle (algo) | méthode d'Euler ; approximation de e par (1 + 1/n)ⁿ | 5 | — | Validé |
| Trigonométrie | cercle, longueur d'arc, radian, enroulement, image d'un réel ; cos et sin d'un réel ; triangle rectangle ; valeurs remarquables ; angles associés | 6 | cos π/4, sin π/4, cos π/3, sin π/3 | Validé |
| Trigonométrie (algo) | approximation de π (Archimède) | 6 | — | Validé |
| Produit scalaire | projection, cosinus, orthogonalité ; bilinéarité, symétrie ; base orthonormée, norme, coordonnées par produits scalaires ; ‖u ± v‖², Al-Kashi ; MA·MB | 7 | Al-Kashi ; ensemble des M tels que MA·MB = 0 | Validé |
| Géométrie repérée | vecteur normal, équation ax + by + c = 0 ; projeté orthogonal ; équation de cercle, centre et rayon ; configurations | 8 | — | Validé |
| Probabilités | indépendance ; partition, probabilités totales ; deux épreuves indépendantes (arbre, tableau) ; n ⩽ 4 épreuves de Bernoulli | 9 | — | Validé |
| Probabilités (algo) | Monte-Carlo (aire sous la parabole, π) | 9, 12 | — | Validé (Ch. 9 ; reprise en Python au Ch. 12) |
| Variables aléatoires | définition, loi, notations {X = a}, P(X ⩽ a) ; espérance, variance, écart type ; linéarité ; König-Huygens ; jeu équitable | 10 | König-Huygens ; espérance de la moyenne d'échantillon | Validé |
| Expérimentations | simuler une variable aléatoire ; moyenne d'échantillon en Python ; N échantillons, proportion des écarts ⩽ 2σ/√n | 10 | — | Validé |
| Logique, ensembles | élément, sous-ensemble, ∅, ∈, ⊂, ∩, ∪, complémentaire, Card, couple, produit cartésien, intervalles | 11 | — | Validé |
| Logique | et / ou ; contre-exemple ; implication, équivalence, réciproque, contraposée ; CN / CS ; statut des égalités et des lettres ; quantificateurs, négation ; disjonction des cas, absurde, contraposée | 11 | — | Validé |
| Listes | générer (extension, ajouts, compréhension) ; manipuler éléments et indices ; parcourir ; itérer ; programmation modulaire | 12 | — | Validé |
| Automatismes | évolutions (valeur finale ou initiale, taux, évolutions successives, taux réciproque) | 13 | — | Validé |
| Automatismes | produit nul ; signe du premier degré et d'une forme factorisée ; développer, factoriser, réduire | 13 | — | Validé |
| Automatismes | résolution graphique ; signe et variations lus ; droites (tracé, lecture, coefficient directeur) | 13 | — | Validé |
| Automatismes | lecture de graphiques statistiques ; indicateurs ; probabilités conditionnelles en tableau croisé ou en arbre ; P(A ∩ B), P_A(B), P_B(A) | 13 | — | Validé |

## 5. Serveur local

- 5050 occupé par l'ancien `python webapp/server.py` de l'utilisateur (PID 6772, lancé le 22/10, code antérieur au lanceur unique) ; Vite PID 24808 sur 5173. Ni l'un ni l'autre n'est arrêté par l'agent.
- La lecture des cours exige un compte connecté : vérifier l'affichage sur ce serveur imposerait de créer un compte dans les données réelles. Vérifications faites par le client de test Flask (sans port), puis sur 5050 avec `python tools/run_preview.py --donnees-test …` dès que l'utilisateur aura arrêté le PID 6772.

## 6. Architecture mise en place (pilote)

- `tools/premiere/` : `cours_commun.py` (constructeur de la Quatrième + courbes échantillonnées, tableaux de signes et de variations CONTRÔLÉS numériquement), `banque_commun.py` (contrôles, identifiants historiques, écriture LaTeX propre), `chapitres.py` (chapitres repris), `cours_chNN.py`, `banque_chNN.py`.
- `tools/build_premiere_courses.py` (refuse de supprimer un identifiant de notion existant) et `tools/build_premiere_bank.py` (remplacement en place, refuse de perdre un identifiant d'exercice).
- Nouveaux identifiants d'exercices curés : 60 000 + 1 000 × chapitre + 100 × rang de la notion + k.
- Générateurs : modules du programme 2026 ajoutés en fin de pool (`_PROGRAMME_2026_MODULES` de `tools/generate_derivative_exercises.py`), bloc ≥ 1 100 000, identifiants stables par famille (offset + 1 000 × rang + k).
- Figure `kind: "tableau"` (geomSvg.js, cours.css, tests Vitest) ; courbes `variant`, `reveal`, `tooltip`.
- Tests : `webapp/tests/test_premiere_programme_2026.py` (JSON = sources, contrôles de banque, quiz, générateurs déterministes, vérificateurs indépendants SymPy qui relisent énoncé et réponse — 30 falsifications sur 30 détectées).
- Navigateur sans port : script `premiere_src/navigateur_sans_port.py` (scratchpad) — Playwright sert les pages par le client de test Flask, données isolées, aucun port ouvert.

## 7. Journal

- 2026-10-25 : phase 1 (programme, audit, plan, matrice).
- 2026-10-25 : **chapitre 2 (pilote) terminé**.
  - Cours : 5 notions (3 historiques réécrites, identifiants et titres conservés ; 2 ajoutées : « Signe du trinôme et inéquations du second degré », « Second degré : modéliser et optimiser »), 30 exemples (2 Free, 3 Premium, 1 Ultra par notion), 4 démonstrations Ultra (variations de la forme canonique, résolution de l'équation [exigée], somme et produit, règle du signe), 5 figures (paraboles, trois signes de Δ, tableau de signes, tableau de variations), tableau de synthèse des formes.
  - Banque : 208 exercices (149 historiques réécrits sans écritures fautives, niveaux réattribués 1 à 4 selon le raisonnement ; 59 nouveaux), mini-quiz 3 par notion.
  - Générateurs : `second_degre.py` corrigé (écritures `-5^2`, `0/0`, `x-(-6)`, `-2\times-12`) sans changer aucun tirage ; nouveau `second_degre_formes.py` (18 familles, 4 notions, 206 exercices servis, exercices sur mesure Ultra).
  - Tests : base Première 756 réussis ; nouveaux tests 8 (1 088 sous-tests) ; Vitest geomSvg 15 ; KaTeX 0 erreur ; parcours Chromium sans port 26/26 (Free/Premium/Ultra, sombre ordinateur et mobile).
  - Chatbot : détection 8/12 questions types ; 2 tests de routage (`test_resolve_rag_coherence`, `test_routage_mathematique_robuste`) repassés en renforçant le vocabulaire indexé (marges faibles : 0,123 pour un seuil de 0,12).

- 2026-10-25 : **chapitre 1 (suites) terminé**.
  - Cours : 6 notions (identifiants et titres conservés), 36 exemples, 4 démonstrations Ultra (variations d'une suite explicite ; termes généraux arithmétique et géométrique [exigées] ; 1 + 2 + … + n et 1 + q + … + qⁿ [exigées]), 6 figures (motif d'allumettes, points d'une suite, alignement arithmétique, deux suites géométriques, escalier de Gauss, convergence vers un point fixe), algorithmes Python (Fibonacci, Syracuse, seuil, sommes, liste de termes).
  - Banque : 108 exercices (65 historiques réécrits : français corrigé, réponses complètes, rang précis du sens de variation, tableaux de limites recalculés à partir de vraies suites ; 43 nouveaux : motifs, dénombrement, Python, Hanoï, suite auxiliaire, intérêts simples/composés, seuils, nombre e).
  - Générateur `suites.py` : écritures corrigées (`-2 \times -4`, `10 \cdot 2^{-n}`, `5858.3`) et familles de limites ramenées au programme 2026 (conjecture numérique ; suppression des « formes indéterminées » et calculs formels de limite, notions de Terminale) — 73 exercices réécrits, mêmes identifiants.
  - Code Python dans les textes : aide `code()` (balise `<code>`, caractères `*`, `/`, `^`, `<`, `>` encodés, sinon réécrits par `mathrender.js::prettify`).
  - Rendu partagé : `geomSvg.js` applique désormais `reveal` aux points (cercle et étiquette) ; 5 points de figures de Seconde et Troisième qui déclaraient `reveal` apparaissent maintenant à l'étape prévue.
  - Tests : ciblés 84 + 36 réussis ; KaTeX 0 erreur ; Chromium sans port 31/31 ; détection chatbot 10/12.

- 2026-10-26 : **chapitre 3 (dérivation) terminé**.
  - Cours : 4 notions — « Nombre dérivé. Tangente », « Approximation affine et dérivabilité » (nouvelle), « Fonction dérivée », « Opérations et dérivation » ; démonstration Ultra dans chaque notion (équation de la tangente, √ non dérivable en 0, dérivées de x² et 1/x, dérivée d'un produit — toutes exigées) ; 4 figures (sécantes → tangente, approximation affine de √x, f et f', règle de l'inverse) ; tableau des règles (4 lignes).
  - **Notion retirée** : « Composition de fonctions et dérivation » (dérivée de g(ax + b), hors programme 2026). Retrait déclaré (`NOTIONS_RETIREES` dans `cours_ch03.py`) ; ses 20 exercices curés réécrits avec le programme (produit, développement, inverse ; √(ax + b) → (ax + b)√x) et rattachés à « Opérations et dérivation » ; ses 96 exercices générés ne sont plus servis (filtre réversible `exercise_generator.registry.NOTIONS_HORS_PROGRAMME`, aucun usage dans les données locales). Test `test_chapitre3_premiere_free_coverage` adapté : l'ancien test de la notion retirée remplacé par des garanties sur la nouvelle notion, sur l'exemple Free de la règle de l'inverse et sur l'absence de la notion retirée.
  - Banque : 204 exercices (171 historiques réécrits par une famille générique avec correction règle par règle et recalcul SymPy ; 33 nouveaux).
  - Générateurs : nouveau `derivation_2026.py` (10 familles, 119 exercices : tangentes, vitesse, approximation affine, coût marginal, puissances négatives, inverse, produit avec √x) pour respecter le plancher historique du chapitre (624 ≥ 567) ; `tangente.py` corrigé (citations d'élève `+ -16`, `bx\ + 0`) ; analyseur LaTeX partagé `exercise_generator/_tex.py`.
  - Contrôle ajouté : `cours_commun.calc` refuse une commande LaTeX hors formule (deux étapes du chapitre 3 s'affichaient en LaTeX brut).
  - Tests : ciblés 51 + 47 réussis ; KaTeX 0 erreur ; Chromium sans port 21/21 ; détection chatbot 8/10 (« dérivée d'un produit / d'un quotient » → « Fonction dérivée », effet du titre historique « Opérations et dérivation »).

- 2026-10-26 : **chapitre 4 (variations et courbes) terminé**.
  - Cours : 5 notions — « Variations d'une fonction » et « Nombre dérivé et extremums locaux » (historiques, identifiants et titres conservés), « Fonctions paires et impaires », « Inégalités et position relative de courbes », « Étude d'une fonction et méthode de Newton » (nouvelles) ; 30 exemples (exemple-838 « f'(a) = 0 sans extremum » gardé en Free) ; démonstration Ultra par notion (f croissante ⇒ f' ≥ 0, extremum ⇒ f'(a) = 0, symétrie d'une fonction paire, parabole au-dessus de ses tangentes, formule de Newton) ; 5 figures (tableau de variations de x³ − 3x contrôlé numériquement, extremums et contre-exemple x³, paire/impaire, √x sous sa tangente, Newton pour √2) ; Newton en Python.
  - Banque : 46 exercices (14 historiques réécrits, 32 nouveaux ; était 14), mini-quiz 3 par notion.
  - Générateur `variations.py` : audit des écritures, 442 exercices, 0 signalement (aucune correction nécessaire).
  - Tests : ciblés 71 puis 84 réussis ; KaTeX 0 erreur ; Chromium sans port 26/26 ; détection chatbot 7/7 après renforcement du vocabulaire indexé (« étudier les variations avec la dérivée », « démontrer une inégalité avec une fonction ») ; routage des chapitres 1 à 3 inchangé. `test_non_regression` : 39 notions (36 + 3 nouvelles).

- 2026-10-26 : **chapitre 5 (fonction exponentielle) terminé**.
  - Cours : 7 notions — les 6 historiques (identifiants et titres conservés, utilisés par le générateur et l'historique des élèves) + « Croissance et décroissance exponentielles » (nouvelle : dérivée de e^{at}, e^{kt} et e^{-kt}, modélisation) ; 42 exemples (exemple-980, exemple-1133, exemple-1216 gardés en Free) ; démonstration Ultra par notion (unicité, relation fonctionnelle, exp(n) = eⁿ, positivité et croissance, e^x ≥ x + 1, dérivée de e^{at} par le taux de variation, suite Ce^{kn} géométrique) ; 7 figures (méthode d'Euler, relation fonctionnelle, (1 + 1/n)ⁿ → e, tableau de signes/variations de (x − 1)eˣ, courbe et tangentes, famille e^{kt}, suite géométrique sur la courbe). Aucune limite (Terminale) : comportements conjecturés sur des valeurs.
  - Banque : 84 exercices (41 historiques réécrits : doublons stricts différenciés, niveaux 5 ramenés à 4, écritures « -1\exp », « 1 × e^{1n} », « x +0 » corrigées, 2 exercices de limites remplacés par des inéquations ; 43 nouveaux : Euler et Python, (1 + 1/n)ⁿ, unicité, modèles radioactivité/capital/refroidissement, seuils, suites).
  - Générateur `exponentielle.py` : mêmes tirages et mêmes identifiants (324/324 vérifiés, 4 510 identifiants du fichier généré inchangés, 41 énoncés du chapitre 5 réécrits) ; familles hors programme réécrites : limites → conjectures numériques et variations de e^{ax} ; asymptote → conjecture ; e^{u(x)} du second degré → dérivée du produit (ax + b)eˣ ; e^{ax + b} justifiée par e^b·e^{ax} ; écritures `4	imes -2`, `e^{-1n}`, `1 	imes e` corrigées.
  - Rendu partagé : `geomSvg.js::toKatexSource` écrit la virgule décimale `{,}` (KaTeX affichait « 2, 5 ») — corrige aussi les libellés décimaux des figures déjà publiées (Première, Quatrième) ; test Vitest ajouté ; deux échappements fautifs (`"-\infty"`) d'un test précédent corrigés.
  - Tests : ciblés 238 + 163 réussis ; Vitest geomSvg 19 ; KaTeX 0 erreur ; Chromium sans port 36/36 ; détection chatbot 7/12 (voir anomalies).

- 2026-10-26 : **chapitre 6 (trigonométrie) terminé**.
  - **Notion retirée** : « Fonctions cosinus et sinus » (parité, périodicité, courbes : hors programme 2026 de Première). Retrait déclaré (`NOTIONS_RETIREES` dans `cours_ch06.py`) ; ses 34 exercices curés rattachés à la nouvelle notion « Angles associés et lecture du cercle », justifications « fonction paire / impaire / périodique / décroissante » réécrites par les symétries du cercle et les tours complets ; entrée ajoutée à `registry.NOTIONS_HORS_PROGRAMME`.
  - Cours : 3 notions — « Repérage sur le cercle trigonométrique » et « Coordonnées d'un point du cercle trigonométrique » (historiques, identifiants et titres conservés), « Angles associés et lecture du cercle » (nouvelle) ; 18 exemples ; démonstrations Ultra (longueur d'arc L = rθ ; cos et sin de π/4 et π/3 [exigée] ; angles associés par symétries) ; 3 figures (enroulement, coordonnées et triangle OHM, symétries −x, π − x, π + x) ; méthode d'Archimède (exemple et exercices Python).
  - Banque : 162 exercices (136 historiques repris depuis `banque_ch06_historiques.py`, niveaux 5 ramenés à 4 ; 26 nouveaux : longueur d'arc, radian, image d'un réel, Archimède, démonstrations π/4 et π/3, cos² + sin² = 1, triangle rectangle, angles associés, équations par lecture du cercle). **Contrôle SymPy** de chaque égalité « cos(…) = … » / « sin(…) = … » (249) et de chaque ensemble de solutions d'équation (13) ; vérificateurs testés sur des erreurs volontaires. Analyseur `_tex` étendu à `\pi`, `\cos`, `\sin`.
  - Générateur `trigonometrie.py` : mêmes tirages et identifiants (4 510 identiques, familles identiques, autres chapitres inchangés) ; familles rattachées aux notions au programme (Coordonnées : 528, Angles associés : 63, Repérage : 16) ; `formule_duplication` (hors programme) réécrite en « angle double lu sur le cercle » ; écritures `× -` (220) et `-1\cos` corrigées ; solutions π − π/6 simplifiées.
  - Tests : ciblés 301 + 12 réussis (nouveau test : toute notion servie existe dans le cours des chapitres repris ; aucune duplication, « fonction paire » ni `× -` dans le pool trigonométrique) ; Vitest 955 ; KaTeX 0 erreur ; Chromium sans port 16/16 ; détection chatbot 8/10.
  - `chapterTitleByNotions.js` (titre de secours) : 8 nouvelles notions des chapitres 2 à 6 ajoutées.

- 2026-10-26 : **chapitre 7 (produit scalaire) terminé**.
  - Cours : 4 notions — les 3 historiques (identifiants et titres conservés) + « Formule d'Al-Kashi et calculs dans le triangle » (nouvelle) ; 24 exemples ; démonstrations Ultra (expression en coordonnées, développement de ‖u ± v‖², Al-Kashi [exigée], ensemble MA·MB = 0 [exigée]) ; 4 figures (projection orthogonale, parallélogramme u ± v, triangle d'Al-Kashi, cercle de diamètre [AB]) ; approfondissements : loi des sinus, concourance des hauteurs (relation d'Euler).
  - Banque : 97 exercices (75 historiques, toutes réponses recalculées et justes ; 8 gabarits paramétrés reconstruits depuis leurs paramètres — énoncé inchangé, réponse et correction recalculées par SymPy ; écritures « (45/2)√3 », « √(81/4) », « 5x +1y +10 », « −1×−6 », « 3(x−(2))+−1(y−q) » corrigées ; 1 niveau 5 ramené à 4 ; 22 nouveaux : projection, carré, triangle équilatéral, losange, bilinéarité, polarisation, coordonnées par produits scalaires, Al-Kashi, loi des sinus, MA·MB = k, hauteurs).
  - Générateur `produit_scalaire.py` : mêmes tirages, identifiants et énoncés (vérifié) ; écritures des produits et carrés de négatifs corrigées (`-8^2`, `× -`, `+ -`, `-1m`).
  - Tests : ciblés 278 + 138 + 90 réussis ; KaTeX 0 erreur ; Chromium sans port 21/21 ; détection chatbot 5/8. Le test historique `test_titre_definitions_ne_declenche_plus_lintent_a_tort` a été maintenu vert en allégeant le LaTeX des champs indexés de « Autres définitions et propriétés » (identités déplacées dans les formules).

- 2026-10-26 : **chapitre 8 (géométrie repérée) terminé**.
  - Cours : 4 notions — « Vecteur normal à une droite » et « Équation d'un cercle » (historiques, identifiants et titres conservés ; exemple-1664 « membre négatif » gardé en Free) + « Projeté orthogonal d'un point sur une droite » et « Configurations dans un repère » (nouvelles) ; 24 exemples ; démonstrations Ultra (droite par point et vecteur normal, projeté et distance d'un point à une droite, équation du cercle, médiatrice de vecteur normal AB) ; 4 figures ; approfondissements : parabole lieu des points équidistants, intersections avec une droite parallèle à un axe.
  - Banque : 76 exercices (56 historiques, réponses toutes recalculées et justes ; écritures « 3x -1y +7 », « +0y », « (x-(3)) », « (3-(0)) », « √9 », « - 1(y + 3) » nettoyées ; 1 niveau 5 ramené à 4 ; 20 nouveaux, vérifiés par SymPy : perpendiculaires, projetés, distance, aire, tangente à un cercle, cercle circonscrit, parabole). Quatre brouillons erronés repérés à la relecture (68203, 68204, 68206, 68406) corrigés avant intégration.
  - Générateur `geometrie_reperee.py` : mêmes tirages et identifiants ; **anomalie corrigée** : les 64 exercices rangés sous « Étude d'un ensemble de points » (notion du Ch. 7) sont rattachés à « Équation d'un cercle » (AM = r) et « Configurations dans un repère » (médiatrice) ; bug d'énoncé corrigé (constante ±1 affichée « + » sans chiffre, 18 énoncés) ; écritures `-1x`, `- -6`, `× -` corrigées (117 signalements → 0).
  - Tests : ciblés 279 réussis (le test de cohérence notions/cours couvre désormais le Ch. 8) ; KaTeX 0 erreur ; Chromium sans port 21/21 ; détection chatbot 7/8.

- 2026-10-26 : **chapitre 9 (probabilités conditionnelles et indépendance) terminé**.
  - Cours : 4 notions — les 3 historiques (identifiants et titres conservés ; la définition de la probabilité conditionnelle relève des automatismes en 2026 et reste rappelée) + « Épreuves indépendantes et épreuves de Bernoulli » (nouvelle : deux épreuves indépendantes par arbre ou tableau, n ⩽ 4 épreuves de Bernoulli, Monte-Carlo, marche aléatoire) ; 24 exemples ; démonstrations Ultra (P_A(B) + P_A(B̄) = 1, probabilités totales, indépendance ⇔ P_A(B) = P(B), probabilité d'un chemin de Bernoulli) ; 4 figures (événements A et B, arbre pondéré, arbre d'indépendance, arbre de 3 épreuves de Bernoulli).
  - Banque : 79 exercices (63 historiques, réponses recalculées ; **2 erreurs de fond corrigées** : 2004 « 2/13 = une personne sur 13 » → environ 1 sur 6,5 ; 2005 valeur 4/23 attribuée à un exercice qui donnait 40/59 → énoncé rendu autonome ; 2016 « 15/23 ≈ 0,529 » → 0,652 ; « 5.8 % » ; virgules décimales ; 5 niveaux 5 ramenés à 4 ; 16 nouveaux vérifiés en fractions exactes).
  - Générateur `probabilites_conditionnelles.py` : audité, 0 écriture fautive, notions conformes — inchangé.
  - Tests : ciblés 279 + 12 réussis ; KaTeX 0 erreur ; Chromium sans port 21/21 ; détection chatbot 7/7. Libellés d'arbres en `\overline{…}` (le caractère combinant « B̄ » perdait sa barre au rendu).
  - Rendu : le serveur sert `static-dist/` (bundle Vite) en priorité ; la correction de la virgule décimale de `geomSvg.js` (Ch. 5) n'y sera visible qu'après `npm run build` (phase finale).

- 2026-10-26 : **chapitre 10 (variables aléatoires) terminé**.
  - Cours : 3 notions — les 2 historiques (identifiants et titres conservés) + « Simulation et échantillonnage » (nouvelle, section « Expérimentations » : moyenne d'échantillon, fluctuation, proportion des écarts ⩽ 2σ/√n, algorithmes d'espérance, de variance et de fréquence des lettres) ; 18 exemples ; démonstrations Ultra (somme des probabilités d'une loi, König-Huygens, espérance de la moyenne d'échantillon) ; 3 figures (diagramme en bâtons, espérance point d'équilibre, moyenne cumulée de 200 lancers simulés de façon reproductible).
  - Banque : 59 exercices (45 historiques, réponses toutes recalculées et justes ; écritures « -1^2 », « 2X -3 », « 3X +0 », « 1X +4 », « × - », « \% » hors formule, « 2.20 euros », « 50.0 euros », σ = √(204/25) → 2√51/5 corrigées ; 3 niveaux 5 ramenés à 4 ; 14 nouveaux, dont approfondissement x ↦ E((X − x)²) et simulation des 2σ/√n).
  - Générateur `variables_aleatoires.py` : mêmes tirages, identifiants, énoncés et réponses (vérifié) ; **erreur de lecture corrigée** « −2² × 7 = 28 » (−2² vaut −4) → « (−2)² × 7 » ; produits de négatifs et « + - » corrigés (114 signalements → « + 0 × … » légitimes seulement).
  - Tests : ciblés 279 + 12 réussis ; KaTeX 0 erreur ; Chromium sans port 16/16 ; détection chatbot 6/7 (« fréquence des lettres » → « Calcul de sommes »).

- 2026-10-26 : **chapitre 11 (vocabulaire ensembliste et logique) créé**.
  - Cours : 4 notions — « Ensembles et notations », « Propositions, connecteurs et quantificateurs », « Implication, réciproque et contraposée », « Types de raisonnement » ; 24 exemples ; démonstrations Ultra ; 4 figures.
  - Banque : 20 exercices (bloc 71 000), vérifiés par calcul sur ensembles.
  - Générateur `logique_ensembles.py` : 14 familles × 32 = 448 exercices (bloc 1 160 000), déterministe.
  - Corrections après relecture : étape « n² + 6n + 0 » de la famille « contre-exemple » réécrite (20 exercices, identifiants inchangés) ; titre de la démonstration Ultra commençant par du texte ; vocabulaire « intersection, réunion, intervalles, contre-exemple » ajouté aux champs indexés.
  - Tests : ciblés réussis ; KaTeX 0 erreur ; Chromium sans port 21/21 ; écritures 0 signalement ; détection chatbot 6/7 (« intersection et réunion d'intervalles » → Ch. 4).

- 2026-10-26 : **chapitre 12 (algorithmique et programmation : listes) créé**.
  - Cours : 4 notions — « Variables, instructions conditionnelles et boucles », « Fonctions et programmation modulaire », « Générer une liste », « Manipuler et parcourir une liste » ; 24 exemples ; démonstrations Ultra (invariants de boucle : somme 1 + … + n, maximum ; correction de est_premier ; longueur d'une liste en compréhension) ; 4 figures (tableau de suivi, schéma de fonction, ajouts successifs, indices positifs et négatifs).
  - Banque : 16 exercices (bloc 72 000) ; chaque programme cité est exécuté au chargement et la sortie annoncée contrôlée.
  - Générateur `listes_python.py` : 14 familles × 32 = 448 exercices (bloc 1 140 000) ; chaque programme affiché est exécuté au tirage (sortie annoncée = sortie réelle) ; écriture « + 0 » corrigée (3 exercices, identifiants inchangés).
  - Tests : ciblés 60 réussis ; KaTeX 0 erreur ; Chromium sans port 21/21 ; détection chatbot 7/8 (« ajouter un élément avec append » → « Manipuler et parcourir une liste », notion voisine légitime).

- 2026-10-26 : **chapitre 13 (automatismes) créé**.
  - Les automatismes ne sont pas un chapitre d'enseignement : espace d'entraînement transversal (questions flash, épreuve anticipée) qui renvoie aux chapitres concernés.
  - Cours : 4 notions — « Évolutions et taux », « Calcul numérique et algébrique », « Fonctions et représentations », « Statistiques et probabilités » ; 24 exemples ; démonstrations Ultra (taux global t₁ + t₂ + t₁t₂, produit nul, coefficient directeur, linéarité de la moyenne) ; 4 figures (évolutions successives, tableau de signes contrôlé, droite par deux points, série statistique).
  - Banque : 17 exercices (bloc 73 000), valeurs recalculées en fractions exactes.
  - Générateur `automatismes.py` : 14 familles × 32 = 448 exercices (bloc 1 180 000) ; étapes de « Développer » réécrites (« 1x × - 2x » → « x × (−2x) », identifiants inchangés).
  - Tests : nouveau `test_premiere_generateurs_chapitres_11_13.py` (déterminisme, blocs d'identifiants, exécution des programmes, génération à la demande) ; compte de notions 57 ; KaTeX 0 erreur ; Chromium sans port 21/21 ; détection chatbot 6/8 (« équation produit nul », « équation réduite d'une droite » → « Équation d'un cercle » : bonus de titre sur « équation »).
  - `chapterTitleByNotions.js` : titres de secours pour toutes les nouvelles notions des Ch. 7 à 13.

## 8. Anomalies et points ouverts

- Publication : la Première est déjà publiée ; tout le travail reste local (aucun commit). Statut non modifié.
- Serveur 5050 : ancien serveur de l'utilisateur (PID 6772) ; validation sur 5050 à faire après son arrêt.
- Chatbot : « somme et produit des racines » → « Calcul de sommes » (Ch. 1), « forme canonique » → « Équation d'un cercle » (Ch. 8), « position relative parabole/droite » → « Vecteur normal à une droite », « tableau de variations d'un trinôme » → Ch. 4 : effet du reclassement par titre ; à revoir quand ces chapitres seront repris.
- ~~Pool généré : `-5^2` (Ch. 7), `-2^2` (Ch. 10)~~ — corrigés.
- Chatbot, chapitre 5 : « méthode d'Euler » → Newton (Ch. 4), « signe de l'exponentielle » / « inéquation » → Ch. 2 ou notion voisine, « dériver exp(3x) » → « Propriétés algébriques », « résoudre e^(x+1) = e^3 » sans notion : le reclassement par titre (poids 0,4) favorise les titres contenant « méthode », « signe », « équations » ; les titres historiques du Ch. 5 ne sont pas modifiés. Piste : prendre en compte les `synonymes` dans le reclassement (changement moteur, à valider sur toutes les classes).
- ~~Chapitre 8 : 64 exercices générés rangés sous une notion du Ch. 7~~ — corrigé (voir journal du Ch. 8).
- Chatbot, chapitre 6 : « valeur de cos(π/3) » → « Angles associés » (même chapitre) ; « cos² + sin² = 1 » seul : aucun mot indexable.
- Chatbot, chapitre 7 : « vecteurs orthogonaux », « norme d'une somme » → « Vecteur normal à une droite » (Ch. 8), « bilinéarité » → notion voisine : reclassement par titre (mots « vecteur », « produit scalaire »).
- Chatbot, chapitres 11 et 13 : « intersection et réunion d'intervalles » → Ch. 4 ; « équation produit nul », « équation réduite d'une droite » → « Équation d'un cercle » (même cause : reclassement par titre).
- Équilibre entre chapitres (ratio ≤ 1,8) : le pool du Ch. 2 est limité à 12 par famille ; à augmenter quand les autres chapitres auront grandi.

- 2026-10-26 : **phases 4-5 (contrôles finaux)**.
  - pytest complet : 2881 réussis, 140 ignorés, 2 échecs (`test_escalade_pedagogique`, Seconde) déjà présents dans la référence du 2026-10-24, avant le chantier : pas une régression. Test « 37 chapitres » de `test_course_content_service.py` actualisé à 40 (3 nouveaux chapitres ; toutes les pages répondent 200 pour Free, Premium et Ultra).
  - Vitest : 955/955 (un premier passage avait signalé 1 échec non reproduit : test instable).
  - ruff, ESLint, Prettier : aucun problème sur les fichiers modifiés.
  - `npm run build` : `webapp/static-dist/` régénéré (ignoré par git) ; virgule décimale des figures présente dans le bundle ; Chromium sans port Ch. 5 36/36, Ch. 13 21/21.

## 9. Prochaine étape (avant la correction du 2026-10-26, voir §10)

Chapitres 1 à 13 intégrés et testés. Reste à l'utilisateur : arrêter l'ancien serveur (PID 6772) et Vite (PID 24808), relancer le serveur sur 5050 pour la validation visuelle ; décider du statut de publication (la Première est déjà publiée) ; autoriser ou non un commit.

## 10. Correction du 2026-10-26 : séparation `premiere` / `premiere_specifique`

**Constat.** La demande était une nouvelle classe indépendante ; le chantier avait modifié la Première existante (10 cours réécrits, 3 chapitres ajoutés, banque et pool généré modifiés, 9 générateurs partagés modifiés, 2 notions retirées).

**Sauvegardes** (hors Git et hors dossiers temporaires) : `%USERPROFILE%\Mathadap_sauvegardes\2026-10-26_separation_premieres\` — voir son `LISEZMOI.md`.
- A : arbre de travail du 25/10 à 13 h 51, avant la première écriture du chantier (25/10 17 h 37). Cours, banque et pool de Première recoupés avec les instantanés pris avant chaque réécriture. Réserve : juste après la copie, une expérience de diagnostic y a remis les cours de **Seconde** dans leur version Git — A n'est donc pas une référence pour la Seconde (qui n'a pas été touchée par la séparation).
- B : état complet du projet avant la séparation (`.git` et `data/` compris), patch de toutes les modifications non commitées, état Git.
- Inventaires SHA-256 vérifiés : 0 écart (A : 944 fichiers ; B : 19 327 fichiers).

**Première spécifique (`premiere_specifique`, non publiée)**
- Registre : `curriculum_registry.py` (« Première spécifique », `published=False`, prévisualisation `NOVAMATH_PREVIEW_CURRICULA=premiere_specifique`).
- Contenus : `webapp/course_content/cours_premiere_specifique/` (13 chapitres, 57 notions), `exercises_bank_premiere_specifique.json` (1 176), `exercises_generated_premiere_specifique.json` (5 854) ; pas de banque « langage naturel » (celle de la Première historique décrit les anciens énoncés).
- Générateurs : package indépendant `webapp/exercise_generator_premiere_specifique/` (16 modules + `_tex`), enregistré dans `exercise_generator/registry.py` sous `premiere_specifique` ; notions hors programme 2026 filtrées pour cette classe seulement.
- Sources et outils : `tools/premiere_specifique/` (ex-`tools/premiere/`), `tools/build_premiere_specifique_courses.py`, `tools/build_premiere_specifique_bank.py`, `tools/generate_premiere_specifique_exercises.py`. Reconstruction complète par ces outils : cours, banque et pool **identiques à l'octet** aux fichiers servis pendant le chantier.
- Identifiants (exercices, notions, chapitres) conservés : aucun conflit, chaque banque, chaque historique (`class_level` dans chaque entrée) et chaque progression de cours (rangée par classe) étant résolus par classe ; vérifié en HTTP (le même identifiant 1185 renvoie deux exercices différents selon la classe).
- Interface : suggestions du chatbot et conversation de démonstration de l'accueil pour la nouvelle classe.
- Tests transposés : `test_premiere_specifique_programme_2026.py`, `test_premiere_specifique_generateurs_chapitres_11_13.py` (avec un test « génération refusée hors prévisualisation »), `test_premiere_specifique_chapitre3_free_coverage.py` ; aide commune `tests/premiere_specifique_preview.py` (même procédé que la Quatrième).

**Première historique (`premiere`, publiée, statut inchangé)** — restaurée depuis A :
- 10 cours, banque (815), banque « langage naturel », pool généré (4 281) et les 13 fichiers de `exercise_generator/` hors registre : **identiques à l'octet** à A. Les 6 modules nouveaux ont quitté ce package (présents dans celui de la nouvelle classe).
- `tools/generate_derivative_exercises.py` remis dans sa version du commit (toutes ses modifications venaient du chantier) : il régénère **exactement** le pool d'origine.
- `exercise_generator/registry.py` : version A + uniquement les ajouts de la nouvelle classe (aucun filtre sur `premiere`).
- Notions `composition-de-fonctions-et-derivation` et `fonctions-cosinus-et-sinus` rétablies.
- Tests remis dans leur version d'avant le chantier : `test_non_regression.py` (34 notions), `test_course_content_service.py` (37 chapitres publiés), `test_chapitre3_premiere_free_coverage.py`. Seul `test_curriculum_publication.py` est complété (deux classes non publiées : Quatrième et Première spécifique).

**Conservé (partagé, additif, sans effet sur l'ancienne Première)** : rendu des tableaux de signes/variations, variantes de courbes et virgule décimale dans `geomSvg.js` / `cours.css` ; titres de secours dans `chapterTitleByNotions.js`. Modifications d'autres chantiers (audit Quatrième du chatbot, cours de Seconde, Quatrième) : non touchées.

**Progression réelle (lecture seule, aucune donnée modifiée)** : 8 élèves ont une progression de cours en Première — 34 entrées sur 35 retrouvent leur notion (dont l'élève qui était sur une notion retirée par le chantier) ; l'entrée orpheline (`n1`, Chapitre_1) n'existe dans aucune version du cours (antérieure au chantier). 80 réponses d'exercices de Première : toutes retrouvent leur exercice. Aucune entrée sous `premiere_specifique`.

**Tests** : pytest complet 2 893 réussis, 2 échecs `test_escalade_pedagogique` (Seconde) présents dans la référence du 24/10, avant le chantier ; Vitest 955/955 ; ruff, ESLint, Prettier sans nouveau signalement. Serveur unique 127.0.0.1:5050 (données de test, prévisualisation `quatrieme,premiere_specifique`) : 5 classes servies ; Chromium : 10 chapitres de `premiere` et 13 de `premiere_specifique` (cours + exercices), un chapitre de chaque autre classe, aucune erreur console ni HTTP.

**Anomalies restantes**
- Première historique, chapitre 3, figure de « Nombre dérivé. Tangente » : l'étiquette `$x_0$` provoque une erreur KaTeX — défaut d'origine (contenu identique à A, traitement des `$` inchangé), non corrigé pour respecter la restauration à l'identique.
- Badge compact de la barre latérale : les deux intitulés y sont tronqués en « Première spéci… » (les cartes du sélecteur, elles, sont complètes et distinctes).
- Polices `/fonts/*.woff2` en 404 sur le serveur local (sans lien avec la séparation).
