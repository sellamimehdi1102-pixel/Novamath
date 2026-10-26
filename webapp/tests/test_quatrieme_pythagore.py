"""
Chantier "Quatrième — chapitre pilote Pythagore" (2026-10-24).

Verrous de la phase 2 :
- registre : "quatrieme" déclarée, NON publiée, servie uniquement en
  prévisualisation locale (jamais en production), classes existantes
  inchangées ;
- cours (cours_quatrieme/chapitre_8.json) : schéma v2, identifiants
  stables, figures géométriquement exactes, filtrage Free/Premium/Ultra
  réellement différencié, aucun contenu hors programme de 4e ;
- banque curée (exercises_bank_quatrieme.json) : identique à sa source
  tools/build_quatrieme_bank.py, contrôles mathématiques rejoués, couverture
  des 4 difficultés, mini-quiz résolus ;
- générateurs (exercise_generator_quatrieme/pythagore.py) : 500 graines par
  famille, réponses recalculées par un vérificateur INDÉPENDANT (relecture
  des nombres de l'énoncé, arithmétique exacte en fractions), déterminisme,
  identifiants stables ;
- parcours HTTP complet en prévisualisation (Free, Premium, Ultra).
"""
import importlib.util
import json
import math
import re
import unittest
import urllib.parse
import uuid
from decimal import ROUND_HALF_UP, Decimal, localcontext
from fractions import Fraction
from pathlib import Path
from unittest import mock

import curriculum_registry
import curriculum_stats
import db
import validate_curriculum_content
from curriculum_registry import (
    CURRICULUM_REGISTRY,
    CURRICULUM_REGISTRY_ALL,
    CurriculumIntegrityError,
    served_registry,
    validate_registry,
)
from exercise_generator import registry as generator_registry
from exercise_generator_quatrieme import pythagore

ROOT = Path(__file__).resolve().parents[2]
PROFILE = CURRICULUM_REGISTRY_ALL["quatrieme"]
CHAPTER_PATH = PROFILE.courses_dir / "chapitre_8.json"
CHAPTER = json.loads(CHAPTER_PATH.read_text(encoding="utf-8"))
# Ce fichier vérifie le chapitre pilote (Chapitre_8) ; les contrôles communs
# à toute la classe sont dans tests/test_quatrieme_programme.py.
CURATED = [e for e in json.loads(PROFILE.exercise_bank.read_text(encoding="utf-8")) if e["chapter_id"] == "Chapitre_8"]
GENERATED = [e for e in json.loads(PROFILE.generated_exercise_bank.read_text(encoding="utf-8")) if e["chapter_id"] == "Chapitre_8"]

NOTION_IDS = [
    "pythagore-hypotenuse-et-egalite",
    "carres-et-racines-carrees",
    "pythagore-calculer-une-longueur",
    "triangle-rectangle-ou-non",
    "problemes-avec-pythagore",
]
NOTIONS_BY_ID = {n["id"]: n for n in CHAPTER["notions"]}
TITLES = {n["title"] for n in CHAPTER["notions"]}


