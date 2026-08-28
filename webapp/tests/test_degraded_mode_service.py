"""
Suite dédiée à chatbot/services/degraded_mode_service.py — mode dégradé
(audit du 2026-07-26) : quand Gemini est durablement indisponible,
llm_fallback_service.generate() tente CE module avant de retomber sur le
message générique de FakeProvider. Utilise la classe "troisieme" (comme
test_learning_context_continuity.py) : Chapitre_13 y contient la vraie
notion "theoreme-de-pythagore".
"""
import unittest

from chatbot.services import degraded_mode_service

CLASS_LEVEL = "troisieme"


def _messages(*turns):
    """turns : liste de (role, content) — le dernier est le message courant."""
    return [{"role": role, "content": content} for role, content in turns]


class TestPalier1And2LearningContext(unittest.TestCase):
    def test_notion_precise_connue_produit_une_reponse_avec_idee_et_exemple(self):
        intent_result = {
            "chapter_id": "Chapitre_13", "notion_id": "theoreme-de-pythagore", "topic_inherited": True,
        }
        answer = degraded_mode_service.try_answer(
            intent_result, _messages(("user", "je n'ai toujours pas compris")), class_level=CLASS_LEVEL,
        )
        self.assertIsNotNone(answer)
        self.assertIn("Pythagore", answer)
        self.assertTrue(answer.startswith("Reprenons"), msg=answer[:80])
        self.assertIn("Dis-moi ensuite précisément ce qui te bloque.", answer)

    def test_reformulation_false_ouvre_differemment(self):
        intent_result = {
            "chapter_id": "Chapitre_13", "notion_id": "theoreme-de-pythagore", "topic_inherited": False,
        }
        answer = degraded_mode_service.try_answer(
            intent_result, _messages(("user", "Explique-moi Pythagore")), class_level=CLASS_LEVEL,
        )
        self.assertTrue(answer.startswith("Voici ce que dit ton cours"), msg=answer[:80])

    def test_chapitre_connu_sans_notion_precise_retombe_sur_une_notion_du_chapitre(self):
        intent_result = {"chapter_id": "Chapitre_13", "notion_id": None, "topic_inherited": True}
        answer = degraded_mode_service.try_answer(
            intent_result, _messages(("user", "réexplique")), class_level=CLASS_LEVEL,
        )
        self.assertIsNotNone(answer)
        self.assertNotIn("Chapitre_13", answer)  # jamais d'identifiant technique dans une réponse à l'élève

    def test_chapitre_introuvable_ne_leve_jamais_et_passe_au_palier_suivant(self):
        intent_result = {"chapter_id": "Chapitre_Inconnu", "notion_id": None, "topic_inherited": True}
        # Aucune notion pour ce chapitre inexistant, aucun historique/message
        # exploitable non plus : doit renvoyer None sans jamais lever.
        answer = degraded_mode_service.try_answer(
            intent_result, _messages(("user", "bla bla bla incompréhensible")), class_level=CLASS_LEVEL,
        )
        self.assertIsNone(answer)


class TestPalier3Historique(unittest.TestCase):
    def test_message_courant_ambigu_mais_historique_parle_de_pythagore(self):
        """Aucun chapter_id connu (Current Learning Context vide), le message
        courant est totalement elliptique — mais les messages précédents de
        la conversation mentionnent clairement Pythagore : le palier 3 doit
        les exploiter plutôt que de renvoyer None."""
        intent_result = {}
        messages = _messages(
            ("user", "Explique-moi le théorème de Pythagore dans un triangle rectangle"),
            ("assistant", "Bien sûr, voici le théorème de Pythagore..."),
            ("user", "je n'ai toujours pas compris"),
        )
        answer = degraded_mode_service.try_answer(intent_result, messages, class_level=CLASS_LEVEL)
        self.assertIsNotNone(answer)
        self.assertIn("Pythagore", answer)


class TestPalier4RechercheSurLeMessage(unittest.TestCase):
    def test_message_courant_seul_contient_le_sujet(self):
        intent_result = {}
        messages = _messages(("user", "C'est quoi le théorème de Pythagore ?"))
        answer = degraded_mode_service.try_answer(intent_result, messages, class_level=CLASS_LEVEL)
        self.assertIsNotNone(answer)
        self.assertIn("Pythagore", answer)


