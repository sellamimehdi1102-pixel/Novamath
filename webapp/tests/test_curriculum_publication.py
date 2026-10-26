"""
Publication des programmes (chantier "préparation de la Quatrième",
2026-10-24) : un programme déclaré avec `published=False` est en
préparation — jamais servi aux élèves, jamais listé, jamais accessible en
forçant `class_level` (localStorage, URL, corps de requête), et ne bloque
pas le démarrage du serveur tant qu'il n'a pas de contenu.

Aucune classe réelle n'est créée ici : le programme "en préparation" des
tests HTTP est un profil de test qui réutilise les ressources de Troisième
(dataclasses.replace), injecté par patch du registre servi — exactement le
mapping que lisent toutes les routes existantes.
"""
import dataclasses
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock

import curriculum_registry
import curriculum_stats
import db
from curriculum_registry import (
    CURRICULUM_REGISTRY,
    CURRICULUM_REGISTRY_ALL,
    CurriculumIntegrityError,
    CurriculumProfile,
    build_registry,
    parse_preview_ids,
    served_registry,
    validate_registry,
)
from exercise_generator import registry as generator_registry

HIDDEN = "classe_en_preparation"


def _profile(profile_id, courses_dir=None, **overrides):
    return CurriculumProfile(
        id=profile_id, label=overrides.pop("label", f"Profil {profile_id}"),
        courses_dir=courses_dir,
        exercise_bank=Path("dummy_bank.json"), natural_bank=Path("dummy_natural.json"),
        program_file=None, models_dir=None, metadata_dir=None, assets_dir=None,
        **overrides,
    )


class TestPublicationParDefaut(unittest.TestCase):
    """Non-régression : les programmes existants gardent exactement leur
    disponibilité actuelle."""

    def test_programmes_existants_publies(self):
        for profile_id in ("troisieme", "seconde", "premiere"):
            with self.subTest(profile=profile_id):
                self.assertIs(CURRICULUM_REGISTRY_ALL[profile_id].published, True)

    def test_registre_servi_identique_au_registre_complet_et_dans_le_meme_ordre(self):
        # Chantier "Quatrième — chapitre pilote" : "quatrieme" est en
        # préparation ; les trois classes existantes restent servies, dans
        # le même ordre qu'avant son ajout. Séparation des deux Premières
        # (2026-10-26) : "premiere_specifique" est aussi en préparation.
        self.assertEqual(list(CURRICULUM_REGISTRY), ["troisieme", "seconde", "premiere"])
        self.assertEqual(
            list(CURRICULUM_REGISTRY),
            [p for p, profile in CURRICULUM_REGISTRY_ALL.items() if profile.published is True],
        )
        self.assertEqual(
            [p for p, profile in CURRICULUM_REGISTRY_ALL.items() if profile.published is not True],
            ["quatrieme", "premiere_specifique"],
        )

    def test_published_vaut_true_par_defaut(self):
        self.assertIs(_profile("x").published, True)

    def test_school_stage_declare(self):
        self.assertEqual(CURRICULUM_REGISTRY["troisieme"].school_stage, "college")
        self.assertEqual(CURRICULUM_REGISTRY["seconde"].school_stage, "lycee")
        self.assertEqual(CURRICULUM_REGISTRY["premiere"].school_stage, "lycee")

    def test_registre_servi_immuable(self):
        with self.assertRaises(TypeError):
            CURRICULUM_REGISTRY["quatrieme"] = None  # type: ignore[index]


class TestRegistreServi(unittest.TestCase):
    def setUp(self):
        self.registry = build_registry((
            _profile("publie"),
            _profile("prepa", published=False),
            _profile("mal_saisi", published="false"),
        ))

    def test_non_publie_absent(self):
        self.assertEqual(list(served_registry(self.registry)), ["publie"])

    def test_valeur_non_booleenne_ne_publie_jamais(self):
        self.assertNotIn("mal_saisi", served_registry(self.registry))

    def test_previsualisation_explicite(self):
        self.assertEqual(list(served_registry(self.registry, frozenset({"prepa"}))), ["publie", "prepa"])

    def test_parse_preview_ids(self):
        self.assertEqual(parse_preview_ids(None), frozenset())
        self.assertEqual(parse_preview_ids(""), frozenset())
        self.assertEqual(parse_preview_ids(" quatrieme , ,terminale "), frozenset({"quatrieme", "terminale"}))