def _load_bank_source():
    spec = importlib.util.spec_from_file_location("build_quatrieme_bank", ROOT / "tools" / "build_quatrieme_bank.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BANK_SOURCE = _load_bank_source()


# ═════════════════════════════════════════════════════════════════════════
# Registre et publication
# ═════════════════════════════════════════════════════════════════════════
class TestRegistreQuatrieme(unittest.TestCase):
    def test_profil_declare_non_publie(self):
        self.assertEqual(PROFILE.label, "Quatrième")
        self.assertIs(PROFILE.published, False)
        self.assertEqual(PROFILE.school_stage, "college")
        self.assertEqual(list(CURRICULUM_REGISTRY_ALL)[:2], ["quatrieme", "troisieme"])

    def test_options_d_affichage_reservees_a_la_quatrieme(self):
        quatrieme = CURRICULUM_REGISTRY_ALL["quatrieme"]
        self.assertTrue(quatrieme.notion_order_from_courses)
        # Le nombre de chapitres prévus diminue à chaque chapitre rédigé : la
        # règle « rédigés + prévus = 17 » est vérifiée par test_quatrieme_programme.py.
        self.assertTrue(len(quatrieme.planned_chapter_titles) < 17)
        self.assertFalse(any("Pythagore" in t for t in quatrieme.planned_chapter_titles))
        for class_level in ("troisieme", "seconde", "premiere"):
            with self.subTest(class_level=class_level):
                self.assertFalse(CURRICULUM_REGISTRY_ALL[class_level].notion_order_from_courses)
                self.assertEqual(CURRICULUM_REGISTRY_ALL[class_level].planned_chapter_titles, ())

    def test_absente_du_registre_servi_par_defaut(self):
        self.assertNotIn("quatrieme", CURRICULUM_REGISTRY)
        self.assertEqual(list(CURRICULUM_REGISTRY), ["troisieme", "seconde", "premiere"])

    def test_previsualisation_place_la_quatrieme_avant_la_troisieme(self):
        served = served_registry(CURRICULUM_REGISTRY_ALL, frozenset({"quatrieme"}))
        self.assertEqual(list(served), ["quatrieme", "troisieme", "seconde", "premiere"])

    def test_previsualisation_valide_en_local_refusee_en_production(self):
        validate_registry(CURRICULUM_REGISTRY_ALL, frozenset({"quatrieme"}), environ={"FLASK_ENV": "development"})
        with self.assertRaises(CurriculumIntegrityError) as ctx:
            validate_registry(CURRICULUM_REGISTRY_ALL, frozenset({"quatrieme"}), environ={"FLASK_ENV": "production"})
        self.assertIn("interdit en production", str(ctx.exception))

    def test_ressources_declarees_existent(self):
        self.assertTrue(PROFILE.courses_dir.is_dir())
        self.assertTrue(PROFILE.exercise_bank.is_file())
        self.assertTrue(PROFILE.generated_exercise_bank.is_file())
        # Aucune reformulation « langage naturel » pour l'instant (toléré).
        self.assertFalse(PROFILE.natural_bank.exists())

    def test_generateurs_inaccessibles_sans_previsualisation(self):
        self.assertEqual(generator_registry.available_notions("quatrieme"), {})
        family = pythagore.FAMILIES[0]
        self.assertIsNone(generator_registry.generate("quatrieme", pythagore.CHAPTER_ID, family.notion, family.id, seed=1))


# ═════════════════════════════════════════════════════════════════════════
# Cours
# ═════════════════════════════════════════════════════════════════════════
def _load_preview_launcher():
    spec = importlib.util.spec_from_file_location("run_preview", ROOT / "tools" / "run_preview.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestLanceurPrevisualisation(unittest.TestCase):
    def setUp(self):
        import os
        import tempfile

        self.os = os
        self.launcher = _load_preview_launcher()
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))
        self.static, self.dist = self.tmp / "static", self.tmp / "static-dist"
        (self.static / "js" / "__tests__").mkdir(parents=True)
        (self.static / "js" / "page.js").write_text("x")
        self.launcher.STATIC_DIR, self.launcher.STATIC_DIST_DIR = self.static, self.dist

    def _age(self, path, seconds_ago):
        t = __import__("time").time() - seconds_ago
        self.os.utime(path, (t, t))

    def test_compilation_perimee_detectee(self):
        self.assertFalse(self.launcher.static_dist_is_stale())  # pas de static-dist : sources servies telles quelles
        self.dist.mkdir()
        (self.dist / "page.js").write_text("x")
        self._age(self.static / "js" / "page.js", 100)
        self.assertFalse(self.launcher.static_dist_is_stale())
        (self.static / "js" / "__tests__" / "page.test.js").write_text("x")  # un test seul ne compte pas
        self._age(self.dist / "page.js", 50)
        self.assertFalse(self.launcher.static_dist_is_stale())
        (self.static / "js" / "page.js").write_text("y")
        self.assertTrue(self.launcher.static_dist_is_stale())

    def _run_main(self, argv, served, port_state=("libre", None, [])):
        """main() avec un faux serveur : `served` = réponse de /api/curricula,
        `port_state` = résultat d'inspect_port (port libre par défaut)."""
        process = mock.Mock(pid=0)
        process.wait.return_value = 0
        process.poll.return_value = None
        with mock.patch.object(self.launcher.subprocess, "Popen", return_value=process) as popen, \
                mock.patch.object(self.launcher, "inspect_port", return_value=port_state), \
                mock.patch.object(self.launcher, "wait_until_served", return_value=served), \
                mock.patch.object(self.launcher, "start_frontend_watch", return_value=None), \
                mock.patch.object(self.launcher, "stop_instance", return_value=True) as stop_instance, \
                mock.patch.object(self.launcher.dev_server, "kill_children_with_this_process"), \
                mock.patch.object(self.launcher, "stop_tree") as stop, \
                mock.patch.object(self.launcher.webbrowser, "open") as browser:
            code = self.launcher.main(argv)
        self.stop_instance = stop_instance
        return code, popen, stop, browser

    def test_transmet_uniquement_la_variable_de_previsualisation(self):
        served = [{"classLevel": "quatrieme", "label": "Quatrième", "totalExercises": 324, "chapters": 1, "notions": 5}]
        code, popen, stop, browser = self._run_main(["--port", "5099", "--no-build"], served)
        self.assertEqual(code, 0)
        (args,), kwargs = popen.call_args
        self.assertEqual(args[1], str(self.launcher.SERVER))
        self.assertEqual(kwargs["env"]["NOVAMATH_PREVIEW_CURRICULA"], "quatrieme")
        self.assertEqual(kwargs["env"]["PORT"], "5099")
        browser.assert_called_once_with("http://127.0.0.1:5099/choisir-classe.html")
        # Seule action d'arrêt : le nettoyage final des processus lancés (serveur, surveillance).
        self.assertIn(mock.call(popen.return_value), stop.call_args_list)
        self.assertEqual(kwargs["env"]["MATHADAP_LAUNCHER"], "run_preview")
        # Stripe désactivé par défaut : aucun paiement réel depuis une prévisualisation.
        self.assertEqual(kwargs["env"]["STRIPE_SECRET_KEY"], "")
        with mock.patch.dict(self.os.environ, {"STRIPE_SECRET_KEY": "sk_test_x"}):
            _, popen, _, _ = self._run_main(["--no-build", "--stripe", "--no-browser"], served)
        self.assertEqual(popen.call_args.kwargs["env"]["STRIPE_SECRET_KEY"], "sk_test_x")

    def test_port_par_defaut_unique(self):
        self.assertEqual(self.launcher.dev_server.DEFAULT_PORT, 5050)
        self.assertEqual(self.launcher.HOST, "127.0.0.1")

    def test_donnees_test_lance_le_meme_serveur_sur_un_dossier_isole(self):
        served = [{"classLevel": "quatrieme", "label": "Quatrième", "totalExercises": 324, "chapters": 1, "notions": 5}]
        _, popen, _, _ = self._run_main(["--no-build", "--no-browser", "--donnees-test", str(self.tmp)], served)
        (args,), kwargs = popen.call_args
        self.assertEqual(args[1:], [str(self.launcher.ISOLATED_SERVER), str(self.tmp.resolve())])
        self.assertEqual(kwargs["env"]["NOVAMATH_PREVIEW_CURRICULA"], "quatrieme")
        # Le dossier par défaut est hors du dépôt : aucun fichier non suivi créé dans le projet.
        self.assertNotIn(str(ROOT), str(self.launcher.DEFAULT_SANDBOX_DIR))

    def test_serveur_sans_la_classe_demandee_arrete_et_signale(self):
        served = [{"classLevel": "troisieme", "label": "Troisième", "totalExercises": 1, "chapters": 1, "notions": 1}]
        code, popen, stop, browser = self._run_main(["--no-build"], served)
        self.assertEqual(code, 1)
        self.assertIn(mock.call(popen.return_value), stop.call_args_list)
        browser.assert_not_called()

    # ── Une seule instance, un seul port (2026-10-25) ──────────────────────
    def _state(self, **mode):
        state = {"pid": 1234, "create_time": 0, "port": 5050, "data": self.launcher.REAL_DATA,
                 "preview": "quatrieme", "stripe": False}
        state.update(mode)
        return state

    def test_instance_deja_lancee_dans_le_meme_mode_ne_demarre_rien(self):
        code, popen, _, browser = self._run_main(["--no-build"], [], ("inscrit", self._state(), [(1234, "127.0.0.1")]))
        self.assertEqual(code, 0)
        popen.assert_not_called()
        self.stop_instance.assert_not_called()
        browser.assert_called_once_with("http://127.0.0.1:5050/choisir-classe.html")

    def test_instance_dans_un_autre_mode_explique_le_redemarrage(self):
        state = self._state(data=f"de test ({self.tmp})")
        code, popen, _, _ = self._run_main(["--no-build", "--no-browser"], [], ("inscrit", state, [(1234, "127.0.0.1")]))
        self.assertEqual(code, 1)
        popen.assert_not_called()
        self.stop_instance.assert_not_called()

    def test_redemarrer_arrete_l_instance_inscrite_puis_relance_sur_le_meme_port(self):
        served = [{"classLevel": "quatrieme", "label": "Quatrième", "totalExercises": 1, "chapters": 1, "notions": 1}]
        state = self._state(data=f"de test ({self.tmp})")
        code, popen, _, _ = self._run_main(["--no-build", "--no-browser", "--redemarrer"], served,
                                           ("inscrit", state, [(1234, "127.0.0.1")]))
        self.assertEqual(code, 0)
        self.stop_instance.assert_called_once_with(state, 5050)
        self.assertEqual(popen.call_args.kwargs["env"]["PORT"], "5050")

    def test_ancien_serveur_non_inscrit_jamais_arrete(self):
        code, popen, _, _ = self._run_main(["--no-build", "--no-browser", "--redemarrer"], [],
                                           ("ancien", None, [(4321, "127.0.0.1")]))
        self.assertEqual(code, 1)
        popen.assert_not_called()
        self.stop_instance.assert_not_called()

    def test_autre_application_echec_sans_autre_port(self):
        import socket

        busy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addCleanup(busy.close)
        busy.bind(("127.0.0.1", 0))
        busy.listen()
        port = busy.getsockname()[1]
        with mock.patch.object(self.launcher, "served_curricula", return_value=None):
            kind, _, _ = self.launcher.inspect_port(port)
        self.assertEqual(kind, "autre")
        code, popen, _, _ = self._run_main(["--no-build", "--no-browser", "--port", str(port)], [], (kind, None, []))
        self.assertEqual(code, 1)
        popen.assert_not_called()

    def test_port_reserve_en_exclusivite(self):
        # Cause des doubles serveurs sous Windows : SO_REUSEADDR des deux côtés.
        # Un port réservé par dev_server refuse toute autre liaison, même SO_REUSEADDR.
        import socket

        dev_server = self.launcher.dev_server
        held = dev_server.exclusive_socket(0)
        self.addCleanup(held.close)
        held.listen()
        port = held.getsockname()[1]
        with self.assertRaises(OSError):
            dev_server.exclusive_socket(port).close()
        intruder = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addCleanup(intruder.close)
        intruder.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        with self.assertRaises(OSError):
            intruder.bind(("127.0.0.1", port))