class TestPalier5BanqueDExercices(unittest.TestCase):
    def test_aucune_notion_mais_chapitre_connu_retombe_sur_un_exercice(self):
        """Rien d'exploitable côté cours (message hors-sujet, aucune notion ne
        matche), mais le chapitre est connu et contient des exercices : le
        palier 5 doit en proposer un plutôt que d'abandonner."""
        intent_result = {"chapter_id": "Chapitre_13", "notion_id": None, "topic_inherited": False}
        messages = _messages(("user", "xyzxyz incompréhensible xyzxyz"))
        answer = degraded_mode_service.try_answer(intent_result, messages, class_level=CLASS_LEVEL)
        # Selon le contenu réel de la banque, soit une notion du chapitre
        # (palier 2, prioritaire) soit un exercice est renvoyé — jamais None
        # tant que le chapitre est connu et contient quelque chose.
        self.assertIsNotNone(answer)


class TestAucunPalierNeTrouveRien(unittest.TestCase):
    def test_renvoie_none_si_absolument_aucun_contexte(self):
        intent_result = {}
        messages = _messages(("user", "xyzxyz1234 incompréhensible xyzxyz5678"))
        answer = degraded_mode_service.try_answer(intent_result, messages, class_level=CLASS_LEVEL)
        self.assertIsNone(answer)


