"""
Durcissement production : server.py::_is_admin comparait ADMIN_KEY avec `==`
(comparaison de chaînes standard, qui s'arrête au premier caractère différent
— un signal temporel exploitable pour retrouver la clé caractère par
caractère). Corrigé en secrets.compare_digest (même mécanisme que
auth.py::csrf_protect). Ce test vérifie le comportement fonctionnel de
_is_admin (jamais le timing, non mesurable de façon fiable en test unitaire) :
la correction ne doit rien changer au comportement observable.
"""
import unittest
from unittest.mock import MagicMock, patch

import server


def _request_with_key(key):
    req = MagicMock()
    req.headers = {"X-Admin-Key": key} if key is not None else {}
    return req


class TestIsAdmin(unittest.TestCase):
    @patch.object(server, "ADMIN_KEY", "un-secret-vraiment-long-1234567890")
    def test_bonne_cle_est_acceptee(self):
        self.assertTrue(server._is_admin(_request_with_key("un-secret-vraiment-long-1234567890")))

    @patch.object(server, "ADMIN_KEY", "un-secret-vraiment-long-1234567890")
    def test_mauvaise_cle_est_refusee(self):
        self.assertFalse(server._is_admin(_request_with_key("mauvaise-cle")))

    @patch.object(server, "ADMIN_KEY", "un-secret-vraiment-long-1234567890")
    def test_cle_presque_correcte_est_refusee(self):
        """Diffère d'un seul caractère à la fin — cas type d'une attaque
        temporelle si la comparaison n'était pas en temps constant."""
        self.assertFalse(server._is_admin(_request_with_key("un-secret-vraiment-long-1234567891")))

    @patch.object(server, "ADMIN_KEY", "un-secret-vraiment-long-1234567890")
    def test_en_tete_absent_est_refuse(self):
        self.assertFalse(server._is_admin(_request_with_key(None)))

    @patch.object(server, "ADMIN_KEY", "un-secret-vraiment-long-1234567890")
    def test_cle_vide_est_refusee(self):
        self.assertFalse(server._is_admin(_request_with_key("")))

    @patch.object(server, "ADMIN_KEY", "")
    def test_admin_key_non_configuree_refuse_meme_un_en_tete_vide(self):
        """ADMIN_KEY vide (non configurée côté serveur) ne doit jamais
        matcher un header vide — compare_digest("", "") vaudrait True sans
        le bool(key) conservé explicitement dans _is_admin."""
        self.assertFalse(server._is_admin(_request_with_key("")))


if __name__ == "__main__":
    unittest.main()