def _walk_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _walk_strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from _walk_strings(v)


# Hors programme de 4e (trigonométrie autre que le cosinus de 4e, identités
# remarquables, inéquations, simplification de radicaux a√b).
_HORS_PROGRAMME_RE = re.compile(
    r"\\sin\b|\\tan\b|\bsinus\b|\btangente\b|trigonom|identit[ée]s? remarquables?|in[ée]quation|\d\s*\\sqrt",
    re.IGNORECASE,
)


class TestCoursPythagore(unittest.TestCase):
    def test_chapitre_et_identifiants_stables(self):
        self.assertEqual(CHAPTER["chapterId"], "Chapitre_8")
        self.assertEqual(CHAPTER["title"], "Théorème de Pythagore")
        self.assertEqual([n["id"] for n in CHAPTER["notions"]], NOTION_IDS)
        for n in CHAPTER["notions"]:
            with self.subTest(notion=n["id"]):
                self.assertEqual(n["schemaVersion"], 2)
                self.assertEqual(n["topic_id"], n["id"])
                self.assertRegex(n["id"], r"^[a-z0-9]+(-[a-z0-9]+)*$")
                for lie in n["notions_liees"]:
                    self.assertIn(lie, NOTIONS_BY_ID)

    def test_validateur_sans_erreur_ni_avertissement(self):
        (report,) = validate_curriculum_content.validate(["quatrieme"])
        self.assertEqual(report.errors, [])
        self.assertEqual(report.warnings, [])

    def test_titres_alignes_sur_banque_et_generateurs(self):
        self.assertEqual(TITLES, set(BANK_SOURCE.NOTIONS))
        self.assertEqual(TITLES, {pythagore.N1, pythagore.N2, pythagore.N3, pythagore.N4, pythagore.N5})
        self.assertEqual({e["notion"] for e in CURATED}, TITLES)
        self.assertLessEqual({e["notion"] for e in GENERATED}, TITLES)

    def test_aucun_contenu_hors_programme(self):
        for text in _walk_strings(CHAPTER):
            self.assertIsNone(_HORS_PROGRAMME_RE.search(text), text[:120])
        for ex in CURATED + GENERATED:
            for text in _walk_strings(ex):
                self.assertIsNone(_HORS_PROGRAMME_RE.search(text), f"{ex['id']} : {text[:120]}")

    def test_structure_pedagogique_complete(self):
        for n in CHAPTER["notions"]:
            with self.subTest(notion=n["id"]):
                for field in ("intro", "pourquoi", "objectif", "definition", "astuce", "explicationSimple", "intuition"):
                    self.assertTrue(n.get(field), field)
                self.assertGreaterEqual(len(n["reglesImportantes"]), 4)
                self.assertGreaterEqual(len(n["erreursFrequentes"]), 4)
                self.assertGreaterEqual(len(n["methode"]["etapes"]), 4)
                self.assertTrue(n["methode"]["etapesParNiveau"]["debutant"] and n["methode"]["etapesParNiveau"]["rapide"])
                self.assertTrue(n["prerequis"] and n["objectifs_pedagogiques"] and n["questionsEclair"])
                self.assertTrue(n["figure"].get("explication"), "figure sans explication rédigée")

    def test_exemples_differencies_par_plan(self):
        """Free : au moins 2 exemples (un par règle essentielle) ; Premium :
        au moins 2 exemples de plus ; Ultra : un exemple en plusieurs étapes,
        et une démonstration pour chaque notion à théorème/propriété."""
        for n in CHAPTER["notions"]:
            with self.subTest(notion=n["id"]):
                niveaux = [e["niveauAcces"] for e in n["exemples"]]
                self.assertGreaterEqual(niveaux.count("free"), 2)
                self.assertGreaterEqual(niveaux.count("premium"), 2)
                self.assertGreaterEqual(niveaux.count("ultra"), 1)
                ids = [e["id"] for e in n["exemples"]]
                self.assertEqual(len(ids), len(set(ids)))
        for notion_id in NOTION_IDS[:4]:
            self.assertTrue(NOTIONS_BY_ID[notion_id]["demonstration"]["etapes"])
        self.assertNotIn("demonstration", NOTIONS_BY_ID["problemes-avec-pythagore"])

    def test_apercus_honnetes(self):
        """Un aperçu Ultra qui promet une démonstration doit correspondre à
        une démonstration réellement rédigée."""
        for n in CHAPTER["notions"]:
            for a in n["apercus"]:
                with self.subTest(notion=n["id"], apercu=a["id"]):
                    self.assertEqual(a["section"], "exemple")
                    texte = (a["titre"] + " " + a["description"]).lower()
                    if any(mot in texte for mot in ("démonstration", "preuve", "démontrer")):
                        self.assertIn("demonstration", n)


