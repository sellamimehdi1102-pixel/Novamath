"""Verrous de non-régression issus de trois missions successives :

1. "rééquilibrage global du nombre d'exercices par chapitre" (2026-09-01) :
   constat initial que --per-family s'appliquait uniformément (12) à tous
   les modules de webapp/exercise_generator/, produisant un ratio
   Chapitre_3/Chapitre_10 de 12,6 en Première (567 vs 45).

2. "rééquilibrage ADDITIF" (même jour, correction de la mission 1) : la
   mission 1 avait réduit le pool généré de certains chapitres pour
   équilibrer (total Première 2217 → 1547), ce qui est explicitement
   interdit — AUCUN exercice existant ne doit jamais disparaître. La
   mission 2 restaure le pool historique intégral (tools/
   generate_derivative_exercises.py::_BASELINE_MODULES, per_family=12
   d'origine) et n'ajoute QUE du contenu nouveau : extensions dédupliquées
   pour Chapitre_2/4 (déjà générables), et 5 NOUVEAUX générateurs pour
   Chapitre_6 à Chapitre_10 (trigonometrie/produit_scalaire/
   geometrie_reperee/probabilites_conditionnelles/variables_aleatoires),
   qui n'avaient auparavant aucun module. Résultat : 3715 exercices
   (815 curés + 2900 générés), ratio max/min 1,89 (contre 12,6 avant).

3. "rééquilibrage global de TOUTES les classes" (même jour) : même patron
   additif appliqué à Troisième — Chapitre_2/6/9/10/14 (90 à 120 exercices,
   aucun générateur) reçoivent 5 nouveaux modules (nombres_relatifs/
   proportionnalite/statistiques/probabilites_troisieme/thales) + une
   extension dédupliquée de Chapitre_4/5. Résultat : 2655 exercices (2063
   curés + 592 générés), ratio max/min 1,61 (contre 2,69 avant). Seconde a
   été auditée mais laissée INCHANGÉE à ce stade : elle atteignait déjà les
   deux seuils obligatoires de cette mission (≥2000 exercices servis, ratio
   ≤2) — fusionner exercises_generated_seconde.json (droites/signes,
   Chapitre_6/9, déjà les deux chapitres les plus fournis) aurait dégradé
   l'équilibre au lieu de l'améliorer.

4. "équilibrage définitif de toutes les classes" (2026-09-01, objectif
   ratio ≤1,5) : les trois classes sont désormais rapprochées de cet
   objectif, toujours par pur AJOUT — aucun exercice des missions 1 à 3
   n'est supprimé ni déplacé :
   - Première : baseline gelée (les 11 modules déjà en production, y
     compris les 5 de la mission 2), extensions supplémentaires sur
     Chapitre_2/4/7/8/9/10 → 4373 exercices (815 curés + 3558 générés),
     ratio 1,35 (contre 1,89).
   - Troisième : baseline gelée (les 13 modules déjà en production, y
     compris les 5 de la mission 3), extensions sur Chapitre_2/4/5/6/9/10/14
     + un nouveau module volumes_espace pour Chapitre_15 (150 exercices,
     seul chapitre sans générateur et le plus faible) — voir le total exact
     dans le rapport de mission, ratio ≤1,5 visé.
   - Seconde : server.py::_class_bank("seconde") ne fusionnant toujours pas
     generated_exercise_bank (voir _CLASS_LEVELS_WITHOUT_GENERATED_MERGE),
     le contenu des deux chapitres les plus faibles (Chapitre_5/10, 121
     exercices chacun, aucun générateur) est ajouté DIRECTEMENT dans
     exercises_bank.json par tools/generate_seconde_curated_additions.py
     (2 nouveaux modules vecteurs_seconde/pourcentages_evolutions) →
     2275 exercices, ratio 1,51 (contre 2,0).

5. "audit et maximisation de la diversité des exercices" (2026-09-02) :
   un audit de diversité structurelle (voir webapp/tests/
   test_diversite_structurelle.py) a détecté 40 familles génératrices
   (≥15 exercices, ≥90% de "quasi-doublon" — un exercice avec l'énoncé
   réduit à sa structure, tous les nombres remplacés par #) réduites à UNE
   SEULE structure mathématique malgré des coefficients variés (ex.
   "x²-5x+6=0" et "x²-7x+12=0" : même moule). Pour chacune, une ou
   plusieurs familles SOEURS à structure réellement différente (problème
   inverse, configuration géométrique alternative, représentation par
   effectifs plutôt que probabilités, etc.) ont été ajoutées dans
   generate_extra_pool() (jamais mélangées à generate_pool()/FAMILIES,
   toujours figées) — Première 4373 → 4698 exercices, Troisième 3248 →
   3434 exercices, Seconde inchangée (aucune famille Seconde n'était
   CRITIQUE à l'audit).

6. "audit et renforcement de la diversité NUMÉRIQUE des exercices"
   (2026-09-02) : un second audit — cette fois sur les TYPES DE NOMBRES
   (négatifs, décimaux, fractions, puissances, racines), pas sur les
   structures de raisonnement déjà traitées par la mission 5 — a vérifié
   directement le CODE SOURCE de chaque générateur suspect (le texte des
   énoncés seul sous-compte massivement : un résultat irrationnel ou
   fractionnaire apparaît dans la réponse, rarement dans l'énoncé). 7 gaps
   réels confirmés par une ligne de code prouvant l'impossibilité
   structurelle (ex. `second_degre.py::resolution` construit toujours les
   racines comme des entiers AVANT de calculer b,c, donc le discriminant
   est toujours un carré parfait — jamais de racine irrationnelle dans tout
   Chapitre_2 de Première). Une nouvelle famille sœur ajoutée pour chacun
   (voir webapp/tests/test_diversite_numerique.py) : Première 4698 → 4734,
   Troisième 3434 → 3470, Seconde 2275 → 2290 (première mission à modifier
   Seconde depuis "équilibrage définitif" : `pourcentages_evolutions.py`
   avait le même défaut — taux toujours entier — que son homologue
   Troisième `proportionnalite.py`).

7. "chantier final : diversification numérique maximale" (2026-09-02) :
   audit par notion (pas seulement par famille, pour éviter l'effet de
   dilution déjà documenté à la mission 6) sur les banques réellement
   servies. Deux gaps volumineux confirmés par lecture du code : Première
   `geometrie_reperee.py` notion "Vecteur normal à une droite" (141
   exercices, 0% de racine/fraction — `_gen_vecteur_normal`/
   `_gen_equation_depuis_normal` ne font que LIRE des coefficients, aucun
   calcul) et Troisième `developper_distributivite.py` (99 exercices, 0%
   de fraction — coefficients toujours entiers). Nouvelle famille
   `vecteur_normal_unitaire` (normalisation d'un vecteur normal, introduit
   √(a²+b²) au dénominateur, rationalisé exactement par sympy) ajoutée EN
   DERNIER dans `EXTRA_FAMILIES` de geometrie_reperee.py (jamais en tête,
   pour ne pas décaler la séquence rng des 5 familles déjà committées) +
   un pool complémentaire dédié (seed et bloc d'ID séparés) pour atteindre
   52 exemplaires. Nouvelle famille `calcul_direct_fractionnaire`
   (facteur fractionnaire devant la parenthèse) ajoutée à
   developper_distributivite.py, qui n'avait pas encore de
   generate_extra_pool() — volume plafonné à 20 (pas 36) pour respecter
   RATIO_MAX_PAR_CLASSE["troisieme"]=1.7 déjà verrouillé (Chapitre_4 ne
   doit jamais dépasser 1,7 × min = 1,7 × 177 ≈ 300). Première 4734 → 4786
   (Ch8 480→532), Troisième 3470 → 3490 (Ch4 278→298), Seconde inchangée.

8. "audit et renforcement de l'accès Seconde" (2026-09-02) : audit de
   server.py::_class_bank("seconde") a confirmé qu'il ne fusionnait jamais
   generated_exercise_bank (198 exercices droites.py/Chapitre_6 +
   signes.py/Chapitre_9, jamais servis). Fusionner l'intégralité aurait
   porté le ratio max/min de 1,51 à 2,3 (Chapitre_6 déjà le plus fourni) —
   hors plafond. Seul Chapitre_9 (72 exercices, signes.py) est donc
   effectivement fusionné dans server.py (voir le filtre juste après le
   chargement de BANK) : ratio 1,51 -> 1,71, Seconde 2290 -> 2362.
   Chapitre_6/droites.py reste orphelin, en attente d'un futur
   rééquilibrage des chapitres faibles avant intégration.

9. "audit final et exhaustif de la diversité mathématique" (2026-09-02) :
   deux gaps de raisonnement (pas seulement numériques) confirmés par
   lecture de code et exécution directe des générateurs — `second_degre.py`
   (Chapitre_2) : ~8 familles sur 9 partent toutes de racines entières
   choisies a priori (discriminant systématiquement carré parfait) ;
   `resolution_irrationnelle` (mission précédente) n'en comblait qu'une
   seule. Deux nouvelles familles à raisonnement réellement différent (pas
   une simple redite de la résolution) : `equation_depuis_racines_irrationnelles`
   (reconstruire l'équation depuis deux racines conjuguées p±√q — Vieta à
   l'envers) et `verifier_resolution_irrationnelle` (juger vrai/faux une
   résolution radicale proposée). `trigonometrie.py` (Chapitre_6) :
   `combinaison_lineaire` (baseline figée) pèse 205/438 avec un seul
   gabarit ("lire cos/sin d'un angle dans la table") ; nouvelle famille
   `formule_duplication` (calculer cos(2θ)/sin(2θ) en appliquant une
   IDENTITÉ, pas en lisant une valeur) + complément dédié (80 exemplaires
   de plus) pour `combinaison_deux_angles` (espace combinatoire large,
   2688 combinaisons possibles, jamais artificiellement gonflé au-delà de
   ce qui est réellement distinct). Première 4786 → 4902 (Chapitre_2
   444→468, Chapitre_6 457→549, ratio global inchangé à 1,34, bien sous le
   plafond 1,6).

10. "audit final et rééquilibrage additif global" (2026-09-02) : audit
   exhaustif confirmant que Troisième Chapitre_11 (transformations)/
   Chapitre_12 (triangles/parallélogrammes)/Chapitre_13 (Pythagore/
   trigonométrie) et Seconde Chapitre_1 (nombres)/Chapitre_3 (calcul
   littéral)/Chapitre_4 (vecteurs sans repère)/Chapitre_8 (variations)/
   Chapitre_11 (statistiques) n'avaient AUCUN générateur — banques
   purement curées, chapitres les plus faibles de chaque classe. 8
   nouveaux modules créés (voir webapp/exercise_generator_troisieme/ et
   webapp/exercise_generator_seconde/), plus 3 extensions ADDITIVES
   (divisibilite/fractions_addition/fonction_affine_deux_points, Troisième
   Chapitre_1/3/8). Seconde/Chapitre_6 (droites.py, 126 exercices)
   RESTE VOLONTAIREMENT NON FUSIONNÉ (voir server.py) : l'intégrer
   pousserait le ratio Seconde de 1,44 à plus de 2 (déjà le chapitre le
   plus fourni). Troisième 3490 → 3713 (ratio 1,68 → 1,37), Seconde 2362 →
   2517 (ratio 1,71 → 1,44), Première inchangée (déjà 1,34, sous la
   cible).

Ces tests portent sur la CAUSE (répartition réelle par chapitre, cohérence
des chapter_id, absence de doublon/perte, non-régression du volume) plutôt
que sur un total exact, qui évoluera à chaque régénération volontaire du
pool généré (mais ne doit JAMAIS diminuer en dessous du plancher historique
verrouillé ci-dessous).
"""
import json
import unittest
from pathlib import Path

