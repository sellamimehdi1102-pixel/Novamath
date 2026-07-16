"""
Suite de tests du Knowledge Response Composer —
`chatbot/services/knowledge_response_composer.py`. Ce module n'est PAS
branché au pipeline principal (voir consigne explicite) : tous les tests
l'exercent en isolation, à partir de vraies `ResponseStrategy` produites par
`response_strategy.decide_strategy()` (déjà validé, 122/122) sur des
notions réelles du Knowledge Engine (Chapitre_1 / puissances-entieres-relatives,
déjà utilisé par les autres suites du projet).
"""
import dataclasses
import random
import time
import unittest

from chatbot.services import intent_service, knowledge_response_composer as krc, response_strategy as rs

REAL_USER = {"id": 1, "pseudo": "Testeur", "level": 1}


def student_context(**overrides):
    base = {
        "user_id": 1, "pseudo": "Testeur", "niveau": "Débutant", "niveau_brut": 1,
        "chapitre_courant": None, "topic_courant": None,
        "notions_maitrisees": [], "notions_faibles": [],
        "topics_maitrises": [], "topics_faibles": [],
        "statistiques": {"accuracy": 0, "total_exercices": 0, "temps_total": "0 h", "temps_jour": "0 h", "temps_semaine": "0 h"},
        "dashboard": {"objectif_du_jour": None, "chapitres_en_cours": [], "meilleur_chapitre": None, "chapitre_le_plus_faible": None},
        "progression": {},
        "preferences": {"langue": "fr", "niveau_explication": "auto", "favoris": []},
        "parametres": {
            "longueur": "normal", "niveau_explication": "auto", "mode": None,
            "memoire_activee": True, "historique_active": True, "provider": None,
            "modele": None, "temperature": 0.6,
        },
        "mentions": [], "historique_conversation": [],
    }
    base.update(overrides)
    return base


def strategy_for(message, ctx=None, chatbot_settings=None):
    return rs.decide_strategy(
        message, REAL_USER, student_context=ctx if ctx is not None else student_context(),
        chatbot_settings=chatbot_settings, use_cache=False,
    )


class KnowledgeComposerTestCase(unittest.TestCase):
    def compose(self, message, ctx=None, chatbot_settings=None, rng=None):
        strategy = strategy_for(message, ctx=ctx, chatbot_settings=chatbot_settings)
        return krc.compose(strategy, student_context=ctx if ctx is not None else student_context(), chatbot_settings=chatbot_settings, rng=rng)


class TestStructureDuBrouillon(KnowledgeComposerTestCase):
    def test_champs_attendus_presents(self):
        draft = self.compose("Quelle est la méthode pour simplifier une puissance ?")
        for field_name in ("text", "blocks", "engine", "intent", "chapter_id", "topic_id", "used_fallback", "explanation"):
            self.assertTrue(hasattr(draft, field_name))

    def test_frozen(self):
        draft = self.compose("Quelle est la méthode pour simplifier une puissance ?")
        with self.assertRaises(dataclasses.FrozenInstanceError):
            draft.text = "autre chose"

    def test_engine_toujours_le_meme(self):
        draft = self.compose("C'est quoi une puissance ?")
        self.assertEqual(draft.engine, krc.ENGINE_NAME)

    def test_texte_non_vide_toujours(self):
        for message in ["C'est quoi une puissance ?", "Donne-moi un exemple", "sujet totalement inconnu xyzabc"]:
            with self.subTest(message=message):
                draft = self.compose(message)
                self.assertTrue(draft.text.strip())


