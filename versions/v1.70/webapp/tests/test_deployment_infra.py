"""
Suite ARCH-03/ARCH-05 : infrastructure de déploiement (Dockerfile,
docker-compose.yml, gunicorn.conf.py, CI GitHub Actions, fichiers de
configuration par plateforme, qualité/documentation). Ne teste aucune
logique métier (voir les services protégés listés dans le cahier des
charges) — uniquement la cohérence des fichiers d'infrastructure ajoutés par
ce chantier.

Les vérifications nécessitant un binaire externe (`gunicorn`, `docker`) se
désactivent proprement (skipTest) quand ce binaire est absent ou sous
Windows (Gunicorn est un serveur POSIX, jamais utilisé hors conteneur/VPS
Linux — voir gunicorn.conf.py) : elles restent pleinement actives sous la CI
Linux (.github/workflows/ci.yml) sans jamais casser la suite locale.
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - PyYAML n'est qu'une dépendance dev/CI
    yaml = None

import tomllib

ROOT = Path(__file__).resolve().parent.parent.parent


def _read(relative_path):
    return (ROOT / relative_path).read_text(encoding="utf-8")


def _load_gunicorn_conf():
    """Charge gunicorn.conf.py comme un module Python autonome — ne
    nécessite PAS le paquet `gunicorn` installé (c'est un simple fichier
    Python lu par l'exécutable gunicorn, aucune dépendance croisée)."""
    spec = importlib.util.spec_from_file_location("novamath_gunicorn_conf", ROOT / "gunicorn.conf.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _EnvIsolatedTestCase(unittest.TestCase):
    ENV_VARS = (
        "PORT", "WEB_CONCURRENCY", "GUNICORN_THREADS", "GUNICORN_WORKER_CLASS",
        "GUNICORN_TIMEOUT", "GUNICORN_GRACEFUL_TIMEOUT", "GUNICORN_KEEPALIVE",
        "GUNICORN_MAX_REQUESTS", "GUNICORN_MAX_REQUESTS_JITTER", "GUNICORN_LOGLEVEL",
        "GUNICORN_ACCESSLOG", "GUNICORN_ERRORLOG", "GUNICORN_PRELOAD_APP",
    )

    def setUp(self):
        self._saved = {name: os.environ.get(name) for name in self.ENV_VARS}
        for name in self.ENV_VARS:
            os.environ.pop(name, None)

    def tearDown(self):
        for name, value in self._saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


# ── gunicorn.conf.py : chargement pur, aucun binaire requis ─────────────────
class TestGunicornConfigDefauts(_EnvIsolatedTestCase):
    def test_bind_port_par_defaut_8000(self):
        self.assertEqual(_load_gunicorn_conf().bind, "0.0.0.0:8000")

    def test_workers_est_un_entier_positif(self):
        workers = _load_gunicorn_conf().workers
        self.assertIsInstance(workers, int)
        self.assertGreater(workers, 0)

    def test_workers_plafonne_a_quatre_par_defaut(self):
        self.assertLessEqual(_load_gunicorn_conf().workers, 4)

    def test_threads_par_defaut_deux(self):
        self.assertEqual(_load_gunicorn_conf().threads, 2)

    def test_worker_class_gthread_par_defaut(self):
        self.assertEqual(_load_gunicorn_conf().worker_class, "gthread")

    def test_timeout_par_defaut_soixante(self):
        self.assertEqual(_load_gunicorn_conf().timeout, 60)

    def test_graceful_timeout_par_defaut_trente(self):
        self.assertEqual(_load_gunicorn_conf().graceful_timeout, 30)

    def test_keepalive_par_defaut_cinq(self):
        self.assertEqual(_load_gunicorn_conf().keepalive, 5)

    def test_max_requests_par_defaut_mille(self):
        self.assertEqual(_load_gunicorn_conf().max_requests, 1000)

    def test_max_requests_jitter_par_defaut_cent(self):
        self.assertEqual(_load_gunicorn_conf().max_requests_jitter, 100)

    def test_accesslog_stdout_par_defaut(self):
        self.assertEqual(_load_gunicorn_conf().accesslog, "-")

    def test_errorlog_stderr_par_defaut(self):
        self.assertEqual(_load_gunicorn_conf().errorlog, "-")

    def test_loglevel_info_par_defaut(self):
        self.assertEqual(_load_gunicorn_conf().loglevel, "info")

    def test_preload_app_true_par_defaut(self):
        self.assertTrue(_load_gunicorn_conf().preload_app)


class TestGunicornConfigSurcharges(_EnvIsolatedTestCase):
    def test_bind_respecte_port_env(self):
        os.environ["PORT"] = "9999"
        self.assertEqual(_load_gunicorn_conf().bind, "0.0.0.0:9999")

    def test_workers_respecte_web_concurrency_env(self):
        os.environ["WEB_CONCURRENCY"] = "7"
        self.assertEqual(_load_gunicorn_conf().workers, 7)

    def test_threads_respecte_gunicorn_threads_env(self):
        os.environ["GUNICORN_THREADS"] = "4"
        self.assertEqual(_load_gunicorn_conf().threads, 4)

    def test_timeout_respecte_env(self):
        os.environ["GUNICORN_TIMEOUT"] = "120"
        self.assertEqual(_load_gunicorn_conf().timeout, 120)

    def test_loglevel_normalise_en_minuscule(self):
        os.environ["GUNICORN_LOGLEVEL"] = "DEBUG"
        self.assertEqual(_load_gunicorn_conf().loglevel, "debug")

    def test_preload_app_respecte_env_false(self):
        os.environ["GUNICORN_PRELOAD_APP"] = "false"
        self.assertFalse(_load_gunicorn_conf().preload_app)

    def test_worker_class_respecte_env(self):
        os.environ["GUNICORN_WORKER_CLASS"] = "sync"
        self.assertEqual(_load_gunicorn_conf().worker_class, "sync")

    def test_valeur_entiere_invalide_retombe_sur_le_defaut(self):
        os.environ["GUNICORN_TIMEOUT"] = "pas-un-entier"
        self.assertEqual(_load_gunicorn_conf().timeout, 60)


class TestGunicornCheckConfig(unittest.TestCase):
    """Intégration réelle avec le binaire gunicorn (POSIX uniquement — voir
    docstring du module) : `--check-config` valide la syntaxe et l'import de
    l'application SANS jamais ouvrir de port ni servir de requête."""

    def setUp(self):
        if sys.platform == "win32":
            self.skipTest("Gunicorn est un serveur POSIX (fcntl/os.fork) — non testable sous Windows.")
        if shutil.which("gunicorn") is None:
            self.skipTest("Binaire gunicorn absent de cet environnement (voir requirements.txt).")

    def test_gunicorn_check_config_reussit(self):
        result = subprocess.run(
            ["gunicorn", "-c", "gunicorn.conf.py", "--check-config", "webapp.server:app"],
            cwd=ROOT, capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)


# ── Dockerfile ────────────────────────────────────────────────────────────
class TestDockerfile(unittest.TestCase):
    def setUp(self):
        self.content = _read("Dockerfile")

    def test_existe(self):
        self.assertTrue((ROOT / "Dockerfile").exists())

    def test_image_python_officielle_legere(self):
        self.assertIn("FROM python:3.12-slim", self.content)

    def test_multi_stage_build(self):
        self.assertIn(" AS builder", self.content)
        self.assertIn(" AS final", self.content)
        self.assertEqual(self.content.count("FROM python:3.12-slim"), 2)

    def test_utilisateur_non_root(self):
        self.assertIn("USER novamath", self.content)
        self.assertNotIn("USER root", self.content)

    def test_pythondontwritebytecode(self):
        self.assertIn("PYTHONDONTWRITEBYTECODE=1", self.content)

    def test_pythonunbuffered(self):
        self.assertIn("PYTHONUNBUFFERED=1", self.content)

    def test_healthcheck_present(self):
        self.assertIn("HEALTHCHECK", self.content)
        self.assertIn("/api/health", self.content)

    def test_cmd_utilise_gunicorn(self):
        self.assertIn('CMD ["gunicorn"', self.content)

    def test_jamais_flask_development_server(self):
        # Seule la ligne CMD (l'instruction réellement exécutée au démarrage
        # du conteneur) importe ici — le mot "app.run()" apparaît par
        # ailleurs dans un commentaire expliquant pourquoi ce n'est PAS
        # utilisé, ce qui ne doit jamais faire échouer ce test.
        cmd_lines = [line for line in self.content.splitlines() if line.strip().startswith("CMD")]
        self.assertTrue(cmd_lines, "aucune instruction CMD trouvée dans le Dockerfile")
        for line in cmd_lines:
            self.assertNotIn("app.run(", line)
            self.assertNotIn("flask run", line)
            self.assertNotIn("server.py", line)

    def test_port_configurable_expose_et_env(self):
        self.assertIn("EXPOSE 8000", self.content)
        self.assertIn("PORT=8000", self.content)

    def test_gunicorn_conf_utilise(self):
        self.assertIn("gunicorn.conf.py", self.content)


# ── docker-compose.yml ────────────────────────────────────────────────────
class TestDockerCompose(unittest.TestCase):
    def setUp(self):
        self.content = _read("docker-compose.yml")

    def test_existe(self):
        self.assertTrue((ROOT / "docker-compose.yml").exists())

    def test_yaml_valide(self):
        if yaml is None:
            self.skipTest("PyYAML absent (voir requirements-dev.txt).")
        parsed = yaml.safe_load(self.content)
        self.assertIn("services", parsed)
        self.assertIn("web", parsed["services"])

    def test_service_web_construit_depuis_le_dockerfile(self):
        self.assertIn("dockerfile: Dockerfile", self.content)

    def test_volumes_nommes_pour_data_et_backups(self):
        self.assertIn("novamath-data:/app/data", self.content)
        self.assertIn("novamath-backups:/app/backups", self.content)

    def test_redemarrage_automatique(self):
        self.assertIn("restart: unless-stopped", self.content)

    def test_flask_env_production(self):
        self.assertIn("FLASK_ENV: production", self.content)

    def test_port_personnalisable_sans_rebuild(self):
        self.assertIn("${PORT:-8000}", self.content)

    def test_service_postgres_reserve_et_desactive(self):
        # Réservé pour plus tard (voir DEPLOYMENT.md), jamais actif par
        # défaut : commenté, avec un profil dédié explicite.
        self.assertIn("profiles", self.content)
        self.assertIn("postgres", self.content.lower())

    def test_healthcheck_defini(self):
        self.assertIn("healthcheck", self.content)
        self.assertIn("/api/health", self.content)


# ── .dockerignore ─────────────────────────────────────────────────────────
class TestDockerignore(unittest.TestCase):
    def setUp(self):
        self.content = _read(".dockerignore")

    def test_existe(self):
        self.assertTrue((ROOT / ".dockerignore").exists())

    def test_exclut_git_et_pycache(self):
        self.assertIn(".git", self.content)
        self.assertIn("__pycache__", self.content)

    def test_exclut_les_tests(self):
        self.assertIn("webapp/tests/", self.content)

    def test_exclut_env_reel_mais_pas_lexemple(self):
        self.assertIn(".env\n", self.content)
        self.assertIn("!.env.example", self.content)

    def test_exclut_les_sources_hors_perimetre_du_site(self):
        for entry in ("versions/", "Chapitres/", "texts/", "tools/legacy-pipeline/"):
            self.assertIn(entry, self.content)


# ── .github/workflows/ci.yml ──────────────────────────────────────────────
class TestCIWorkflow(unittest.TestCase):
    def setUp(self):
        self.path = ".github/workflows/ci.yml"
        self.content = _read(self.path)

    def test_existe(self):
        self.assertTrue((ROOT / self.path).exists())

    def test_yaml_valide_avec_des_jobs(self):
        if yaml is None:
            self.skipTest("PyYAML absent (voir requirements-dev.txt).")
        parsed = yaml.safe_load(self.content)
        self.assertIn("jobs", parsed)
        self.assertGreaterEqual(len(parsed["jobs"]), 2)

    def test_declenche_sur_push_et_pull_request(self):
        if yaml is None:
            self.skipTest("PyYAML absent (voir requirements-dev.txt).")
        parsed = yaml.safe_load(self.content)
        triggers = parsed.get(True, parsed.get("on"))
        self.assertIn("push", triggers)
        self.assertIn("pull_request", triggers)

    def test_etape_installation_des_dependances(self):
        self.assertIn("pip install", self.content)

    def test_etape_lint(self):
        self.assertIn("ruff", self.content)

    def test_etape_verification_des_imports(self):
        self.assertIn("import server", self.content)

    def test_etape_tests(self):
        self.assertIn("pytest", self.content)

    def test_etape_build_docker(self):
        self.assertIn("docker/build-push-action", self.content)
        self.assertIn("push: false", self.content)

    def test_ne_deploie_jamais(self):
        # Seules les lignes hors commentaire comptent : le fichier explique
        # délibérément en commentaire ce qu'il NE fait jamais (ex : "aucun
        # `docker push`"), ce qui ne doit jamais faire échouer ce test.
        code_lines = "\n".join(
            line for line in self.content.splitlines() if not line.strip().startswith("#")
        ).lower()
        interdits = ("docker push", "railway up", "fly deploy", "gcloud run deploy", "az webapp", "kubectl apply")
        for terme in interdits:
            self.assertNotIn(terme, code_lines, f"la CI ne doit jamais exécuter : {terme}")


# ── Qualité : .editorconfig / .gitattributes ─────────────────────────────
class TestEditorConfig(unittest.TestCase):
    def test_existe_et_root_true(self):
        content = _read(".editorconfig")
        self.assertTrue(content.strip().startswith("#") or "root = true" in content)
        self.assertIn("root = true", content)

    def test_regles_python(self):
        content = _read(".editorconfig")
        self.assertIn("[*.py]", content)


class TestGitattributes(unittest.TestCase):
    def test_existe_et_normalise_les_fins_de_ligne(self):
        content = _read(".gitattributes")
        self.assertIn("text=auto", content)

    def test_binaires_marques(self):
        content = _read(".gitattributes")
        self.assertIn("*.pkl binary", content)
        self.assertIn("*.db binary", content)


# ── .gitignore : jamais de suppression, uniquement des ajouts ────────────
class TestGitignoreRegression(unittest.TestCase):
    ENTREES_DORIGINE = (".env", "__pycache__/", "*.pyc", "data/novamath.db", ".flask_secret_key", ".admin_key", "backups/")

    def setUp(self):
        self.content = _read(".gitignore")

    def test_conserve_toutes_les_entrees_dorigine(self):
        for entree in self.ENTREES_DORIGINE:
            self.assertIn(entree, self.content, f"entrée .gitignore préexistante disparue : {entree}")

    def test_ajoute_lexclusion_des_env_par_environnement(self):
        self.assertIn(".env.*", self.content)
        self.assertIn("!.env.example", self.content)

    def test_ajoute_lexclusion_des_caches_de_test(self):
        self.assertIn(".pytest_cache/", self.content)


# ── Cohérence des variables d'environnement ───────────────────────────────
class TestVariablesDocumentees(unittest.TestCase):
    def setUp(self):
        self.env_example = _read(".env.example")

    def test_toutes_les_variables_gunicorn_sont_documentees(self):
        variables = (
            "PORT", "WEB_CONCURRENCY", "GUNICORN_THREADS", "GUNICORN_WORKER_CLASS",
            "GUNICORN_TIMEOUT", "GUNICORN_GRACEFUL_TIMEOUT", "GUNICORN_KEEPALIVE",
            "GUNICORN_MAX_REQUESTS", "GUNICORN_MAX_REQUESTS_JITTER", "GUNICORN_LOGLEVEL",
            "GUNICORN_ACCESSLOG", "GUNICORN_ERRORLOG", "GUNICORN_PRELOAD_APP",
        )
        for variable in variables:
            self.assertIn(variable, self.env_example, f"variable non documentée dans .env.example : {variable}")

    def test_google_oauth_documente(self):
        self.assertIn("GOOGLE_CLIENT_ID", self.env_example)
        self.assertIn("GOOGLE_CLIENT_SECRET", self.env_example)

    def test_gunicorn_conf_ne_code_aucune_valeur_en_dur_sans_variable_env(self):
        content = _read("gunicorn.conf.py")
        for variable in ("PORT", "WEB_CONCURRENCY", "GUNICORN_THREADS", "GUNICORN_TIMEOUT"):
            self.assertTrue(
                f'"{variable}"' in content or f"'{variable}'" in content,
                f"{variable} devrait être lue depuis l'environnement dans gunicorn.conf.py",
            )


# ── Documentation ──────────────────────────────────────────────────────────
class TestDeploymentDocs(unittest.TestCase):
    def setUp(self):
        self.deployment = _read("DEPLOYMENT.md")
        self.readme = _read("README.md")

    def test_deployment_md_existe(self):
        self.assertTrue((ROOT / "DEPLOYMENT.md").exists())

    def test_readme_reference_deployment_md(self):
        self.assertIn("DEPLOYMENT.md", self.readme)

    def test_sections_requises_presentes(self):
        for section in (
            "## Installation", "## Développement", "## Docker", "## Production",
            "## Variables d'environnement", "## Déploiement par plateforme",
            "## Sauvegardes", "## Rollback", "## Mise à jour",
        ):
            self.assertIn(section, self.deployment, f"section manquante dans DEPLOYMENT.md : {section}")

    def test_couvre_chaque_plateforme_demandee(self):
        for plateforme in ("VPS Linux", "Docker", "Railway", "Render", "Fly.io", "Coolify", "Azure App Service", "Google Cloud Run"):
            self.assertIn(plateforme, self.deployment, f"plateforme non documentée : {plateforme}")

    def test_documente_les_environnements(self):
        for env in ("development", "staging", "production"):
            self.assertIn(env, self.deployment)


# ── Fichiers de configuration par plateforme ──────────────────────────────
class TestRailwayConfig(unittest.TestCase):
    def test_json_valide(self):
        parsed = json.loads(_read("railway.json"))
        self.assertEqual(parsed["build"]["builder"], "DOCKERFILE")

    def test_healthcheck_configure(self):
        parsed = json.loads(_read("railway.json"))
        self.assertEqual(parsed["deploy"]["healthcheckPath"], "/api/health")


class TestRenderConfig(unittest.TestCase):
    def test_yaml_valide(self):
        if yaml is None:
            self.skipTest("PyYAML absent (voir requirements-dev.txt).")
        parsed = yaml.safe_load(_read("render.yaml"))
        service = parsed["services"][0]
        self.assertEqual(service["dockerfilePath"], "./Dockerfile")
        self.assertEqual(service["healthCheckPath"], "/api/health")

    def test_secrets_jamais_en_clair(self):
        content = _read("render.yaml")
        self.assertNotIn("sk_live", content)
        self.assertNotIn("sk_test", content)


class TestFlyConfig(unittest.TestCase):
    def test_toml_valide(self):
        with open(ROOT / "fly.toml", "rb") as f:
            parsed = tomllib.load(f)
        self.assertEqual(parsed["http_service"]["internal_port"], 8080)

    def test_healthcheck_configure(self):
        with open(ROOT / "fly.toml", "rb") as f:
            parsed = tomllib.load(f)
        checks = parsed["http_service"]["checks"]
        self.assertTrue(any(c["path"] == "/api/health" for c in checks))


# ── requirements-dev.txt ──────────────────────────────────────────────────
class TestRequirementsDev(unittest.TestCase):
    def test_existe_et_inclut_requirements_txt(self):
        content = _read("requirements-dev.txt")
        self.assertIn("-r requirements.txt", content)

    def test_ne_modifie_pas_requirements_txt(self):
        content = _read("requirements.txt")
        for dependance in ("Flask==3.1.3", "gunicorn==23.0.0", "stripe==15.3.1", "cryptography==49.0.0"):
            self.assertIn(dependance, content)


if __name__ == "__main__":
    unittest.main()
