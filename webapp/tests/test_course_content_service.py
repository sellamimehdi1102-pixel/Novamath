"""
Suite du filtrage de contenu pédagogique par plan (Chantier "Répartition du
contenu des cours par plan", 2026-08-26) : webapp/course_content_service.py
(filtrage pur) et webapp/server.py::api_course_content (câblage HTTP réel).

Deux niveaux, comme le reste du projet (voir test_quota_service.py +
test_chatbot_quota_integration.py) :
- TestFilterNotion* : filter_notion() en isolation, sans DB ni HTTP.
- TestApiCourseContent* : la vraie route, server.app.test_client(), pour
  vérifier le câblage (401/404, format JSON réel, Owner, non-régression du
  chatbot/quotas/prix — hors de portée de ce fichier mais confirmée ne pas
  avoir bougé par les suites dédiées).
"""
import os
import random
import unittest

import curriculum_registry
import db
import owner_test_plan_service
import server
from course_content_service import filter_notion
from plan_service import Plan


def _register(client):
    email = f"test{random.randint(1_000_000, 9_999_999)}@gmail.com"
    username = f"testuser{random.randint(100_000, 999_999)}"
    resp = client.post("/api/auth/register", json={
        "email": email, "username": username, "pseudo": "Test",
        "birth_date": "2000-01-01",
        "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
        "accept_terms": True, "accept_privacy": True,
    })
    user = resp.get_json()["user"]
    csrf = client.get_cookie("nm_csrf").value
    return user, {"X-CSRF-Token": csrf}


def _set_plan(user_id, plan_value):
    db.set_stripe_subscription(user_id, "sub_test", plan_value, "active")


_RICH_NOTION = {
    "id": "notion-riche",
    "title": "Notion riche",
    "intro": "Intro",
    "objectif": "Objectif",
    "definition": "Définition",
    "reglesImportantes": ["Règle 1", "Règle 2"],
    "formules": [{"expression": "F1"}, {"expression": "F2"}, {"expression": "F3"}],
    "methode": {
        "etapes": [{"texte": "Étape normale"}],
        "etapesParNiveau": {
            "debutant": [{"texte": "Étape débutant"}],
            "normal": [{"texte": "Étape normale"}],
            "rapide": [{"texte": "Étape rapide"}],
        },
    },
    "exemples": [{"enonce": "Exemple 1"}, {"enonce": "Exemple 2"}, {"enonce": "Exemple 3"}],
    "erreursFrequentes": ["Erreur 1"],
    "erreursFrequentesDetail": [{"pourquoi": "..."}],
    "astuce": "Astuce",
    "explicationSimple": "Explication simple",
    "intuition": "Intuition",
    "exemplesConcrets": ["Concret 1"],
    "aRetenir": ["Point 1", "Point 2"],
    "demonstration": {"titre": "Pourquoi ?", "etapes": [{"texte": "..."}], "conclusion": "..."},
    "figure": {"kind": "geom", "viewBox": [0, 0, 1, 1]},
    "quizExerciseIds": [1, 2],
}

_MINIMAL_NOTION = {
    "id": "notion-minimale",
    "title": "Notion minimale",
    "intro": "Intro",
    "definition": "Définition",
    "reglesImportantes": ["Règle unique"],
    "exemples": [{"enonce": "Seul exemple"}],
    "quizExerciseIds": [1],
    # Pas de formules, pas de methode, pas de figure, pas de demonstration,
    # pas de champs Premium+ — représente une notion "pauvre" comme
    # racine-carree avant l'audit.
}


