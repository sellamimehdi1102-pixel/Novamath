"""Quatrième — contrôles communs à TOUS les chapitres (chantier « classe
complète », 2026-10-24). Le chapitre pilote garde en plus ses contrôles
spécifiques (figures à l'échelle, générateurs Pythagore) dans
test_quatrieme_pythagore.py.

Ajouter un chapitre (tools/quatrieme/chapitres.py) suffit à le soumettre à
tous les tests ci-dessous : structure du cours au schéma v2, répartition
Free/Premium/Ultra, hors-programme, figures, banque curée (contrôles
recalculés, volume, 4 niveaux, diversité, quiz), générateurs (vérificateur
indépendant sur 300 graines par famille, déterminisme du pool) et routes du
site en prévisualisation.
"""
import importlib.util
import json
import math
import re
import sys
import unittest
import urllib.parse
import uuid
from pathlib import Path
from unittest import mock

import curriculum_registry
import curriculum_stats
import validate_curriculum_content
from curriculum_registry import CURRICULUM_REGISTRY_ALL, served_registry
from exercise_generator import registry as generator_registry
from exercise_generator_quatrieme import pythagore

from tests.quatrieme_verificateurs import CHECKERS

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from quatrieme.chapitres import modules as chapter_modules  # noqa: E402

PROFILE = CURRICULUM_REGISTRY_ALL["quatrieme"]
COURSES = {
    int(p.stem.split("_")[1]): json.loads(p.read_text(encoding="utf-8"))
    for p in sorted(PROFILE.courses_dir.glob("chapitre_*.json"))
}
CURATED = json.loads(PROFILE.exercise_bank.read_text(encoding="utf-8"))
GENERATED = json.loads(PROFILE.generated_exercise_bank.read_text(encoding="utf-8"))
WRITTEN = chapter_modules()  # [(numéro, module cours, module banque)] hors pilote
GENERATOR_MODULES = [m for m in generator_registry._MODULES_BY_CLASS_LEVEL["quatrieme"] if m is not pythagore]
ALL_NOTIONS = {n["id"]: n for c in COURSES.values() for n in c["notions"]}
FIGURE_KINDS = validate_curriculum_content.supported_figure_kinds()

# Hors programme de 4e : sinus et tangente (3e), identités remarquables,
# inéquations, simplification de radicaux a√b.
_HORS_PROGRAMME_RE = re.compile(
    r"\\sin\b|\\tan\b|\bsinus\b|\btangente\b|trigonom|identit[ée]s? remarquables?|in[ée]quation|\d\s*\\sqrt",
    re.IGNORECASE,
)


