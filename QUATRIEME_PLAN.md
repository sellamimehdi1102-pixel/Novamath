# Quatrième — cartographie des chapitres (proposition, 2026-10-24)

Statut : **proposition à valider**. Seul le chapitre 8 (Pythagore) est rédigé.
Aucun autre chapitre n'est engagé.

Sources :
- programme du cycle 4 (BO n° 31 du 30 juillet 2020) et repères annuels de 4e
  (BO n° 22 du 29 mai 2019), applicables en 2026-2027 ;
- manuel iParcours 4e, utilisé comme référence de progression et jamais copié ;
- inventaire et écarts relevés lors de l'audit.

Le symbole ⚠️ signale un point dont la répartition 4e/3e doit être vérifiée
sur le texte du BO **avant** rédaction. L'annexe officielle n'a pas pu être
consultée pendant l'audit (erreur 403), et je ne présente pas ces points comme
acquis.

## 1. Règles communes à tous les chapitres

### Chaîne de travail du chapitre pilote

1. Le cours est produit par un script (`course_content/cours_quatrieme/chapitre_N.json`).
   - Chaque figure est calculée et vérifiée par un test : codages, longueurs, étapes.
2. Les exercices rédigés sont écrits dans `tools/build_quatrieme_bank.py`.
   - Chaque valeur annoncée est recalculée.
   - Le fichier n'est pas écrit si un seul contrôle échoue.
3. Chaque chapitre a son module de générateurs dans `webapp/exercise_generator_quatrieme/`.
   - Un vérificateur indépendant relit l'énoncé et refait le calcul sur 500 graines par famille.
4. Les tests suivent le modèle de `test_quatrieme_pythagore.py` et `cours-quatrieme-pythagore.test.js`.
5. Le titre du chapitre est retiré de `planned_chapter_titles` dans `curriculum_registry.py`.

### Volume

On vise la **couverture des compétences**, pas un nombre identique d'exercices par chapitre :
- chaque notion a des exercices rédigés aux 4 niveaux ;
- chaque type de raisonnement a au moins une famille générée ;
- 3 mini-quiz rédigés de niveau 1 ou 2.

Repère indicatif : 18 à 30 exercices rédigés par notion, et 25 générés par famille.

### Abonnements (même répartition que Pythagore)

| Plan | Contenu |
|---|---|
| **Free** | Cours complet et utilisable : définition, règles, méthode, 2 exemples, erreurs, figure expliquée, mini-quiz |
| **Premium** | 2 exemples de plus, intuition, exemples concrets, erreurs détaillées, formule complémentaire, « à retenir » |
| **Ultra** | Un exemple qui combine plusieurs compétences, une démonstration adaptée à la 4e quand elle a du sens, et les exercices sur mesure, ouverts automatiquement par les générateurs |

### Intégrations sans code supplémentaire

Le registre, les routes, la page Exercices, le lecteur de cours, le mini-quiz, la recherche, le tableau de bord et le chatbot (moteur local et RAG) lisent déjà le contenu de façon générique.

Par chapitre, il faut seulement :
- retirer le titre de `planned_chapter_titles` ;
- éventuellement compléter les suggestions du chatbot (`chatbot.js`, entrée `quatrieme`).

### Figures disponibles dans le moteur

- `geom` : points, segments, polygones, angles et arcs, vecteurs, courbes, repère ;
- `numberline` : droite graduée ;
- `bars`, `pie`, `boxplot` : diagrammes ;
- `tree` : arbre de probabilités ;
- `pipeline` : chaîne de calculs ;
- `solid` : cube, pavé, cylindre, cône, sphère, pyramide, en schémas génériques.

**Seul besoin nouveau identifié :** un patron de cône (secteur angulaire) pour le chapitre 12. On peut le dessiner en `geom` avec des arcs. Aucun type de figure nouveau n'est à prévoir.

## 2. Ordre proposé et lots de rédaction

L'ordre suit les prérequis. La numérotation reste celle déjà fixée dans le registre, car les identifiants de chapitre ne doivent jamais changer.

| Lot | Chapitres | Raison |
|---|---|---|
| 1 | 1 Relatifs · 2 Fractions (comparaison, addition) · 3 Fractions (×, ÷) | Socle de calcul de tous les autres chapitres |
| 2 | 5 Puissances · 4 Nombres premiers · 6 Calcul littéral | 6 réutilise 1 à 3 ; 4 et 5 sont indépendants |
| 3 | 7 Équations · 13 Proportionnalité | 7 s'appuie sur 6 ; 13 réutilise 3 et 7 |
| 4 | 9 Thalès · 10 Cosinus | S'appuient sur 8 (Pythagore, déjà rédigé) et sur 3 et 7 |
| 5 | 11 Translations et rotations · 12 Pyramides, cônes, volumes | Géométrie de transformation et de l'espace |
| 6 | 14 Statistiques · 15 Probabilités · 16 Fonction ⚠️ | 16 est à confirmer, voir la fiche |

