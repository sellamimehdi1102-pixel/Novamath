"""
Bibliothèque de gabarits pédagogiques (par catégorie de notion), utilisée par
`generate_cours_from_bank.py` (Première, source de vérité générée) et par
`enrich_cours_seconde.py` (Seconde, contenu déjà curaté à la main : ce module
ne fait qu'AJOUTER les nouveaux champs, jamais remplacer ce qui existe déjà).

Principe : aucun texte mathématique n'est inventé ici (aucune formule, aucun
résultat de calcul). Les gabarits ne fournissent que du texte *pédagogique
générique* — analogie, motivation, cadre de lecture — rattaché à une famille
de notions (ex. "toutes les notions de suites"), jamais à un exercice
particulier. Le contenu mathématique réel (définition, étapes, exemples)
continue de venir exclusivement de la banque d'exercices ou du cours existant.

Détection de catégorie : uniquement lexicale (mots-clés dans l'id/titre de la
notion), pas de classification statistique — reproductible et vérifiable à la
main.
"""
import re
import unicodedata


def fold(text):
    """Aplatit accents/casse — même convention que generate_cours_from_bank._slug."""
    folded = "".join(c for c in unicodedata.normalize("NFKD", text or "") if not unicodedata.combining(c))
    return folded.lower()


# Ordre = priorité (premier motif qui matche gagne) : les catégories les plus
# spécifiques sont placées avant les catégories génériques qui pourraient
# aussi matcher un mot commun.
_CATEGORY_RULES = (
    ("solides", r"cube|pave droit|cylindre|c[oô]ne|sphere|pyramide|prisme|volume d.un solide"),
    ("suites", r"suite|limite d.une suite|somme des termes|somme des n premiers|calcul de sommes"),
    ("second_degre", r"trinome|polynome|second degre|discriminant"),
    ("derivation", r"deriv|tangente|extremum"),
    ("exponentielle", r"exponentielle|nombre e\b"),
    ("trigonometrie", r"trigonometri|cosinus|sinus"),
    ("produit_scalaire", r"produit scalaire|orthogonal|vecteur normal|equation d.un cercle"),
    ("probabilites", r"probabilit|evenement|echantillon|simulation|fluctuation|arbres? ponderes?|independance"),
    ("variables_aleatoires", r"variables? aleatoires?|esperance|variance"),
    ("statistiques", r"moyenne|ecart.type|quartile|representation.*donnees|diagramme"),
    ("pourcentages", r"proportion|evolution|pourcentage"),
    ("vecteurs", r"vecteur|translation|colinearite"),
    ("repere", r"repere|coordonnee|milieu|norme"),
    ("droites", r"droite|systeme|coefficient directeur"),
    ("fonctions_generalites", r"fonction|courbe|parite|graphique"),
    ("variations", r"variation|croissant|decroissant|maximum|minimum"),
    ("signe", r"signe|tableau de signe|inequation"),
    ("calcul_litteral", r"distributivite|factoris|developp|identite remarquable|equations? produits?|equations? quotients?|fractions? de lettres?"),
    ("intervalles", r"intervalle|inegalite(?![ -]triangulaire)|comparaison|valeur absolue"),
    ("arithmetique", r"multiple|diviseur|nombre premier|pgcd"),
    ("racines", r"racine carree|racine"),
    ("ensembles_nombres", r"ensembles? de(s)? nombres?"),
    ("puissances", r"puissance"),
)


def detect_category(notion_id, title, tags=None):
    haystack = fold(f"{notion_id} {title} {' '.join(tags or [])}")
    for category, pattern in _CATEGORY_RULES:
        if re.search(pattern, haystack):
            return category
    return "generique"


