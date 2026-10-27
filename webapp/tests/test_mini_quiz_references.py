"""
Correction "mini-quiz défectueux" (2026-10-24) : 27 notions (5 en Troisième,
22 en Première) référençaient des exercices supprimés de la banque — la
Première par la réduction de exercises_bank_premiere.json (2000 -> 815
exercices, commit 4a1e5b7), la Troisième par tools/dedup_troisieme_notions.py
— et cours.js faisait alors disparaître tout le mini-quiz.

Verrous de non-régression, sur les classes réellement servies :
- chaque référence de quiz est servie par GET /api/exercise/<id> (même
  banque que server.py::_class_bank, y compris le sous-ensemble généré de
  Seconde), pour Free, Premium et Ultra ;
- chaque exercice de quiz appartient au chapitre et à la notion du cours ;
- le contenu de cours filtré par plan conserve quizExerciseIds ;
- validate_curriculum_content ne signale aucune erreur bloquante.
"""
import json
import unittest
import uuid

import curriculum_registry
import db
import server
import validate_curriculum_content

# Notion de cours sans exercice propre dans la banque de son chapitre : la
# notion "Vecteurs colinéaires" (Seconde, Chapitre_4, sans repère) s'appuie
# sur l'exercice 52, classé "Condition de colinéarité" au Chapitre_5 dans
# exercises_bank.json — même compétence (alignement par colinéarité
# vectorielle, sans coordonnées). Signalé dans le rapport, non modifié ici.
EXCEPTIONS_CHAPITRE = {("seconde", "condition-de-colinearite"): {52}}


def _courses(profile):
    for path in sorted(profile.courses_dir.glob("chapitre_*.json")):
        chapter = json.loads(path.read_text(encoding="utf-8"))
        for notion in chapter["notions"]:
            yield chapter["chapterId"], notion


class TestReferencesQuiz(unittest.TestCase):
    def test_toutes_les_references_existent_dans_la_banque_servie(self):
        for class_level, profile in curriculum_registry.CURRICULUM_REGISTRY.items():
            served = server._class_bank(class_level)["bank_by_id"]
            missing = [
                (chapter_id, notion["id"], q)
                for chapter_id, notion in _courses(profile)
                for q in notion.get("quizExerciseIds") or []
                if q not in served
            ]
            with self.subTest(class_level=class_level):
                self.assertEqual(missing, [])

    def test_identifiants_entiers_sans_doublon_dans_un_quiz(self):
        for class_level, profile in curriculum_registry.CURRICULUM_REGISTRY.items():
            for chapter_id, notion in _courses(profile):
                ids = notion.get("quizExerciseIds") or []
                with self.subTest(class_level=class_level, notion=notion["id"]):
                    self.assertTrue(all(isinstance(q, int) and not isinstance(q, bool) for q in ids))
                    self.assertEqual(len(ids), len(set(ids)))

    def test_chaque_exercice_appartient_au_chapitre_et_a_la_notion(self):
        for class_level, profile in curriculum_registry.CURRICULUM_REGISTRY.items():
            served = server._class_bank(class_level)["bank_by_id"]
            for chapter_id, notion in _courses(profile):
                ids = notion.get("quizExerciseIds") or []
                tolerated = EXCEPTIONS_CHAPITRE.get((class_level, notion["id"]), set())
                with self.subTest(class_level=class_level, notion=notion["id"]):
                    for q in ids:
                        if q in tolerated:
                            continue
                        self.assertEqual(served[q].get("chapter_id"), chapter_id, f"exercice {q}")
                    # Troisième/Première : libellé de notion identique entre
                    # cours et banque. Seconde : les titres de cours ont été
                    # reformulés ("Les puissances" / "Puissances entières
                    # relatives") — on exige alors que toutes les questions
                    # d'un même quiz relèvent d'une seule notion de la banque.
                    labels = {served[q].get("notion") for q in ids}
                    if class_level == "seconde":
                        self.assertLessEqual(len(labels), 1, labels)
                    else:
                        self.assertEqual(labels, {notion["title"]} if ids else set())

    def test_les_27_notions_corrigees_ont_trois_questions(self):
        corrigees = {
            "troisieme": {
                "criteres-de-divisibilite", "addition-et-soustraction-de-fractions",
                "developper-un-produit-avec-la-simple-distributivite",
                "factoriser-une-somme-ou-une-difference",
                "determiner-une-fonction-affine-a-partir-de-deux-images",
            },
            "premiere": {
                "generalites-sur-les-suites", "sens-de-variation-d-une-suite", "suite-arithmetique",
                "suite-geometrique", "calcul-de-sommes", "variations-d-une-fonction",
                "nombre-derive-et-extremums-locaux", "courbe-representative",
                "nouvelle-notation-et-nombre-e", "proprietes-algebriques",
                "lien-avec-les-suites-geometriques", "reperage-sur-le-cercle-trigonometrique",
                "autres-definitions-et-proprietes",
                "produit-scalaire,-colinearite-et-orthogonalite-de-vecteurs",
                "etude-d-un-ensemble-de-points", "vecteur-normal-a-une-droite", "equation-d-un-cercle",
                "probabilite-conditionnelle", "arbres-ponderes", "notion-d-independance",
                "variables-aleatoires-reelles", "esperance-–-variance-–-ecart-type",
            },
        }
        self.assertEqual(sum(len(v) for v in corrigees.values()), 27)
        for class_level, notion_ids in corrigees.items():
            notions = {n["id"]: n for _, n in _courses(curriculum_registry.CURRICULUM_REGISTRY[class_level])}
            for notion_id in notion_ids:
                with self.subTest(class_level=class_level, notion=notion_id):
                    self.assertEqual(len(notions[notion_id]["quizExerciseIds"]), 3)

    def test_validateur_sans_erreur_bloquante(self):
        for report in validate_curriculum_content.validate(list(curriculum_registry.CURRICULUM_REGISTRY)):
            with self.subTest(class_level=report.class_level):
                self.assertEqual(report.errors, [])