class TestFilterNotionFree(unittest.TestCase):
    def setUp(self):
        self.result = filter_notion(_RICH_NOTION, Plan.FREE)

    def test_recoit_le_contenu_essentiel(self):
        for field in ("intro", "objectif", "definition", "reglesImportantes", "astuce", "figure", "quizExerciseIds"):
            with self.subTest(field=field):
                self.assertEqual(self.result[field], _RICH_NOTION[field])

    def test_recoit_exactement_le_premier_exemple(self):
        self.assertEqual(self.result["exemples"], [_RICH_NOTION["exemples"][0]])

    def test_recoit_exactement_la_premiere_formule(self):
        self.assertEqual(self.result["formules"], [_RICH_NOTION["formules"][0]])

    def test_recoit_le_profil_methode_normal(self):
        self.assertEqual(self.result["methode"]["etapesParNiveau"]["normal"], _RICH_NOTION["methode"]["etapesParNiveau"]["normal"])

    def test_ne_recoit_aucun_contenu_premium(self):
        self.assertNotIn("explicationSimple", self.result)
        self.assertNotIn("intuition", self.result)
        self.assertNotIn("exemplesConcrets", self.result)
        self.assertNotIn("erreursFrequentesDetail", self.result)
        self.assertNotIn("aRetenir", self.result)
        self.assertEqual(self.result["methode"]["etapesParNiveau"]["debutant"], [])
        self.assertEqual(self.result["methode"]["etapesParNiveau"]["rapide"], [])

    def test_ne_recoit_aucun_contenu_ultra(self):
        self.assertNotIn("demonstration", self.result)

    def test_locked_content_signale_premium_et_ultra(self):
        locked = self.result["locked_content"]
        self.assertTrue(locked["premium"])
        self.assertEqual(locked["premium_extra_examples"], 2)
        self.assertEqual(locked["premium_extra_formulas"], 2)
        self.assertTrue(locked["ultra"])


class TestFilterNotionPremium(unittest.TestCase):
    def setUp(self):
        self.result = filter_notion(_RICH_NOTION, Plan.PREMIUM)

    def test_recoit_le_contenu_free(self):
        self.assertEqual(self.result["definition"], _RICH_NOTION["definition"])
        self.assertEqual(self.result["reglesImportantes"], _RICH_NOTION["reglesImportantes"])

    def test_recoit_le_contenu_premium(self):
        self.assertEqual(self.result["exemples"], _RICH_NOTION["exemples"])
        self.assertEqual(self.result["formules"], _RICH_NOTION["formules"])
        self.assertEqual(self.result["explicationSimple"], _RICH_NOTION["explicationSimple"])
        self.assertEqual(self.result["intuition"], _RICH_NOTION["intuition"])
        self.assertEqual(self.result["exemplesConcrets"], _RICH_NOTION["exemplesConcrets"])
        self.assertEqual(self.result["erreursFrequentesDetail"], _RICH_NOTION["erreursFrequentesDetail"])
        self.assertEqual(self.result["aRetenir"], _RICH_NOTION["aRetenir"])
        self.assertEqual(self.result["methode"]["etapesParNiveau"]["debutant"], _RICH_NOTION["methode"]["etapesParNiveau"]["debutant"])
        self.assertEqual(self.result["methode"]["etapesParNiveau"]["rapide"], _RICH_NOTION["methode"]["etapesParNiveau"]["rapide"])

    def test_ne_recoit_aucun_contenu_ultra(self):
        self.assertNotIn("demonstration", self.result)

    def test_locked_content_signale_uniquement_ultra(self):
        locked = self.result["locked_content"]
        self.assertFalse(locked["premium"])
        self.assertEqual(locked["premium_extra_examples"], 0)
        self.assertTrue(locked["ultra"])


class TestFilterNotionUltra(unittest.TestCase):
    def setUp(self):
        self.result = filter_notion(_RICH_NOTION, Plan.ULTRA)

    def test_recoit_absolument_tout(self):
        for field in ("exemples", "formules", "explicationSimple", "intuition", "exemplesConcrets", "erreursFrequentesDetail", "aRetenir", "demonstration"):
            with self.subTest(field=field):
                self.assertEqual(self.result[field], _RICH_NOTION[field])

    def test_locked_content_ne_signale_rien(self):
        locked = self.result["locked_content"]
        self.assertFalse(locked["premium"])
        self.assertFalse(locked["ultra"])