def _pt(spec, ref):
    if isinstance(ref, str):
        p = next(p for p in spec["points"] if p["label"] == ref)
        return (p["x"], p["y"])
    return (ref["x"], ref["y"])


def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


class TestFigures(unittest.TestCase):
    def _fig(self, notion_id):
        return NOTIONS_BY_ID[notion_id]["figure"]

    def test_chaque_codage_d_angle_droit_est_un_vrai_angle_droit(self):
        """Le petit carré (polygone variant "marker") a 4 côtés égaux et des
        angles droits, et son premier sommet est un sommet de la figure."""
        for notion_id in NOTION_IDS:
            fig = self._fig(notion_id)
            markers = [p for p in fig["polygons"] if p.get("variant") == "marker"]
            with self.subTest(notion=notion_id):
                self.assertEqual(len(markers), 1)
                v, a, c, b = (_pt(fig, r) for r in markers[0]["points"])
                ux, uy, wx, wy = a[0] - v[0], a[1] - v[1], b[0] - v[0], b[1] - v[1]
                self.assertAlmostEqual(ux * wx + uy * wy, 0, places=3)
                self.assertAlmostEqual(math.hypot(ux, uy), math.hypot(wx, wy), places=2)
                self.assertAlmostEqual(c[0], v[0] + ux + wx, places=2)
                self.assertAlmostEqual(c[1], v[1] + uy + wy, places=2)

    def test_longueurs_des_figures_conformes_aux_donnees(self):
        f1 = self._fig("pythagore-hypotenuse-et-egalite")
        A, B, C = (_pt(f1, x) for x in "ABC")
        self.assertAlmostEqual(_dist(A, B), 3, places=2)
        self.assertAlmostEqual(_dist(A, C), 4, places=2)
        self.assertAlmostEqual(_dist(B, C), 5, places=2)
        self.assertEqual(B[1], C[1])  # hypoténuse horizontale (anti-stéréotype)

        f2 = self._fig("carres-et-racines-carrees")
        A, B, C, D = (_pt(f2, x) for x in "ABCD")
        for p, q in ((A, B), (B, C), (C, D), (D, A)):
            self.assertAlmostEqual(_dist(p, q) ** 2, 20, places=6)

        f3 = self._fig("pythagore-calculer-une-longueur")
        U, V, W = (_pt(f3, x) for x in "UVW")
        scale = _dist(W, V) / 8
        self.assertAlmostEqual(_dist(U, V) / scale, 17, places=2)
        self.assertAlmostEqual(_dist(U, W) / scale, 15, places=2)

        f4 = self._fig("triangle-rectangle-ou-non")
        A, B, C, O4, N, P = (_pt(f4, x) for x in "ABCONP")
        self.assertAlmostEqual(_dist(A, B), 4, places=2)
        self.assertAlmostEqual(_dist(A, C), 3, places=2)
        self.assertAlmostEqual(_dist(B, C), 5, places=2)
        self.assertAlmostEqual(_dist(O4, N), 5, places=2)
        self.assertAlmostEqual(_dist(O4, P), 5, places=2)
        self.assertAlmostEqual(_dist(N, P), 7, places=2)
        angle_o = math.degrees(math.acos(((N[0] - O4[0]) * (P[0] - O4[0]) + (N[1] - O4[1]) * (P[1] - O4[1])) / 25))
        self.assertTrue(88 < angle_o < 90, angle_o)  # « presque » droit, mais pas droit
        # Aucun codage d'angle droit sur le triangle non rectangle.
        marker = next(p for p in f4["polygons"] if p.get("variant") == "marker")
        self.assertEqual(_pt(f4, marker["points"][0]), A)

        f5 = self._fig("problemes-avec-pythagore")
        foot, top = (1.0, 0.0), (0.0, round(math.sqrt(15), 3))
        ladder = next(s for s in f5["segments"] if s.get("variant") == "hypotenuse")
        self.assertEqual((_pt(f5, ladder["from"]), _pt(f5, ladder["to"])), (foot, top))
        self.assertAlmostEqual(_dist(foot, top), 4, places=2)

    def test_etapes_de_revelation_coherentes(self):
        for notion_id in NOTION_IDS:
            fig = self._fig(notion_id)
            with self.subTest(notion=notion_id):
                self.assertEqual(len(fig["steps"]), 3)
                reveals = {el.get("reveal") for key in ("polygons", "segments", "texts") for el in fig.get(key, [])}
                self.assertLessEqual(reveals - {None}, {2, 3})
                self.assertTrue(fig["alt"])


# ═════════════════════════════════════════════════════════════════════════
# Banque curée
# ═════════════════════════════════════════════════════════════════════════
def _squelette(enonce):
    """Énoncé sans ses nombres ni ses noms de points : deux exercices de même
    squelette ne diffèrent que par les valeurs."""
    s = re.sub(r"\d+(\{,\}\d+)?", "#", enonce)
    return re.sub(r"\b[A-Z]{1,4}\b", "P", s)