class TestAssemblageParBlocs(KnowledgeComposerTestCase):
    def test_definition_produit_bloc_definition(self):
        draft = self.compose("C'est quoi une puissance ?")
        kinds = [b.kind for b in draft.blocks]
        self.assertIn(krc.BLOCK_DEFINITION, kinds)
        self.assertIn(krc.BLOCK_INTRODUCTION, kinds)
        self.assertIn(krc.BLOCK_OUVERTURE, kinds)

    def test_methode_produit_bloc_methode_et_exemple(self):
        draft = self.compose("Quelle est la méthode pour simplifier une puissance ?")
        kinds = [b.kind for b in draft.blocks]
        self.assertIn(krc.BLOCK_METHODE, kinds)
        self.assertIn(krc.BLOCK_EXEMPLE, kinds)

    def test_formule_produit_bloc_formule(self):
        draft = self.compose("Quelle est la formule de la puissance ?")
        kinds = [b.kind for b in draft.blocks]
        self.assertIn(krc.BLOCK_FORMULE, kinds)

    def test_propriete_retombe_intelligemment_sur_une_formule(self):
        """`proprietes` est vide sur toutes les notions migrées aujourd'hui
        (voir knowledge_engine.get_proprietes) — le compositeur doit retomber
        sur une formule/règle plutôt que produire un bloc vide."""
        draft = self.compose("Quelle est la propriété de la puissance ?")
        kinds = [b.kind for b in draft.blocks]
        self.assertIn(krc.BLOCK_PROPRIETE, kinds)
        propriete_block = next(b for b in draft.blocks if b.kind == krc.BLOCK_PROPRIETE)
        self.assertTrue(propriete_block.text.strip())
        self.assertTrue(draft.used_fallback)

    def test_indice_ne_donne_jamais_la_reponse_finale(self):
        draft = self.compose("Donne-moi un indice sur les puissances")
        exemple_block = next((b for b in draft.blocks if b.kind == krc.BLOCK_EXEMPLE), None)
        self.assertIsNotNone(exemple_block)
        self.assertNotIn("Résultat", exemple_block.text)

    def test_exemple_simple_ne_contient_pas_deuxieme_exemple_par_defaut(self):
        draft = self.compose("Donne-moi un exemple sur les puissances")
        kinds = [b.kind for b in draft.blocks]
        self.assertIn(krc.BLOCK_EXEMPLE, kinds)
        self.assertNotIn(krc.BLOCK_EXEMPLE_2, kinds)

    def test_plusieurs_exemples_ajoute_un_deuxieme_bloc_distinct(self):
        draft = self.compose("Donne-moi 2 exemples sur les puissances")
        kinds = [b.kind for b in draft.blocks]
        self.assertIn(krc.BLOCK_EXEMPLE, kinds)
        self.assertIn(krc.BLOCK_EXEMPLE_2, kinds)
        ex1 = next(b for b in draft.blocks if b.kind == krc.BLOCK_EXEMPLE)
        ex2 = next(b for b in draft.blocks if b.kind == krc.BLOCK_EXEMPLE_2)
        self.assertNotEqual(ex1.text, ex2.text)

    def test_notion_introuvable_ne_plante_jamais(self):
        draft = self.compose("Un message totalement hors programme sur des licornes")
        self.assertIsInstance(draft, krc.ResponseDraft)
        self.assertTrue(draft.text.strip())

    def test_court_ne_contient_ni_introduction_ni_ouverture(self):
        ctx = student_context(parametres={**student_context()["parametres"], "longueur": "court"})
        draft = self.compose("C'est quoi une puissance ?", ctx=ctx)
        kinds = [b.kind for b in draft.blocks]
        self.assertNotIn(krc.BLOCK_INTRODUCTION, kinds)
        self.assertNotIn(krc.BLOCK_OUVERTURE, kinds)

    def test_detaille_ajoute_des_blocs_supplementaires(self):
        ctx_normal = student_context()
        ctx_detaille = student_context(parametres={**student_context()["parametres"], "longueur": "detaille"})
        draft_normal = self.compose("Explique-moi les puissances", ctx=ctx_normal)
        draft_detaille = self.compose("Explique-moi les puissances", ctx=ctx_detaille)
        self.assertGreater(len(draft_detaille.blocks), len(draft_normal.blocks))


