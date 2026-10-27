"""
Chantier "préparation de la Quatrième" (2026-10-24) :

- le prompt système nomme désormais la classe active de l'élève (jusqu'ici
  `class_level` ne servait qu'à filtrer l'historique) et oriente le niveau
  sans interdire une demande explicite d'approfondissement ;
- chatbot.check_cours_generic_content audite les dossiers réels du registre
  (l'ancienne liste pointait vers des dossiers vidés : faux "0 problème") ;
- validate_curriculum_content applique les validations à chaque programme
  du registre et sépare erreurs bloquantes et avertissements pédagogiques.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import curriculum_registry
import validate_curriculum_content as vcc
from chatbot import check_cours_generic_content, knowledge_engine, prompt_builder
from curriculum_registry import CURRICULUM_REGISTRY, CURRICULUM_REGISTRY_ALL, CurriculumProfile

SETTINGS = {"responseLength": "normal", "explanationLevel": "auto", "memoryEnabled": False}


def _prompt(class_level):
    return prompt_builder.build_system_prompt({"id": 0}, SETTINGS, class_level=class_level)


class TestClasseDansLePrompt(unittest.TestCase):
    def test_chaque_classe_servie_est_nommee(self):
        for class_level, profile in CURRICULUM_REGISTRY.items():
            with self.subTest(class_level=class_level):
                prompt = _prompt(class_level)
                self.assertIn(f"CLASSE DE L'ÉLÈVE : {profile.label}", prompt)

    def test_etape_de_scolarite(self):
        self.assertIn("Troisième (collège)", _prompt("troisieme"))
        self.assertIn("Seconde (lycée)", _prompt("seconde"))

    def test_chapitres_de_la_classe_et_pas_des_autres(self):
        prompt = _prompt("troisieme")
        self.assertIn("Théorème de Thalès", prompt)
        self.assertNotIn("Vecteurs et repère", prompt)  # chapitre de Seconde

    def test_titres_de_remplissage_jamais_listes(self):
        self.assertNotIn("Chapitre 1 ;", _prompt("premiere"))

    def test_approfondissement_explicite_autorise(self):
        prompt = _prompt("troisieme")
        self.assertIn("N'introduis pas spontanément", prompt)
        self.assertIn("demande explicitement un approfondissement", prompt)
        self.assertIn("réponds à sa demande", prompt)

    def test_classe_absente_inconnue_ou_non_servie_aucune_consigne(self):
        for class_level in (None, "", "terminale"):
            with self.subTest(class_level=class_level):
                self.assertNotIn("CLASSE DE L'ÉLÈVE", _prompt(class_level))
        prepa = dict(CURRICULUM_REGISTRY)
        prepa.pop("troisieme")
        with mock.patch.object(curriculum_registry, "CURRICULUM_REGISTRY", prepa):
            self.assertNotIn("CLASSE DE L'ÉLÈVE", _prompt("troisieme"))

    def test_classe_transmise_meme_si_la_memoire_de_profil_est_desactivee(self):
        prompt = _prompt("seconde")
        self.assertIn("Mémoire de profil désactivée", prompt)
        self.assertIn("CLASSE DE L'ÉLÈVE : Seconde", prompt)

    def test_conversation_manager_transmet_class_level(self):
        # Les deux appels réels (stream + regenerate) passent class_level.
        source = Path(prompt_builder.__file__).with_name("conversation_manager.py").read_text(encoding="utf-8")
        self.assertEqual(source.count("class_level=rag_class_level, topic_label=topic_label"), 2)


class TestListChapterTitles(unittest.TestCase):
    def test_ordre_numerique(self):
        titres = knowledge_engine.list_chapter_titles("troisieme")
        self.assertEqual(len(titres), 15)
        self.assertEqual(titres[0], "Nombres entiers")
        self.assertEqual(titres[-1], "Solides de l'espace")


class TestCheckCoursGenericContent(unittest.TestCase):
    def test_dossiers_par_defaut_issus_du_registre_et_existants(self):
        dirs = check_cours_generic_content.default_dirs()
        self.assertEqual(dirs, [p.courses_dir for p in CURRICULUM_REGISTRY_ALL.values() if p.courses_dir])
        for d in dirs:
            self.assertTrue(d.is_dir(), d)

    def test_cible_par_identifiant_de_classe(self):
        self.assertEqual(check_cours_generic_content.resolve_target("seconde"), CURRICULUM_REGISTRY["seconde"].courses_dir)

    def test_dossier_introuvable_jamais_silencieux(self):
        with mock.patch("builtins.print"):
            self.assertEqual(check_cours_generic_content.main(["/chemin/inexistant"]), 2)


def _notion(nid, **overrides):
    notion = {
        "id": nid, "title": nid, "definition": "Une définition.",
        "figure": {"kind": "geom"}, "quizExerciseIds": [1],
        "exemples": [{"id": "e1", "niveauAcces": "free"}],
    }
    notion.update(overrides)
    return notion


class TestValidateCurriculumContent(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.courses = self.root / "cours"
        self.courses.mkdir()
        self.bank = self.root / "bank.json"
        self.bank.write_text(json.dumps([{"id": 1, "chapter_id": "Chapitre_1"}, {"id": 2, "chapter_id": "Chapitre_2"}]), encoding="utf-8")
        self.kinds = vcc.supported_figure_kinds()

    def tearDown(self):
        self._tmp.cleanup()

    def _chapter(self, n, notions, chapter_id=None, title="Titre"):
        data = {"chapterId": chapter_id or f"Chapitre_{n}", "title": title, "notions": notions}
        (self.courses / f"chapitre_{n}.json").write_text(json.dumps(data), encoding="utf-8")

    def _profile(self, published=True, bank=True, courses=True):
        return CurriculumProfile(
            id="test_classe", label="Test", courses_dir=self.courses if courses else self.root / "absent",
            exercise_bank=self.bank if bank else self.root / "absente.json", natural_bank=self.root / "n.json",
            program_file=None, models_dir=None, metadata_dir=None, assets_dir=None, published=published,
        )

    def _report(self, **kwargs):
        chapter = kwargs.pop("chapter", None)
        return vcc.validate_class(self._profile(**kwargs), chapter=chapter, figure_kinds=self.kinds)

    def test_types_de_figures_lus_dans_le_moteur_de_rendu(self):
        self.assertTrue({"geom", "tree", "numberline", "solid"} <= self.kinds)

    def test_contenu_valide_sans_erreur(self):
        self._chapter(1, [_notion("a")])
        self.assertEqual(self._report().errors, [])

    def test_erreurs_bloquantes(self):
        self._chapter(1, [
            _notion("a", quizExerciseIds=[1, 999]),
            _notion("b", figure={"kind": "inconnu"}),
            _notion("c", exemples=[{"id": "e", "niveauAcces": "gratuit"}]),
            _notion("d", apercus=[{"niveau": "free"}]),
            _notion("e", definition=""),
        ])
        self._chapter(2, [_notion("a", quizExerciseIds=[2])], chapter_id="Chapitre_9")
        errors = "\n".join(self._report().errors)
        for attendu in ("[999]", "'inconnu'", "'gratuit'", "apercus[0]", "« definition »", "déjà utilisé", "attendu 'Chapitre_2'"):
            self.assertIn(attendu, errors)

    def test_avertissements_pedagogiques_non_bloquants(self):
        self._chapter(1, [_notion("a", figure=None, quizExerciseIds=[2], exemples=[{"id": "e", "niveauAcces": "premium"}])], title="Chapitre 1")
        report = self._report()
        self.assertEqual(report.errors, [])
        warnings = "\n".join(report.warnings)
        for attendu in ("aucune figure", "aucun exemple accessible en Free", "autre chapitre", "remplissage"):
            self.assertIn(attendu, warnings)

    def test_banque_absente_references_non_verifiees(self):
        self._chapter(1, [_notion("a", quizExerciseIds=[999])])
        report = self._report(bank=False)
        self.assertEqual(report.errors, [])
        self.assertIn("non vérifiées", "\n".join(report.warnings))

    def test_cible_un_seul_chapitre_mais_unicite_sur_toute_la_classe(self):
        self._chapter(1, [_notion("a")])
        self._chapter(2, [_notion("a", quizExerciseIds=[2])])
        report = self._report(chapter="Chapitre_2")
        self.assertEqual(report.chapters, 1)
        self.assertIn("déjà utilisé", "\n".join(report.errors))
        self.assertIn("introuvable", "\n".join(self._report(chapter="7").errors))

    def test_classe_en_preparation_sans_contenu_ignoree(self):
        report = self._report(published=False, courses=False)
        self.assertEqual(report.errors, [])
        self.assertEqual(report.skipped, "aucun contenu de cours pour l'instant")
        self.assertEqual(report.status, "en préparation (non publié)")

    def test_classe_publiee_sans_contenu_bloquante(self):
        self.assertTrue(self._report(courses=False).errors)

    def test_tous_les_programmes_du_registre_sont_parcourus(self):
        reports = vcc.validate()
        self.assertEqual([r.class_level for r in reports], list(CURRICULUM_REGISTRY_ALL))
        for r in reports:
            self.assertGreater(r.notions, 0, r.class_level)

    def test_programme_inconnu(self):
        with self.assertRaises(KeyError):
            vcc.validate(["terminale"])
        with mock.patch("builtins.print"):
            self.assertEqual(vcc.main(["terminale"]), 2)


if __name__ == "__main__":
    unittest.main()