class TestVariationDuModeDegrade(unittest.TestCase):
    """Chantier "mode dégradé répétitif" (2026-08-22) : audit LIVE confirmé —
    deux appels consécutifs sur la même notion (Gemini indisponible plusieurs
    tours de suite, ex. quota Free Tier épuisé) produisaient un texte
    strictement identique (a_retenir[0] + même exemple à chaque fois). Cette
    suite vérifie la stratégie de sélection "premier élément non encore vu
    dans l'historique" (_pick_unused), déterministe et testable — jamais un
    random.choice qui pourrait retomber deux fois de suite sur le même
    élément par hasard. Notion réelle riche utilisée : Chapitre_13/
    theoreme-de-pythagore (6 a_retenir, 5 règles, 3 erreurs, 4 exemples)."""

    def _two_calls(self, intent_result, first_message, second_message):
        r1 = degraded_mode_service.try_answer(
            intent_result, _messages(("user", first_message)), class_level=CLASS_LEVEL,
        )
        r2 = degraded_mode_service.try_answer(
            intent_result,
            _messages(("user", first_message), ("assistant", r1), ("user", second_message)),
            class_level=CLASS_LEVEL,
        )
        return r1, r2

    def test_deux_appels_consecutifs_ne_choisissent_pas_le_meme_a_retenir(self):
        intent_result = {"chapter_id": "Chapitre_13", "notion_id": "theoreme-de-pythagore", "topic_inherited": True}
        r1, r2 = self._two_calls(intent_result, "je n'ai toujours pas compris", "explique autrement")
        idee1 = r1.split("\n")[2]
        idee2 = r2.split("\n")[2]
        self.assertNotEqual(idee1, idee2)

    def test_deux_appels_consecutifs_avec_restart_basics_ne_choisissent_pas_la_meme_regle(self):
        intent_result = {
            "chapter_id": "Chapitre_13", "notion_id": "theoreme-de-pythagore", "topic_inherited": True,
            "intent": "restart_basics",
        }
        r1, r2 = self._two_calls(intent_result, "j'ai rien compris", "j'ai toujours rien compris")
        idee1 = r1.split("\n")[2]
        idee2 = r2.split("\n")[2]
        self.assertNotEqual(idee1, idee2)

    def test_reformulation_puis_restart_basics_puis_reformulation_variation_reelle(self):
        """Reproduit la séquence réelle observée (audit LIVE) : REFORMULATION
        -> RESTART_BASICS -> REFORMULATION sur la VRAIE notion "valeur
        absolue" (un seul exemple — la variation ne peut venir QUE des
        a_retenir/règles/erreurs, jamais de l'exemple, cf. contrainte du
        chantier)."""
        chapter_id, notion_id = "Chapitre_2", "valeur-absolue-dun-nombre-reel"
        messages = _messages(("user", "c'est quoi une valeur absolue"))

        intents = ["reformulation", "restart_basics", "reformulation"]
        answers = []
        for i, intent in enumerate(intents):
            intent_result = {
                "chapter_id": chapter_id, "notion_id": notion_id, "topic_inherited": True, "intent": intent,
            }
            answer = degraded_mode_service.try_answer(intent_result, messages, class_level="seconde")
            self.assertIsNotNone(answer, f"tour {i}: réponse vide")
            self.assertIn("valeur absolue".lower(), answer.lower())
            answers.append(answer)
            messages = messages + [{"role": "assistant", "content": answer}, {"role": "user", "content": "encore"}]

        # L'exemple (un seul disponible) est légitimement identique partout —
        # seule la ligne "idée importante"/l'ajout RESTART_BASICS doit varier.
        idees = [a.split("\n")[2] for a in answers]
        self.assertNotEqual(idees[0], idees[1], "REFORMULATION puis RESTART_BASICS doivent varier")
        self.assertTrue(any(a != answers[0] for a in answers[1:]), "aucune des 3 réponses ne doit être un pur copier-coller de la première")

    def test_notion_avec_un_seul_a_retenir_reutilise_sans_planter(self):
        notion = {"title": "Notion mono-élément", "definition": "Def.", "a_retenir": ["Seul élément."], "regles": [], "exemples": [], "erreurs": []}
        r1, actual1, _ = degraded_mode_service._build_pedagogical_answer(notion, reformulation=True, intent="reformulation", avoid_blob="")
        r2, actual2, _ = degraded_mode_service._build_pedagogical_answer(notion, reformulation=True, intent="reformulation", avoid_blob=r1)
        self.assertIn("Seul élément.", r1)
        self.assertIn("Seul élément.", r2)  # répétition acceptable : rien d'autre à proposer
        self.assertEqual(actual1, "definition")
        self.assertEqual(actual2, "definition")

    def test_notion_sans_exemple_reponse_non_vide(self):
        notion = {"title": "Sans exemple", "definition": "Def.", "a_retenir": ["Idée."], "regles": [], "exemples": [], "erreurs": []}
        answer, actual, _ = degraded_mode_service._build_pedagogical_answer(notion, reformulation=False, intent="reformulation", avoid_blob="")
        self.assertTrue(answer.strip())
        self.assertNotIn("Voici un autre exemple", answer)
        self.assertEqual(actual, "definition")

    def test_notion_sans_methode_ni_regle_reponse_non_vide(self):
        notion = {"title": "Sans méthode", "definition": "Def.", "a_retenir": [], "regles": [], "exemples": [], "erreurs": []}
        answer, actual, _ = degraded_mode_service._build_pedagogical_answer(notion, reformulation=False, intent="reformulation", avoid_blob="")
        self.assertTrue(answer.strip())
        self.assertIn("Def.", answer)
        self.assertEqual(actual, "definition")

    def test_notion_avec_champs_incomplets_reponse_propre(self):
        notion = {"title": "Incomplète"}  # aucun champ optionnel présent
        answer, actual, _ = degraded_mode_service._build_pedagogical_answer(notion, reformulation=False, intent=None, avoid_blob="")
        self.assertTrue(answer.strip())
        self.assertIn("Incomplète", answer)
        self.assertEqual(actual, "definition")

    def test_pick_unused_favorise_un_element_non_deja_vu(self):
        self.assertEqual(degraded_mode_service._pick_unused(["a", "b", "c"], "a"), "b")
        self.assertEqual(degraded_mode_service._pick_unused(["a", "b", "c"], "a \nb"), "c")

    def test_pick_unused_repli_sur_le_premier_si_tout_deja_vu(self):
        self.assertEqual(degraded_mode_service._pick_unused(["a", "b"], "a \nb"), "a")

    def test_pick_unused_liste_vide_renvoie_none(self):
        self.assertIsNone(degraded_mode_service._pick_unused([], ""))

    def test_aucun_appel_llm_dans_le_module(self):
        """Garde-fou structurel : ce module ne doit importer ni provider_manager
        ni un quelconque provider — il n'appelle jamais de fournisseur IA,
        avant comme après ce correctif (uniquement knowledge_engine/
        intent_service/search_service, tous des accès aux données)."""
        import chatbot.services.degraded_mode_service as mod
        self.assertNotIn("provider_manager", mod.__dict__)
        self.assertNotIn("llm_fallback_service", mod.__dict__)


if __name__ == "__main__":
    unittest.main()
