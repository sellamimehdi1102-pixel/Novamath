"""
Régression "troisieme" (curriculum_registry.py) : un programme déclaré dans
CURRICULUM_REGISTRY avec un courses_dir peut passer toutes les vérifications
de fichiers sur disque et pourtant ne jamais être atteignable en HTTP (mauvais
static_folder, oubli de copie par le build Vite, permissions...). Cette suite
ferme ce trou en effectuant le VRAI fetch HTTP que webapp/static/js/cours.js
fait au clic sur "Ouvrir"/"Continuer" (voir cours.js::loadChapterContent),
pour chaque chapitre de chaque programme — pas seulement une vérification de
chemin sur disque.

Chantier "Répartition du contenu des cours par plan" (2026-08-26) : le
contenu ne passe plus par un fetch statique direct (webapp/static/data/
cours*/, retiré de static/) mais par GET /api/course-content/<classe>/
<chapitre> (voir server.py::api_course_content / course_content_service.py).
Cette suite est mise à jour pour exercer la VRAIE route utilisée aujourd'hui
par cours.js, et vérifie explicitement que l'ancien chemin statique n'est
plus jamais accessible (voir aussi tests/test_course_content_service.py pour
le filtrage Free/Premium/Ultra lui-même).
"""
import random
import unittest

import curriculum_registry
import server


def _register(client):
    email = f"test{random.randint(1_000_000, 9_999_999)}@gmail.com"
    username = f"testuser{random.randint(100_000, 999_999)}"
    resp = client.post("/api/auth/register", json={
        "email": email, "username": username, "pseudo": "Test",
        "birth_date": "2000-01-01",
        "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
        "accept_terms": True, "accept_privacy": True,
    })
    user = resp.get_json()["user"]
    csrf = client.get_cookie("nm_csrf").value
    return user, {"X-CSRF-Token": csrf}


class TestFetchHTTPChapitresParCurriculum(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()
        self.user, self.headers = _register(self.client)

    def test_aucun_fetch_de_chapitre_via_lapi_ne_retourne_404(self):
        failures = []
        checked = 0
        for profile in curriculum_registry.CURRICULUM_REGISTRY.values():
            if profile.courses_dir is None:
                continue
            for chapitre_path in sorted(profile.courses_dir.glob("chapitre_*.json")):
                num = chapitre_path.stem.split("_")[1]
                url = f"/api/course-content/{profile.id}/Chapitre_{num}"
                resp = self.client.get(url, headers=self.headers)
                checked += 1
                if resp.status_code != 200:
                    failures.append(f"{profile.id!r} : {url} -> {resp.status_code}")

        self.assertGreater(checked, 0, "aucun chapitre trouvé — le test lui-même serait un faux négatif")
        self.assertEqual(failures, [], "\n" + "\n".join(failures))

    def test_rapport_par_curriculum(self):
        """Pas une assertion stricte — un rapport lisible (nombre de
        chapitres, statut) pour chaque programme, imprimé lors d'un `-s`."""
        for profile in curriculum_registry.CURRICULUM_REGISTRY.values():
            if profile.courses_dir is None:
                print(f"{profile.id:12s} — pas de courses_dir (ressource assumée absente)")
                continue
            chapitres = sorted(profile.courses_dir.glob("chapitre_*.json"))
            statuses = [
                self.client.get(f"/api/course-content/{profile.id}/Chapitre_{p.stem.split('_')[1]}", headers=self.headers).status_code
                for p in chapitres
            ]
            all_ok = all(s == 200 for s in statuses)
            print(f"{profile.id:12s} — {len(chapitres)} chapitre(s), tous 200 = {all_ok}")
            self.assertTrue(all_ok, f"{profile.id!r} a au moins un chapitre en échec : {statuses}")

    def test_lancien_chemin_statique_direct_nest_plus_accessible(self):
        """Le contenu complet des cours ne doit plus jamais être servi comme
        fichier statique brut (voir curriculum_registry.COURSE_CONTENT_DIR,
        déplacé hors de webapp/static/) — sans quoi le filtrage Premium/Ultra
        de la nouvelle route serait purement cosmétique, contournable par un
        simple fetch direct de l'ancien chemin."""
        anon_client = server.app.test_client()  # même un visiteur non connecté
        for profile in curriculum_registry.CURRICULUM_REGISTRY.values():
            if profile.courses_dir is None:
                continue
            course_dir_name = "cours" if profile.id == "seconde" else f"cours_{profile.id}"
            for chapitre_path in sorted(profile.courses_dir.glob("chapitre_*.json")):
                url = f"/data/{course_dir_name}/{chapitre_path.name}"
                resp = anon_client.get(url)
                self.assertEqual(
                    resp.status_code, 404,
                    f"{url} est encore accessible directement (statut {resp.status_code}) — "
                    "le contenu Premium/Ultra pourrait être récupéré sans passer par le filtrage.",
                )


if __name__ == "__main__":
    unittest.main()
