"""Verrous de non-régression issus de deux missions successives :

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

Ces tests portent sur la CAUSE (répartition réelle par chapitre, cohérence
des chapter_id, absence de doublon/perte, non-régression du volume) plutôt
que sur un total exact, qui évoluera à chaque régénération volontaire du
pool généré (mais ne doit JAMAIS diminuer en dessous du plancher historique
verrouillé ci-dessous).
"""
import json
import unittest
from pathlib import Path

from curriculum_registry import CURRICULUM_REGISTRY

ROOT = Path(__file__).resolve().parent.parent.parent


def _load(path):
    if path is None or not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


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
    """Chaque exercice (banque curée + pool généré) doit porter un chapter_id
    non vide qui correspond à un chapitre réellement déclaré pour sa classe —
    jamais un identifiant orphelin qu'aucun cours ne référence."""

    def test_tous_les_chapter_id_correspondent_a_un_chapitre_declare(self):
        for class_level, profile in CURRICULUM_REGISTRY.items():
            known = _known_chapter_ids(profile)
            if not known:
                continue
            combined = _load(profile.exercise_bank) + _load(profile.generated_exercise_bank)
            with self.subTest(class_level=class_level):
                bad = sorted({e.get("chapter_id") for e in combined if e.get("chapter_id") not in known})
                self.assertEqual(bad, [], f"{class_level} : chapter_id orphelin(s) {bad}")

    def test_aucun_exercice_sans_chapter_id(self):
        for class_level, profile in CURRICULUM_REGISTRY.items():
            combined = _load(profile.exercise_bank) + _load(profile.generated_exercise_bank)
            with self.subTest(class_level=class_level):
                sans_chapitre = sum(1 for e in combined if not e.get("chapter_id"))
                self.assertEqual(sans_chapitre, 0)


class TestAucunDoublonNiPerte(unittest.TestCase):
    """Le rééquilibrage régénère exercises_generated_premiere.json (pool
    généré) mais ne doit jamais toucher exercises_bank_premiere.json (banque
    curée) : mêmes IDs curés qu'avant, aucune collision avec les IDs générés
    (offsets 900_000+, voir docstring des modules de exercise_generator/)."""

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


class TestRepartitionPremiereTousChapitres(unittest.TestCase):
    """Les 5 nouveaux générateurs (Chapitre_6 à 10) permettent désormais de
    rapprocher TOUS les chapitres de Première les uns des autres (avant ces
    générateurs, seuls Chapitre_1-5 pouvaient être rapprochés — voir
    l'ancienne version de ce test). Verrou large (ratio ≤ 3) : bien au-dessus
    de ce qui est réellement atteint (1,89 au moment d'écrire ce test), pour
    tolérer une marge si le pool est régénéré avec des paramètres légèrement
    différents, tout en interdisant un retour au ratio extrême (12,6) d'avant
    ces générateurs."""

    def test_ratio_max_min_reste_maitrise(self):
        profile = CURRICULUM_REGISTRY["premiere"]
        combined = _load(profile.exercise_bank) + _load(profile.generated_exercise_bank)
        counts = {}
        for ex in combined:
            ch = ex.get("chapter_id")
            if ch:
                counts[ch] = counts.get(ch, 0) + 1
        self.assertEqual(len(counts), 10)
        ratio = max(counts.values()) / min(counts.values())
        self.assertLessEqual(ratio, 3.0, f"Répartition par chapitre : {counts} (ratio {ratio:.2f})")

    def test_chaque_chapitre_a_desormais_au_moins_250_exercices(self):
        """Avant les 5 nouveaux générateurs, Chapitre_10 (Variables
        aléatoires) ne comptait que 45 exercices — c'est exactement ce que ce
        verrou empêche de se reproduire silencieusement."""
        profile = CURRICULUM_REGISTRY["premiere"]
        combined = _load(profile.exercise_bank) + _load(profile.generated_exercise_bank)
        counts = {}
        for ex in combined:
            ch = ex.get("chapter_id")
            if ch:
                counts[ch] = counts.get(ch, 0) + 1
        for ch, n in counts.items():
            with self.subTest(chapter=ch):
                self.assertGreaterEqual(n, 250, f"{ch} : seulement {n} exercices")


class TestAucuneRegressionDeVolumeParChapitre(unittest.TestCase):
    """Plancher historique VERROUILLÉ (état committé juste avant la mission
    "rééquilibrage additif", voir git show 5acb6cb:exercises_generated_premiere.json
    + exercises_bank_premiere.json) : aucun chapitre ne doit plus jamais
    repasser sous ces valeurs, quelle que soit une future régénération —
    exactement la garde-fou "TOTAL APRÈS >= TOTAL AVANT" exigée par la
    mission, mais vérifiée chapitre par chapitre plutôt que sur le seul
    total (un total global stable pourrait sinon masquer un chapitre vidé
    compensé par un autre gonflé)."""

    PLANCHER_HISTORIQUE = {
        "Chapitre_1": 425, "Chapitre_2": 281, "Chapitre_3": 567, "Chapitre_4": 146,
        "Chapitre_5": 423, "Chapitre_6": 136, "Chapitre_7": 75, "Chapitre_8": 56,
        "Chapitre_9": 63, "Chapitre_10": 45,
    }

    def test_aucun_chapitre_sous_son_plancher_historique(self):
        profile = CURRICULUM_REGISTRY["premiere"]
        combined = _load(profile.exercise_bank) + _load(profile.generated_exercise_bank)
        counts = {}
        for ex in combined:
            ch = ex.get("chapter_id")
            if ch:
                counts[ch] = counts.get(ch, 0) + 1
        for ch, plancher in self.PLANCHER_HISTORIQUE.items():
            with self.subTest(chapter=ch):
                self.assertGreaterEqual(counts.get(ch, 0), plancher,
                                         f"{ch} : {counts.get(ch, 0)} < plancher historique {plancher}")

    def test_total_premiere_jamais_sous_2217(self):
        profile = CURRICULUM_REGISTRY["premiere"]
        combined = _load(profile.exercise_bank) + _load(profile.generated_exercise_bank)
        self.assertGreaterEqual(len(combined), 2217)


class TestVolumeMinimumParClasse(unittest.TestCase):
    """Mission "rééquilibrage additif" : chaque classe doit servir au moins
    2000 exercices réellement disponibles (exercise_bank + generated_exercise_bank
    quand fusionné en service réel — voir _CLASS_LEVELS_WITHOUT_GENERATED_MERGE
    dans curriculum_stats.py pour le cas particulier de "seconde")."""

    def test_chaque_classe_atteint_2000_exercices_reellement_servis(self):
        import curriculum_stats
        curriculum_stats.clear_cache()
        for class_level in CURRICULUM_REGISTRY:
            with self.subTest(class_level=class_level):
                stats = curriculum_stats.compute_stats(class_level)
                self.assertGreaterEqual(stats["totalExercises"], 2000,
                                         f"{class_level} : seulement {stats['totalExercises']} exercices servis")


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