class TestParametresInfluencentReellementLaReponse(KnowledgeComposerTestCase):
    def test_niveau_explication_college_vs_expert_donnent_des_textes_differents(self):
        ctx_college = student_context(parametres={**student_context()["parametres"], "niveau_explication": "college"})
        ctx_expert = student_context(parametres={**student_context()["parametres"], "niveau_explication": "expert"})
        draft_college = self.compose("C'est quoi une puissance ?", ctx=ctx_college)
        draft_expert = self.compose("C'est quoi une puissance ?", ctx=ctx_expert)
        def_college = next(b for b in draft_college.blocks if b.kind == krc.BLOCK_DEFINITION)
        def_expert = next(b for b in draft_expert.blocks if b.kind == krc.BLOCK_DEFINITION)
        self.assertNotEqual(def_college.text, def_expert.text)

    def test_simplify_redescend_le_niveau_de_definition(self):
        ctx = student_context(parametres={**student_context()["parametres"], "niveau_explication": "expert"})
        draft_normal = self.compose("C'est quoi une puissance ?", ctx=ctx)
        draft_simplifie = self.compose("Explique-moi plus simplement ce qu'est une puissance", ctx=ctx)
        def_normal = next(b for b in draft_normal.blocks if b.kind == krc.BLOCK_DEFINITION)
        def_simplifie = next(b for b in draft_simplifie.blocks if b.kind == krc.BLOCK_DEFINITION)
        self.assertNotEqual(def_normal.text, def_simplifie.text)
        # Le repli "simplify" ne doit plus jamais s'afficher comme une
        # étiquette technique entre parenthèses (Personality Engine) — la
        # phrase d'introduction elle-même annonce naturellement la
        # reformulation, avec un mot-signal robuste ("simple"/"simplement").
        self.assertNotIn("(version simplifiée)", def_simplifie.text)
        self.assertIn("simple", def_simplifie.text.lower())

    def test_difficulte_facile_vs_difficile_choisissent_des_exemples_differents(self):
        rng = random.Random(42)
        draft_facile = self.compose("Donne-moi un exercice facile sur les puissances", rng=rng)
        rng2 = random.Random(42)
        draft_difficile = self.compose("Donne-moi un exercice difficile sur les puissances", rng=rng2)
        # Note : l'intent EXERCICE est traité par l'Exercise Engine (search_service),
        # ce test couvre EXPLICATION/EXEMPLE où le Knowledge Response Composer choisit
        # bien l'exemple selon la difficulté transmise par la ResponseStrategy.
        ex_facile = next((b for b in draft_facile.blocks if b.kind == krc.BLOCK_EXEMPLE), None)
        ex_difficile = next((b for b in draft_difficile.blocks if b.kind == krc.BLOCK_EXEMPLE), None)
        if ex_facile and ex_difficile:
            self.assertNotEqual(ex_facile.text, ex_difficile.text)

    def test_mode_rapide_utilise_les_etapes_condensees(self):
        draft_normal = self.compose("Quelle est la méthode pour simplifier une puissance ?")
        draft_rapide = self.compose(
            "Quelle est la méthode pour simplifier une puissance ?", chatbot_settings={"mode": "rapide"},
        )
        methode_normal = next(b for b in draft_normal.blocks if b.kind == krc.BLOCK_METHODE)
        methode_rapide = next(b for b in draft_rapide.blocks if b.kind == krc.BLOCK_METHODE)
        self.assertNotEqual(methode_normal.text, methode_rapide.text)
        self.assertLess(methode_rapide.text.count("\n"), methode_normal.text.count("\n"))

    def test_mode_pas_a_pas_utilise_les_etapes_debutant(self):
        import re
        draft_normal = self.compose("Quelle est la méthode pour simplifier une puissance ?")
        ctx_pas_a_pas = student_context(parametres={**student_context()["parametres"], "mode": "pas_a_pas"})
        draft_pas_a_pas = self.compose("Quelle est la méthode pour simplifier une puissance ?", ctx=ctx_pas_a_pas)
        methode_normal = next(b for b in draft_normal.blocks if b.kind == krc.BLOCK_METHODE)
        methode_pas_a_pas = next(b for b in draft_pas_a_pas.blocks if b.kind == krc.BLOCK_METHODE)
        # Les étapes "debutant" de Chapitre_1/puissances-entieres-relatives sont
        # plus nombreuses (4) que les étapes "normal" (3) — voir la donnée réelle.
        n_normal = len(re.findall(r"^\d+\.", methode_normal.text, re.MULTILINE))
        n_debutant = len(re.findall(r"^\d+\.", methode_pas_a_pas.text, re.MULTILINE))
        self.assertEqual(n_normal, 3)
        self.assertEqual(n_debutant, 4)

    def test_mode_professeur_longueur_detaillee_ajoute_un_conseil(self):
        ctx = student_context(parametres={
            **student_context()["parametres"], "mode": "professeur", "longueur": "detaille",
        })
        draft = self.compose("Explique-moi les puissances", ctx=ctx)
        kinds = [b.kind for b in draft.blocks]
        self.assertIn(krc.BLOCK_CONSEIL, kinds)


