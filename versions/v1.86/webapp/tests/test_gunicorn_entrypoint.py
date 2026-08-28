"""
Suite Phase 0 (ARCH-01) : `webapp` doit être importable comme un package
Python classique, condition nécessaire pour `gunicorn webapp.server:app`
(WSGI callable `app`) lancé depuis la racine du projet plutôt que via
`python webapp/server.py`.
"""
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


class TestPointDEntreeGunicorn(unittest.TestCase):
    def test_webapp_server_app_importable_depuis_la_racine(self):
        result = subprocess.run(
            [sys.executable, "-c", "from webapp.server import app; print(type(app).__name__)"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Flask", result.stdout)

    def test_gunicorn_declare_dans_requirements(self):
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
        self.assertIn("gunicorn", requirements.lower())


if __name__ == "__main__":
    unittest.main()
