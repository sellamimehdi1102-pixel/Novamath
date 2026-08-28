"""
Tests du Personality Engine (Phase ton/personnalité) : mémoire de style
partagée (phrasing_memory.py) appliquée à response_composer.py, et correction
du doublon de rappel sur la combinaison mode=professeur + longueur=detaille.

response_composer.py compose des réponses de DONNÉES (PROGRESSION/
STATISTIQUE/DASHBOARD/PROFIL/PARAMETRES/SERIE, template_library.py) — testé
ici directement, sans passer par le pipeline complet (comportement pur,
aucune dépendance réseau/DB).
"""
import unittest

from chatbot.services import intent_service, phrasing_memory, response_composer


def _student_context_with_history(*assistant_texts):
    return {
        "historique_conversation": [
            {"role": "assistant", "content": t} for t in assistant_texts
        ]
    }


class TestPhrasingMemory(unittest.TestCase):
    """Le module partagé lui-même (extrait de knowledge_response_composer.py)."""

    def test_recent_assistant_text_ignore_les_messages_utilisateur(self):
        ctx = {
            "historique_conversation": [
                {"role": "user", "content": "Salut"},
                {"role": "assistant", "content": "Bonjour !"},
            ]
        }
        self.assertNotIn("Salut", phrasing_memory.recent_assistant_text(ctx))
        self.assertIn("Bonjour !", phrasing_memory.recent_assistant_text(ctx))

    def test_recent_assistant_text_context_vide_ne_plante_pas(self):
        self.assertEqual(phrasing_memory.recent_assistant_text(None), "")
        self.assertEqual(phrasing_memory.recent_assistant_text({}), "")

    def test_pick_rendered_evite_une_variante_presente_dans_avoid_blob(self):
        import random
        rng = random.Random(1)
        variants = ["A", "B", "C"]
        for _ in range(20):
            self.assertNotEqual(phrasing_memory.pick_rendered(rng, variants, "A"), "A")

    def test_pick_rendered_replie_sur_tout_le_pool_si_tout_est_deja_utilise(self):
        import random
        rng = random.Random(1)
        variants = ["A", "B"]
        # "A \nB" contient les deux variantes : repli sur le pool complet,
        # jamais d'exception, jamais de liste vide.
        result = phrasing_memory.pick_rendered(rng, variants, "A \nB")
        self.assertIn(result, variants)

    def test_pick_rendered_substitue_le_mapping_avant_de_comparer(self):
        """Le blind spot corrigé : un pool avec placeholder doit être
        comparé sur le texte RENDU, jamais sur le template brut."""
        import random
        rng = random.Random(1)
        variants = ["Voici la définition de **{title}** :", "Pour rappel, **{title}** :"]
        rendered_first = variants[0].format(title="Puissances")
        # Le texte déjà rendu est dans l'historique : la variante équivalente
        # ne doit jamais être re-choisie tant qu'une autre existe.
        for _ in range(20):
            result = phrasing_memory.pick_rendered(rng, variants, rendered_first, mapping={"title": "Puissances"})
            self.assertNotEqual(result, rendered_first)

    def test_pick_rendered_sans_mapping_laisse_les_variantes_inchangees(self):
        """Pool sans placeholder (12 des 13 pools de knowledge_response_
        composer.py) : mapping=None doit se comporter exactement comme un
        pick simple, aucune substitution ne devant s'appliquer."""
        import random
        rng = random.Random(1)
        variants = ["Astuce :", "Petit conseil :"]
        result = phrasing_memory.pick_rendered(rng, variants, "")
        self.assertIn(result, variants)


class TestResponseComposerAntiRepetition(unittest.TestCase):
    """response_composer.py était jusqu'ici dépourvu de toute mémoire anti-
    répétition (audit ton/personnalité) — vérifie qu'il en bénéficie
    désormais, sans casser les appelants existants qui ne passent rien."""

    def _variables_serie(self):
        return {"serie_actuelle": "Chapitre 3", "dernier_chapitre": "Chapitre 2"}

    def test_compose_fonctionne_toujours_sans_student_context(self):
        """Compatibilité ascendante : local_knowledge_service.py appelait
        compose() sans student_context avant cette phase — doit continuer à
        produire une réponse valide."""
        text = response_composer.compose(intent_service.SERIE, self._variables_serie(), {})
        self.assertIsInstance(text, str)
        self.assertTrue(text)

    def test_evite_de_repeter_le_texte_rendu_deja_utilise(self):
        """Les 3 variantes de SERIE, une fois formatées avec les mêmes
        variables, donnent 3 textes distincts. Si 2 des 3 apparaissent déjà
        dans l'historique récent, la 3e doit être choisie à coup sûr."""
        variables = self._variables_serie()
        from chatbot.services import template_library
        rendered = [t.format(**variables) for t in template_library.TEMPLATES[intent_service.SERIE]]
        ctx = _student_context_with_history(rendered[0], rendered[1])
        for _ in range(10):
            text = response_composer.compose(intent_service.SERIE, variables, {}, student_context=ctx)
            self.assertEqual(text, rendered[2])

    def test_repli_sur_tout_le_pool_si_toutes_les_variantes_ont_deja_servi(self):
        """Aucune exception, aucun texte vide si l'historique contient déjà
        toutes les variantes possibles (mieux vaut répéter que planter)."""
        variables = self._variables_serie()
        from chatbot.services import template_library
        rendered = [t.format(**variables) for t in template_library.TEMPLATES[intent_service.SERIE]]
        ctx = _student_context_with_history(*rendered)
        text = response_composer.compose(intent_service.SERIE, variables, {}, student_context=ctx)
        self.assertIn(text, rendered)


class TestPasDeDoublonProfesseurDetaille(unittest.TestCase):
    """Bug identifié à l'audit ton/personnalité : mode=professeur +
    longueur=detaille produisaient deux phrases quasi identiques
    ("N'hésite pas à me demander plus de détails...") à la suite."""

    def test_une_seule_invitation_a_creuser_pour_professeur_et_detaille(self):
        variables = {"serie_actuelle": "Chapitre 3", "dernier_chapitre": "Chapitre 2"}
        settings = {"mode": "professeur", "responseLength": "detaille"}
        for _ in range(15):
            text = response_composer.compose(intent_service.SERIE, variables, settings)
            self.assertEqual(
                text.count("N'hésite pas à me demander plus de détails"), 1,
                msg=f"doublon détecté dans : {text!r}",
            )

    def test_detaille_seul_ajoute_bien_une_invitation(self):
        variables = {"serie_actuelle": "Chapitre 3", "dernier_chapitre": "Chapitre 2"}
        text = response_composer.compose(intent_service.SERIE, variables, {"responseLength": "detaille"})
        self.assertNotEqual(text, response_composer.compose(intent_service.SERIE, variables, {}))

    def test_professeur_seul_ajoute_bien_le_conseil(self):
        variables = {"serie_actuelle": "Chapitre 3", "dernier_chapitre": "Chapitre 2"}
        text = response_composer.compose(intent_service.SERIE, variables, {"mode": "professeur"})
        self.assertIn("N'hésite pas à me demander plus de détails", text)


if __name__ == "__main__":
    unittest.main()
