# Quatrième — suivi du chantier

Classe **non publiée** (`published=False`). Prévisualisation : `python tools/run_preview.py`
(ou `--donnees-test` pour des comptes d'essai isolés).

Statuts : À faire · En cours · Contenu terminé · Tests en cours · Validé.
Un chapitre n'est « Validé » qu'après le parcours réel dans Chromium (cours, figures, mini-quiz, série d'exercices).

## 1. Audit préalable (2026-10-24)

**Référence applicable en 2026-2027 :** programme du cycle 4 (BO n° 31 du 30 juillet 2020) et attendus de fin de 4e (Eduscol, note de service n° 2019-072).

Le programme publié au BO du 5 mars 2026 ne s'applique à la 4e qu'à la rentrée 2027.

**Points tranchés par le texte officiel** (document Eduscol « Attendus de fin d'année de 4e », lu intégralement) :

| Point | Attendus officiels de fin de 4e | Décision |
|---|---|---|
| Thalès | « le théorème de Thalès et sa réciproque dans la configuration des triangles emboîtés » | Chapitre 9 : théorème et réciproque, triangles emboîtés ; configuration papillon exclue (3e) |
| Transformations | Seule la translation est citée | Chapitre 11 « Translations » ; rotation retirée du plan |
| Cas d'égalité des triangles | Cités parmi les connaissances de géométrie de 4e | Chapitre 12 ajouté (absent du manuel) |
| Fonction | « Comprendre et utiliser la notion de fonction » : formule, graphique, lecture | Chapitre 15, centré sur la dépendance entre deux grandeurs |
| Calcul littéral | Distributivité **simple**, programmes de calcul, équivalence | Double distributivité retirée (présente dans le manuel, pas dans les attendus) |
| Puissances | Exposants positifs ; puissances de 10 d'exposants positifs ou négatifs ; préfixes de nano à giga ; notation scientifique | Chapitre 5 conforme |
| Arithmétique | Nombres premiers inférieurs à 100, décomposition, fractions égales et simplification, problèmes | Chapitre 4 (absent du manuel) |
| Espace | Repérage (abscisse, ordonnée, altitude) ; pyramide et cône : perspective, patrons, volumes ; agrandissement-réduction (longueurs, aires, volumes) | Chapitre 13 ; sections de solides exclues (absentes des attendus) |
| Statistiques | Diagrammes circulaires ; médiane (effectif total ≤ 30) | Chapitre 16 ; étendue non retenue |
| Probabilités | Vocabulaire, contraire, calcul, formes variées, cibles par les aires | Chapitre 17 |
| Grandeurs composées | Conversions de vitesses (km/h ↔ m/s) et de débits | Chapitre 14 |
| Algorithmique (Scratch) | Niveaux 1 et 2 | **Hors périmètre** : Mathadap ne propose pas d'exercices de programmation par blocs, ni en 4e ni dans aucune autre classe. Les programmes de calcul sont traités au chapitre 6 |

**Erreurs du manuel à ne pas reprendre :**
- G4, p. 139 : base présentée comme un losange alors que c'est un rectangle ;
- D2, p. 161 : 59/25 vaut 2,36, et non 2,56 ;
- D2, p. 161 : la définition de la médiane doit reposer sur la moitié de l'effectif total.

## 2. Organisation définitive

| N° | Chapitre | Notions (titres provisoires jusqu'à rédaction) |
|---|---|---|
| 1 | Nombres relatifs | produit de deux relatifs · signe d'un produit de plusieurs facteurs · quotient · enchaînements de calculs |
| 2 | Fractions : comparer, additionner, soustraire | quotients égaux · comparer et ranger · additionner et soustraire · problèmes |
| 3 | Fractions : multiplier et diviser | produit, fraction d'une quantité · inverse et division · calculs enchaînés et problèmes |
| 4 | Divisibilité et nombres premiers | multiples et diviseurs · nombres premiers · décomposition · fractions et problèmes |
| 5 | Puissances | puissances d'un nombre · puissances de 10 · notation scientifique · préfixes et ordres de grandeur |
| 6 | Calcul littéral | expressions littérales · réduire · développer · factoriser · prouver (programmes de calcul) |
| 7 | Équations | tester une solution · résoudre ax + b = c · inconnue des deux côtés · mettre en équation |
| 8 | Théorème de Pythagore ✅ | (chapitre pilote, 5 notions) |
| 9 | Théorème de Thalès | configuration et rapports · calculer une longueur · réciproque (parallélisme) · agrandissement-réduction |
| 10 | Cosinus | cosinus d'un angle aigu · calculer une longueur · calculer un angle |
| 11 | Translations | image par une translation · propriétés de conservation · frises, pavages, raisonnements |
| 12 | Triangles égaux | triangles égaux · cas d'égalité · démontrer |
| 13 | Espace | repérage dans un pavé · pyramides et cônes · volumes · agrandissement-réduction |
| 14 | Proportionnalité et grandeurs | quatrième proportionnelle · reconnaître la proportionnalité · formules · grandeurs composées |
| 15 | Notion de fonction | exprimer une grandeur en fonction d'une autre · tableau et graphique · lire un graphique |
| 16 | Statistiques | diagrammes circulaires · médiane · interpréter une série |
| 17 | Probabilités | vocabulaire · calculer une probabilité · événement contraire |

**Identifiants des exercices :**
- rédigés : 40 000 + 1 000 × chapitre + 100 × rang de la notion + k ;
- générés : 4 000 000 + 10 000 × chapitre ;
- exception historique : Pythagore garde ses identifiants 480 000.

**Sources :**
- cours : `tools/quatrieme/cours_chNN.py`, écrits par `python tools/build_quatrieme_courses.py` ;
- exercices rédigés : `tools/quatrieme/banque_chNN.py`, écrits par `python tools/build_quatrieme_bank.py` ;
- générateurs : `webapp/exercise_generator_quatrieme/`, pool écrit par `python tools/generate_quatrieme_exercises.py`.

## 3. État par chapitre

| N° | Cours | Notions | Figures | Exercices rédigés (niv. 1/2/3/4) | Exercices générés (familles) | Mini-quiz | Free / Premium / Ultra | Chatbot | Site | Tests | Statut |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | ✅ | 4 | 4 | 80 (21/25/22/12) | 200 (8) | 12 | ✅ | ✅ | ✅ | ✅ | Validé |
| 2 | ✅ | 4 | 4 | 76 (20/24/20/12) | 200 (8) | 12 | ✅ | ✅ | ✅ | ✅ | Validé |
| 3 | ✅ | 3 | 3 | 59 (14/19/16/10) | 200 (8) | 9 | ✅ | ✅ | ✅ | ✅ | Validé |
| 4 | ✅ | 4 | 4 | 72 (17/23/20/12) | 200 (8) | 12 | ✅ | ✅ | ✅ | ✅ | Validé |
| 5 | ✅ | 4 | 4 | 70 (19/22/17/12) | 200 (8) | 12 | ✅ | ✅ | ✅ | ✅ | Validé |
| 6 | ✅ | 4 | 4 | 69 (19/22/16/12) | 225 (9) | 12 | ✅ | ✅ | ✅ | ✅ | Validé |
| 7 | ✅ | 4 | 4 | 69 (18/23/16/12) | 225 (9) | 12 | ✅ | ✅ | ✅ | ✅ | Validé |
| 8 | ✅ | 5 | 5 | 124 (30/36/34/24) | 200 (8) | 15 | ✅ | ✅ | ✅ | ✅ | Validé |
| 9 | ✅ | 4 | 4 | 68 (20/21/16/11) | 200 (8) | 12 | ✅ | ✅ | ✅ | ✅ | Validé |
| 10 | ✅ | 4 | 4 | 68 (20/23/15/10) | 200 (8) | 12 | ✅ | ✅ | ✅ | ✅ | Validé |
| 11 | ✅ | 3 | 3 | 61 (17/21/15/8) | 200 (8) | 9 | ✅ | ✅ | ✅ | ✅ | Validé |
| 12 | ✅ | 3 | 3 | 66 (17/21/17/11) | 150 (6) | 9 | ✅ | ✅ | ✅ | ✅ | Validé |
| 13 | ✅ | 4 | 4 | 68 (20/22/16/10) | 200 (8) | 12 | ✅ | ✅ | ✅ | ✅ | Validé |
| 14 | ✅ | 4 | 4 | 69 (18/23/16/12) | 200 (8) | 12 | ✅ | ✅ | ✅ | ✅ | Validé |
| 15 | ✅ | 3 | 3 | 58 (17/17/15/9) | 175 (7) | 9 | ✅ | ✅ | ✅ | ✅ | Validé |
| 16 | ✅ | 3 | 3 | 57 (17/18/13/9) | 175 (7) | 9 | ✅ | ✅ | ✅ | ✅ | Validé |
| 17 | ✅ | 4 | 4 | 68 (21/22/16/9) | 200 (8) | 12 | ✅ | ✅ | ✅ | ✅ | Validé |

## 4. Journal des lots

### Lot A — chapitres 1, 2, 3 (Validé)

**Contenu :** 11 notions rédigées ; 215 exercices rédigés ; 24 familles de générateurs (600 exercices dans le pool servi).

**Tests :** `test_quatrieme_programme.py` et `test_quatrieme_pythagore.py` réussis. Chaque famille de générateur passe le vérificateur indépendant sur 300 graines (7 200 exercices relus et recalculés).

**Chromium**, via `run_preview.py --donnees-test`, avec inscription depuis la page de choix :
- page Exercices : les 3 chapitres, avec leurs notions dans l'ordre du cours ;
- chaque notion : cours, figure, formules, mini-quiz 3/3 ;
- « Commencer les exercices » ouvre la bonne notion, avec indice, méthode et correction ;
- mobile 390 px sans débordement.

Bilan : 52/54 puis 16/16. Les 2 « KO » correspondaient à la limite Free de 20 exercices par jour, correctement appliquée (HTTP 429 et message à l'élève).

**Corrections faites pendant le lot :**
- la page d'exercice affichait l'identifiant `Chapitre_8` au lieu du titre (correction pour toutes les classes) ;
- les générateurs pouvaient proposer un entier déguisé en fraction ;
- exercices reformulés : 7 pour diversité, 2 pour rester dans le programme (41414 et 42117 évitaient la double distributivité et les identités remarquables), 2 corrigés (42416, réponse contradictoire ; 43118, données incohérentes) ;
- le lanceur ignore les ports refusés par les navigateurs (5060 et 5061) ;
- figures agrandies par défaut (`emphasis`) pour la lisibilité des libellés.

### Lot B — chapitres 4, 5, 6 (Validé)

**Contenu :**
- 12 notions rédigées ;
- 211 exercices rédigés ;
- 25 familles de générateurs (625 exercices dans le pool servi).

Le chapitre 6 n'utilise que la distributivité simple. Il ne contient ni double distributivité ni identités remarquables (contrôle automatique).

**Tests :**
- `test_quatrieme_programme.py` et `test_quatrieme_pythagore.py` : 68 tests réussis, 26 861 sous-tests.
- Campagne hors tests : 400 graines par famille pour les chapitres 5 et 6, toutes vérifiées par les vérificateurs indépendants.
- Test de mutation sur le chapitre 6 : une réponse faussée d'une unité est détectée dans 100 % des cas où elle contient un nombre.
- Le vérificateur du calcul littéral réévalue chaque expression en arithmétique exacte, sur 7 valeurs de x (dont une non entière). Il contrôle aussi :
  - la forme réduite ;
  - le facteur maximal d'une factorisation ;
  - les parenthèses d'un programme de calcul ;
  - les étapes intermédiaires.

**Chromium** (`run_preview.py --donnees-test`, port 5070, compte neuf pour chaque chapitre) : 20/20 contrôles pour chacun des chapitres 4, 5 et 6, sans erreur console ni réponse HTTP ≥ 400. Ces contrôles portent sur :
- la carte du chapitre et l'ordre des notions ;
- le cours, la figure et ses 3 étapes, les 2 exemples Free ;
- l'absence d'erreur KaTeX ;
- le mini-quiz 3/3 ;
- la série lancée sur la bonne notion, avec indice, méthode et correction ;
- l'affichage mobile à 390 px.

**Corrections pendant le lot :**
- banque du chapitre 6 :
  - 46212 : l'énoncé demandait de démontrer une égalité fausse ; il est reformulé en question ;
  - 46412 : il utilisait la double distributivité ; il est remplacé par « le carré d'un nombre pair est un multiple de 4 » ;
- générateurs du chapitre 6 : le facteur −1 n'est plus proposé (écriture « −1(…) ») ;
- générateur `puissance10_decimal` : diversité portée de 12 à plus de 200 énoncés distincts ;
- générateur `conversion_prefixe` : seules les unités cohérentes sont proposées (pas de « nm en Gm »).

**Point mineur ouvert :** les libellés de l'échelle des ordres de grandeur (chapitre 5, notion 4) sont petits sur ordinateur, mais restent lisibles.

### Lot C — chapitres 7 et 14 (Validé)

**Contenu :**
- 8 notions ;
- 138 exercices rédigés ;
- 17 familles de générateurs (425 exercices dans le pool).

Le chapitre 14 couvre :
- la quatrième proportionnelle (dont les briques de l'exemple officiel), les pourcentages et les échelles ;
- la reconnaissance de la proportionnalité dans un tableau et sur un graphique (alignement avec l'origine) ;
- les formules : d = v × t, longueur du cercle et d'un arc, loi d'Ohm ;
- les grandeurs composées : km/h ↔ m/s et débits m³/s ↔ L/min.

**Tests :**
- 68 tests réussis, 34 026 sous-tests ;
- 400 graines par famille, toutes vérifiées ;
- test de mutation : toutes les réponses faussées sont détectées.

**Chromium :** 20/20 pour chacun des chapitres 7 et 14 (compte neuf par chapitre).

**Corrections pendant le lot :**
- **Collision de nom de module (corrigée avant toute diffusion).** Le générateur s'appelait d'abord `proportionnalite`, comme un module de la Troisième. L'import de la Quatrième dans `exercise_generator/registry.py` masquait l'un des deux modules. Le module est renommé `proportionnalite_grandeurs`, et le script de branchement refuse désormais tout nom déjà présent dans le registre.
- **Recherche du chatbot :** la notion « Quotients égaux et simplification » (chapitre 2) était devancée par le chapitre 14. Le vocabulaire « grandeur quotient » du chapitre 14 est remplacé par « grandeur composée », et le « à retenir » du chapitre 2 est enrichi. La notion revient en tête (0,25 contre 0,18).
- **Générateur de prix :** les prix sont désormais réalistes par type d'objet, et les montants sont écrits avec deux décimales (« 12,50 € »). Le défaut a été détecté par le vérificateur.
- **Exercices reformulés :**
  - 5 réponses rédigées du chapitre 7 (47112, 47315, 47411, 47412, 47413) ;
  - 2 énoncés identiques à des tirages du générateur (47402, 54401).
- **Figures :** les textes d'étapes de la balance (chapitre 7) sont réordonnés ; les apostrophes sont retirées des libellés du graphique (chapitre 14), car elles faisaient passer le texte en mode mathématique.

### Lot D — chapitres 9, 10, 12 (Validé)

**Contenu :**
- 11 notions ;
- 202 exercices rédigés ;
- 22 familles de générateurs (550 exercices dans le pool).

**Chapitre 9, Thalès :**
- configuration des triangles emboîtés uniquement (la configuration papillon relève de la 3e) ;
- théorème, réciproque et agrandissement-réduction (longueurs × k, aires × k²) ;
- figures calculées et vérifiées par assertions : triangle 6,5-7-7,5, rapport 0,4, alignements, parallélisme.

**Chapitre 10, Cosinus :**
- cosinus seul : ni sinus, ni tangente, ni le mot « trigonométrie » (test hors programme) ;
- les valeurs approchées des générateurs sont calculées une seule fois, et les tirages trop proches d'une demi-unité d'arrondi sont rejetés ;
- la plage d'angle conseillée pour une échelle est alignée sur l'exemple officiel (65° à 75°).

**Chapitre 12, Triangles égaux :**
- les trois cas d'égalité : CCC, CAC, ACA ;
- les contre-exemples : trois angles, angle non compris ;
- les démonstrations rédigées : médiatrice, configuration en X, triangle isocèle, parallélogramme.

**Tests :**
- 68 tests réussis, 43 527 sous-tests ;
- 400 graines par famille, toutes vérifiées ;
- test de mutation : 100 % des réponses faussées sont détectées ;
- pour « reconnaître un cas d'égalité », le vérificateur refait l'analyse : 1 600 verdicts faux sur 1 600 sont rejetés.

**Chromium :** 20/20 pour le chapitre 9, 20/20 pour le chapitre 10, 16/16 pour le chapitre 12 (3 notions).

**Corrections pendant le lot :**
- **Nom de module :** `thales` existe déjà en Troisième, le module s'appelle donc `thales_emboites`.
- **Test du pilote mis à jour, sans affaiblissement :** il interdisait « Théorème de Thalès » dans le prompt de 4e, alors que ce chapitre est désormais au programme de 4e. Le contrôle porte maintenant sur des chapitres propres à la 3e (« Fonctions affines », « trigonométrie »).
- **Recherche du chatbot :**
  - les titres des notions 1 et 3 du chapitre 10 sont renommés « Nommer les côtés d'un triangle rectangle » et « Utiliser le cosinus pour trouver un côté » ;
  - leur vocabulaire indexé est allégé.
  
  Sans cela, « Calcule la longueur de l'hypoténuse » était rattaché au cosinus au lieu de Pythagore, et la recherche « hypoténuse » ne renvoyait plus le chapitre 8.
- **Exercices et figures :**
  - chapitre 9 : diversité de la notion 3 relevée (deux énoncés reformulés) ;
  - chapitre 12 : un exemple qui utilisait implicitement le sinus a été reformulé ;
  - chapitre 12 : les aperçus Premium et Ultra ne promettent plus de « démonstration » de cours qu'ils ne contiennent pas.
- **Vérificateur de la réciproque :** il ne contrôlait que « Oui/Non » ; il contrôle désormais aussi la valeur des rapports annoncés.

### Lot E — chapitres 11 et 13 (Validé)

**Contenu :**
- 7 notions ;
- 129 exercices rédigés ;
- 16 familles de générateurs (400 exercices dans le pool).

**Chapitre 11, Translations :**
- translation seule, conformément aux attendus (la rotation relève de la 3e) ;
- image d'un point ou d'une figure sur quadrillage, dans un repère et par le parallélogramme ;
- conservations ;
- frises et pavages.

**Chapitre 13, Espace :**
- repérage dans un pavé (abscisse, ordonnée, altitude) ;
- pyramides et cônes : perspective cavalière et patrons (dont l'angle du secteur du patron de cône) ;
- volumes, avec la démonstration du facteur 1/3 par trois pyramides dans un cube ;
- agrandissement-réduction des longueurs, aires et volumes (k, k², k³) ;
- sections de solides non traitées (hors attendus de 4e) ;
- figures en perspective cavalière calculées : fuyantes à 45°, coefficient 0,5, arêtes cachées en pointillés. Le cône est dessiné avec une base en ellipse horizontale.

**Tests :**
- 68 tests réussis, 50 192 sous-tests ;
- 400 graines par famille, toutes vérifiées ;
- test de mutation : 100 % des réponses faussées sont détectées.

**Chromium :** 16/16 pour le chapitre 11 (3 notions), 20/20 pour le chapitre 13.

**Corrections pendant le lot :**
- **Noms de modules :** `translations_plan` et `espace_volumes` (le script de branchement vérifie l'absence de collision).
- **Générateurs :**
  - rapport 1/3 affiché en fraction, car il n'est pas décimal ;
  - deux familles élargies pour atteindre au moins 40 énoncés distincts (bases de 3 à 12 côtés ; variante « calculer la hauteur d'un cône »).
- **Exercices :** 51314 (réponse hésitante) et 51116 (ordre des sommets du parallélogramme : AA'OB) corrigés.
- **Figures :**
  - cône redessiné, avec une base en ellipse horizontale ;
  - libellés repositionnés ou rendus neutres (« (+4 ; +2) », « h ») ;
  - le lien du chapitre 9 vers la notion du chapitre 13 « Agrandissement et réduction : longueurs, aires, volumes » est rétabli.

### Lot F — chapitres 15, 16, 17 (Validé)

**Chapitre 15, Notion de fonction :**
- exprimer une grandeur en fonction d'une autre (formule), tableau de valeurs et graphique, lecture graphique dans les deux sens ;
- la figure du repère utilise le moteur commun, qui nomme toujours l'axe vertical « y » : le cours précise « axe noté $y$ sur la figure » plutôt que de modifier le moteur partagé par les autres classes.

**Chapitre 16, Statistiques :**
- diagrammes circulaires (angles et effectifs), médiane d'une liste ou d'un tableau (effectif total ≤ 30), moyenne et comparaison de séries ;
- module `statistiques_quatrieme` (nom distinct de celui de la Troisième).

**Chapitre 17, Probabilités :**
- vocabulaire, calcul en situation d'équiprobabilité, événement contraire (avec démonstration de $P(	ext{non } A) = 1 - P(A)$), probabilités par les aires et issues non équiprobables (osselet, dé truqué) ;
- module `probabilites_quatrieme` (8 familles) ;
- la figure de l'urne officielle utilise des libellés neutres (« gagnante », « perdante ») : le moteur des diagrammes circulaires impose ses couleurs, qui contredisaient « rouge » et « orange ».

**Tests :**
- 68 tests réussis, 59 289 sous-tests ;
- 400 graines par famille, toutes vérifiées par des vérificateurs indépendants ;
- test de mutation : 1 600 réponses faussées sur 1 600 détectées au chapitre 17.

**Chromium :** 16/16 pour le chapitre 15, 16/16 pour le chapitre 16, 20/20 pour le chapitre 17 ; aucune erreur de console ni de réponse HTTP ≥ 400.

**Registre :** `planned_chapter_titles` est vide, et la Quatrième reste `published=False`.

## 5. Finalisation (terminée le 2026-10-25)

- [x] suggestions du chatbot pour la Quatrième : une question par domaine (relatifs, fractions, équations, Pythagore, Thalès, probabilités), chacune rattachée au bon chapitre ;
- [x] pytest complet : 2 854 réussis, 140 ignorés, 60 666 sous-tests ; 2 échecs **préexistants** et identiques à la référence (`test_escalade_pedagogique.py`, sans lien avec la Quatrième) ;
- [x] Vitest : 62 fichiers, 946 tests réussis (un test de minutage du chatbot avait échoué sous la charge d'un pytest lancé en parallèle ; il passe isolément et lors de la relance complète) ;
- [x] ruff (règles de la CI et règles `F` sur les fichiers du chantier), ESLint et Prettier sur `chatbot.js` ;
- [x] `npm run build`, validation des classes comprise ;
- [x] Quatrième absente du registre servi par défaut (`premiere`, `seconde`, `troisieme`), `published=False` ;
- [x] non-régression des autres classes : 134 familles de Quatrième à identifiants uniques, modules de générateurs remis dans l'ordre des chapitres dans `exercise_generator/registry.py` ;
- [x] parcours Chromium de contrôle après les derniers changements : chapitres 1, 8 et 17.

**Bilan global :**
- 17 chapitres et 64 notions ;
- 64 figures et 16 démonstrations ;
- 192 questions de mini-quiz ;
- exemples de cours : 128 Free, 128 Premium et 64 Ultra ;
- 1 202 exercices rédigés (niveaux 1, 2, 3 et 4 : 325, 382, 300 et 195) ;
- 3 350 exercices générés par 134 familles.

**Non fait volontairement :**
- `graphify update .` n'a pas été lancé, car le dossier `graphify-out/` était déjà supprimé dans l'arbre de travail avant le chantier ;
- aucun commit.

## 6. Audit final et serveur local unique (2026-10-25, en cours)

### A. Serveur local unique — fait, testé sur un port de test (5050 : voir « Reste »)

**Cause des doubles serveurs :** Werkzeug 3.1.8 lie son socket avec `SO_REUSEADDR` (`allow_reuse_address = True`). Sous Windows, deux sockets `SO_REUSEADDR` peuvent écouter le même port. Mesuré sur ce poste : seule cette combinaison donne deux écoutes, et `SO_EXCLUSIVEADDRUSE` refuse toute autre liaison.

**Correctif :** nouveau module `webapp/dev_server.py`, utilisé par `server.py` et par `tools/preview_isolated_server.py`. Il :
- réserve le port en exclusivité ;
- conserve le rechargeur Werkzeug, qui garde le même socket entre deux redémarrages ;
- place les processus dans un *Job Object* Windows (aucun enfant orphelin) ;
- inscrit l'instance dans un fichier d'état `%TEMP%/mathadap-dev-5050.json`.

**Lanceur `tools/run_preview.py` :** port 5050 fixe, sans aucun repli sur un autre port. Il prend en charge :
- les actions `--statut`, `--redemarrer` et `--arreter` ;
- une instance déjà lancée, qui est reconnue (aucune seconde instance) ;
- un ancien serveur non inscrit, jamais arrêté automatiquement ;
- une autre application sur le port, qui provoque un échec explicite ;
- la surveillance du frontend (`vite build --watch --emptyOutDir=false`).

Les scripts npm (`dev`, `dev:donnees-test`, `dev:statut`, `dev:redemarrer`, `dev:arreter` ; `preview` devient un alias), les tâches VS Code, le README et DEPLOYMENT sont alignés.

**Scénarios testés** (port de test 5391, données de test isolées) : 23/23, dont :
- second lancement ;
- autre mode ;
- `SO_REUSEADDR` refusé ;
- `server.py` direct refusé ;
- rechargement après une modification du backend, sur le même socket ;
- frontend recompilé et servi ;
- `--arreter` et `--redemarrer` ;
- lanceur tué sans aucun processus résiduel ;
- autre application sur le port.

Tests unitaires du lanceur mis à jour (nouveau contrat).

**Reste :**
- un ancien `python webapp/server.py` (PID 6772, lancé le 22/10, sans la Quatrième) occupe 5050 : à arrêter par l'utilisateur ;
- un `npm run dev` (serveur Vite sur 5173, lancé le 22/10) tourne aussi : à arrêter par l'utilisateur.

### B/C. Audit des contenus — en cours

**Formules :** 19 814 formules distinctes (cours, banque, pool) rendues par KaTeX 0.16.11 en mode strict, toutes sans erreur. 7 caractères Unicode placés dans `	ext{}` (€, ³, µ) ont été corrigés, ainsi que la notation `cos⁻¹` sortie de la formule (16 occurrences, chapitre 10).

**Calculs :** 2 047 égalités des cours et 16 597 des exercices (énoncés, réponses, étapes) vérifiées arithmétiquement. Corrections :
- 54115 : arrondi 17,061 corrigé en 17,0616 ;
- 53313 : écriture `144π ÷ 48π` ambiguë, remplacée par une fraction.

Les autres signalements sont des erreurs d'élèves présentées volontairement.

**Diversité :**
- doublon exact 45106 / 41209 : 45106 réécrit (parité de l'exposant) ;
- 26 groupes de même squelette dans la banque : séries d'application progressives, conservées ;
- 46 familles générées sur 134 n'ont qu'un seul gabarit d'énoncé (seules les valeurs changent).

**Niveaux :** progression monotone de la longueur des énoncés, du nombre d'étapes et de la part de raisonnement ; aucun exercice de niveau 3 ou 4 ne tire sa difficulté de grands nombres seulement.

**Générateurs :** 134 familles déterministes, chacune avec un vérificateur, notions cohérentes avec les cours ; pool régénéré identique au fichier livré ; identifiants uniques.

**Programme :** 58 attendus officiels confrontés au contenu. Omission corrigée, « écrire un protocole de construction » :
- exercices 52223, 52224 (chapitre 12), 51121 (chapitre 11) et 49418 (chapitre 9) ;
- règle ajoutée au cours du chapitre 12.

Ajout de l'exemple officiel « ordre de grandeur pour contrôler un résultat » (45418). La banque compte désormais 1 207 exercices.

**Relecture pédagogique des 64 notions :** faite, chapitre par chapitre (définitions, règles, méthodes, 320 exemples avec leurs réponses, erreurs fréquentes, démonstrations). Corrections :
- **Chapitre 4 :** règle « tout entier n ≥ 1… (sauf 1) » reformulée.
- **Chapitre 5 :**
  - masse de l'électron : il manquait trois zéros (9,1 × 10⁻²⁸ au lieu de 9,1 × 10⁻³¹ kg) ;
  - « rapport des exposants » remplacé par 10⁸ ÷ 10⁻³ = 10¹¹.
- **Chapitre 8 (pilote, exemple Ultra) :** la double distributivité, hors programme de 4e, est remplacée par un raisonnement d'aires (bande en L : (x + 1)² − x² = 2x + 1).
- **Chapitre 10 :**
  - l'échelle à 72° était jugée « trop inclinée » ; elle respecte en fait la recommandation officielle (65° à 75°) ;
  - l'exemple Ultra s'appuyait sur cos² 30° = 3/4 exact, hors programme : il garde désormais la valeur en mémoire et montre l'erreur d'un arrondi prématuré ;
  - exercice 50407 aligné sur la plage 65°–75°.
- **Chapitre 12 :** énoncé de l'exemple Ultra aligné sur sa résolution.
- **Chapitre 14 :** chaîne d'égalités m³/s = L/s = L/h corrigée.
- **Chapitre 17 :**
  - l'urne officielle retrouve ses boules rouge et orange, avec un nouveau paramètre facultatif `color` des diagrammes circulaires (liste fermée, sans effet sur les figures existantes, test Vitest ajouté).

**Relecture d'un exemple par famille générée (134) :** corrections de rédaction dans 10 générateurs :
- coquille « w'hypoténuse » ;
- accords « chacune » et « d'une place » ;
- parenthèses autour de nombres positifs ;
- `= pprox` fautif ;
- égalités redondantes ;
- durée « 210/60 h » remplacée par 3,5 h ;
- calcul de valeur détaillé ;
- formulations « le mur (ou le poteau) » et « l'objet » précisées.

Pool régénéré, 400 tirages par famille vérifiés, tests de la Quatrième réussis (73).

**Abonnements (64 notions, 3 plans) :**
- audit du filtrage serveur : 0 problème. Free reçoit 2 exemples, la définition, au moins 3 règles, la méthode, la figure, le quiz et les aperçus ; Premium ajoute 2 exemples et les explications ; Ultra ajoute 1 exemple et les 16 démonstrations ; aucun texte verrouillé ne fuit ;
- de bout en bout sur l'instance de test : réponses de l'API correctes pour les 3 plans et les 17 chapitres ; exercices sur mesure réservés à Ultra (64 notions, 134 familles, 8/8 générés) ; quota Free de 20 exercices par jour appliqué (429 dès le 21ᵉ) ; Premium non bloqué ; lien de mise à niveau vers la page Abonnements.

**Figures :**
- chaînes par étapes de 3 cases ou plus empilées verticalement (sous-titres auparavant d'environ 5 px, désormais lisibles ; la figure de Première, chapitre 3, en profite aussi) ; test Vitest ajouté ;
- échelle des ordres de grandeur du chapitre 5 redessinée sur deux axes (tout petits / très grands objets), avec « Terre → Lune » ;
- urne officielle du chapitre 17 en rouge et orange (paramètre `color` facultatif).

**Chatbot :** 52 questions variées (reformulations, demandes d'exercice et de cours, erreurs d'élève, notions proches, vocabulaire ambigu, autres classes). Le contenu indexé (« à retenir », astuces) a été enrichi pour quatre notions :
- « moins par moins » (chapitre 1) ;
- « quelle fraction est la plus grande » (chapitre 2) ;
- « trouver x » (chapitre 7) ;
- « calculer un angle d'un triangle rectangle » (chapitre 10).

**Deux échecs pytest préexistants (`test_escalade_pedagogique`) : cause établie, non corrigés volontairement.**
- Ils réussissent sur le commit `HEAD` et échouent dans l'arbre de travail.
- Remettre seulement les cours de Seconde (`course_content/cours/*.json`, refonte du 2026-10-23, antérieure à ce chantier) dans leur version `HEAD` les fait repasser.
- Ces tests ne réussissaient que grâce à une correspondance TF-IDF fortuite : « encore une autre façon » rapproché de « opérations sur les événements », avec un score de 0,122 pour un seuil de 0,12. La réécriture des cours a fait tomber ce score à 0,097.
- Le routage actuel envoie donc vers le LLM une relance sans mot de sujet.
- Les faire passer proprement demande une décision sur le routage des relances (réponse locale ou LLM), valable pour toutes les classes : à trancher par l'utilisateur.

**Reste à faire :**
- figures (chapitre 5, sous-titres des figures par étapes) ;
- navigation et Chromium ;
- chatbot ;
- `test_escalade_pedagogique` ;
- tests finaux et rapport.
- **Chromium, 17 chapitres (instance de test 5391, compte Ultra, base isolée) :** tous les contrôles réels réussis ; 0 erreur de console, 0 réponse HTTP en échec. Les 64 « KO » restants viennent du contrôle « 2 exemples Free », non pertinent pour un compte Ultra.
- **Abonnements de bout en bout :** 20/22. Les 2 échecs viennent du script : le titre de la démonstration du chapitre 17 commence par une formule, et le script ne cherchait donc que « Pourquoi ».
- **Thème sombre, ordinateur et mobile :** réussi sur les 17 chapitres.

**État au moment de la compaction (2026-10-25) :**
- **Fait :**
  - serveur unique (code, 23 scénarios) ;
  - audits KaTeX, calculs, diversité, niveaux, programme et cours (64 notions) ;
  - générateurs (134 familles) ;
  - abonnements ;
  - figures ;
  - navigation Chromium ;
  - diagnostic des échecs de `test_escalade_pedagogique`.
- **Reste :**
  1. test HTTP du chatbot avec `CHATBOT_PROVIDER=fake` (script `scratchpad/quatrieme/chatbot_e2e.py`), en redémarrant l'instance 5391 avec cette variable ; voir le traitement des questions hors classe (dérivée, sinus, inéquation) ;
  2. tests finaux : pytest Quatrième et chatbot, Vitest, ruff, ESLint, Prettier, build ;
  3. arrêter l'instance de test 5391 (`python tools/run_preview.py --port 5391 --arreter`) ;
  4. faire arrêter par l'utilisateur l'ancien serveur PID 6772 et le Vite PID 24808, puis valider `python tools/run_preview.py` sur 5050 ;
  5. rapport final.

**Clôture de l'audit (2026-10-25) :**
- **Chatbot (HTTP, `CHATBOT_PROVIDER=fake`) :** un calcul sans mot de sujet (« pourquoi 1/3 + 1/4 ne fait pas 2/7 », « (-3)² = -9 c'est faux ? ») faisait proposer, par la recherche libre dans la banque, un exercice de cosinus et des cartes « S'entraîner » sans rapport (même défaut en Troisième et en Seconde). Corrigé : `search_service.has_topic_word`, utilisé par le palier 5 de `degraded_mode_service` et par `action_cards_service` (sans chapitre connu ni mot de sujet : clarification neutre, aucune carte). 5 tests ajoutés dans `test_degraded_mode_service.py`.
- **Non corrigé (routage TF-IDF générique, toutes classes) :** « dérivée » est rapprochée de « Calculer un angle avec le cosinus » par le seul mot « calculer » (Troisième : « Calculer une image »), « sinus » du cosinus (Troisième : angles et parallèles), « inéquation » de la méthode des équations, « trouver x dans 3x + 5 = 20 » de « Réduire une expression ». Aucune détection « hors programme » n'existe ; la corriger relève d'une évolution du routeur, à décider (même zone que les 2 échecs de `test_escalade_pedagogique`).
- **Scripts corrigés :** `check_lot.py` (5 exemples attendus pour le compte Ultra) : 308/308 ; `audit_plans_e2e.py` (démonstration repérée par son intitulé) : 22/22.
- **Tests finaux :** pytest complet 2 861 réussis, 2 échecs (les 2 connus de `test_escalade_pedagogique`), 140 ignorés ; suites du chatbot après la dernière correction : 1 553 réussis, mêmes 2 échecs ; Vitest 948/948 ; ruff (règles CI et F), ESLint, Prettier propres ; `npm run build` réussi.
- **Instance de test 5391 :** arrêtée, aucun processus résiduel.
- **5050 :** toujours occupé par l'ancien serveur de l'utilisateur (PID 6772, `webapp/server.py`, 22/10) ; le lanceur le signale et refuse de démarrer sans l'arrêter. Vite PID 24808 toujours sur 5173. Validation sur 5050 à faire après leur arrêt par l'utilisateur.