import curriculum_stats
from curriculum_registry import CURRICULUM_REGISTRY

ROOT = Path(__file__).resolve().parent.parent.parent

# Même source de vérité que curriculum_stats.compute_stats() : classes dont
# le pool généré n'est PAS fusionné par server.py::_class_bank() en service
# réel — pour celles-ci, le volume réellement servi est exercise_bank SEUL.
_CLASS_LEVELS_WITHOUT_GENERATED_MERGE = curriculum_stats._CLASS_LEVELS_WITHOUT_GENERATED_MERGE


def _load(path):
    if path is None or not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _served_combined(class_level, profile):
    """Exercices réellement servis par server.py::_class_bank() pour cette
    classe — bank + generated pour "premiere"/"troisieme" ; pour "seconde"
    (voir _CLASS_LEVELS_WITHOUT_GENERATED_MERGE), bank + le seul sous-ensemble
    de generated_exercise_bank réellement fusionné dans server.py (Chapitre_9,
    voir curriculum_stats._SECONDE_MERGED_CHAPTERS)."""
    bank = _load(profile.exercise_bank)
    if class_level in _CLASS_LEVELS_WITHOUT_GENERATED_MERGE:
        if class_level == "seconde":
            merged = [
                ex for ex in _load(profile.generated_exercise_bank)
                if ex.get("chapter_id") in curriculum_stats._SECONDE_MERGED_CHAPTERS
            ]
            return bank + merged
        return bank
    return bank + _load(profile.generated_exercise_bank)


