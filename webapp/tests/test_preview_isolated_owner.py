"""tools/preview_isolated_server.py::_owner_de_test — mode test Owner sur la
base de test isolée (2026-10-26) : l'owner est le compte de la base isolée
dont l'email est l'unique adresse de NOVAMATH_SUPER_ADMIN_EMAILS ; sinon le
mode Owner est désactivé (jamais l'id de data/ appliqué à un autre compte)."""
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import preview_isolated_server as pis  # noqa: E402


class _FakeDb:
    def __init__(self, users):
        self.users = {u["email"]: u for u in users}

    def get_user_by_email(self, email):
        return self.users.get(email.lower())


class TestOwnerDeTest(unittest.TestCase):
    def _run(self, env, users):
        with mock.patch.dict(os.environ, env, clear=False), mock.patch("builtins.print"):
            os.environ.pop("NOVAMATH_OWNER_USER_ID", None) if "NOVAMATH_OWNER_USER_ID" not in env else None
            pis._owner_de_test(_FakeDb(users))
            return os.environ.get("NOVAMATH_OWNER_USER_ID")

    def test_compte_de_la_base_isolee_devient_owner(self):
        got = self._run({"NOVAMATH_SUPER_ADMIN_EMAILS": " Proprio@Gmail.com ", "NOVAMATH_OWNER_USER_ID": "1543"},
                        [{"id": 36, "email": "proprio@gmail.com"}, {"id": 1543, "email": "eleve@gmail.com"}])
        self.assertEqual(got, "36")

    def test_aucun_compte_correspondant_desactive_owner(self):
        got = self._run({"NOVAMATH_SUPER_ADMIN_EMAILS": "proprio@gmail.com", "NOVAMATH_OWNER_USER_ID": "1543"},
                        [{"id": 1543, "email": "eleve@gmail.com"}])
        self.assertIsNone(got)

    def test_plusieurs_adresses_desactive_owner(self):
        got = self._run({"NOVAMATH_SUPER_ADMIN_EMAILS": "proprio@gmail.com,autre@gmail.com", "NOVAMATH_OWNER_USER_ID": "36"},
                        [{"id": 36, "email": "proprio@gmail.com"}])
        self.assertIsNone(got)

    def test_aucune_adresse_desactive_owner(self):
        got = self._run({"NOVAMATH_SUPER_ADMIN_EMAILS": "", "NOVAMATH_OWNER_USER_ID": "36"}, [{"id": 36, "email": "proprio@gmail.com"}])
        self.assertIsNone(got)


if __name__ == "__main__":
    unittest.main()