class TestBanqueCuree(unittest.TestCase):
    def test_json_identique_a_sa_source_et_controles_rejoues(self):
        self.assertEqual(CURATED, BANK_SOURCE.build())
        self.assertEqual(BANK_SOURCE.check_all(), [])

    def test_schema_identifiants_et_chapitre(self):
        ids = [e["id"] for e in CURATED]
        self.assertEqual(len(ids), len(set(ids)))
        for e in CURATED:
            with self.subTest(id=e["id"]):
                self.assertEqual(set(e), {"id", "chapter_id", "notion", "difficulty", "enonce", "answer", "hint", "solution_steps"})
                self.assertTrue(48_100 < e["id"] < 48_600)
                self.assertEqual(e["chapter_id"], "Chapitre_8")
                self.assertIn(e["difficulty"], (1, 2, 3, 4))
                self.assertTrue(e["solution_steps"])
                self.assertNotIn(e["hint"], e["answer"])

    def test_couverture_des_quatre_difficultes_par_notion(self):
        for title in TITLES:
            difficultes = [e["difficulty"] for e in CURATED if e["notion"] == title]
            with self.subTest(notion=title):
                self.assertGreaterEqual(len(difficultes), 18)
                self.assertEqual(set(difficultes), {1, 2, 3, 4})

    def test_diversite_reelle_des_enonces(self):
        """Aucune série « mêmes phrases, autres nombres » : au moins 85 % des
        énoncés curés d'une notion ont un squelette qui leur est propre."""
        for title in TITLES:
            enonces = [e["enonce"] for e in CURATED if e["notion"] == title]
            with self.subTest(notion=title):
                self.assertGreaterEqual(len({_squelette(x) for x in enonces}) / len(enonces), 0.85)

    def test_aucun_identifiant_partage_avec_une_autre_classe(self):
        ours = {e["id"] for e in CURATED + GENERATED}
        for class_level, profile in CURRICULUM_REGISTRY_ALL.items():
            if class_level == "quatrieme":
                continue
            for path in (profile.exercise_bank, profile.generated_exercise_bank):
                if path is None or not path.exists():
                    continue
                theirs = {e.get("id") for e in json.loads(path.read_text(encoding="utf-8"))}
                with self.subTest(fichier=path.name):
                    self.assertEqual(ours & theirs, set())


class TestMiniQuiz(unittest.TestCase):
    def test_references_resolues_coherentes_et_stables(self):
        by_id = {e["id"]: e for e in CURATED}
        for n in CHAPTER["notions"]:
            quiz = n["quizExerciseIds"]
            with self.subTest(notion=n["id"]):
                self.assertEqual(len(quiz), 3)
                self.assertEqual(len(set(quiz)), 3)
                self.assertEqual(tuple(quiz), BANK_SOURCE.QUIZ[n["id"]])
                for q in quiz:
                    self.assertIn(q, by_id)  # exercice curé, jamais généré
                    self.assertEqual(by_id[q]["notion"], n["title"])
                    self.assertEqual(by_id[q]["chapter_id"], CHAPTER["chapterId"])
                    self.assertLessEqual(by_id[q]["difficulty"], 2)


# ═════════════════════════════════════════════════════════════════════════
# Générateurs — vérificateur indépendant
# ═════════════════════════════════════════════════════════════════════════
_NUM = r"(\d+(?:\{,\}\d+)?)"


def _f(text):
    return Fraction(text.replace("{,}", "."))


def _fr(x):
    x = Fraction(x)
    if x.denominator == 1:
        return str(x.numerator)
    with localcontext() as ctx:
        ctx.prec = 40
        return format((Decimal(x.numerator) / Decimal(x.denominator)).normalize(), "f").replace(".", "{,}")


def _exact_root(x2):
    x2 = Fraction(x2)
    n, d = math.isqrt(x2.numerator), math.isqrt(x2.denominator)
    return Fraction(n, d) if n * n == x2.numerator and d * d == x2.denominator else None


def _rounded_root(x2, decimals):
    x2 = Fraction(x2)
    with localcontext() as ctx:
        ctx.prec = 40
        r = (Decimal(x2.numerator) / Decimal(x2.denominator)).sqrt()
        return format(r.quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP), "f").replace(".", "{,}")


_PRECISION = {"au dixième": 1, "au centième": 2, "au millimètre": 1, "au centimètre": 2, "à l'unité": 0}


def _precision(enonce):
    for label, decimals in _PRECISION.items():
        if label in enonce:
            return decimals
    return None