# Chaque catégorie fournit :
# - "pourquoi"    : à quoi ça sert dans la vraie vie (utilisé dans l'intro).
# - "analogie"     : explication simple, avant la définition officielle.
# - "intuition"    : ce qu'il faut vraiment retenir, après la définition.
# - "concrets"     : exemples de la vie réelle où la notion apparaît.
# - "astuce"       : moyen mnémotechnique générique (utilisé seulement si la
#                     banque d'exercices n'en fournit aucun).
CONTENT = {
    "puissances": {
        "pourquoi": "compter très vite des quantités qui doublent ou qui se répètent (populations, calculs informatiques, intérêts composés) sans écrire une multiplication à rallonge",
        "analogie": (
            "Imagine que tu dois écrire « 2 fois 2 fois 2 fois 2 fois 2 ». C'est long et on risque de se "
            "tromper en comptant les « 2 ». Une puissance, c'est juste une écriture raccourcie pour dire "
            "« ce nombre, multiplié par lui-même, un certain nombre de fois »."
        ),
        "intuition": (
            "Une puissance n'est rien d'autre qu'une multiplication répétée écrite en abrégé. Le petit "
            "chiffre en haut (l'exposant) compte combien de fois on répète le nombre du bas (la base) dans "
            "la multiplication. Ne confonds jamais « multiplier par l'exposant » et « répéter la "
            "multiplication » : ce sont deux opérations complètement différentes."
        ),
        "concrets": [
            "le nombre d'octets en informatique (2, 4, 8, 16... des puissances de 2)",
            "la croissance d'une population de bactéries qui double régulièrement",
            "les intérêts composés d'une épargne bancaire",
        ],
        "astuce": "Pour ne jamais te tromper entre additionner et multiplier les exposants, teste toujours la règle sur un petit exemple simple (comme 2² × 2³) avant de l'appliquer à ton exercice.",
    },
    "racines": {
        "pourquoi": "retrouver la longueur du côté d'un carré quand on ne connaît que son aire, ou calculer une distance dans un repère",
        "analogie": (
            "Imagine un carré dont tu connais l'aire (par exemple 9 m²) mais pas la longueur du côté. La "
            "racine carrée est justement l'outil qui te permet de retrouver ce côté : c'est le nombre "
            "positif qui, multiplié par lui-même, redonne l'aire de départ."
        ),
        "intuition": (
            "La racine carrée « défait » ce que fait la mise au carré. Il ne faut jamais oublier qu'une "
            "racine carrée est toujours un nombre positif (ou nul) : $\\sqrt{9}$ vaut $3$, jamais $-3$, même "
            "si $(-3)^2$ vaut aussi $9$."
        ),
        "concrets": [
            "calculer le côté d'un terrain carré connaissant sa surface",
            "calculer une distance entre deux points dans un plan (GPS, cartographie)",
            "vérifier si un nombre est un carré parfait",
        ],
        "astuce": "Pour retenir qu'une racine carrée est toujours positive, imagine une longueur de côté de carré : une longueur ne peut jamais être négative.",
    },
    "arithmetique": {
        "pourquoi": "répartir équitablement des objets en groupes égaux, simplifier des fractions, ou organiser un emploi du temps qui se répète",
        "analogie": (
            "Imagine que tu dois répartir des bonbons en paquets identiques, sans qu'il en reste. Les "
            "multiples et les diviseurs servent exactement à ça : savoir quels nombres de paquets sont "
            "possibles, et quels nombres ne se divisent par rien d'autre qu'eux-mêmes (les nombres premiers)."
        ),
        "intuition": (
            "Un multiple d'un nombre, c'est ce nombre répété un certain nombre de fois. Un diviseur, c'est "
            "au contraire un nombre qui rentre exactement dans un autre, sans reste. Un nombre premier n'a "
            "que deux diviseurs : lui-même et 1 — ne le confonds pas avec un nombre qui a juste peu de "
            "diviseurs connus."
        ),
        "concrets": [
            "organiser des équipes de taille égale pour un tournoi",
            "simplifier une fraction au maximum",
            "la cryptographie (codes secrets) qui utilise les nombres premiers",
        ],
        "astuce": "Pour tester si un petit nombre est premier, essaie de le diviser seulement par 2, 3, 5, 7 : s'il ne se divise par aucun d'eux et qu'il est inférieur à leur carré, il est premier.",
    },
    "ensembles_nombres": {
        "pourquoi": "savoir de quel « type » de nombre on parle avant de résoudre un problème (un nombre de personnes ne peut pas être négatif ni décimal, par exemple)",
        "analogie": (
            "Imagine des boîtes emboîtées les unes dans les autres : la plus petite contient les nombres "
            "qui servent à compter, la suivante ajoute les nombres négatifs, une autre ajoute les fractions, "
            "et la plus grande contient tous les nombres qu'on utilise au lycée. Chaque nombre appartient à "
            "certaines boîtes selon ce qu'il est."
        ),
        "intuition": (
            "Ces ensembles sont emboîtés (N ⊂ Z ⊂ D ⊂ Q ⊂ R) : tout entier naturel est aussi un entier "
            "relatif, tout entier relatif est aussi un réel, etc. Ne confonds pas « appartenir à un "
            "ensemble » et « être égal à un ensemble » : un nombre appartient à plusieurs boîtes à la fois."
        ),
        "concrets": [
            "un nombre de personnes (toujours un entier naturel)",
            "une température (peut être un réel négatif)",
            "un prix affiché en supermarché (souvent un nombre décimal)",
        ],
        "astuce": "Pour retenir l'ordre des ensembles, pense à des poupées russes : N est la plus petite poupée, R est la plus grande, et chaque poupée est entièrement contenue dans la suivante.",
    },
    "intervalles": {
        "pourquoi": "décrire toutes les valeurs possibles d'une quantité (une température, une distance, une note) sans les lister une par une",
        "analogie": (
            "Imagine que tu donnes une plage horaire à un ami : « viens entre 14h et 16h ». Tu ne dis pas "
            "toutes les minutes possibles une par une, tu donnes juste les deux bornes. Un intervalle "
            "fonctionne exactement pareil avec des nombres."
        ),
        "intuition": (
            "Un crochet tourné vers l'intérieur ([ ou ]) signifie que la borne est incluse ; tourné vers "
            "l'extérieur (] ou [), elle est exclue. Ne confonds jamais une inégalité (une phrase mathématique "
            "vraie ou fausse) et un intervalle (l'ensemble des solutions de cette inégalité)."
        ),
        "concrets": [
            "une fourchette de prix acceptable pour un achat",
            "une plage de température de conservation d'un médicament",
            "les notes qui donnent une mention à un examen",
        ],
        "astuce": "Pour retenir le sens des crochets, imagine une porte : un crochet fermé « [ » est une porte qui laisse entrer la valeur, un crochet ouvert « ] » est une porte qui la bloque à l'extérieur.",
    },
    "calcul_litteral": {
        "pourquoi": "transformer une expression compliquée en une expression plus simple à calculer ou à résoudre, sans changer sa valeur",
        "analogie": (
            "Imagine que tu ranges une phrase trop longue en une phrase plus courte qui veut dire exactement "
            "la même chose. Développer et factoriser, c'est pareil : on réécrit une expression sous une "
            "autre forme, plus pratique selon ce qu'on veut en faire, sans jamais changer sa valeur."
        ),
        "intuition": (
            "Développer, c'est supprimer des parenthèses en distribuant une multiplication. Factoriser, "
            "c'est l'opération inverse : faire réapparaître des parenthèses en mettant un facteur commun en "
            "évidence. Ne confonds pas les deux sens : on développe pour calculer, on factorise pour résoudre "
            "une équation produit nul."
        ),
        "concrets": [
            "calculer rapidement une aire décomposée en plusieurs rectangles",
            "simplifier une formule utilisée en physique ou en économie",
            "résoudre une équation en la ramenant à un produit de facteurs nuls",
        ],
        "astuce": "Pour ne pas oublier un terme en développant, imagine que chaque terme de la première parenthèse doit « serrer la main » à chaque terme de la deuxième parenthèse, un par un.",
    },
    "vecteurs": {
        "pourquoi": "décrire un déplacement (une direction, un sens et une longueur) sans dépendre du point de départ",
        "analogie": (
            "Imagine une flèche tracée sur une carte pour indiquer un déplacement : « avance de 3 cases à "
            "droite et 2 cases vers le haut ». Cette flèche a une direction, un sens et une longueur, mais "
            "elle reste la même flèche où qu'on la dessine sur la carte. C'est exactement ce qu'est un vecteur."
        ),
        "intuition": (
            "Un vecteur n'a pas de position fixe : deux flèches de même longueur, même direction et même "
            "sens représentent le même vecteur, même si elles sont dessinées à des endroits différents. Ne "
            "confonds jamais un vecteur (un déplacement) avec un point (une position)."
        ),
        "concrets": [
            "un déplacement GPS (direction et distance à parcourir)",
            "une force en physique (intensité et direction)",
            "un vent (vitesse et direction)",
        ],
        "astuce": "Pour retenir qu'un vecteur ne dépend pas de sa position, imagine que tu peux le faire glisser n'importe où sur une feuille tant que sa longueur et sa direction ne changent pas.",
    },
    "repere": {
        "pourquoi": "donner l'adresse exacte d'un point avec seulement deux nombres, comme une adresse GPS",
        "analogie": (
            "Imagine un jeu de bataille navale : chaque case du plateau est repérée par une lettre et un "
            "chiffre. Un repère mathématique fonctionne pareil, mais avec deux nombres (l'abscisse et "
            "l'ordonnée) qui donnent la position exacte d'un point."
        ),
        "intuition": (
            "Les coordonnées d'un point donnent sa position par rapport à une origine fixe : la première "
            "coordonnée (abscisse) se lit horizontalement, la seconde (ordonnée) se lit verticalement. Ne "
            "les inverse jamais : (2 ; 5) et (5 ; 2) ne désignent pas le même point."
        ),
        "concrets": [
            "les coordonnées GPS d'un lieu",
            "la position d'une pièce sur un échiquier",
            "un pixel sur un écran d'ordinateur",
        ],
        "astuce": "Pour ne jamais inverser abscisse et ordonnée, retiens l'ordre alphabétique : « a » d'abscisse vient avant « o » d'ordonnée, donc l'abscisse se lit en premier.",
    },
    "droites": {
        "pourquoi": "décrire tous les points alignés d'un seul coup, avec une seule équation, plutôt que de les citer un par un",
        "analogie": (
            "Imagine une règle posée sur une feuille quadrillée : tous les points qu'elle touche suivent "
            "une même règle de construction. Cette règle, c'est justement l'équation de la droite : une "
            "formule qui dit exactement quels points sont alignés sur cette règle."
        ),
        "intuition": (
            "Le coefficient directeur mesure à quelle vitesse la droite monte ou descend ; l'ordonnée à "
            "l'origine indique où elle coupe l'axe vertical. Ne confonds jamais ces deux nombres : le "
            "premier change la pente, le second ne fait que décaler la droite vers le haut ou le bas."
        ),
        "concrets": [
            "la trajectoire d'un objet qui se déplace à vitesse constante",
            "l'évolution linéaire d'un prix ou d'un forfait téléphonique",
            "une piste de ski en pente régulière",
        ],
        "astuce": "Pour retenir le rôle du coefficient directeur, imagine une personne qui monte une colline : plus le nombre est grand, plus la colline est raide.",
    },
    "fonctions_generalites": {
        "pourquoi": "décrire comment une quantité dépend d'une autre (un prix qui dépend d'une quantité, une distance qui dépend d'un temps)",
        "analogie": (
            "Imagine une machine : tu rentres un nombre, elle applique toujours la même règle, et elle "
            "ressort un seul résultat. C'est exactement ce qu'est une fonction : à chaque nombre de départ, "
            "elle associe un unique nombre d'arrivée."
        ),
        "intuition": (
            "Une fonction associe à chaque valeur de départ (l'antécédent) une unique valeur d'arrivée "
            "(l'image). Ne confonds jamais ces deux mots : l'image est ce qu'on obtient en sortie, "
            "l'antécédent est ce qu'on a mis en entrée."
        ),
        "concrets": [
            "le prix d'un trajet en taxi selon la distance parcourue",
            "la température d'un four selon le temps de chauffe",
            "le salaire selon le nombre d'heures travaillées",
        ],
        "astuce": "Pour ne pas confondre image et antécédent, retiens que l'image est toujours ce qui sort de la machine, l'antécédent ce qu'on y met.",
    },
    "variations": {
        "pourquoi": "savoir si une quantité augmente ou diminue, par exemple pour trouver le meilleur ou le pire moment d'une évolution",
        "analogie": (
            "Imagine que tu marches le long de la courbe d'une fonction, de gauche à droite, comme sur un "
            "chemin de randonnée. Si tu montes, la fonction est croissante ; si tu descends, elle est "
            "décroissante."
        ),
        "intuition": (
            "Une fonction est croissante sur un intervalle si, à chaque fois qu'on avance vers la droite, "
            "les valeurs augmentent. Elle est décroissante si elles diminuent. Ne confonds pas la forme de "
            "la courbe (qui peut être arrondie) avec son sens de variation (qui ne parle que de montée ou "
            "descente)."
        ),
        "concrets": [
            "l'évolution de la température au fil d'une journée",
            "l'évolution d'un cours de bourse",
            "la vitesse d'un objet qui accélère puis ralentit",
        ],
        "astuce": "Pour retenir qu'une fonction croissante « monte », imagine une personne qui monte une colline en avançant vers la droite.",
    },
    "signe": {
        "pourquoi": "savoir sur quel intervalle une expression est positive ou négative, ce qui est indispensable pour résoudre une inéquation",
        "analogie": (
            "Imagine un thermomètre géant posé le long de l'axe des nombres : à certains endroits il "
            "affiche un nombre positif, à d'autres un nombre négatif, et il passe par zéro à des endroits "
            "précis. Étudier le signe, c'est justement repérer ces zones."
        ),
        "intuition": (
            "Le signe d'une expression change en général uniquement là où elle s'annule. Un tableau de "
            "signes résume cette information sur toute la droite des nombres. Ne confonds jamais « résoudre "
            "une équation » (trouver où l'expression vaut zéro) et « résoudre une inéquation » (trouver où "
            "elle est positive ou négative)."
        ),
        "concrets": [
            "déterminer quand un bénéfice devient positif dans une entreprise",
            "déterminer à partir de quand une quantité dépasse un seuil autorisé",
            "résoudre une inéquation de physique (vitesse positive, distance positive...)",
        ],
        "astuce": "Pour construire un tableau de signes sans erreur, place d'abord tous les nombres qui annulent l'expression, dans l'ordre croissant, avant de chercher le signe entre eux.",
    },
    "statistiques": {
        "pourquoi": "résumer une grande série de données en quelques nombres faciles à comparer",
        "analogie": (
            "Imagine les notes de toute une classe à un contrôle. Plutôt que de lire toutes les notes une "
            "par une, la moyenne et l'écart-type te donnent en deux nombres une idée du niveau général et "
            "de la dispersion des résultats."
        ),
        "intuition": (
            "La moyenne résume la « valeur centrale » d'une série. L'écart-type mesure à quel point les "
            "valeurs sont dispersées autour de cette moyenne. Deux séries peuvent avoir la même moyenne mais "
            "un écart-type très différent — ne confonds jamais ces deux informations."
        ),
        "concrets": [
            "comparer les notes de deux classes différentes",
            "analyser la régularité des performances d'un sportif",
            "étudier la dispersion des salaires dans une entreprise",
        ],
        "astuce": "Pour retenir le rôle de l'écart-type, pense à des joueurs de fléchettes : deux joueurs peuvent viser le même centre en moyenne, mais l'un est beaucoup plus régulier que l'autre.",
    },
    "pourcentages": {
        "pourquoi": "comparer des évolutions de tailles différentes sur une base commune (100), par exemple des augmentations de prix ou de population",
        "analogie": (
            "Imagine que tu compares l'augmentation du prix d'un stylo (qui passe de 1€ à 1,10€) et celle "
            "d'une voiture (qui passe de 10 000€ à 10 500€). En euros, la voiture augmente beaucoup plus. En "
            "pourcentage, c'est le stylo qui augmente le plus. Le pourcentage sert justement à comparer des "
            "évolutions sur une base commune, indépendamment de la taille de départ."
        ),
        "intuition": (
            "Une évolution en pourcentage se calcule toujours par rapport à la valeur de départ, jamais par "
            "rapport à la valeur d'arrivée. Enchaîner plusieurs évolutions successives ne s'additionne pas "
            "directement : il faut multiplier les coefficients multiplicateurs."
        ),
        "concrets": [
            "les soldes et remises en magasin",
            "l'évolution démographique d'une ville",
            "l'inflation des prix d'une année sur l'autre",
        ],
        "astuce": "Pour ne jamais additionner deux pourcentages d'évolutions successives par erreur, retiens qu'on multiplie toujours les coefficients multiplicateurs entre eux.",
    },
    "suites": {
        "pourquoi": "décrire une liste de nombres qui se construisent les uns à partir des autres, par exemple une épargne qui augmente chaque mois",
        "analogie": (
            "Imagine une file de dominos numérotés : chaque nombre de la liste dépend du précédent, selon "
            "une règle fixe qui ne change jamais. C'est exactement ce qu'est une suite : une liste de "
            "nombres construits les uns après les autres."
        ),
        "intuition": (
            "Une suite associe à chaque rang (0, 1, 2, 3...) un nombre bien précis. Ne confonds jamais le "
            "rang (la position dans la liste, un entier) et le terme (la valeur à ce rang, qui peut être "
            "n'importe quel nombre)."
        ),
        "concrets": [
            "l'évolution d'une épargne bancaire mois après mois",
            "la croissance d'une population d'animaux d'année en année",
            "le nombre de bactéries qui double régulièrement",
        ],
        "astuce": "Pour ne pas confondre rang et terme, retiens que le rang est le numéro de la case dans la file, le terme est ce qu'il y a écrit dessus.",
    },
    "second_degre": {
        "pourquoi": "résoudre des problèmes où une quantité dépend du carré d'une autre, comme une trajectoire ou une aire à optimiser",
        "analogie": (
            "Imagine que tu lances une balle en l'air : sa hauteur suit une courbe qui monte puis "
            "redescend, en forme de dôme ou de vallée. Cette forme est celle d'une fonction du second degré, "
            "et le trinôme est justement l'expression qui la décrit."
        ),
        "intuition": (
            "Le signe du discriminant indique combien de solutions possède l'équation : deux, une seule, "
            "ou aucune. Ne confonds jamais le sommet de la parabole (le point le plus haut ou le plus bas) "
            "avec les racines de l'équation (les points où la courbe touche l'axe horizontal)."
        ),
        "concrets": [
            "la trajectoire d'un objet en chute libre ou d'un ballon",
            "optimiser une aire (par exemple maximiser la surface d'un enclos avec une longueur de clôture fixée)",
            "calculer un bénéfice maximal en économie",
        ],
        "astuce": "Pour retenir la forme d'une parabole, imagine un pont suspendu (vers le bas) ou un dôme (vers le haut) selon le signe du coefficient devant le carré.",
    },
    "derivation": {
        "pourquoi": "mesurer la vitesse à laquelle une quantité change à un instant précis, par exemple la vitesse instantanée d'une voiture",
        "analogie": (
            "Imagine que tu regardes le compteur de vitesse d'une voiture : il ne donne pas la vitesse "
            "moyenne du trajet, mais la vitesse exacte à cet instant précis. La dérivée fait exactement ça "
            "pour une fonction : elle donne sa vitesse de variation à un instant donné."
        ),
        "intuition": (
            "Le nombre dérivé en un point donne la pente de la tangente à la courbe en ce point. Un "
            "extremum local (maximum ou minimum) correspond toujours à un endroit où la dérivée s'annule et "
            "change de signe — ne confonds pas « dérivée nulle » et « extremum » : les deux vont ensemble, "
            "mais il faut aussi vérifier le changement de signe."
        ),
        "concrets": [
            "la vitesse instantanée affichée par le compteur d'une voiture",
            "trouver le moment où un bénéfice est maximal",
            "trouver la dimension qui minimise la matière utilisée pour fabriquer un objet",
        ],
        "astuce": "Pour retenir ce qu'est une dérivée, pense au compteur de vitesse : ce n'est jamais une moyenne, toujours une valeur instantanée.",
    },
    "exponentielle": {
        "pourquoi": "décrire une évolution qui s'accélère (ou ralentit) de plus en plus vite, comme une épidémie ou une population qui explose",
        "analogie": (
            "Imagine une rumeur : au début elle se propage lentement, puis de plus en plus vite car chaque "
            "personne informée en informe d'autres à son tour. La fonction exponentielle décrit exactement "
            "ce type de croissance qui s'emballe."
        ),
        "intuition": (
            "La fonction exponentielle est la seule fonction (à une constante près) qui est sa propre "
            "dérivée : sa vitesse de croissance à un instant donné est proportionnelle à sa propre valeur à "
            "cet instant. Ne la confonds pas avec une fonction du second degré : la croissance exponentielle "
            "finit toujours par dépasser n'importe quelle croissance polynomiale."
        ),
        "concrets": [
            "la propagation d'une épidémie ou d'une rumeur",
            "la croissance d'un capital avec intérêts composés",
            "la décroissance radioactive d'un élément chimique",
        ],
        "astuce": "Pour retenir que la croissance exponentielle « s'emballe », imagine une boule de neige qui roule et grossit de plus en plus vite en dévalant une pente.",
    },
    "trigonometrie": {
        "pourquoi": "repérer un point sur un cercle (donc un angle) et faire le lien entre angles et coordonnées",
        "analogie": (
            "Imagine une aiguille de montre qui tourne autour du centre d'une horloge : sa position à "
            "chaque instant peut être décrite par l'angle qu'elle a parcouru. Le cercle trigonométrique "
            "fonctionne pareil, mais avec des angles mesurés en radians."
        ),
        "intuition": (
            "Sur le cercle trigonométrique de rayon 1, l'abscisse d'un point correspond au cosinus de "
            "l'angle, l'ordonnée correspond au sinus. Ne les inverse jamais : cosinus = abscisse (horizontal), "
            "sinus = ordonnée (vertical)."
        ),
        "concrets": [
            "la position d'une aiguille d'horloge ou d'une roue qui tourne",
            "les ondes sonores et lumineuses (mouvements périodiques)",
            "la navigation et le repérage d'un angle de direction",
        ],
        "astuce": "Pour ne pas inverser cosinus et sinus, retiens que « cosinus » commence comme « côté horizontal » (l'abscisse), et sinus reste donc pour la verticale.",
    },
    "produit_scalaire": {
        "pourquoi": "mesurer si deux directions sont perpendiculaires, ou calculer un angle entre deux vecteurs, ce qui sert en géométrie et en physique",
        "analogie": (
            "Imagine deux personnes qui tirent chacune sur une corde dans une direction différente : le "
            "produit scalaire mesure à quel point leurs efforts « vont dans le même sens ». S'il vaut zéro, "
            "les deux directions sont perpendiculaires."
        ),
        "intuition": (
            "Le produit scalaire de deux vecteurs vaut zéro si et seulement si ces vecteurs sont "
            "orthogonaux (perpendiculaires). Ne confonds jamais le produit scalaire (un nombre) avec un "
            "vecteur : le résultat d'un produit scalaire n'est jamais une flèche, toujours un nombre."
        ),
        "concrets": [
            "vérifier qu'un mur est perpendiculaire à un autre en architecture",
            "calculer le travail d'une force en physique",
            "détecter un angle droit dans un plan sans rapporteur",
        ],
        "astuce": "Pour retenir que le produit scalaire donne un nombre et non un vecteur, pense au mot « scalaire » : il vient de « échelle », donc un simple nombre sur une échelle.",
    },
    "probabilites": {
        "pourquoi": "estimer les chances qu'un événement se produise avant qu'il n'arrive, par exemple au jeu, en météo ou en médecine",
        "analogie": (
            "Imagine que tu lances un dé : tu ne sais pas à l'avance quel numéro va sortir, mais tu sais "
            "que chaque face a la même chance de sortir. La probabilité, c'est justement ce qui mesure cette "
            "chance, entre 0 (impossible) et 1 (certain)."
        ),
        "intuition": (
            "Une probabilité est toujours un nombre compris entre 0 et 1 (ou entre 0 % et 100 %). Ne "
            "confonds jamais un événement (une situation possible, comme « obtenir un nombre pair ») avec sa "
            "probabilité (le nombre qui mesure sa chance de se réaliser)."
        ),
        "concrets": [
            "les jeux de dés, de cartes ou de pile ou face",
            "les prévisions météorologiques (chance de pluie)",
            "un test médical (probabilité d'être malade selon le résultat)",
        ],
        "astuce": "Pour vérifier un calcul de probabilité, rappelle-toi que la somme des probabilités de tous les résultats possibles doit toujours faire exactement 1.",
    },
    "variables_aleatoires": {
        "pourquoi": "associer un nombre (souvent un gain ou une durée) à chaque résultat possible d'une expérience aléatoire, pour en calculer une moyenne théorique",
        "analogie": (
            "Imagine un jeu où chaque résultat du dé rapporte un certain nombre de points. La variable "
            "aléatoire, c'est justement cette règle qui transforme chaque résultat du hasard en un nombre "
            "précis (les points gagnés)."
        ),
        "intuition": (
            "L'espérance est la moyenne des valeurs possibles, pondérée par leur probabilité : c'est ce "
            "qu'on peut espérer gagner « en moyenne » si on répète l'expérience un grand nombre de fois. "
            "Ne confonds pas l'espérance (une moyenne théorique) avec un résultat réellement observé."
        ),
        "concrets": [
            "le gain moyen espéré à un jeu de hasard",
            "la durée de vie moyenne attendue d'un appareil",
            "le nombre moyen de clients attendus dans une file d'attente",
        ],
        "astuce": "Pour retenir ce qu'est l'espérance, imagine que tu joues au même jeu des milliers de fois : l'espérance est le gain moyen que tu observerais sur le long terme.",
    },
    "solides": {
        "pourquoi": "calculer le volume ou la surface d'un objet réel à trois dimensions (un emballage, une pièce, un réservoir)",
        "analogie": (
            "Imagine que tu déplies un objet en carton pour voir toutes ses faces à plat : un solide, c'est "
            "justement une forme à trois dimensions dont on peut calculer combien de matière il contient "
            "(le volume) ou combien de carton il faudrait pour le fabriquer (la surface)."
        ),
        "intuition": (
            "Chaque solide a une formule de volume différente selon sa forme. Ne confonds jamais l'aire "
            "d'une face (une surface, en unités carrées) et le volume du solide entier (en unités cubes)."
        ),
        "concrets": [
            "calculer le volume d'un emballage ou d'un réservoir",
            "calculer la quantité de peinture nécessaire pour une surface",
            "estimer la quantité d'eau que peut contenir une piscine",
        ],
        "astuce": "Pour ne pas confondre aire et volume, retiens que l'aire se mesure en cm² (une surface plate), le volume en cm³ (un espace en trois dimensions).",
    },
    "generique": {
        "pourquoi": "résoudre des problèmes concrets qui reviennent souvent, en mathématiques comme dans la vie de tous les jours",
        "analogie": (
            "Imagine que cette notion est un nouvel outil dans ta boîte à outils mathématique : une fois "
            "que tu sais quand et comment l'utiliser, elle te fait gagner beaucoup de temps sur des "
            "problèmes qui, sans elle, seraient très longs à résoudre."
        ),
        "intuition": (
            "Avant d'appliquer une règle, prends toujours le temps de bien identifier ce que l'énoncé te "
            "donne. La plupart des erreurs viennent d'une règle appliquée trop vite, sans avoir vérifié "
            "qu'elle s'applique bien à la situation."
        ),
        "concrets": [
            "de nombreux problèmes de la vie courante qui se ramènent à ce type de calcul",
        ],
        "astuce": "Pour bien retenir une méthode, refais-la sur un exemple très simple avant de l'appliquer à un exercice plus compliqué.",
    },
}


