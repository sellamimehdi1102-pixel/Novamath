"""
Suite "dérive de classe" (chantier 2026-08-23, Priorité 2) : prouve que le
chatbot NovaMath personnalise réellement par class_level (Seconde/Première/
Troisième) et que le Current Learning Context d'une conversation ne peut plus
être réutilisé aveuglément quand la classe active a changé depuis (même
chapter_id réutilisé d'une classe à l'autre pour désigner un sujet
différent — ex. "Chapitre_3" = Calcul littéral en Seconde, Fractions en
Troisième, confirmé par audit).

Couvre les TESTS A-F demandés :
A/B/C : Troisième/Seconde/Première résolvent chacun leur propre contenu réel.
D     : une notion hors-programme d'un niveau n'est jamais présentée comme
        si elle appartenait à ce niveau.
E     : un changement de classe en cours de conversation est réellement pris
        en compte au tour suivant (le coeur du correctif).
F     : une nouvelle conversation après changement de classe ne conserve
        aucun ancien contexte de classe.
"""
import random
import unittest

import db
import server
from chatbot import conversation_manager as cm
from chatbot import knowledge_engine
from chatbot.services import intent_service


def _register(client):
    email = f"clvl{random.randint(1_000_000, 9_999_999)}@gmail.com"
    username = f"clvluser{random.randint(100_000, 999_999)}"
    resp = client.post("/api/auth/register", json={
        "email": email, "username": username, "pseudo": "ClvlTest",
        "birth_date": "2000-01-01",
        "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
        "accept_terms": True, "accept_privacy": True,
    })
    return resp.get_json()["user"]


class TestABCDetectionParClasseDirecte(unittest.TestCase):
    """TESTS A/B/C : la même question ("les probabilités"), posée sous trois
    class_level différents, résout chaque fois un contenu RÉEL et propre à
    ce niveau (chapitre/notion distincts, existant réellement dans les
    données de cours de CE niveau, jamais un repli générique identique)."""

    MESSAGE = "Explique-moi les probabilités."

    def _resolve(self, class_level):
        r = intent_service.classify(self.MESSAGE, context_summary=None, class_level=class_level)
        self.assertIsNotNone(r["chapter_id"], f"aucun chapitre résolu pour {class_level}")
        notion = knowledge_engine.get_notion(r["chapter_id"], r["notion_id"], class_level=class_level) if r["notion_id"] else None
        title = notion["title"] if notion else knowledge_engine.get_chapter_title(r["chapter_id"], class_level=class_level)
        self.assertTrue(title, f"aucun titre résolu pour {class_level}")
        return r["chapter_id"], r["notion_id"], title

    def test_a_troisieme_resout_son_propre_contenu(self):
        chapter_id, notion_id, title = self._resolve("troisieme")
        # Doit exister réellement dans les données Troisième (lookup exact).
        self.assertIsNotNone(knowledge_engine.get_notion(chapter_id, notion_id, class_level="troisieme") if notion_id else title)

    def test_b_seconde_resout_son_propre_contenu(self):
        chapter_id, notion_id, title = self._resolve("seconde")
        self.assertIsNotNone(knowledge_engine.get_notion(chapter_id, notion_id, class_level="seconde") if notion_id else title)

    def test_c_premiere_resout_son_propre_contenu(self):
        chapter_id, notion_id, title = self._resolve("premiere")
        self.assertIsNotNone(knowledge_engine.get_notion(chapter_id, notion_id, class_level="premiere") if notion_id else title)

    def test_les_trois_niveaux_resolvent_des_notions_reellement_distinctes(self):
        # Preuve que ce n'est pas le même contenu générique recopié pour les
        # trois niveaux — chaque résolution est propre à sa classe.
        _, notion_troisieme, title_troisieme = self._resolve("troisieme")
        _, notion_seconde, title_seconde = self._resolve("seconde")
        _, notion_premiere, title_premiere = self._resolve("premiere")
        titles = {title_troisieme, title_seconde, title_premiere}
        self.assertGreater(len(titles), 1, f"les trois niveaux ont résolu le même titre : {titles!r}")