class TestGenerateursIndependants(unittest.TestCase):
    """500 graines par famille. Chaque réponse est recalculée à partir des
    seuls nombres lus dans l'énoncé — jamais à partir du code du générateur."""

    SEEDS = range(500)

    def _length(self, x2, enonce, answer, unit):
        self.assertGreater(x2, 0)
        exact = _exact_root(x2)
        if exact is not None:
            self.assertIn(f"{_fr(exact)}$ {unit}", answer)
        else:
            decimals = _precision(enonce)
            self.assertIsNotNone(decimals, enonce)
            self.assertIn(f"\\sqrt{{{_fr(x2)}}}", answer)
            self.assertIn(f"\\approx {_rounded_root(x2, decimals)}$ {unit}", answer)

    def _check(self, family_id, ex):
        e, a = ex["enonce"], ex["answer"]
        if family_id == "ecrire_egalite":
            tri, v = re.search(r"triangle \$([A-Z]{3})\$ est rectangle en \$([A-Z])\$", e).groups()
            hyp = "".join(sorted(c for c in tri if c != v))
            self.assertIn(f"{hyp}^2 = ", a)
        elif family_id == "encadrer_racine":
            n = int(re.search(r"\\sqrt\{(\d+)\}", e).group(1))
            k = math.isqrt(n)
            self.assertNotEqual(k * k, n)
            self.assertIn(f"{k} < \\sqrt{{{n}}} < {k + 1}", a)
            self.assertIn(f"\\approx {_rounded_root(n, 1)}$", a)
        elif family_id in ("calcul_hypotenuse", "calcul_cote"):
            (_, x1, unit), (_, x2, unit2) = re.findall(r"\$([A-Z]{2}) = " + _NUM + r"\$ (cm|m|mm|km)", e)
            self.assertEqual(unit, unit2)
            x1, x2 = _f(x1), _f(x2)
            if family_id == "calcul_hypotenuse":
                self._length(x1 * x1 + x2 * x2, e, a, unit)
            else:
                self.assertGreater(x1, x2)  # hypoténuse strictement plus longue
                self._length(x1 * x1 - x2 * x2, e, a, unit)
        elif family_id == "rectangle_ou_non":
            tri = re.search(r"triangle \$([A-Z]{3})\$", e).group(1)
            sides = {s: _f(x) for s, x in re.findall(r"\$([A-Z]{2}) = " + _NUM + r"\$ cm", e)}
            self.assertEqual(len(sides), 3)
            x, y, z = sorted(sides.values())
            self.assertLess(z, x + y)  # le triangle existe
            longest = max(sides, key=sides.get)
            if x * x + y * y == z * z:
                vertex = next(c for c in tri if c not in longest)
                self.assertTrue(a.startswith("Oui"), e)
                self.assertIn(f"rectangle en ${vertex}$", a)
                self.assertIn("réciproque", " ".join(ex["solution_steps"]))
            else:
                self.assertTrue(a.startswith("Non"), e)
                self.assertGreaterEqual(abs(z * z - (x * x + y * y)), Fraction(1, 2))
                self.assertIn("contraposée", " ".join(ex["solution_steps"]))
        elif family_id == "diagonale_rectangle":
            L, W = (_f(x) for x in re.findall(r"\$" + _NUM + r"\$ (?:cm|m)", e)[:2])
            d2 = L * L + W * W
            if "baguette" in e:
                b = _f(re.search(r"baguette rigide de \$" + _NUM + r"\$", e).group(1))
                self.assertGreater(b, max(L, W))
                self.assertTrue(a.startswith("Oui" if b * b < d2 else "Non"), e)
            else:
                unit = re.search(r"\$ (cm|m) ", e).group(1)
                exact = _exact_root(d2)
                if exact is not None:
                    self.assertIn(f"${_fr(exact)}$ {unit}", a)
                else:
                    self.assertIn(f"${_rounded_root(d2, _precision(e))}$ {unit}", a)
        elif family_id == "echelle_mur":
            values = [_f(x) for x in re.findall(r"\$" + _NUM + r"\$ m", e)]
            self.assertEqual(len(values), 2)
            big, small = values
            x2 = big * big - small * small if ("hauteur du poteau" in e or "À quelle hauteur" in e) else big * big + small * small
            self.assertGreater(x2, 0)
            exact = _exact_root(x2)
            self.assertIn(f"${_fr(exact) if exact is not None else _rounded_root(x2, 2)}$ m", a)
        elif family_id == "hauteur_isocele":
            if "équilatéral" in e:
                base = cote = _f(re.search(r"de côté \$" + _NUM + r"\$", e).group(1))
            else:
                cote = _f(re.search(r"AB = AC = " + _NUM, e).group(1))
                base = _f(re.search(r"BC = " + _NUM, e).group(1))
            self.assertGreater(cote, base / 2)
            h2 = cote * cote - (base / 2) ** 2
            exact = _exact_root(h2)
            if exact is not None:
                self.assertIn(f"$AH = {_fr(exact)}$ cm", a)
                self.assertIn(f"${_fr(base * exact / 2)}$ cm$^2$", a)
            else:
                self.assertIn(f"$AH \\approx {_rounded_root(h2, 1)}$ cm", a)
                aire2 = base * base * h2 / 4  # (aire)² exact
                self.assertIn(f"${_rounded_root(aire2, 1)}$ cm$^2$", a)
        else:
            self.fail(f"famille sans vérificateur indépendant : {family_id}")

    def test_cinq_cents_graines_par_famille(self):
        for family in pythagore.FAMILIES:
            enonces = set()
            for seed in self.SEEDS:
                ex = pythagore.generate_one(family.id, seed=seed)
                with self.subTest(family=family.id, seed=seed):
                    self.assertEqual(ex["notion"], family.notion)
                    self.assertEqual(ex["chapter_id"], "Chapitre_8")
                    for text in [ex["enonce"], ex["answer"], ex["hint"], *ex["solution_steps"]]:
                        self.assertEqual(text.count("$") % 2, 0, text)
                    self._check(family.id, ex)
                enonces.add(ex["enonce"])
            with self.subTest(family=family.id, controle="variété"):
                self.assertGreaterEqual(len(enonces), 100)

    def test_deterministe(self):
        for family in pythagore.FAMILIES:
            self.assertEqual(pythagore.generate_one(family.id, seed=42), pythagore.generate_one(family.id, seed=42))
        self.assertEqual(pythagore.generate_pool(per_family=25, seed=40080001), GENERATED)

    def test_pool_genere_identifiants_et_familles(self):
        ids = [e["id"] for e in GENERATED]
        self.assertEqual(ids, list(range(480_000, 480_000 + len(GENERATED))))
        self.assertEqual({e["family"] for e in GENERATED}, {f.id for f in pythagore.FAMILIES})
        self.assertEqual(len({e["enonce"] for e in GENERATED}), len(GENERATED))
        self.assertEqual({e["enonce"] for e in GENERATED} & {e["enonce"] for e in CURATED}, set())
        for e in GENERATED:
            with self.subTest(id=e["id"]):
                self._check(e["family"], e)

    def test_difficulte_croissante_avec_le_niveau_declare(self):
        by_level = {}
        for f in pythagore.FAMILIES:
            by_level.setdefault(f.level, []).append(pythagore.FAMILY_BASE_SCORE[f.id])
        moyennes = [sum(v) / len(v) for _, v in sorted(by_level.items())]
        self.assertEqual(moyennes, sorted(moyennes))
        self.assertEqual({e["difficulty"] for e in GENERATED}, {1, 2, 3, 4})


# ═════════════════════════════════════════════════════════════════════════
# Parcours HTTP — prévisualisation locale
# ═════════════════════════════════════════════════════════════════════════
def _register(client):
    suffix = uuid.uuid4().hex[:12]
    resp = client.post("/api/auth/register", json={
        "email": f"q4{suffix}@gmail.com", "username": f"q4{suffix}", "pseudo": "Test",
        "birth_date": "2000-01-01", "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
        "accept_terms": True, "accept_privacy": True,
    })
    return resp.get_json()["user"], {"X-CSRF-Token": client.get_cookie("nm_csrf").value}