## 3. Fiches par chapitre

Les difficultés suivent la même échelle partout : 1 Fondamental, 2 Intermédiaire, 3 Avancé, 4 Difficile.

### Ch. 1 — Nombres relatifs (manuel N1)

**Notions :**
1. Addition et soustraction, enchaînements ;
2. Produit, et signe d'un produit de n facteurs ;
3. Inverse et quotient ;
4. Priorités opératoires avec relatifs.

**Prérequis :** relatifs de 5e, distance à zéro, priorités de 5e.

**Compétences :** calculer, choisir le signe, distinguer opposé et inverse, calculer une expression.

**Exercices, du niveau 1 au niveau 4 :**
- somme directe, puis enchaînement, puis parenthèses et crochets, puis problème de températures ou d'altitudes ;
- signe seul, puis produit de deux facteurs, puis de n facteurs, puis calcul astucieux ;
- « inverse ou opposé ? » ;
- trouver l'erreur d'un élève.

**Figures :** `numberline` pour l'addition comme déplacement ; `pipeline` pour les priorités.

**Générateurs :** somme ou différence ; signe d'un produit ; produit ou quotient ; expression à priorités, avec un arbre d'évaluation vérifié.

**Ultra :** démonstration de la règle des signes du produit, à partir de la distributivité sur 0 = a × (b + (−b)).

### Ch. 2 — Fractions : comparaison, addition, soustraction (N2)

**Notions :**
1. Quotients égaux et simplification ;
2. Même dénominateur et comparaison ;
3. Addition et soustraction.

**Prérequis :** multiples et diviseurs, critères de divisibilité.

**Compétences :** réduire au même dénominateur, comparer, calculer, simplifier le résultat.

**Exercices :** compléter une égalité, comparer, calculer, problème de partage, repérer une erreur (additionner les dénominateurs).

**Figures :** `numberline` pour placer une fraction ; `geom` pour les rectangles de parts.

**Générateurs :** égalité de quotients ; comparaison ; somme ou différence avec un dénominateur multiple ou quelconque. Les calculs sont faits en `Fraction`.

**Ultra :** pourquoi a/b = ka/kb, avec un argument par le partage.

### Ch. 3 — Fractions : multiplication et division (N3)

**Notions :**
1. Produit, et fraction d'une quantité ;
2. Inverse et division ;
3. Produit en croix, pour l'égalité de deux quotients.

**Prérequis :** chapitre 2.

**Compétences :** multiplier, diviser par une fraction, calculer une fraction d'une quantité, résoudre a/b = x/d.

**Exercices :** produit simplifié avant calcul, fraction d'une quantité, quotient, quatrième proportionnelle par produit en croix, problème en deux étapes.

**Figures :** `geom` pour une fraction de fraction sur un rectangle.

**Générateurs :** produit ; quotient ; fraction d'une quantité ; produit en croix.

**Ultra :** pourquoi diviser revient à multiplier par l'inverse.

### Ch. 4 — Nombres premiers (ajout du programme, absent du manuel)

**Notions :**
1. Diviseurs et nombres premiers ;
2. Décomposition en produit de facteurs premiers ;
3. Applications : simplification de fractions, problèmes de partage.

⚠️ À confirmer : la place exacte de la décomposition en 5e ou en 4e.

**Compétences :** reconnaître un nombre premier inférieur à 100, décomposer, simplifier une fraction en écriture irréductible.

**Exercices :** premier ou non, avec justification ; décomposition ; fraction irréductible ; problème de paquets identiques.

**Figures :** aucune n'est indispensable (`pipeline` pour l'arbre de divisions successives).

**Générateurs :** primalité ; décomposition ; simplification par décomposition.

**Ultra :** il existe une infinité de nombres premiers, en version guidée.

### Ch. 5 — Puissances (N4)

**Notions :**
1. aⁿ, avec a⁰ et a¹ ;
2. Puissances de 10, préfixes et notation scientifique ;
3. Produits et quotients de puissances de 10.

⚠️ À confirmer : la répartition 4e/3e de a⁻ⁿ pour un a quelconque.

**Compétences :** calculer, écrire en notation scientifique, comparer des ordres de grandeur, convertir avec les préfixes.

**Exercices :** calculer une puissance, déterminer le signe de (−a)ⁿ, passer en notation scientifique et revenir, faire des calculs sur les puissances de 10, ordres de grandeur.

