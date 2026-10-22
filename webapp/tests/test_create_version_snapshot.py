"""
Suite de create_version_snapshot.py — vérifie que le script de versioning
produit des instantanés étiquetés "Mathadap" (PRODUCT_NAME) après le
rebranding, sans jamais toucher aux vrais VERSION / versions/ / CHANGELOG.md
du dépôt : tous les chemins du module sont monkeypatchés vers un répertoire
temporaire isolé pour chaque test.
"""
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "create_version_snapshot", ROOT / "create_version_snapshot.py"
)
cvs = importlib.util.module_from_spec(SPEC)
sys.modules["create_version_snapshot"] = cvs
SPEC.loader.exec_module(cvs)


class CreateVersionSnapshotTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = tempfile.TemporaryDirectory()
        tmp_root = Path(self._tmp_dir.name)

        (tmp_root / "webapp" / "static" / "js").mkdir(parents=True)
        (tmp_root / "webapp" / "server.py").write_text(
            "app.run(host='0.0.0.0', port=5050)\n", encoding="utf-8"
        )

        self._orig = dict(
            ROOT=cvs.ROOT,
            VERSIONS_DIR=cvs.VERSIONS_DIR,
            VERSION_FILE=cvs.VERSION_FILE,
            VERSION_JS=cvs.VERSION_JS,
            ROOT_CHANGELOG=cvs.ROOT_CHANGELOG,
        )
        cvs.ROOT = tmp_root
        cvs.VERSIONS_DIR = tmp_root / "versions"
        cvs.VERSION_FILE = tmp_root / "VERSION"
        cvs.VERSION_JS = tmp_root / "webapp" / "static" / "js" / "version.js"
        cvs.ROOT_CHANGELOG = tmp_root / "CHANGELOG.md"

    def tearDown(self):
        for key, value in self._orig.items():
            setattr(cvs, key, value)
        self._tmp_dir.cleanup()

    def test_product_name_is_mathadap(self):
        self.assertEqual(cvs.PRODUCT_NAME, "Mathadap")

    def test_snapshot_uses_mathadap_in_generated_files(self):
        sys.argv = ["create_version_snapshot.py", "Test snapshot"]
        cvs.main()

        dest = cvs.VERSIONS_DIR / "v1.01"
        self.assertTrue(dest.exists())

        run_bat = (dest / "RUN.bat").read_text(encoding="utf-8")
        self.assertIn("Mathadap v1.01", run_bat)
        self.assertNotIn("NovaMath", run_bat)

        readme = (dest / "README.md").read_text(encoding="utf-8")
        self.assertIn("Mathadap v1.01", readme)

        version_changelog = (dest / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertTrue(version_changelog.startswith("# Mathadap v1.01"))

    def test_root_changelog_created_when_missing_keeps_historical_title(self):
        sys.argv = ["create_version_snapshot.py", "Test snapshot"]
        cvs.main()

        root_changelog = cvs.ROOT_CHANGELOG.read_text(encoding="utf-8")
        self.assertTrue(root_changelog.startswith("# NovaMath"))
        self.assertIn("## v1.01", root_changelog)


if __name__ == "__main__":
    unittest.main()