class TestFilterNotionContenuManquant(unittest.TestCase):
    """§5 du chantier : un champ absent ne doit provoquer aucune erreur, et le
    comportement doit rester identique à aujourd'hui (rien à retirer =
    aucune trace de filtrage)."""

    def test_notion_sans_demonstration_fonctionne(self):
        result = filter_notion(_MINIMAL_NOTION, Plan.FREE)
        self.assertNotIn("demonstration", result)
        self.assertFalse(result["locked_content"]["ultra"])  # rien à débloquer, pas de fausse promesse

    def test_notion_sans_exemples_supplementaires_fonctionne(self):
        result = filter_notion(_MINIMAL_NOTION, Plan.FREE)
        self.assertEqual(result["exemples"], _MINIMAL_NOTION["exemples"])
        self.assertEqual(result["locked_content"]["premium_extra_examples"], 0)
        self.assertFalse(result["locked_content"]["premium"])

    def test_figure_absente_ne_plante_pas(self):
        result = filter_notion(_MINIMAL_NOTION, Plan.FREE)
        self.assertNotIn("figure", result)

    def test_methode_absente_ne_plante_pas(self):
        result = filter_notion(_MINIMAL_NOTION, Plan.PREMIUM)
        self.assertNotIn("methode", result)


class TestFilterNotionFigureResteFree(unittest.TestCase):
    def test_figure_toujours_presente_meme_en_free(self):
        result = filter_notion(_RICH_NOTION, Plan.FREE)
        self.assertEqual(result["figure"], _RICH_NOTION["figure"])


# ── Refonte pédagogique des cours (2026-10-23) : classification explicite
# par exemple (`niveauAcces`), au lieu du seul repli positionnel. Notion avec
# 3 exemples "essentiels" (une règle chacun) classés "free", et 2 exemples
# "variante/piège" classés "premium" — exactement le cas réel du cours pilote
# "Composition de fonctions et dérivation" (3 règles : puissance, racine,
# inverse, chacune avec un exemple gratuit, plus 2 exemples Premium).
_MULTI_REGLE_NOTION = {
    "id": "notion-multi-regle",
    "title": "Notion à plusieurs règles essentielles",
    "intro": "Intro",
    "definition": "Définition",
    "reglesImportantes": ["Règle A", "Règle B", "Règle C"],
    "exemples": [
        {"id": "ex-a", "enonce": "Règle A — essentiel", "niveauAcces": "free"},
        {"id": "ex-b", "enonce": "Règle B — essentiel", "niveauAcces": "free"},
        {"id": "ex-piege-a", "enonce": "Règle A — piège", "niveauAcces": "premium"},
        {"id": "ex-c", "enonce": "Règle C — essentiel", "niveauAcces": "free"},
        {"id": "ex-approfondi", "enonce": "Approfondissement", "niveauAcces": "ultra"},
    ],
    "quizExerciseIds": [1],
}