class TestValidationRegistre(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.vide = self.tmp / "vide"
        self.vide.mkdir()
        self.avec_contenu = self.tmp / "avec_contenu"
        self.avec_contenu.mkdir()
        (self.avec_contenu / "chapitre_1.json").write_text("{}", encoding="utf-8")
        self.dev = {"FLASK_ENV": "development"}

    def tearDown(self):
        self._tmp.cleanup()

    def _validate(self, *profiles, preview=frozenset(), environ=None):
        validate_registry(build_registry(profiles), preview_ids=preview, environ=environ or self.dev)

    def test_registre_reel_valide(self):
        validate_registry()

    def test_classe_publiee_valide(self):
        self._validate(_profile("ok", self.avec_contenu))

    def test_classe_publiee_ressources_manquantes(self):
        for courses_dir in (self.tmp / "absent", self.vide):
            with self.subTest(courses_dir=courses_dir.name):
                with self.assertRaises(CurriculumIntegrityError) as ctx:
                    self._validate(_profile("publiee_vide", courses_dir))
                self.assertIn("publiee_vide", str(ctx.exception))

    def test_classe_non_publiee_en_preparation_sans_contenu(self):
        # Dossier absent ou vide : état normal d'un programme en préparation.
        self._validate(_profile("prepa_absent", self.tmp / "absent", published=False))
        self._validate(_profile("prepa_vide", self.vide, published=False))

    def test_classe_non_publiee_mal_configuree_reste_une_erreur(self):
        with self.assertRaises(CurriculumIntegrityError) as ctx:
            self._validate(_profile("prepa", self.vide, published=False, label=" "))
        self.assertIn("libellé vide", str(ctx.exception))

    def test_configurations_invalides(self):
        cas = {
            "identifiant": _profile("Quatrième"),
            "libellé": _profile("sans_label", label=""),
            "published": _profile("pub_texte", published="false"),
            "school_stage": _profile("etape", school_stage="primaire"),
        }
        for nom, profile in cas.items():
            with self.subTest(cas=nom):
                with self.assertRaises(CurriculumIntegrityError) as ctx:
                    self._validate(profile)
                self.assertIn("Configuration invalide", str(ctx.exception))

    def test_previsualisation_exige_le_contenu(self):
        with self.assertRaises(CurriculumIntegrityError) as ctx:
            self._validate(_profile("prepa", self.vide, published=False), preview=frozenset({"prepa"}))
        self.assertIn("prepa", str(ctx.exception))
        self._validate(_profile("prepa", self.avec_contenu, published=False), preview=frozenset({"prepa"}))

    def test_previsualisation_classe_inconnue(self):
        with self.assertRaises(CurriculumIntegrityError) as ctx:
            self._validate(_profile("ok", self.avec_contenu), preview=frozenset({"inconnue"}))
        self.assertIn("programme inconnu 'inconnue'", str(ctx.exception))

    def test_previsualisation_classe_deja_publiee(self):
        with self.assertRaises(CurriculumIntegrityError) as ctx:
            self._validate(_profile("ok", self.avec_contenu), preview=frozenset({"ok"}))
        self.assertIn("déjà publié", str(ctx.exception))

    def test_previsualisation_interdite_en_production(self):
        prepa = _profile("prepa", self.avec_contenu, published=False)
        with self.assertRaises(CurriculumIntegrityError) as ctx:
            self._validate(prepa, preview=frozenset({"prepa"}), environ={"FLASK_ENV": "production"})
        self.assertIn("interdit en production", str(ctx.exception))

    def test_toutes_les_erreurs_collectees_en_une_fois(self):
        with self.assertRaises(CurriculumIntegrityError) as ctx:
            self._validate(_profile("a_vide", self.vide), _profile("B"), preview=frozenset({"x"}))
        message = str(ctx.exception)
        for attendu in ("a_vide", "'B'", "'x'"):
            self.assertIn(attendu, message)

    def test_registre_explicite_jamais_influence_par_la_variable_d_environnement(self):
        with mock.patch.object(curriculum_registry, "PREVIEW_CURRICULA", frozenset({"inconnue"})):
            validate_registry(build_registry((_profile("ok", self.avec_contenu),)), environ=self.dev)


def _register(client):
    suffix = uuid.uuid4().hex[:12]
    resp = client.post("/api/auth/register", json={
        "email": f"pub{suffix}@gmail.com", "username": f"pub{suffix}", "pseudo": "Test",
        "birth_date": "2000-01-01",
        "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
        "accept_terms": True, "accept_privacy": True,
    })
    user = resp.get_json()["user"]
    return user, {"X-CSRF-Token": client.get_cookie("nm_csrf").value}


class _HiddenClassHTTPCase(unittest.TestCase):
    """Un programme non publié, doté de VRAIES ressources (celles de
    Troisième) : seul le drapeau de publication l'empêche d'être servi —
    preuve que c'est bien ce drapeau qui protège, pas l'absence de contenu."""

    preview = False

    def setUp(self):
        import server
        from chatbot import knowledge_engine

        self.server = server
        self.knowledge_engine = knowledge_engine
        hidden = dataclasses.replace(
            CURRICULUM_REGISTRY_ALL["troisieme"], id=HIDDEN, label="Classe en préparation", published=False,
        )
        all_profiles = build_registry(tuple(CURRICULUM_REGISTRY_ALL.values()) + (hidden,))
        served = served_registry(all_profiles, frozenset({HIDDEN}) if self.preview else frozenset())
        modules = {**generator_registry._MODULES_BY_CLASS_LEVEL, HIDDEN: generator_registry._MODULES_BY_CLASS_LEVEL["troisieme"]}
        for patcher in (
            mock.patch.object(curriculum_registry, "CURRICULUM_REGISTRY_ALL", all_profiles),
            mock.patch.object(curriculum_registry, "CURRICULUM_REGISTRY", served),
            mock.patch.object(curriculum_stats, "CURRICULUM_REGISTRY", served),
            mock.patch.object(generator_registry, "_MODULES_BY_CLASS_LEVEL", modules),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.addCleanup(self._purge_caches)
        curriculum_stats.clear_cache()

        self.client = server.app.test_client()
        self.user, self.headers = _register(self.client)

    def _purge_caches(self):
        curriculum_stats.clear_cache()
        for cache in (
            self.server._class_bank_cache, self.server._level_engine_cache,
            self.knowledge_engine._index_by_class, self.knowledge_engine._by_ids_by_class,
        ):
            cache.pop(HIDDEN, None)


class TestClasseNonPublieeInaccessible(_HiddenClassHTTPCase):
    def test_absente_du_selecteur_et_des_statistiques_publiques(self):
        resp = self.client.get("/api/curricula")
        self.assertEqual(resp.status_code, 200)
        ids = [c["classLevel"] for c in resp.get_json()]
        self.assertEqual(ids, ["troisieme", "seconde", "premiere"])
        self.assertEqual(self.client.get(f"/api/site/stats?class_level={HIDDEN}").status_code, 404)

    def test_routes_get_refusent_la_classe(self):
        urls = [
            f"/api/chapters?class_level={HIDDEN}",
            f"/api/exercise/0?class_level={HIDDEN}",
            f"/api/course-content/{HIDDEN}/Chapitre_1",
            f"/api/course-progress?class_level={HIDDEN}",
            f"/api/chatbot/context-preview?class_level={HIDDEN}",
            f"/api/chatbot/greeting?class_level={HIDDEN}",
            f"/api/chatbot/mentions?q=thales&class_level={HIDDEN}",
            f"/api/search?q=thales&class_level={HIDDEN}",
            f"/api/search/exercises-by-notion?chapter_id=Chapitre_14&notion=Th%C3%A9or%C3%A8me&class_level={HIDDEN}",
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url, headers=self.headers).status_code, 404)

    def test_routes_post_refusent_la_classe_dans_le_corps(self):
        conv = self.client.post("/api/chatbot/conversations", json={}, headers=self.headers).get_json()["conversation"]
        cas = [
            ("/api/course-progress", {"class_level": HIDDEN, "chapterId": "Chapitre_1", "notionId": "x", "patch": {"status": "done"}}),
            ("/api/practice/load", {"class_level": HIDDEN, "exercise_id": 0}),
            ("/api/practice/result", {"class_level": HIDDEN, "exercise_id": 0, "correct": True}),
            (f"/api/chatbot/conversations/{conv['id']}/messages", {"class_level": HIDDEN, "message": "Bonjour"}),
        ]
        for url, body in cas:
            with self.subTest(url=url):
                self.assertEqual(self.client.post(url, json=body, headers=self.headers).status_code, 404)

    def test_aucun_contournement_par_parametre_cookie_ou_entete(self):
        self.client.set_cookie("preview", "true")
        for extra in ("&preview=true", "&preview=1", f"&preview={HIDDEN}"):
            with self.subTest(extra=extra):
                resp = self.client.get(
                    f"/api/chapters?class_level={HIDDEN}{extra}",
                    headers={**self.headers, "X-Preview": "true", "X-Preview-Curricula": HIDDEN},
                )
                self.assertEqual(resp.status_code, 404)

    def test_generation_sur_mesure_refusee_meme_en_ultra(self):
        db.set_stripe_subscription(self.user["id"], "sub_test", "ultra", "active")
        options = self.client.get("/api/practice/generate/options", headers=self.headers).get_json()["notions"]
        self.assertNotIn(HIDDEN, {n["class_level"] for n in options})
        troisieme = next(n for n in options if n["class_level"] == "troisieme")
        body = {**{k: troisieme[k] for k in ("chapter_id", "notion")}, "family_id": troisieme["families"][0]["family_id"]}
        ok = self.client.post("/api/practice/generate", json={**body, "class_level": "troisieme"}, headers=self.headers)
        self.assertEqual(ok.status_code, 200)
        refuse = self.client.post("/api/practice/generate", json={**body, "class_level": HIDDEN}, headers=self.headers)
        self.assertEqual(refuse.status_code, 404)

    def test_classes_existantes_toujours_servies(self):
        for class_level in ("troisieme", "seconde", "premiere"):
            with self.subTest(class_level=class_level):
                self.assertEqual(self.client.get(f"/api/chapters?class_level={class_level}", headers=self.headers).status_code, 200)
                self.assertEqual(self.client.get(f"/api/course-content/{class_level}/Chapitre_1", headers=self.headers).status_code, 200)


class TestClasseNonPublieePrevisualisee(_HiddenClassHTTPCase):
    """Même programme, prévisualisé (variable d'environnement du processus,
    simulée ici par le registre servi) : les MÊMES routes le servent — la
    prévisualisation ne passe par aucun code spécifique dans server.py."""

    preview = True

    def test_routes_ouvertes_en_previsualisation(self):
        ids = [c["classLevel"] for c in self.client.get("/api/curricula").get_json()]
        self.assertIn(HIDDEN, ids)
        self.assertEqual(self.client.get(f"/api/chapters?class_level={HIDDEN}", headers=self.headers).status_code, 200)
        self.assertEqual(self.client.get(f"/api/course-content/{HIDDEN}/Chapitre_1", headers=self.headers).status_code, 200)


if __name__ == "__main__":
    unittest.main()