class _QuatriemeHTTPCase(unittest.TestCase):
    preview = False

    def setUp(self):
        import server
        from chatbot import knowledge_engine
        from chatbot.services import search_service

        self.server = server
        self._caches = (
            server._class_bank_cache, server._level_engine_cache,
            knowledge_engine._index_by_class, knowledge_engine._by_ids_by_class,
            search_service._exercise_index_by_class, search_service._exercise_by_id_by_class,
            search_service._exercise_index_by_chapter_by_class,
        )
        served = served_registry(CURRICULUM_REGISTRY_ALL, frozenset({"quatrieme"}) if self.preview else frozenset())
        for patcher in (
            mock.patch.object(curriculum_registry, "CURRICULUM_REGISTRY", served),
            mock.patch.object(curriculum_stats, "CURRICULUM_REGISTRY", served),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.addCleanup(self._purge)
        self._purge()
        self.client = server.app.test_client()
        self.user, self.headers = _register(self.client)

    def _purge(self):
        curriculum_stats.clear_cache()
        for cache in self._caches:
            cache.pop("quatrieme", None)

    def _plan(self, plan):
        if plan != "free":
            db.set_stripe_subscription(self.user["id"], "sub_test", plan, "active")


class TestQuatriemeInvisibleSansPrevisualisation(_QuatriemeHTTPCase):
    def test_absente_des_api_et_routes_refusees(self):
        self.assertNotIn("quatrieme", [c["classLevel"] for c in self.client.get("/api/curricula").get_json()])
        for url in (
            "/api/chapters?class_level=quatrieme",
            "/api/course-content/quatrieme/Chapitre_8",
            "/api/exercise/48101?class_level=quatrieme",
            "/api/exercise/480000?class_level=quatrieme",
            "/api/course-progress?class_level=quatrieme",
            "/api/search?q=pythagore&class_level=quatrieme",
            "/api/site/stats?class_level=quatrieme",
            "/api/chapters?class_level=quatrieme&preview=true",
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url, headers=self.headers).status_code, 404)
        body = {"class_level": "quatrieme", "chapterId": "Chapitre_8", "notionId": NOTION_IDS[0], "patch": {"status": "done"}}
        self.assertEqual(self.client.post("/api/course-progress", json=body, headers=self.headers).status_code, 404)

    def test_generation_ultra_refusee(self):
        self._plan("ultra")
        options = self.client.get("/api/practice/generate/options", headers=self.headers).get_json()["notions"]
        self.assertNotIn("quatrieme", {o["class_level"] for o in options})
        f = pythagore.FAMILIES[2]
        body = {"class_level": "quatrieme", "chapter_id": "Chapitre_8", "notion": f.notion, "family_id": f.id}
        self.assertEqual(self.client.post("/api/practice/generate", json=body, headers=self.headers).status_code, 404)

    def test_classes_existantes_inchangees(self):
        for class_level in ("troisieme", "seconde", "premiere"):
            with self.subTest(class_level=class_level):
                self.assertEqual(self.client.get(f"/api/chapters?class_level={class_level}").status_code, 200)