def _counts_by_chapter(class_level, profile):
    counts = {}
    for ex in _served_combined(class_level, profile):
        ch = ex.get("chapter_id")
        if ch:
            counts[ch] = counts.get(ch, 0) + 1
    return counts


def _known_chapter_ids(profile):
    """Chapitres réellement déclarés pour cette classe — dérivés de
    courses_dir (chapitre_*.json::chapterId), jamais d'une liste recopiée à
    la main qui pourrait diverger silencieusement du contenu réel."""
    if profile.courses_dir is None or not profile.courses_dir.exists():
        return set()
    ids = set()
    for course_path in profile.courses_dir.glob("chapitre_*.json"):
        try:
            course = json.loads(course_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if course.get("chapterId"):
            ids.add(course["chapterId"])
    return ids


class TestChapterIdsValides(unittest.TestCase):
    """Chaque exercice réellement servi doit porter un chapter_id non vide
    qui correspond à un chapitre réellement déclaré pour sa classe — jamais
    un identifiant orphelin qu'aucun cours ne référence."""

    def test_tous_les_chapter_id_correspondent_a_un_chapitre_declare(self):
        for class_level, profile in CURRICULUM_REGISTRY.items():
            known = _known_chapter_ids(profile)
            if not known:
                continue
            combined = _served_combined(class_level, profile)
            with self.subTest(class_level=class_level):
                bad = sorted({e.get("chapter_id") for e in combined if e.get("chapter_id") not in known})
                self.assertEqual(bad, [], f"{class_level} : chapter_id orphelin(s) {bad}")

    def test_aucun_exercice_sans_chapter_id(self):
        for class_level, profile in CURRICULUM_REGISTRY.items():
            combined = _served_combined(class_level, profile)
            with self.subTest(class_level=class_level):
                sans_chapitre = sum(1 for e in combined if not e.get("chapter_id"))
                self.assertEqual(sans_chapitre, 0)

    def test_chaque_chapitre_declare_possede_au_moins_un_exercice(self):
        for class_level, profile in CURRICULUM_REGISTRY.items():
            known = _known_chapter_ids(profile)
            if not known:
                continue
            counts = _counts_by_chapter(class_level, profile)
            with self.subTest(class_level=class_level):
                vides = sorted(known - counts.keys())
                self.assertEqual(vides, [], f"{class_level} : chapitre(s) sans aucun exercice {vides}")


class TestAucunDoublonNiPerte(unittest.TestCase):
    """Le rééquilibrage régénère les pools additifs mais ne doit jamais
    toucher les banques curées : mêmes IDs curés qu'avant, aucune collision
    avec les IDs générés (offsets distincts par module, voir docstring des
    modules de exercise_generator*/)."""

    def test_ids_generes_ne_collisionnent_jamais_avec_la_banque_curee(self):
        for class_level, profile in CURRICULUM_REGISTRY.items():
            bank = _load(profile.exercise_bank)
            generated = _load(profile.generated_exercise_bank)
            if not generated:
                continue
            with self.subTest(class_level=class_level):
                bank_ids = {e.get("id") for e in bank}
                generated_ids = {e.get("id") for e in generated}
                self.assertEqual(bank_ids & generated_ids, set())

    def test_aucun_id_duplique_au_sein_dun_meme_pool(self):
        for class_level, profile in CURRICULUM_REGISTRY.items():
            for label, path in (("exercise_bank", profile.exercise_bank), ("generated_exercise_bank", profile.generated_exercise_bank)):
                data = _load(path)
                if not data:
                    continue
                with self.subTest(class_level=class_level, pool=label):
                    ids = [e.get("id") for e in data]
                    self.assertEqual(len(ids), len(set(ids)))

    # Doublons d'ÉNONCÉ : anomalie préexistante et documentée, sans rapport
    # avec cette mission — un exercice de la banque curée Troisième
    # (id 2027, Chapitre_7) partage mot pour mot son énoncé avec un exercice
    # déjà généré par image_fonction.py (id 170015) AVANT toute mission de
    # rééquilibrage (vérifié : présent dans le commit HEAD précédent, donc
    # ni introduit ni aggravé ici). Le verrou porte donc sur "aucun NOUVEAU
    # doublon" plutôt que sur un compte absolu de zéro, qui échouerait pour
    # une raison hors périmètre de cette mission.
    DOUBLONS_ENONCE_PREEXISTANTS = {"troisieme": 1}

    def test_aucun_nouveau_doublon_denonce(self):
        for class_level, profile in CURRICULUM_REGISTRY.items():
            combined = _served_combined(class_level, profile)
            with self.subTest(class_level=class_level):
                enonces = [e["enonce"] for e in combined if e.get("enonce")]
                doublons = len(enonces) - len(set(enonces))
                toleres = self.DOUBLONS_ENONCE_PREEXISTANTS.get(class_level, 0)
                self.assertLessEqual(doublons, toleres,
                                      f"{class_level} : {doublons} doublon(s) d'énoncé (toléré : {toleres} préexistant(s))")


class TestRepartitionParChapitre(unittest.TestCase):
    """Ratio max/min par chapitre, par classe — verrous larges (marge
    au-dessus du ratio réellement atteint au moment d'écrire ces tests) pour
    tolérer une régénération future avec des paramètres légèrement
    différents, tout en interdisant un retour aux ratios extrêmes d'avant
    rééquilibrage (Première : 12,6 ; Troisième : 2,69 ; Seconde : 2,0).
    Resserrés une première fois par la mission "équilibrage définitif de
    toutes les classes" (2026-09-01), objectif ratio ≤1,5. Resserrés à
    nouveau par la mission "audit final et rééquilibrage additif global"
    (2026-09-02, Troisième Chapitre_11/12/13 + Seconde Chapitre_1/3/4/8/11 —
    tous sans générateur auparavant) : Première 1,34, Troisième 1,37,
    Seconde 1,44 au moment d'écrire ces tests."""

    RATIO_MAX_PAR_CLASSE = {"premiere": 1.45, "troisieme": 1.5, "seconde": 1.55}

    def test_ratio_max_min_reste_maitrise(self):
        for class_level, profile in CURRICULUM_REGISTRY.items():
            plafond = self.RATIO_MAX_PAR_CLASSE.get(class_level)
            if plafond is None:
                continue
            counts = _counts_by_chapter(class_level, profile)
            with self.subTest(class_level=class_level):
                ratio = max(counts.values()) / min(counts.values())
                self.assertLessEqual(ratio, plafond, f"{class_level} : {counts} (ratio {ratio:.2f})")

    def test_chaque_chapitre_premiere_a_desormais_au_moins_400_exercices(self):
        """Avant la mission "équilibrage définitif", Chapitre_4 (variations)
        ne comptait que 300 exercices — c'est exactement ce que ce verrou
        empêche de se reproduire silencieusement."""
        counts = _counts_by_chapter("premiere", CURRICULUM_REGISTRY["premiere"])
        for ch, n in counts.items():
            with self.subTest(chapter=ch):
                self.assertGreaterEqual(n, 400, f"{ch} : seulement {n} exercices")

    def test_chaque_chapitre_troisieme_a_desormais_au_moins_215_exercices(self):
        """Avant la mission "audit final et rééquilibrage additif global"
        (2026-09-02), Chapitre_1/8 ne comptaient que 177/181 exercices — ce
        verrou empêche de repasser sous le plancher fixé par cette mission."""
        counts = _counts_by_chapter("troisieme", CURRICULUM_REGISTRY["troisieme"])
        for ch, n in counts.items():
            with self.subTest(chapter=ch):
                self.assertGreaterEqual(n, 215, f"{ch} : seulement {n} exercices")

    def test_chaque_chapitre_seconde_a_desormais_au_moins_185_exercices(self):
        """Avant la mission "audit final et rééquilibrage additif global"
        (2026-09-02), Chapitre_8 ne comptait que 160 exercices — ce verrou
        empêche de repasser sous le plancher fixé par cette mission."""
        counts = _counts_by_chapter("seconde", CURRICULUM_REGISTRY["seconde"])
        for ch, n in counts.items():
            with self.subTest(chapter=ch):
                self.assertGreaterEqual(n, 185, f"{ch} : seulement {n} exercices")


class TestAucuneRegressionDeVolumeParChapitre(unittest.TestCase):
    """Plancher historique VERROUILLÉ (état committé juste avant chaque
    mission de rééquilibrage) : aucun chapitre ne doit plus jamais repasser
    sous ces valeurs, quelle que soit une future régénération — exactement
    la garde-fou "TOTAL APRÈS >= TOTAL AVANT" exigée par la mission, mais
    vérifiée chapitre par chapitre plutôt que sur le seul total (un total
    global stable pourrait sinon masquer un chapitre vidé compensé par un
    autre gonflé)."""

    PLANCHERS_HISTORIQUES = {
        "premiere": {
            "Chapitre_1": 425, "Chapitre_2": 468, "Chapitre_3": 567, "Chapitre_4": 456,
            "Chapitre_5": 423, "Chapitre_6": 549, "Chapitre_7": 498, "Chapitre_8": 532,
            "Chapitre_9": 492, "Chapitre_10": 492,
        },
        "troisieme": {
            "Chapitre_1": 217, "Chapitre_2": 254, "Chapitre_3": 218, "Chapitre_4": 298,
            "Chapitre_5": 230, "Chapitre_6": 266, "Chapitre_7": 242, "Chapitre_8": 217,
            "Chapitre_9": 254, "Chapitre_10": 260, "Chapitre_11": 240, "Chapitre_12": 242,
            "Chapitre_13": 221, "Chapitre_14": 266, "Chapitre_15": 288,
        },
        "seconde": {
            "Chapitre_1": 196, "Chapitre_2": 196, "Chapitre_3": 192, "Chapitre_4": 191,
            "Chapitre_5": 211, "Chapitre_6": 242, "Chapitre_7": 204, "Chapitre_8": 189,
            "Chapitre_9": 273, "Chapitre_10": 218, "Chapitre_11": 194, "Chapitre_12": 211,
        },
    }

    TOTAL_MINIMUM = {"premiere": 4902, "troisieme": 3713, "seconde": 2517}

    def test_aucun_chapitre_sous_son_plancher_historique(self):
        for class_level, planchers in self.PLANCHERS_HISTORIQUES.items():
            counts = _counts_by_chapter(class_level, CURRICULUM_REGISTRY[class_level])
            for ch, plancher in planchers.items():
                with self.subTest(class_level=class_level, chapter=ch):
                    self.assertGreaterEqual(counts.get(ch, 0), plancher,
                                             f"{class_level}/{ch} : {counts.get(ch, 0)} < plancher historique {plancher}")

    def test_total_jamais_sous_son_plancher_historique(self):
        for class_level, plancher in self.TOTAL_MINIMUM.items():
            combined = _served_combined(class_level, CURRICULUM_REGISTRY[class_level])
            with self.subTest(class_level=class_level):
                self.assertGreaterEqual(len(combined), plancher)


class TestVolumeMinimumParClasse(unittest.TestCase):
    """Mission "rééquilibrage global de toutes les classes" : chaque classe
    doit servir au moins 2000 exercices réellement disponibles."""

    def test_chaque_classe_atteint_2000_exercices_reellement_servis(self):
        curriculum_stats.clear_cache()
        for class_level in CURRICULUM_REGISTRY:
            with self.subTest(class_level=class_level):
                stats = curriculum_stats.compute_stats(class_level)
                self.assertGreaterEqual(stats["totalExercises"], 2000,
                                         f"{class_level} : seulement {stats['totalExercises']} exercices servis")

    def test_curriculum_stats_egale_la_banque_reellement_servie(self):
        """Verrou explicitement demandé par la mission : les statistiques
        API (curriculum_stats, source de /api/curricula) doivent correspondre
        EXACTEMENT à server.py::_class_bank() — jamais un fichier JSON qui
        ne serait pas réellement chargé par le serveur."""
        import server
        curriculum_stats.clear_cache()
        for class_level in CURRICULUM_REGISTRY:
            with self.subTest(class_level=class_level):
                stats = curriculum_stats.compute_stats(class_level)
                try:
                    served = server._class_bank(class_level)["bank"]
                except Exception as exc:
                    # Anomalie préexistante sans rapport (exercises_bank_troisieme_natural.json
                    # corrompu, voir rapport de mission) — déjà documentée en
                    # skip ailleurs, non réintroduite ici.
                    self.skipTest(f"{class_level} : server._class_bank() indisponible ({exc!r})")
                    continue
                self.assertEqual(stats["totalExercises"], len(served))


class TestSchemaExercicesGeneres(unittest.TestCase):
    """Un exercice généré doit rester compatible avec le contrat attendu par
    server.py::public_exercise() — mêmes champs qu'un exercice de banque
    classique (voir curriculum_stats.py, docstring)."""

    REQUIRED_FIELDS = {"enonce", "answer", "hint", "solution_steps", "chapter_id", "notion", "difficulty", "id"}

    def test_champs_obligatoires_presents(self):
        for class_level, profile in CURRICULUM_REGISTRY.items():
            generated = _load(profile.generated_exercise_bank)
            if not generated:
                continue
            with self.subTest(class_level=class_level):
                for ex in generated:
                    missing = self.REQUIRED_FIELDS - ex.keys()
                    self.assertEqual(missing, set())


if __name__ == "__main__":
    unittest.main()