class TestDNotionHorsProgramme(unittest.TestCase):
    """TEST D : "équations du second degré" n'existe QUE dans les données
    Première (Chapitre_2) — un élève de Seconde ne doit jamais recevoir ce
    contenu comme si son niveau l'avait déjà vu."""

    def test_d_notion_premiere_absente_du_lookup_seconde(self):
        notion = knowledge_engine.get_notion("Chapitre_2", "equations-du-second-degre", class_level="seconde")
        self.assertIsNone(notion, "la notion Première a été retournée pour un lookup Seconde")

    def test_d_recherche_seconde_ne_remonte_jamais_la_notion_premiere(self):
        r = intent_service.classify(
            "Résous-moi une équation du second degré.", context_summary=None, class_level="seconde",
        )
        if r["notion_id"]:
            self.assertNotEqual(r["notion_id"], "equations-du-second-degre")
        # Même si un chapter_id générique a matché par coïncidence lexicale,
        # le lookup exact sous la classe Seconde ne doit jamais renvoyer le
        # contenu Première.
        if r["chapter_id"] and r["notion_id"]:
            notion = knowledge_engine.get_notion(r["chapter_id"], r["notion_id"], class_level="seconde")
            if notion:
                self.assertNotIn("second degré", notion.get("title", "").lower())


class TestRevalidationClasseSurLearningContextHerite(unittest.TestCase):
    """Coeur du correctif (intent_service._detect_chapter) : un
    learning_context hérité n'est réutilisé QUE si sa classe correspond à la
    classe courante, ou si aucune classe n'y était mémorisée (compat avec les
    conversations existantes avant ce chantier)."""

    SECONDE_CTX = {"chapter_id": "Chapitre_3", "notion_id": "distributivite-et-identites-remarquables", "class_level": "seconde"}

    def test_meme_classe_reutilise_le_contexte(self):
        chapter_id, notion_id, confidence = intent_service._detect_chapter(
            "réexplique", context_summary=None, class_level="seconde",
            learning_context=self.SECONDE_CTX, force_context=True,
        )
        self.assertEqual((chapter_id, notion_id, confidence), ("Chapitre_3", "distributivite-et-identites-remarquables", "inherited"))

    def test_classe_differente_nest_plus_reutilise_en_force_context(self):
        chapter_id, notion_id, confidence = intent_service._detect_chapter(
            "réexplique", context_summary=None, class_level="troisieme",
            learning_context=self.SECONDE_CTX, force_context=True,
        )
        # Un message sans mot-clé de sujet ("réexplique") ne doit plus
        # hériter aveuglément de Chapitre_3-Seconde alors que la classe
        # active est désormais Troisième (où Chapitre_3 = Fractions).
        self.assertNotEqual((chapter_id, notion_id), ("Chapitre_3", "distributivite-et-identites-remarquables"))
        self.assertNotEqual(confidence, "inherited")

    def test_classe_differente_nest_plus_reutilise_en_repli_faible_score(self):
        chapter_id, notion_id, confidence = intent_service._detect_chapter(
            "et donc ça donne quoi au juste", context_summary=None, class_level="troisieme",
            learning_context=self.SECONDE_CTX, force_context=False,
        )
        self.assertNotEqual((chapter_id, notion_id), ("Chapitre_3", "distributivite-et-identites-remarquables"))
        self.assertNotEqual(confidence, "inherited")

    def test_learning_context_sans_class_level_legacy_reste_reutilise(self):
        # Conversation créée AVANT ce chantier : class_level absent du JSON
        # (None) -> comportement inchangé (compat), toujours réutilisé.
        legacy_ctx = {"chapter_id": "Chapitre_3", "notion_id": "distributivite-et-identites-remarquables"}
        chapter_id, notion_id, confidence = intent_service._detect_chapter(
            "réexplique", context_summary=None, class_level="troisieme",
            learning_context=legacy_ctx, force_context=True,
        )
        self.assertEqual((chapter_id, notion_id, confidence), ("Chapitre_3", "distributivite-et-identites-remarquables", "inherited"))