class TestFilterNotionNiveauAccesExplicite(unittest.TestCase):
    """Un exemple classé explicitement (niveauAcces) n'est plus soumis au
    repli positionnel : sa position dans la liste n'a plus d'importance."""

    def test_free_recoit_tous_les_exemples_classes_free_quelle_que_soit_leur_position(self):
        result = filter_notion(_MULTI_REGLE_NOTION, Plan.FREE)
        ids = [ex["id"] for ex in result["exemples"]]
        self.assertEqual(ids, ["ex-a", "ex-b", "ex-c"])

    def test_free_ne_recoit_ni_lexemple_premium_ni_lexemple_ultra(self):
        result = filter_notion(_MULTI_REGLE_NOTION, Plan.FREE)
        ids = [ex["id"] for ex in result["exemples"]]
        self.assertNotIn("ex-piege-a", ids)
        self.assertNotIn("ex-approfondi", ids)

    def test_free_aucune_fuite_de_contenu_payant_dans_la_reponse_serialisee(self):
        """Le contenu texte d'un exemple payant ne doit apparaître NULLE
        PART dans la réponse Free, pas seulement absent de `exemples` — vérifié
        sur la sérialisation JSON complète, pas seulement sur la clé."""
        import json as _json
        result = filter_notion(_MULTI_REGLE_NOTION, Plan.FREE)
        serialized = _json.dumps(result, ensure_ascii=False)
        self.assertNotIn("Règle A — piège", serialized)
        self.assertNotIn("Approfondissement", serialized)
        self.assertNotIn("ex-piege-a", serialized)
        self.assertNotIn("ex-approfondi", serialized)

    def test_premium_recoit_free_et_premium_mais_pas_ultra(self):
        result = filter_notion(_MULTI_REGLE_NOTION, Plan.PREMIUM)
        ids = [ex["id"] for ex in result["exemples"]]
        self.assertEqual(set(ids), {"ex-a", "ex-b", "ex-piege-a", "ex-c"})
        self.assertNotIn("ex-approfondi", ids)

    def test_premium_aucune_fuite_de_contenu_ultra(self):
        import json as _json
        result = filter_notion(_MULTI_REGLE_NOTION, Plan.PREMIUM)
        serialized = _json.dumps(result, ensure_ascii=False)
        self.assertNotIn("Approfondissement", serialized)
        self.assertNotIn("ex-approfondi", serialized)

    def test_ultra_recoit_absolument_tous_les_exemples(self):
        result = filter_notion(_MULTI_REGLE_NOTION, Plan.ULTRA)
        ids = [ex["id"] for ex in result["exemples"]]
        self.assertEqual(set(ids), {"ex-a", "ex-b", "ex-piege-a", "ex-c", "ex-approfondi"})

    def test_locked_content_free_signale_premium_et_ultra_avec_le_bon_compte(self):
        locked = filter_notion(_MULTI_REGLE_NOTION, Plan.FREE)["locked_content"]
        self.assertTrue(locked["premium"])
        self.assertEqual(locked["premium_extra_examples"], 1)
        self.assertTrue(locked["ultra"])

    def test_locked_content_premium_signale_uniquement_ultra(self):
        locked = filter_notion(_MULTI_REGLE_NOTION, Plan.PREMIUM)["locked_content"]
        self.assertFalse(locked["premium"])
        self.assertEqual(locked["premium_extra_examples"], 0)
        self.assertTrue(locked["ultra"])

    def test_questionseclair_ancree_sur_un_exemple_retire_disparait_en_free(self):
        """Bug trouvé lors de l'audit du pilote : une question éclair ancrée
        sur un exemple Premium/Ultra (apres="exemple:<id>") ne doit jamais
        rester visible une fois cet exemple retiré — sinon son id et son
        énoncé (qui peut décrire indirectement le contenu verrouillé) fuient
        dans la réponse Free."""
        notion = {
            **_MULTI_REGLE_NOTION,
            "questionsEclair": [
                {"apres": "pourquoi", "question": "Q libre", "piste": "P"},
                {"apres": "exemple:ex-a", "question": "Q sur exemple free", "piste": "P"},
                {"apres": "exemple:ex-piege-a", "question": "Q sur exemple premium", "piste": "P"},
                {"apres": "exemple:ex-approfondi", "question": "Q sur exemple ultra", "piste": "P"},
            ],
        }
        result = filter_notion(notion, Plan.FREE)
        anchors = [q["apres"] for q in result["questionsEclair"]]
        self.assertEqual(anchors, ["pourquoi", "exemple:ex-a"])
        serialized = __import__("json").dumps(result, ensure_ascii=False)
        self.assertNotIn("Q sur exemple premium", serialized)
        self.assertNotIn("Q sur exemple ultra", serialized)

    def test_questionseclair_ancree_sur_un_exemple_vise_reste_visible_si_lexemple_est_accessible(self):
        notion = {
            **_MULTI_REGLE_NOTION,
            "questionsEclair": [{"apres": "exemple:ex-piege-a", "question": "Q", "piste": "P"}],
        }
        result = filter_notion(notion, Plan.PREMIUM)
        self.assertEqual([q["apres"] for q in result["questionsEclair"]], ["exemple:ex-piege-a"])

    def test_une_valeur_niveauacces_invalide_retombe_sur_le_repli_positionnel(self):
        """Une faute de frappe ("Free" au lieu de "free", etc.) ne doit
        jamais exposer accidentellement du contenu : repli sur la règle
        positionnelle historique, jamais un défaut permissif."""
        notion = {
            **_MINIMAL_NOTION,
            "exemples": [
                {"id": "ex1", "enonce": "Un", "niveauAcces": "Free"},
                {"id": "ex2", "enonce": "Deux", "niveauAcces": "bogus"},
            ],
        }
        result = filter_notion(notion, Plan.FREE)
        ids = [ex["id"] for ex in result["exemples"]]
        # Repli positionnel : index 0 = free (gardé), index 1 = premium (retiré).
        self.assertEqual(ids, ["ex1"])