def _load_tool(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _walk_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _walk_strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from _walk_strings(v)


def _squelette(enonce):
    s = re.sub(r"\d+(\{,\}\d+)?", "#", enonce)
    return re.sub(r"\b[A-Z]{1,4}\b", "P", s)


# ═════════════════════════════════════════════════════════════════════════
# Organisation de la classe
# ═════════════════════════════════════════════════════════════════════════
class TestOrganisation(unittest.TestCase):
    def test_chapitres_ecrits_et_chapitres_prevus(self):
        written = {number for number, _c, _b in WRITTEN}
        self.assertEqual(set(COURSES), written | {8})
        titles = {COURSES[n]["title"] for n in COURSES}
        self.assertEqual(titles & set(PROFILE.planned_chapter_titles), set())
        # 17 chapitres au total (voir QUATRIEME_SUIVI.md) : rédigés + prévus.
        self.assertEqual(len(COURSES) + len(PROFILE.planned_chapter_titles), 17)
        for number, course in COURSES.items():
            self.assertEqual(course["chapterId"], f"Chapitre_{number}")

    def test_validateur_sans_erreur_ni_avertissement(self):
        (report,) = validate_curriculum_content.validate(["quatrieme"])
        self.assertEqual(report.errors, [])
        self.assertEqual(report.warnings, [])
        self.assertEqual(report.chapters, len(COURSES))
        self.assertEqual(report.notions, len(ALL_NOTIONS))

    def test_classe_toujours_non_publiee(self):
        self.assertIs(PROFILE.published, False)
        self.assertNotIn("quatrieme", curriculum_registry.CURRICULUM_REGISTRY)


# ═════════════════════════════════════════════════════════════════════════
# Cours
# ═════════════════════════════════════════════════════════════════════════
class TestCours(unittest.TestCase):
    def test_identifiants_et_invariants_du_schema(self):
        ids = [n["id"] for c in COURSES.values() for n in c["notions"]]
        self.assertEqual(len(ids), len(set(ids)), "identifiant de notion dupliqué dans la classe")
        for n in ALL_NOTIONS.values():
            with self.subTest(notion=n["id"]):
                self.assertRegex(n["id"], r"^[a-z0-9]+(-[a-z0-9]+)*$")
                self.assertEqual(n["schemaVersion"], 2)
                self.assertEqual(n["topic_id"], n["id"])
                self.assertEqual(n["definitions"]["lycee"], n["definition"])
                self.assertEqual(n["methode"]["etapesParNiveau"]["normal"], n["methode"]["etapes"])
                self.assertEqual([e["description"] for e in n["erreursFrequentesDetail"]], n["erreursFrequentes"])
                for lie in n["notions_liees"]:
                    self.assertIn(lie, ALL_NOTIONS)

    def test_structure_pedagogique_complete(self):
        for n in ALL_NOTIONS.values():
            with self.subTest(notion=n["id"]):
                for field in ("intro", "pourquoi", "objectif", "definition", "astuce", "explicationSimple", "intuition"):
                    self.assertTrue(n.get(field), field)
                self.assertGreaterEqual(len(n["reglesImportantes"]), 3)
                self.assertGreaterEqual(len(n["erreursFrequentes"]), 3)
                self.assertGreaterEqual(len(n["methode"]["etapes"]), 3)
                self.assertTrue(n["methode"]["etapesParNiveau"]["debutant"] and n["methode"]["etapesParNiveau"]["rapide"])
                self.assertTrue(n["prerequis"] and n["objectifs_pedagogiques"] and n["questionsEclair"] and n["aRetenir"])
                self.assertTrue(n["formules"])

    def test_exemples_differencies_par_plan_et_apercus_honnetes(self):
        for n in ALL_NOTIONS.values():
            with self.subTest(notion=n["id"]):
                niveaux = [e["niveauAcces"] for e in n["exemples"]]
                self.assertGreaterEqual(niveaux.count("free"), 2)
                self.assertGreaterEqual(niveaux.count("premium"), 2)
                self.assertGreaterEqual(niveaux.count("ultra"), 1)
                self.assertEqual({a["niveau"] for a in n["apercus"]}, {"premium", "ultra"})
                for a in n["apercus"]:
                    texte = (a["titre"] + " " + a["description"]).lower()
                    if any(mot in texte for mot in ("démonstration", "preuve", "démontrer")):
                        self.assertIn("demonstration", n, a["id"])
                for e in n["exemples"]:
                    self.assertTrue(e["calcul"] and e["reponse"], e["id"])

    def test_aucun_contenu_hors_programme(self):
        for number, course in COURSES.items():
            for text in _walk_strings(course):
                with self.subTest(chapitre=number):
                    self.assertIsNone(_HORS_PROGRAMME_RE.search(text), text[:120])
        for ex in CURATED + GENERATED:
            for text in _walk_strings(ex):
                self.assertIsNone(_HORS_PROGRAMME_RE.search(text), f"{ex['id']} : {text[:120]}")

    def test_figures_valides_et_expliquees(self):
        for n in ALL_NOTIONS.values():
            fig = n["figure"]
            with self.subTest(notion=n["id"]):
                self.assertIn(fig.get("kind", "geom"), FIGURE_KINDS)
                self.assertTrue(fig.get("alt"))
                self.assertEqual(len(fig.get("steps", [])), 3)
                expl = fig.get("explication") or {}
                self.assertTrue(expl.get("resume") and expl.get("lecture") and expl.get("aRetenir"))
                if fig.get("kind", "geom") == "geom":
                    reveals = {el.get("reveal") for key in ("polygons", "segments", "texts", "arcs") for el in fig.get(key, [])}
                    self.assertLessEqual(reveals - {None}, {2, 3})
                    self.assertEqual(len(fig["viewBox"]), 4)
                    self.assertTrue(fig["viewBox"][2] > 0 and fig["viewBox"][3] > 0)
                    labels = {p["label"] for p in fig.get("points", []) if p.get("label")}
                    for key in ("segments", "vectors"):
                        for s in fig.get(key, []):
                            for end in (s["from"], s["to"]):
                                if isinstance(end, str):
                                    self.assertIn(end, labels, f"point {end!r} inconnu")

    def test_codages_d_angle_droit_reellement_droits(self):
        for n in ALL_NOTIONS.values():
            fig = n["figure"]
            for marker in (p for p in fig.get("polygons", []) if p.get("variant") == "marker"):
                pts = [(q["x"], q["y"]) if isinstance(q, dict) else next((p["x"], p["y"]) for p in fig["points"] if p["label"] == q)
                       for q in marker["points"]]
                v, a, c, b = pts
                ux, uy, wx, wy = a[0] - v[0], a[1] - v[1], b[0] - v[0], b[1] - v[1]
                with self.subTest(notion=n["id"]):
                    self.assertAlmostEqual(ux * wx + uy * wy, 0, places=3)
                    self.assertAlmostEqual(math.hypot(ux, uy), math.hypot(wx, wy), places=2)


# ═════════════════════════════════════════════════════════════════════════
# Banque curée
# ═════════════════════════════════════════════════════════════════════════
class TestBanque(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bank_tool = _load_tool("build_quatrieme_bank")

    def test_json_identique_aux_sources_et_controles_rejoues(self):
        self.assertEqual(CURATED, self.bank_tool.build_all())
        self.assertEqual(self.bank_tool.check_all_chapters(), [])

    def test_schema_et_identifiants(self):
        ids = [e["id"] for e in CURATED]
        self.assertEqual(len(ids), len(set(ids)))
        for e in CURATED:
            with self.subTest(id=e["id"]):
                self.assertEqual(set(e), {"id", "chapter_id", "notion", "difficulty", "enonce", "answer", "hint", "solution_steps"})
                number = int(e["chapter_id"].split("_")[1])
                self.assertTrue(40_000 + 1_000 * number < e["id"] < 40_000 + 1_000 * (number + 1))
                titles = [n["title"] for n in COURSES[number]["notions"]]
                self.assertIn(e["notion"], titles)

    def test_notions_alignees_cours_banque_generateurs(self):
        for number, cours, banque in WRITTEN:
            course = COURSES[number]
            with self.subTest(chapitre=number):
                self.assertEqual([n["id"] for n in course["notions"]], list(banque.NOTION_IDS))
                self.assertEqual([n["title"] for n in course["notions"]], list(banque.NOTIONS))
                for n in course["notions"]:
                    self.assertEqual(tuple(n["quizExerciseIds"]), tuple(banque.QUIZ[n["id"]]))
        for module in GENERATOR_MODULES:
            number = int(module.CHAPTER_ID.split("_")[1])
            titles = {n["title"] for n in COURSES[number]["notions"]}
            for family in module.FAMILIES:
                self.assertIn(family.notion, titles, family.id)

    def test_volume_niveaux_et_diversite_par_notion(self):
        for number, _cours, banque in WRITTEN:
            for title in banque.NOTIONS:
                exs = [e for e in CURATED if e["notion"] == title and e["chapter_id"] == f"Chapitre_{number}"]
                with self.subTest(chapitre=number, notion=title):
                    self.assertGreaterEqual(len(exs), 16)
                    self.assertEqual({e["difficulty"] for e in exs}, {1, 2, 3, 4})
                    enonces = [e["enonce"] for e in exs]
                    self.assertGreaterEqual(len({_squelette(x) for x in enonces}) / len(enonces), 0.85)

    def test_mini_quiz_sur_exercices_cures_faciles(self):
        by_id = {e["id"]: e for e in CURATED}
        for n in ALL_NOTIONS.values():
            quiz = n["quizExerciseIds"]
            with self.subTest(notion=n["id"]):
                self.assertEqual(len(set(quiz)), 3)
                for q in quiz:
                    self.assertIn(q, by_id)
                    self.assertEqual(by_id[q]["notion"], n["title"])
                    self.assertLessEqual(by_id[q]["difficulty"], 2)

    def test_aucun_identifiant_partage_avec_une_autre_classe(self):
        ours = {e["id"] for e in CURATED + GENERATED}
        self.assertEqual(len(ours), len(CURATED) + len(GENERATED))
        for class_level, profile in CURRICULUM_REGISTRY_ALL.items():
            if class_level == "quatrieme":
                continue
            for path in (profile.exercise_bank, profile.generated_exercise_bank):
                if path is None or not path.exists():
                    continue
                theirs = {e.get("id") for e in json.loads(path.read_text(encoding="utf-8"))}
                with self.subTest(fichier=path.name):
                    self.assertEqual(ours & theirs, set())


# ═════════════════════════════════════════════════════════════════════════
# Générateurs
# ═════════════════════════════════════════════════════════════════════════
class TestGenerateurs(unittest.TestCase):
    SEEDS = 300

    def test_chaque_famille_a_un_verificateur_independant(self):
        for module in GENERATOR_MODULES:
            for family in module.FAMILIES:
                self.assertIn(family.id, CHECKERS, f"{module.__name__}.{family.id}")

    def test_trois_cents_graines_par_famille(self):
        for module in GENERATOR_MODULES:
            for family in module.FAMILIES:
                enonces = set()
                for seed in range(self.SEEDS):
                    ex = module.generate_one(family.id, seed=seed)
                    enonces.add(ex["enonce"])
                    with self.subTest(famille=family.id, seed=seed):
                        self.assertEqual(ex["chapter_id"], module.CHAPTER_ID)
                        self.assertEqual(ex["notion"], family.notion)
                        self.assertEqual(ex["difficulty"], family.level)
                        self.assertNotIn(ex["hint"], ex["answer"])
                        for text in (ex["enonce"], ex["answer"], *ex["solution_steps"]):
                            self.assertEqual(text.count("$") % 2, 0, text)
                            self.assertEqual(text.count("{"), text.count("}"), text)
                        CHECKERS[family.id](ex)
                with self.subTest(famille=family.id, diversite=len(enonces)):
                    self.assertGreaterEqual(len(enonces), 40)

    def test_pool_servi_deterministe_et_identifiants_reserves(self):
        tool = _load_tool("generate_quatrieme_exercises")
        pool, problems = tool.build_pool()
        self.assertEqual(problems, [])
        self.assertEqual(pool, GENERATED)
        for module in GENERATOR_MODULES:
            ours = [e for e in GENERATED if e["chapter_id"] == module.CHAPTER_ID]
            with self.subTest(module=module.__name__):
                self.assertEqual({e["family"] for e in ours}, {f.id for f in module.FAMILIES})
                for e in ours:
                    self.assertTrue(module.GENERATED_ID_OFFSET <= e["id"] < module.GENERATED_ID_OFFSET + 10_000)
                    CHECKERS[e["family"]](e)


# ═════════════════════════════════════════════════════════════════════════
# Site (prévisualisation)
# ═════════════════════════════════════════════════════════════════════════
class TestSiteEnPrevisualisation(unittest.TestCase):
    def setUp(self):
        import server
        from chatbot import knowledge_engine
        from chatbot.services import search_service

        self._caches = (
            server._class_bank_cache, server._level_engine_cache,
            knowledge_engine._index_by_class, knowledge_engine._by_ids_by_class,
            search_service._exercise_index_by_class, search_service._exercise_by_id_by_class,
            search_service._exercise_index_by_chapter_by_class,
        )
        served = served_registry(CURRICULUM_REGISTRY_ALL, frozenset({"quatrieme"}))
        for patcher in (
            mock.patch.object(curriculum_registry, "CURRICULUM_REGISTRY", served),
            mock.patch.object(curriculum_stats, "CURRICULUM_REGISTRY", served),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.addCleanup(self._purge)
        self._purge()
        self.client = server.app.test_client()
        suffix = uuid.uuid4().hex[:12]
        resp = self.client.post("/api/auth/register", json={
            "email": f"q4p{suffix}@gmail.com", "username": f"q4p{suffix}", "pseudo": "Test",
            "birth_date": "2000-01-01", "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
            "accept_terms": True, "accept_privacy": True,
        })
        self.user = resp.get_json()["user"]
        self.headers = {"X-CSRF-Token": self.client.get_cookie("nm_csrf").value}

    def _purge(self):
        curriculum_stats.clear_cache()
        for cache in self._caches:
            cache.pop("quatrieme", None)

    def test_chapitres_dans_l_ordre_avec_titres_et_notions_du_cours(self):
        data = self.client.get("/api/chapters?class_level=quatrieme").get_json()
        self.assertEqual(data["chapters"], [f"Chapitre_{n}" for n in sorted(COURSES)])
        for meta in data["chapters_meta"]:
            course = COURSES[int(meta["id"].split("_")[1])]
            with self.subTest(chapitre=meta["id"]):
                self.assertEqual(meta["title"], course["title"])
                self.assertEqual([n["notion"] for n in meta["notions_detail"]], [n["title"] for n in course["notions"]])
        stats = next(c for c in self.client.get("/api/curricula").get_json() if c["classLevel"] == "quatrieme")
        self.assertEqual(stats["chapters"], len(COURSES))
        self.assertEqual(stats["notions"], len(ALL_NOTIONS))
        self.assertEqual(stats["totalExercises"], len(CURATED) + len(GENERATED))

    def test_cours_servis_et_filtres_par_plan(self):
        for number in COURSES:
            resp = self.client.get(f"/api/course-content/quatrieme/Chapitre_{number}", headers=self.headers)
            self.assertEqual(resp.status_code, 200)
            for n in resp.get_json()["notions"]:
                with self.subTest(notion=n["id"]):
                    self.assertEqual({e["niveauAcces"] for e in n["exemples"]}, {"free"})
                    for field in ("explicationSimple", "intuition", "aRetenir", "erreursFrequentesDetail", "exemplesConcrets", "demonstration"):
                        self.assertNotIn(field, n)
                    self.assertTrue(n["reglesImportantes"] and n["methode"]["etapes"] and n["figure"])

    def test_pratique_par_notion_et_quiz_servis(self):
        for n in ALL_NOTIONS.values():
            chapter_id = next(f"Chapitre_{k}" for k, c in COURSES.items() if n in c["notions"])
            query = urllib.parse.urlencode({"chapter_id": chapter_id, "notion": n["title"], "class_level": "quatrieme", "limit": 20})
            resp = self.client.get(f"/api/search/exercises-by-notion?{query}", headers=self.headers)
            with self.subTest(notion=n["id"]):
                self.assertEqual(resp.status_code, 200)
                self.assertGreaterEqual(len(resp.get_json()["results"]), 16)
                for q in n["quizExerciseIds"]:
                    r = self.client.get(f"/api/exercise/{q}?class_level=quatrieme", headers=self.headers)
                    self.assertEqual(r.status_code, 200)

    def test_chatbot_rattache_chaque_notion_a_son_chapitre(self):
        from chatbot.services import intent_service, search_service

        for number, course in COURSES.items():
            for n in course["notions"]:
                question = f"Explique-moi : {n['title'].lower()}"
                detected = intent_service._detect_chapter(question, None, class_level="quatrieme")
                with self.subTest(notion=n["id"]):
                    self.assertEqual(detected[0], f"Chapitre_{number}", question)
                    resultats = search_service.search(n["title"], scope=["cours"], limit=3, class_level="quatrieme")
                    self.assertIn(n["id"], [r.get("notion_id") for r in resultats])

    def test_generation_sur_mesure_ultra_pour_chaque_famille(self):
        import db

        db.set_stripe_subscription(self.user["id"], "sub_test", "ultra", "active")
        for module in GENERATOR_MODULES:
            for family in module.FAMILIES:
                body = {"class_level": "quatrieme", "chapter_id": module.CHAPTER_ID, "notion": family.notion, "family_id": family.id}
                resp = self.client.post("/api/practice/generate", json=body, headers=self.headers)
                with self.subTest(famille=family.id):
                    self.assertEqual(resp.status_code, 200)
                    CHECKERS[family.id](resp.get_json()["exercise"])


if __name__ == "__main__":
    unittest.main()