_STEP_PREFIX = re.compile(r"^\s*[ÉE]tape\s*\d+\s*:?\s*", re.IGNORECASE)
_CONNECTORS_FIRST = "Nous commençons par regarder ce que l'énoncé nous donne : "
_CONNECTORS_MID = "Nous poursuivons le calcul : "
_CONNECTORS_LAST = "Nous arrivons ainsi au résultat : "


def humanize_steps(steps):
    """Retire le préfixe mécanique « Étape N : » (présent tel quel dans la
    banque d'exercices) et le remplace par une phrase de professeur qui
    dépend seulement de la position de l'étape (début / milieu / fin) —
    aucune réécriture du contenu mathématique lui-même, qui reste celui,
    réel, de la banque d'exercices."""
    cleaned = [_STEP_PREFIX.sub("", s).strip() for s in steps]
    result = []
    for i, text in enumerate(cleaned):
        if i == 0:
            connector = _CONNECTORS_FIRST
        elif i == len(cleaned) - 1 and len(cleaned) > 1:
            connector = _CONNECTORS_LAST
        else:
            connector = _CONNECTORS_MID
        # Si le texte a déjà été humanisé par ailleurs (pas de préfixe
        # mécanique détecté au départ), on évite de plaquer un connecteur
        # redondant devant une phrase qui commence déjà par un connecteur.
        if text == steps[i].strip():
            result.append(text)
        else:
            result.append(connector + text[0].lower() + text[1:] if text else connector.rstrip(" :"))
    return result


def build_intro(notion_label, category):
    info = CONTENT.get(category, CONTENT["generique"])
    return (
        f"Aujourd'hui, nous allons apprendre : {notion_label.lower()}.\n\n"
        f"Cette notion sert à {info['pourquoi']}.\n\n"
        f"Tout au long de cette leçon, nous allons apprendre à l'utiliser pas à pas, avec des exemples "
        f"expliqués en détail."
    )


def build_explication_simple(category):
    return CONTENT.get(category, CONTENT["generique"])["analogie"]


def build_intuition(category):
    return CONTENT.get(category, CONTENT["generique"])["intuition"]


def build_exemples_concrets(category):
    return list(CONTENT.get(category, CONTENT["generique"])["concrets"])


def build_astuce_fallback(category):
    return CONTENT.get(category, CONTENT["generique"])["astuce"]