class TestQuatriemeEnPrevisualisation(_QuatriemeHTTPCase):
    preview = True

    def test_selecteur_et_chapitres(self):
        curricula = self.client.get("/api/curricula").get_json()
        self.assertEqual([c["classLevel"] for c in curricula], ["quatrieme", "troisieme", "seconde", "premiere"])
        data = self.client.get("/api/chapters?class_level=quatrieme").get_json()
        self.assertIn("Chapitre_8", data["chapters"])
        meta = next(c for c in data["chapters_meta"] if c["id"] == "Chapitre_8")
        self.assertEqual(meta["title"], "Théorème de Pythagore")
        self.assertEqual(meta["n_exercises"], len(CURATED) + len(GENERATED))
        self.assertEqual({n["notion"] for n in meta["notions_detail"]}, TITLES)
        self.assertEqual(sorted(int(d) for d in meta["difficulties_available"]), [1, 2, 3, 4])
        # Carte du sélecteur : jamais présentée comme un programme officiel complet.
        self.assertEqual({c["classLevel"]: c["published"] for c in curricula},
                         {"quatrieme": False, "troisieme": True, "seconde": True, "premiere": True})

    def test_notions_dans_l_ordre_pedagogique_du_cours(self):
        chapters_meta = self.client.get("/api/chapters?class_level=quatrieme").get_json()["chapters_meta"]
        meta = next(c for c in chapters_meta if c["id"] == "Chapitre_8")
        ordre_du_cours = [n["title"] for n in CHAPTER["notions"]]
        self.assertEqual([n["notion"] for n in meta["notions_detail"]], ordre_du_cours)
        self.assertEqual(meta["notions_cours"], ordre_du_cours)
        self.assertNotIn("notion_order", meta)  # clé interne, jamais exposée
        # Classes existantes : ordre alphabétique historique, inchangé.
        for class_level in ("troisieme", "seconde", "premiere"):
            for chapter in self.client.get(f"/api/chapters?class_level={class_level}").get_json()["chapters_meta"]:
                notions = [n["notion"] for n in chapter["notions_detail"]]
                with self.subTest(class_level=class_level, chapter=chapter["id"]):
                    self.assertEqual(notions, sorted(notions))

    def test_chatbot_ne_rattache_pas_un_chapitre_prevu_a_pythagore(self):
        from chatbot.services import intent_service

        # Tant qu'un chapitre est seulement PRÉVU, une question sur son sujet
        # n'est rattachée à aucune notion ; une fois rédigé, elle doit l'être à
        # CE chapitre (jamais à Pythagore).
        planned = set(CURRICULUM_REGISTRY_ALL["quatrieme"].planned_chapter_titles)
        for question, planned_title, number in (
            ("Explique-moi le théorème de Thalès", "Théorème de Thalès", 9),
            ("c'est quoi le cosinus ?", "Cosinus", 10),
            ("Comment additionner des fractions ?", "Fractions : comparaison, addition et soustraction", 2),
            ("Comment calculer le volume d'une pyramide ?", "Pyramides, cônes et volumes", 13),
        ):
            detected = intent_service._detect_chapter(question, None, class_level="quatrieme")
            with self.subTest(question=question):
                if planned_title in planned:
                    self.assertEqual(detected, (None, None, "none"))
                else:
                    self.assertEqual(detected[0], f"Chapitre_{number}")
        for question, notion_id in (
            ("Comment calculer une racine carrée ?", "carres-et-racines-carrees"),
            ("Comment savoir si un triangle est rectangle ?", "triangle-rectangle-ou-non"),
            ("Calcule la longueur de l'hypoténuse", "pythagore-calculer-une-longueur"),
        ):
            with self.subTest(question=question):
                self.assertEqual(intent_service._detect_chapter(question, None, class_level="quatrieme")[:2], ("Chapitre_8", notion_id))
        # Même garde à la racine de toute recherche de cours/exercices (sonde
        # de stratégie, contexte RAG, mode dégradé, /api/search...).
        from chatbot import knowledge_engine
        from chatbot.services import search_service

        if "Théorème de Thalès" in planned:
            self.assertEqual(knowledge_engine.search("Explique-moi le théorème de Thalès", class_level="quatrieme"), [])
            self.assertEqual(search_service.search("Explique-moi le théorème de Thalès", class_level="quatrieme"), [])
        self.assertTrue(search_service.search("Explique-moi le théorème de Pythagore", class_level="quatrieme"))
        # Classe complète (aucun chapitre prévu déclaré) : détection inchangée.
        self.assertEqual(
            intent_service._detect_chapter("Explique-moi le théorème de Thalès", None, class_level="troisieme")[0], "Chapitre_14",
        )

    def test_contenu_filtre_par_plan(self):
        attendu = {}
        for plan in ("free", "premium", "ultra"):
            self._plan(plan)
            resp = self.client.get("/api/course-content/quatrieme/Chapitre_8", headers=self.headers)
            self.assertEqual(resp.status_code, 200)
            attendu[plan] = {n["id"]: n for n in resp.get_json()["notions"]}
        for notion_id in NOTION_IDS:
            free, premium, ultra = (attendu[p][notion_id] for p in ("free", "premium", "ultra"))
            with self.subTest(notion=notion_id):
                self.assertEqual({e["niveauAcces"] for e in free["exemples"]}, {"free"})
                self.assertGreater(len(premium["exemples"]), len(free["exemples"]))
                self.assertGreater(len(ultra["exemples"]), len(premium["exemples"]))
                for field in ("explicationSimple", "intuition", "aRetenir", "erreursFrequentesDetail", "exemplesConcrets"):
                    self.assertNotIn(field, free)
                    self.assertIn(field, premium)
                self.assertEqual(len(free["formules"]), 1)
                self.assertEqual(len(premium["formules"]), 2)
                self.assertNotIn("demonstration", premium)
                self.assertEqual("demonstration" in ultra, notion_id != "problemes-avec-pythagore")
                self.assertTrue(free["locked_content"]["premium"] and free["locked_content"]["ultra"])
                self.assertEqual(free["quizExerciseIds"], NOTIONS_BY_ID[notion_id]["quizExerciseIds"])
                self.assertIn("figure", free)
                self.assertNotIn("apercus", ultra)

    def test_mini_quiz_servis_pour_chaque_plan(self):
        for plan in ("free", "premium", "ultra"):
            self._plan(plan)
            for n in CHAPTER["notions"]:
                for q in n["quizExerciseIds"]:
                    resp = self.client.get(f"/api/exercise/{q}?class_level=quatrieme", headers=self.headers)
                    with self.subTest(plan=plan, exercice=q):
                        self.assertEqual(resp.status_code, 200)
                        self.assertEqual(resp.get_json()["exercise"]["notion"], n["title"])

    def test_serie_progression_et_reprise(self):
        load = self.client.post("/api/practice/load", json={"class_level": "quatrieme", "exercise_id": 48301}, headers=self.headers)
        self.assertEqual(load.status_code, 200)
        result = self.client.post("/api/practice/result", json={"class_level": "quatrieme", "exercise_id": 48301, "correct": True}, headers=self.headers)
        self.assertEqual(result.status_code, 200)
        self.assertIn("Chapitre_8", " ".join(result.get_json()["history"]))
        patch = {"status": "done", "quizScore": 2, "quizTotal": 3}
        body = {"class_level": "quatrieme", "chapterId": "Chapitre_8", "notionId": "triangle-rectangle-ou-non", "patch": patch}
        self.assertEqual(self.client.post("/api/course-progress", json=body, headers=self.headers).status_code, 200)
        progress = self.client.get("/api/course-progress?class_level=quatrieme", headers=self.headers).get_json()
        self.assertEqual(progress["Chapitre_8"]["triangle-rectangle-ou-non"]["status"], "done")
        # La progression de 4e ne déborde jamais sur la 3e (même chapter_id possible).
        autre = self.client.get("/api/course-progress?class_level=troisieme", headers=self.headers).get_json()
        self.assertNotIn("triangle-rectangle-ou-non", json.dumps(autre))

    def test_passer_a_la_pratique_par_notion(self):
        for title in TITLES:
            query = urllib.parse.urlencode({"chapter_id": "Chapitre_8", "notion": title, "class_level": "quatrieme", "limit": 20})
            resp = self.client.get(f"/api/search/exercises-by-notion?{query}", headers=self.headers)
            with self.subTest(notion=title):
                self.assertEqual(resp.status_code, 200)
                # Correspondance EXACTE notion du cours ↔ notion des exercices :
                # chaque notion fournit une série complète (plafond de la route : 20).
                self.assertEqual(len(resp.get_json()["results"]), 20)

    def test_generation_sur_mesure_ultra(self):
        self._plan("ultra")
        options = self.client.get("/api/practice/generate/options", headers=self.headers).get_json()["notions"]
        quatrieme = [o for o in options if o["class_level"] == "quatrieme" and o["chapter_id"] == "Chapitre_8"]
        self.assertEqual({o["notion"] for o in quatrieme}, TITLES)
        for option in quatrieme:
            for family in option["families"]:
                body = {"class_level": "quatrieme", "chapter_id": option["chapter_id"], "notion": option["notion"], "family_id": family["family_id"]}
                resp = self.client.post("/api/practice/generate", json=body, headers=self.headers)
                with self.subTest(family=family["family_id"]):
                    self.assertEqual(resp.status_code, 200)
                    self.assertEqual(resp.get_json()["exercise"]["notion"], option["notion"])

    def test_recherche_et_chatbot_au_niveau_quatrieme(self):
        from chatbot import prompt_builder

        resp = self.client.get("/api/search?q=hypoténuse&class_level=quatrieme", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Chapitre_8", json.dumps(resp.get_json(), ensure_ascii=False))
        prompt = prompt_builder.build_system_prompt(
            {"id": 0}, {"responseLength": "normal", "explanationLevel": "auto", "memoryEnabled": False}, class_level="quatrieme",
        )
        self.assertIn("CLASSE DE L'ÉLÈVE : Quatrième (collège)", prompt)
        self.assertIn("Théorème de Pythagore", prompt)
        # Aucun chapitre propre à la 3e ne doit fuiter dans le prompt de 4e
        # (Thalès, d'abord pris comme témoin, est devenu un chapitre de 4e).
        self.assertNotIn("Fonctions affines", prompt)
        self.assertNotIn("trigonométrie", prompt)


if __name__ == "__main__":
    unittest.main()