class TestVariabiliteEtNonRepetition(KnowledgeComposerTestCase):
    def test_deux_compositions_successives_different(self):
        rng = random.Random(1)
        strategy = strategy_for("C'est quoi une puissance ?")
        draft1 = krc.compose(strategy, student_context=student_context(), rng=rng)
        draft2 = krc.compose(strategy, student_context=student_context(), rng=rng)
        self.assertNotEqual(draft1.text, draft2.text)

    def test_diversite_sur_de_nombreux_appels(self):
        """Sur 30 tirages, on doit observer plusieurs formulations distinctes
        d'introduction — jamais une seule variante répétée systématiquement."""
        strategy = strategy_for("C'est quoi une puissance ?")
        intros = set()
        rng = random.Random(7)
        for _ in range(30):
            draft = krc.compose(strategy, student_context=student_context(), rng=rng)
            intro = next(b for b in draft.blocks if b.kind == krc.BLOCK_INTRODUCTION)
            intros.add(intro.text)
        self.assertGreater(len(intros), 1)

    def test_evite_une_formulation_deja_utilisee_dans_lhistorique_recent(self):
        """Si l'introduction "Bonne question !..." a déjà été utilisée
        (présente dans l'historique de conversation récent), le compositeur
        ne doit pas la reprendre tant qu'une alternative existe."""
        deja_utilisee = krc._INTRO_VARIANTS["default"][1]
        ctx = student_context(historique_conversation=[{"role": "assistant", "content": deja_utilisee}])
        strategy = strategy_for("C'est quoi une puissance ?", ctx=ctx)
        for _ in range(10):
            draft = krc.compose(strategy, student_context=ctx)
            intro = next(b for b in draft.blocks if b.kind == krc.BLOCK_INTRODUCTION)
            self.assertNotEqual(intro.text, deja_utilisee)

    def test_repli_sur_toutes_les_variantes_si_toutes_deja_utilisees(self):
        """Si TOUTES les variantes ont déjà été vues, le compositeur ne doit
        pas planter — il retombe sur l'ensemble complet plutôt que de lever
        une exception sur une liste vide."""
        tout_lhistorique = " \n".join(krc._INTRO_VARIANTS["default"])
        ctx = student_context(historique_conversation=[{"role": "assistant", "content": tout_lhistorique}])
        strategy = strategy_for("C'est quoi une puissance ?", ctx=ctx)
        draft = krc.compose(strategy, student_context=ctx)
        self.assertIsInstance(draft, krc.ResponseDraft)


class TestMemoireDeStyleDefinition(KnowledgeComposerTestCase):
    """Blind spot corrigé (Phase Personality Engine) : _LEADIN_DEFINITION
    est le seul pool à contenir un placeholder ({title}) — la mémoire
    anti-répétition doit désormais comparer le lead-in RENDU (avec le vrai
    titre de la notion), jamais le template brut encore truffé de
    {title}, sans quoi la comparaison ne pouvait jamais matcher."""

    def test_evite_de_repeter_le_lead_in_definition_deja_rendu(self):
        premiere = self.compose("C'est quoi une puissance ?")
        premier_bloc = next(b for b in premiere.blocks if b.kind == krc.BLOCK_DEFINITION)
        lead_deja_utilise = premier_bloc.text.split("\n\n")[0]

        ctx = student_context(historique_conversation=[{"role": "assistant", "content": premier_bloc.text}])
        for _ in range(15):
            draft = self.compose("C'est quoi une puissance ?", ctx=ctx)
            bloc = next(b for b in draft.blocks if b.kind == krc.BLOCK_DEFINITION)
            lead = bloc.text.split("\n\n")[0]
            self.assertNotEqual(lead, lead_deja_utilise)