def _register(client):
    suffix = uuid.uuid4().hex[:12]
    resp = client.post("/api/auth/register", json={
        "email": f"quiz{suffix}@gmail.com", "username": f"quiz{suffix}", "pseudo": "Test",
        "birth_date": "2000-01-01",
        "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
        "accept_terms": True, "accept_privacy": True,
    })
    return resp.get_json()["user"]


class TestQuizParPlanHTTP(unittest.TestCase):
    """Le mini-quiz fait partie du contenu Free : chaque exercice référencé
    doit être servi, et quizExerciseIds conservé par le filtrage du cours,
    quel que soit le plan."""

    def test_exercices_et_references_servis_pour_free_premium_ultra(self):
        for plan in ("free", "premium", "ultra"):
            client = server.app.test_client()
            user = _register(client)
            if plan != "free":
                db.set_stripe_subscription(user["id"], "sub_test", plan, "active")
            for class_level, profile in curriculum_registry.CURRICULUM_REGISTRY.items():
                with self.subTest(plan=plan, class_level=class_level):
                    for path in sorted(profile.courses_dir.glob("chapitre_*.json")):
                        source = json.loads(path.read_text(encoding="utf-8"))
                        resp = client.get(f"/api/course-content/{class_level}/{source['chapterId']}")
                        self.assertEqual(resp.status_code, 200)
                        served = {n["id"]: n.get("quizExerciseIds") for n in resp.get_json()["notions"]}
                        for notion in source["notions"]:
                            self.assertEqual(served[notion["id"]], notion.get("quizExerciseIds"))
                            for q in notion.get("quizExerciseIds") or []:
                                r = client.get(f"/api/exercise/{q}?class_level={class_level}")
                                self.assertEqual(r.status_code, 200, f"{plan} {class_level} {notion['id']} {q}")


if __name__ == "__main__":
    unittest.main()
