"""Aide de test : servir la classe NON PUBLIÉE « Première spécifique »
(`premiere_specifique`) comme sur une instance de prévisualisation
(NOVAMATH_PREVIEW_CURRICULA=premiere_specifique), sans variable
d'environnement — même procédé que test_quatrieme_programme.py
(TestSiteEnPrevisualisation) : on remplace le registre servi le temps du test
et on vide les caches par classe."""
import unittest
import uuid
from unittest import mock

import curriculum_registry
import curriculum_stats
from curriculum_registry import CURRICULUM_REGISTRY_ALL, served_registry

CLASS_LEVEL = "premiere_specifique"
PROFILE = CURRICULUM_REGISTRY_ALL[CLASS_LEVEL]


def _purge():
    import server
    from chatbot import knowledge_engine
    from chatbot.services import search_service

    curriculum_stats.clear_cache()
    for cache in (
        server._class_bank_cache, server._level_engine_cache,
        knowledge_engine._index_by_class, knowledge_engine._by_ids_by_class,
        search_service._exercise_index_by_class, search_service._exercise_by_id_by_class,
        search_service._exercise_index_by_chapter_by_class,
    ):
        cache.pop(CLASS_LEVEL, None)


def serve_in_preview(test_case):
    """À appeler dans setUp : la classe est servie jusqu'à la fin du test."""
    served = served_registry(CURRICULUM_REGISTRY_ALL, frozenset({CLASS_LEVEL}))
    for patcher in (
        mock.patch.object(curriculum_registry, "CURRICULUM_REGISTRY", served),
        mock.patch.object(curriculum_stats, "CURRICULUM_REGISTRY", served),
    ):
        patcher.start()
        test_case.addCleanup(patcher.stop)
    test_case.addCleanup(_purge)
    _purge()


class PreviewHTTPCase(unittest.TestCase):
    """Client HTTP réel (server.app.test_client) avec un compte Free neuf,
    la Première spécifique étant servie en prévisualisation."""

    def setUp(self):
        import server

        serve_in_preview(self)
        self.client = server.app.test_client()
        suffix = uuid.uuid4().hex[:12]
        resp = self.client.post("/api/auth/register", json={
            "email": f"ps{suffix}@gmail.com", "username": f"ps{suffix}", "pseudo": "Test",
            "birth_date": "2000-01-01", "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
            "accept_terms": True, "accept_privacy": True,
        })
        self.user = resp.get_json()["user"]
        self.headers = {"X-CSRF-Token": self.client.get_cookie("nm_csrf").value}