# ── Rendre visibles les contenus Premium/Ultra verrouillés (2026-10-23) :
# champsLibresForces (champs scalaires exemptés du verrou Premium pour une
# notion précise) et apercus (métadonnées publiques décrivant un contenu
# verrouillé, jamais le contenu lui-même). ──────────────────────────────────
_NOTION_AVEC_CHAMPS_FORCES = {
    **_MINIMAL_NOTION,
    "explicationSimple": "Explication essentielle pour cette notion.",
    "intuition": "Intuition essentielle pour cette notion.",
    "aRetenir": ["Point essentiel 1"],
    "erreursFrequentesDetail": [{"description": "Erreur", "pourquoi": "..."}],
    "erreursFrequentes": ["Erreur"],
    "exemplesConcrets": ["Concret essentiel"],
    "champsLibresForces": ["explicationSimple", "intuition", "aRetenir"],
    # erreursFrequentesDetail et exemplesConcrets ne sont volontairement PAS
    # dans la liste : doivent rester Premium, pour vérifier que seuls les
    # champs explicitement listés sont exemptés.
}

_NOTION_AVEC_APERCUS = {
    **_MINIMAL_NOTION,
    "exemples": [{"id": "ex-free", "enonce": "Libre", "niveauAcces": "free"}],
    "demonstration": {"titre": "Pourquoi ?", "etapes": [{"texte": "..."}], "conclusion": "..."},
    "apercus": [
        {"id": "ap1", "section": "exemple", "niveau": "premium", "titre": "2 exemples de plus", "description": "Deux exemples supplémentaires."},
        {"id": "ap2", "section": "exemple", "niveau": "ultra", "titre": "La démonstration", "description": "Pourquoi la formule est vraie."},
        {"id": "ap-invalide", "section": "exemple", "niveau": "gold", "titre": "Palier inexistant", "description": "..."},
    ],
}


class TestFilterNotionChampsLibresForces(unittest.TestCase):
    def test_un_champ_liste_dans_champslibresforces_reste_visible_en_free(self):
        result = filter_notion(_NOTION_AVEC_CHAMPS_FORCES, Plan.FREE)
        self.assertEqual(result["explicationSimple"], _NOTION_AVEC_CHAMPS_FORCES["explicationSimple"])
        self.assertEqual(result["intuition"], _NOTION_AVEC_CHAMPS_FORCES["intuition"])
        self.assertEqual(result["aRetenir"], _NOTION_AVEC_CHAMPS_FORCES["aRetenir"])

    def test_un_champ_non_liste_reste_premium_meme_si_dautres_sont_forces(self):
        result = filter_notion(_NOTION_AVEC_CHAMPS_FORCES, Plan.FREE)
        self.assertNotIn("erreursFrequentesDetail", result)
        self.assertNotIn("exemplesConcrets", result)

    def test_sans_champslibresforces_comportement_strictement_inchange(self):
        """Non-régression explicite : une notion sans ce champ (152 des 153
        notions existantes) garde exactement le comportement d'avant."""
        notion = {k: v for k, v in _NOTION_AVEC_CHAMPS_FORCES.items() if k != "champsLibresForces"}
        result = filter_notion(notion, Plan.FREE)
        self.assertNotIn("explicationSimple", result)
        self.assertNotIn("intuition", result)
        self.assertNotIn("aRetenir", result)


class TestFilterNotionApercus(unittest.TestCase):
    def test_free_recoit_les_apercus_premium_et_ultra(self):
        result = filter_notion(_NOTION_AVEC_APERCUS, Plan.FREE)
        niveaux = {a["niveau"] for a in result["apercus"]}
        self.assertEqual(niveaux, {"premium", "ultra"})

    def test_premium_ne_recoit_que_lapercu_ultra(self):
        result = filter_notion(_NOTION_AVEC_APERCUS, Plan.PREMIUM)
        niveaux = {a["niveau"] for a in result["apercus"]}
        self.assertEqual(niveaux, {"ultra"})

    def test_ultra_ne_recoit_aucun_apercu(self):
        result = filter_notion(_NOTION_AVEC_APERCUS, Plan.ULTRA)
        self.assertNotIn("apercus", result)

    def test_un_apercu_avec_un_niveau_invalide_est_ignore(self):
        result = filter_notion(_NOTION_AVEC_APERCUS, Plan.FREE)
        ids = [a["id"] for a in result["apercus"]]
        self.assertNotIn("ap-invalide", ids)

    def test_un_apercu_ne_contient_jamais_le_contenu_protege_lui_meme(self):
        """Un aperçu n'est que métadonnée (titre/description) — jamais le
        contenu réel (ici la démonstration) ne doit apparaître dans la
        réponse Free, ni dans l'aperçu ni ailleurs."""
        result = filter_notion(_NOTION_AVEC_APERCUS, Plan.FREE)
        serialized = __import__("json").dumps(result, ensure_ascii=False)
        self.assertNotIn("Pourquoi ?", serialized)  # titre interne de demonstration, pas de l'apercu
        self.assertNotIn("etapes", str(result.get("demonstration", {})))
        self.assertNotIn("demonstration", result)

    def test_notion_sans_apercus_ne_recoit_pas_cette_cle(self):
        result = filter_notion(_MINIMAL_NOTION, Plan.FREE)
        self.assertNotIn("apercus", result)