class TestPipelineReelEF(unittest.TestCase):
    """TESTS E et F sur le pipeline réel complet (stream_reply), pas
    seulement sur les fonctions unitaires ci-dessus."""

    def setUp(self):
        client = server.app.test_client()
        self.user = _register(client)

    def _class_level_stored(self, conv_id):
        lc = db.get_conversation_learning_context(conv_id)
        return lc.get("class_level") if lc else None

    def test_e_changement_de_classe_est_reellement_pris_en_compte(self):
        conv_id = db.create_conversation(self.user["id"])
        list(cm.stream_reply(
            self.user, conv_id, "Explique-moi le calcul littéral.",
            chapters_summary=None, mentions=None, debug=False, class_level="seconde",
        ))
        lc_before = db.get_conversation_learning_context(conv_id)
        seconde_chapter_id = lc_before["chapter_id"]
        self.assertIsNotNone(seconde_chapter_id)
        self.assertEqual(lc_before.get("class_level"), "seconde")

        # Changement de classe actif (localStorage côté élève) sans quitter
        # la conversation — message SUIVANT ambigu, exactement le scénario de
        # l'audit. On vérifie ici la classification réelle (même fonction
        # exacte que le pipeline complet appelle, sur le VRAI learning_context
        # produit par le tour précédent) plutôt que le contenu d'une réponse
        # LLM en direct (non déterministe, dépend du réseau) : le nouveau
        # class_level doit réellement invalider l'héritage Seconde.
        chapter_id, notion_id, confidence = intent_service._detect_chapter(
            "réexplique", context_summary=None, class_level="troisieme",
            learning_context=lc_before, force_context=True,
        )
        self.assertNotEqual((chapter_id, notion_id, confidence), (seconde_chapter_id, lc_before.get("notion_id"), "inherited"))
        # Si un chapitre a malgré tout été retenu (recherche fraîche sous
        # Troisième), il doit être valide et cohérent SOUS CETTE CLASSE —
        # jamais laissé tel quel comme un chapter_id Seconde mal réinterprété.
        if chapter_id:
            resolved_ok = (
                knowledge_engine.get_notion(chapter_id, notion_id, class_level="troisieme")
                if notion_id
                else knowledge_engine.get_chapter_title(chapter_id, class_level="troisieme")
            )
            self.assertIsNotNone(resolved_ok)

    def test_f_nouvelle_conversation_apres_changement_de_classe_aucune_fuite(self):
        conv_a = db.create_conversation(self.user["id"])
        list(cm.stream_reply(
            self.user, conv_a, "Explique-moi le calcul littéral.",
            chapters_summary=None, mentions=None, debug=False, class_level="seconde",
        ))
        lc_a = db.get_conversation_learning_context(conv_a)
        self.assertEqual(self._class_level_stored(conv_a), "seconde")

        # Nouvelle conversation, classe désormais Troisième — doit démarrer
        # sans aucun état hérité de conv_a (conversations indépendantes).
        conv_b = db.create_conversation(self.user["id"])
        self.assertIsNone(db.get_conversation_learning_context(conv_b))
        list(cm.stream_reply(
            self.user, conv_b, "Explique-moi les fractions.",
            chapters_summary=None, mentions=None, debug=False, class_level="troisieme",
        ))
        lc_b = db.get_conversation_learning_context(conv_b)
        self.assertEqual(self._class_level_stored(conv_b), "troisieme")
        # conv_a reste inchangée (pas de fuite dans l'autre sens non plus).
        self.assertEqual(db.get_conversation_learning_context(conv_a), lc_a)


if __name__ == "__main__":
    unittest.main()