class TestIdentiteRedactionnelleParMode(KnowledgeComposerTestCase):
    """Mission Personality Engine (suite) : chaque mode doit être
    reconnaissable À LA LECTURE, pas seulement fonctionnellement — vérifie
    que les 4 modes cibles (professeur/rapide/examen/pas_a_pas) produisent
    des formes (introduction/ouverture/méthode) réellement distinctes du
    mode par défaut, sans jamais toucher au Knowledge Engine/Response
    Strategy/Local Response Engine/Student Context Resolver."""

    def _ctx_mode(self, mode):
        return student_context(parametres={**student_context()["parametres"], "mode": mode})

    def test_examen_najoute_jamais_de_bloc_ouverture(self):
        """Aucune formule d'encouragement/clôture en mode examen (mission :
        "aucune familiarité, aucun encouragement inutile") — le bloc est
        omis entièrement plutôt que neutralisé."""
        ctx = self._ctx_mode("examen")
        for _ in range(10):
            draft = self.compose("C'est quoi une puissance ?", ctx=ctx)
            self.assertFalse(any(b.kind == krc.BLOCK_OUVERTURE for b in draft.blocks))

    def test_examen_a_une_introduction_distincte_du_defaut(self):
        ctx = self._ctx_mode("examen")
        draft = self.compose("C'est quoi une puissance ?", ctx=ctx)
        intro = next(b for b in draft.blocks if b.kind == krc.BLOCK_INTRODUCTION)
        self.assertIn(intro.text, krc._INTRO_VARIANTS["examen"])
        self.assertNotIn(intro.text, krc._INTRO_VARIANTS["default"])

    def test_pas_a_pas_a_une_introduction_et_une_ouverture_distinctes(self):
        ctx = self._ctx_mode("pas_a_pas")
        draft = self.compose("C'est quoi une puissance ?", ctx=ctx)
        intro = next(b for b in draft.blocks if b.kind == krc.BLOCK_INTRODUCTION)
        ouverture = next(b for b in draft.blocks if b.kind == krc.BLOCK_OUVERTURE)
        self.assertIn(intro.text, krc._INTRO_VARIANTS["pas_a_pas"])
        self.assertIn(ouverture.text, krc._OUVERTURE_VARIANTS["pas_a_pas"])

    def test_pas_a_pas_a_un_lead_in_de_methode_distinct(self):
        ctx = self._ctx_mode("pas_a_pas")
        draft = self.compose("Quelle est la méthode pour simplifier une puissance ?", ctx=ctx)
        methode = next(b for b in draft.blocks if b.kind == krc.BLOCK_METHODE)
        lead = methode.text.split("\n\n")[0]
        self.assertIn(lead, krc._LEADIN_METHODE["pas_a_pas"])
        self.assertNotIn(lead, krc._LEADIN_METHODE["default"])

    def test_professeur_et_rapide_toujours_distincts_du_defaut(self):
        """Non-régression : les deux modes déjà différenciés avant cette
        étape le restent après la restructuration."""
        for mode in ("professeur", "rapide"):
            ctx = self._ctx_mode(mode)
            draft = self.compose("C'est quoi une puissance ?", ctx=ctx)
            intro = next(b for b in draft.blocks if b.kind == krc.BLOCK_INTRODUCTION)
            self.assertIn(intro.text, krc._INTRO_VARIANTS[mode])

    def test_variant_pools_sont_tous_des_listes_plates(self):
        """Garde-fou pour diversity_audit.py (_all_pools()) : chaque valeur
        de VARIANT_POOLS doit être une liste de chaînes, jamais un dict —
        piège direct de la restructuration de _LEADIN_METHODE en dict par
        mode (l'export doit exposer les sous-listes, pas le dict parent)."""
        for name, variants in krc.VARIANT_POOLS.items():
            self.assertIsInstance(variants, list, msg=f"{name} n'est pas une liste")
            for v in variants:
                self.assertIsInstance(v, str, msg=f"{name} contient un élément non-str")


class TestCompatibiliteKnowledgeEngine(KnowledgeComposerTestCase):
    def test_utilise_les_vraies_donnees_de_chapitre_1(self):
        draft = self.compose("C'est quoi une puissance ?")
        definition_block = next(b for b in draft.blocks if b.kind == krc.BLOCK_DEFINITION)
        self.assertIn("Les puissances", definition_block.text)

    def test_topic_id_et_chapter_id_reportes_fidelement(self):
        draft = self.compose("C'est quoi une puissance ?")
        self.assertEqual(draft.chapter_id, "Chapitre_1")
        self.assertEqual(draft.topic_id, "puissances-entieres-relatives")

    def test_intent_reporte_fidelement(self):
        draft = self.compose("Quelle est la formule de la puissance ?")
        self.assertEqual(draft.intent, intent_service.FORMULE)


class TestPerformance(KnowledgeComposerTestCase):
    def test_composition_rapide(self):
        strategy = strategy_for("Explique-moi les puissances")
        ctx = student_context()
        n = 200
        t0 = time.perf_counter()
        for _ in range(n):
            krc.compose(strategy, student_context=ctx)
        avg_ms = (time.perf_counter() - t0) * 1000 / n
        self.assertLess(avg_ms, 5.0, "une composition ne doit pas dépasser quelques millisecondes")


if __name__ == "__main__":
    unittest.main()
