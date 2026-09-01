"""Verrous de non-régression issus de la mission "rééquilibrage global du
nombre d'exercices par chapitre" (2026-09-01).

Constat de départ (audité, pas supposé) : en Première, --per-family
s'appliquait uniformément (12) à tous les modules de
webapp/exercise_generator/, sans tenir compte du nombre de familles par
module ni du contenu déjà présent dans exercises_bank_premiere.json — d'où
un ratio Chapitre_3/Chapitre_10 de 12,6 (567 vs 45). tools/
generate_derivative_exercises.py a été recalibré (MODULES porte désormais un
per_family propre à chaque module) pour que Chapitre_1 à Chapitre_5 (les
seuls chapitres avec un générateur symbolique) convergent vers un volume
proche les uns des autres. Chapitre_6 à Chapitre_10 n'ont AUCUN générateur :
leur volume reste plafonné à exercises_bank_premiere.json (banque curée,
jamais modifiée par cette mission) — documenté comme limite architecturale,
pas comme un oubli.

Ces tests portent sur la CAUSE (répartition réelle par chapitre, cohérence
des chapter_id, absence de doublon/perte) plutôt que sur un total exact, qui
évoluera à chaque régénération volontaire du pool généré.
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


class TestRepartitionPremiereChapitresGenerables(unittest.TestCase):
    """Chapitre_1 à Chapitre_5 (Première) sont les seuls dotés d'un générateur
    symbolique (webapp/exercise_generator/) — ce sont donc les seuls que
    cette mission peut réellement rapprocher les uns des autres sans toucher
    à la banque curée ni fabriquer de contenu hors sujet. Avant recalibrage :
    425/281/567/146/423 (ratio max/min 3,9 rien qu'entre eux). Verrou : ne
    doit plus jamais s'écarter de plus de ±25 % de leur propre moyenne."""

    GENERABLE_CHAPTERS = [f"Chapitre_{i}" for i in range(1, 6)]

    def test_chapitres_1_a_5_restent_proches_de_leur_moyenne(self):
        profile = CURRICULUM_REGISTRY["premiere"]
        combined = _load(profile.exercise_bank) + _load(profile.generated_exercise_bank)
        counts = {}
        for ch in self.GENERABLE_CHAPTERS:
            counts[ch] = sum(1 for e in combined if e.get("chapter_id") == ch)
        moyenne = sum(counts.values()) / len(counts)
        for ch, n in counts.items():
            with self.subTest(chapter=ch):
                ecart = abs(n - moyenne) / moyenne
                self.assertLessEqual(ecart, 0.25, f"{ch} : {n} exercices, écart de {ecart:.0%} à la moyenne ({moyenne:.0f})")


class TestChapitresSansGenerateurInchanges(unittest.TestCase):
    """Chapitre_6 à Chapitre_10 (Première) n'ont aucun module dans
    webapp/exercise_generator/ (voir registry.py) : cette mission ne peut
    donc PAS les enrichir sans fabriquer du contenu hors sujet ou en écrire
    de nouveaux générateurs (hors périmètre, documenté dans le rapport de
    mission). Verrou : leur volume doit rester EXACTEMENT celui de la banque
    curée (aucune perte, aucun ajout artificiel)."""

    UNGENERABLE_CHAPTERS = {"Chapitre_6": 136, "Chapitre_7": 75, "Chapitre_8": 56, "Chapitre_9": 63, "Chapitre_10": 45}

    def test_volume_inchange_pour_les_chapitres_sans_generateur(self):
        profile = CURRICULUM_REGISTRY["premiere"]
        bank = _load(profile.exercise_bank)
        generated = _load(profile.generated_exercise_bank)
        for ch, expected in self.UNGENERABLE_CHAPTERS.items():
            with self.subTest(chapter=ch):
                n_bank = sum(1 for e in bank if e.get("chapter_id") == ch)
                n_generated = sum(1 for e in generated if e.get("chapter_id") == ch)
                self.assertEqual(n_generated, 0, f"{ch} n'a aucun générateur déclaré : un exercice généré y apparaît de façon inattendue")
                self.assertEqual(n_bank, expected)


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