class ApiCourseContentTestCase(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()
        self.user, self.headers = _register(self.client)


class TestApiCourseContentAuth(ApiCourseContentTestCase):
    def test_non_connecte_ne_recoit_rien(self):
        anon = server.app.test_client()
        resp = anon.get("/api/course-content/seconde/Chapitre_1")
        self.assertEqual(resp.status_code, 401)
        self.assertNotIn("notions", resp.get_json() or {})

    def test_chapitre_inconnu_404(self):
        resp = self.client.get("/api/course-content/seconde/Chapitre_9999", headers=self.headers)
        self.assertEqual(resp.status_code, 404)

    def test_classe_inconnue_404(self):
        resp = self.client.get("/api/course-content/inconnue/Chapitre_1", headers=self.headers)
        self.assertEqual(resp.status_code, 404)

    def test_tentative_de_traversee_de_chemin_404(self):
        resp = self.client.get("/api/course-content/seconde/..%2f..%2fnovamath", headers=self.headers)
        self.assertIn(resp.status_code, (404, 400))


class TestApiCourseContentParPlan(ApiCourseContentTestCase):
    def test_free_recoit_le_contenu_essentiel_uniquement(self):
        # Seconde, Première ET Troisième ont désormais chacune leur contenu
        # classé notion par notion (refontes pédagogiques successives) : plus
        # aucun chapitre réel ne témoigne du comportement par défaut (aucun
        # champsLibresForces, aucun niveauAcces explicite, repli positionnel
        # sur les exemples). On teste donc directement filter_notion() avec
        # une notion synthétique non classée, robuste à toute évolution future
        # du contenu réel — c'est exactement ce que ce test cherche à vérifier :
        # le COMPORTEMENT PAR DÉFAUT du filtrage, pas un contenu précis.
        notion_non_classee = {
            "id": "notion-test-non-classee",
            "title": "Notion de test",
            "aRetenir": ["Un point à retenir."],
            "demonstration": {"titre": "Démonstration", "etapes": [], "conclusion": ""},
            "exemples": [{"id": "ex1", "titre": "Exemple 1"}, {"id": "ex2", "titre": "Exemple 2"}],
        }
        filtered = filter_notion(notion_non_classee, Plan.FREE)
        self.assertNotIn("aRetenir", filtered)
        self.assertNotIn("demonstration", filtered)
        self.assertLessEqual(len(filtered["exemples"]), 1)

    def test_premium_recoit_free_plus_premium(self):
        _set_plan(self.user["id"], "premium")
        resp = self.client.get("/api/course-content/seconde/Chapitre_1", headers=self.headers)
        notion = resp.get_json()["notions"][0]
        self.assertIn("aRetenir", notion)
        self.assertNotIn("demonstration", notion)

    def test_ultra_recoit_tout(self):
        _set_plan(self.user["id"], "ultra")
        resp = self.client.get("/api/course-content/premiere/Chapitre_3", headers=self.headers)
        notion = next(n for n in resp.get_json()["notions"] if n["id"] == "fonction-derivee")
        self.assertIn("demonstration", notion)
        self.assertFalse(notion["locked_content"]["premium"])
        self.assertFalse(notion["locked_content"]["ultra"])


class TestApiCourseContentOwner(ApiCourseContentTestCase):
    """Même mécanisme générique que quota_service (owner_test_plan_service.
    effective_plan) — aucune branche spéciale ajoutée pour les cours."""

    def setUp(self):
        super().setUp()
        self._saved_owner_env = os.environ.get("NOVAMATH_OWNER_USER_ID")
        os.environ["NOVAMATH_OWNER_USER_ID"] = str(self.user["id"])

    def tearDown(self):
        # owner_test_plan_service persiste dans system_settings (table
        # GLOBALE, pas de DB isolée dans cette suite — voir server.app.test_client()
        # ci-dessus) : sans ce nettoyage, un plan de test/quotas laissés actifs
        # ici POLLUERAIENT tous les tests suivants qui touchent un compte
        # owner, y compris dans d'autres fichiers exécutés dans la même
        # session pytest. Effectué AVANT de restaurer la variable
        # d'environnement, tant que self.user est encore reconnu comme owner.
        owner_test_plan_service.set_test_plan(self.user, None)
        owner_test_plan_service.set_unlimited_quotas(self.user, True)
        if self._saved_owner_env is None:
            os.environ.pop("NOVAMATH_OWNER_USER_ID", None)
        else:
            os.environ["NOVAMATH_OWNER_USER_ID"] = self._saved_owner_env

    def test_owner_sans_test_actif_recoit_tout(self):
        resp = self.client.get("/api/course-content/premiere/Chapitre_3", headers=self.headers)
        notion = next(n for n in resp.get_json()["notions"] if n["id"] == "fonction-derivee")
        self.assertIn("demonstration", notion)

    def test_owner_test_free_recoit_le_contenu_free(self):
        owner_test_plan_service.set_test_plan(self.user, "free")
        owner_test_plan_service.set_unlimited_quotas(self.user, False)
        # Toutes les classes ont désormais leur contenu classé notion par
        # notion (voir le commentaire de test_free_recoit_le_contenu_essentiel_uniquement) :
        # `demonstration` reste le seul champ TOUJOURS réservé à Ultra sans
        # exception possible (aucun override champsLibresForces ne s'applique
        # à lui, voir course_content_service.py), donc son absence en plan
        # free est une assertion robuste à tout contenu réel, contrairement à
        # `aRetenir` qui peut désormais être exempté notion par notion.
        resp = self.client.get("/api/course-content/troisieme/Chapitre_1", headers=self.headers)
        notion = resp.get_json()["notions"][0]
        self.assertNotIn("demonstration", notion)

    def test_owner_test_ultra_recoit_tout(self):
        owner_test_plan_service.set_test_plan(self.user, "ultra")
        owner_test_plan_service.set_unlimited_quotas(self.user, False)
        resp = self.client.get("/api/course-content/premiere/Chapitre_3", headers=self.headers)
        notion = next(n for n in resp.get_json()["notions"] if n["id"] == "fonction-derivee")
        self.assertIn("demonstration", notion)


class TestApiCourseContentCompatibilite(ApiCourseContentTestCase):
    def test_37_chapitres_se_chargent_pour_les_trois_plans(self):
        checked = 0
        for plan in (None, "premium", "ultra"):
            if plan:
                _set_plan(self.user["id"], plan)
            for class_level, profile in curriculum_registry.CURRICULUM_REGISTRY.items():
                for path in sorted(profile.courses_dir.glob("chapitre_*.json")):
                    num = path.stem.split("_")[1]
                    resp = self.client.get(f"/api/course-content/{class_level}/Chapitre_{num}", headers=self.headers)
                    self.assertEqual(resp.status_code, 200, f"{class_level}/Chapitre_{num} (plan={plan})")
                    checked += 1
        self.assertEqual(checked, 37 * 3)

    def test_une_figure_reste_accessible_en_free(self):
        """§10 du chantier : les figures restent Free par défaut, jamais
        retirées automatiquement — revérifié en HTTP réel (déjà couvert
        unitairement par TestFilterNotionFigureResteFree)."""
        resp = self.client.get("/api/course-content/seconde/Chapitre_7", headers=self.headers)
        notions = resp.get_json()["notions"]
        has_any_figure = any(n.get("figure") for n in notions)
        self.assertTrue(has_any_figure, "aucune figure trouvée dans Chapitre_7 — le test lui-même serait un faux négatif")


if __name__ == "__main__":
    unittest.main()