**Figures :** `numberline` logarithmique simplifiée (ordres de grandeur).

**Générateurs :** valeur d'une puissance ; notation scientifique ; 10ᵐ × 10ᵖ et 10ᵐ / 10ᵖ ; conversion avec préfixe.

**Ultra :** pourquoi a⁰ = 1, par la règle des quotients.

### Ch. 6 — Calcul littéral (N5)

**Notions :**
1. Réduire une expression ;
2. Développer par simple distributivité ;
3. Factoriser par un facteur commun simple ;
4. Supprimer des parenthèses (opposé d'une somme) ;
5. Développer par double distributivité.

**Prérequis :** chapitres 1 à 3.

**Compétences :** transformer une expression, tester une égalité pour une valeur, produire une expression à partir d'un programme de calcul.

**Exercices :** réduire ; développer ; factoriser ; prouver ou réfuter une égalité (contre-exemple) ; programme de calcul.

**Figures :** `geom` pour l'aire du rectangle découpé, qui illustre la double distributivité.

**Générateurs :** réduction ; développement simple et double, vérifiés avec SymPy ; factorisation ; test d'une égalité.

**Ultra :** la double distributivité démontrée par deux simples distributivités, plus l'aire.

### Ch. 7 — Équations (N6)

**Notions :**
1. Tester si un nombre est solution ;
2. Résoudre ax + b = c ;
3. Inconnue dans les deux membres ;
4. Mettre un problème en équation.

**Prérequis :** chapitre 6.

**Compétences :** résoudre et vérifier, mettre en équation, interpréter la solution dans le contexte.

**Exercices :** tester une solution ; résoudre en 1 ou 2 étapes ; équation avec x des deux côtés ; problème (âges, périmètres, tarifs) ; trouver l'erreur d'une résolution.

**Figures :** `geom` en balance, facultatif.

**Générateurs :** test de solution ; résolution à coefficients entiers ou décimaux ; mise en équation de contextes paramétrés, avec la solution vérifiée par substitution.

**Ultra :** pourquoi on peut ajouter ou multiplier les deux membres, avec les conditions (multiplicateur non nul).

### Ch. 8 — Théorème de Pythagore ✅ rédigé (G1, plus la racine carrée du programme)

Voir `cours_quatrieme/chapitre_8.json`.

La contraposée reste une **méthode** pour démontrer qu'un triangle n'est pas rectangle, sans présentation formelle de logique.

### Ch. 9 — Théorème de Thalès, triangles emboîtés (ajout du programme, absent du manuel)

**Notions :**
1. Configuration et égalité des trois rapports ;
2. Calculer une longueur ;
3. Agrandissement et réduction, avec le coefficient.

⚠️ À confirmer : la réciproque est-elle exigible en 4e ? La configuration papillon relève de la 3e.

**Prérequis :** chapitres 3 (produit en croix), 7 et 8.

**Compétences :** repérer les triangles emboîtés et le parallélisme, écrire les rapports dans le bon ordre, calculer.

**Exercices :** compléter les rapports ; calculer une longueur ; problème d'ombre ou de hauteur ; justifier le parallélisme donné ; trouver l'erreur d'ordre des rapports.

**Figures :** `geom` avec deux triangles emboîtés et des parallèles codées, dont les rapports sont vérifiés par un test.

**Générateurs :** longueur manquante, avec une configuration aux longueurs rationnelles exactes ; coefficient d'agrandissement.

**Ultra :** démonstration par les aires, à la manière d'Euclide.

### Ch. 10 — Cosinus (G2)

**Notions :**
1. Côté adjacent et hypoténuse ;
2. Définition de cos et valeurs entre 0 et 1 ;
3. Calculer un côté ;
4. Calculer un angle à la calculatrice.

Sinus et tangente relèvent de la 3e ; un test de hors-programme le vérifiera.

**Prérequis :** chapitre 8, angles complémentaires.

**Compétences :** nommer les côtés selon l'angle, choisir la formule, régler la calculatrice en degrés, arrondir.

**Exercices :** nommer les côtés ; calculer le côté adjacent ; calculer l'hypoténuse ; calculer un angle ; problème de rampe ou d'échelle combiné avec Pythagore.

**Figures :** `geom` avec un angle codé par un arc et le côté adjacent mis en évidence.

**Générateurs :** côté adjacent ; hypoténuse ; angle, calculés en flottants contrôlés et arrondis une seule fois.

**Ultra :** le cosinus ne dépend que de l'angle, via Thalès (chapitre 9).

### Ch. 11 — Translations et rotations (G3)

**Notions :**
1. Translation : image d'un point et parallélogramme ;
2. Rotation : centre, angle, sens ;
3. Propriétés de conservation.

⚠️ À confirmer : la rotation en 4e ou en 3e selon les repères. Le manuel la traite en 4e.

**Compétences :** construire une image, reconnaître une transformation, utiliser les conservations.

**Exercices :** image sur quadrillage ; reconnaître une transformation ; compléter une frise ; justifier une conservation.

**Figures :** `geom` avec quadrillage, `vectors` et `arcs`, et l'image révélée par étapes.

**Générateurs :** images de points par translation ou rotation de 90° ou 180° sur quadrillage. Les coordonnées sont entières et vérifiées.

**Ultra :** pourquoi la translation conserve les longueurs, par le parallélogramme.

### Ch. 12 — Pyramides, cônes, volumes (G4)

**Notions :**
1. Pyramide et cône : vocabulaire et patrons ;
2. Volume = aire de la base × hauteur ÷ 3 ;
3. Sections parallèles à la base ⚠️ (vérifier la répartition 4e/3e).

**Compétences :** reconnaître, calculer un volume, convertir les unités de volume.

**Exercices :** vocabulaire ; volume d'une pyramide à base carrée puis rectangulaire ; volume d'un cône ; conversion ; problème de contenance.

**Figures :** `solid` (pyramide, cône) ; `geom` pour le patron de cône (secteur angulaire), le seul besoin nouveau.

**Générateurs :** volume de la pyramide ; volume du cône (valeur exacte en π puis arrondi) ; conversions.

**Ultra :** pourquoi le facteur 1/3, par le découpage d'un cube en 3 pyramides.

**Points à corriger par rapport au manuel :** la base d'un exemple p. 139 est présentée comme un losange alors que c'est un rectangle, et le sommaire annonce des « aires » non traitées.

### Ch. 13 — Proportionnalité (D1)

**Notions :**
1. Quatrième proportionnelle ;
2. Pourcentages ;
3. Vitesse moyenne ;
4. Grandeurs composées (débit, masse volumique).

**Prérequis :** chapitre 3.

**Compétences :** reconnaître une situation de proportionnalité, calculer, convertir les unités composées.

**Exercices :** tableau ; pourcentage d'une quantité ; évolution ; vitesse, distance et durée (avec conversion de durées) ; débit.

**Figures :** `geom` pour le graphique de proportionnalité (droite passant par l'origine) ; `bars`.

**Générateurs :** quatrième proportionnelle ; pourcentage ; vitesse et durée en heures et minutes ; grandeur composée.

**Ultra :** proportionnalité et alignement des points avec l'origine.

### Ch. 14 — Statistiques (D2)

**Notions :**
1. Effectifs et fréquences ;
2. Moyenne pondérée ;
3. Médiane, avec les effectifs cumulés ;
4. Étendue ⚠️ (vérifier la répartition).

**Compétences :** calculer et interpréter, choisir l'indicateur.

**Exercices :** tableau d'effectifs ; moyenne pondérée ; médiane d'une série paire ou impaire ; comparer deux séries ; trouver une valeur manquante pour une moyenne donnée.

**Figures :** `bars`, `pie`.

**Générateurs :** moyenne pondérée ; médiane ; effectifs cumulés, avec des séries générées et vérifiées.

**Points à corriger par rapport au manuel :** à la p. 161, 59/25 vaut 2,36 et non 2,56. La médiane se définit avec **la moitié** de l'effectif total.

### Ch. 15 — Probabilités (D3)

**Notions :**
1. Expérience, issue, événement ;
2. Équiprobabilité et calcul ;
3. Événement contraire ;
4. Fréquence et probabilité.

**Compétences :** calculer une probabilité, utiliser le contraire, interpréter une simulation.

**Exercices :** dé, urne, roue ; événement contraire ; comparaison de deux jeux ; fréquences observées.

**Figures :** `tree`, à une seule épreuve ou deux simples selon le programme ; `bars` pour les fréquences.

**Générateurs :** urne ou dé ; contraire ; comparaison de jeux. Les calculs sont faits en `Fraction`.

**Ultra :** pourquoi P(Ā) = 1 − P(A).

### Ch. 16 — Fonction ⚠️ (à confirmer avant toute rédaction)

Les sources consultées divergent : notion de fonction en 4e ou en 3e. Si les repères placent la notion en 3e, ce chapitre devient **« Dépendance entre grandeurs, formules et graphiques »**, ou il est supprimé, et la liste `planned_chapter_titles` sera ajustée.

## 4. Décisions attendues

1. Valider les points ⚠️ au regard du BO : Thalès (réciproque), rotation, sections, étendue, fonction.
2. Valider l'ordre des lots et le volume indicatif.
3. Dire si l'algorithmique (manuel A1) reste hors périmètre, comme pour les autres classes.
