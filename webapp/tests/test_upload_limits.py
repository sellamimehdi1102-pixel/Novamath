"""
Suite Release Candidate — protection contre les uploads massifs.

Contexte : avant ce correctif, aucune limite globale (MAX_CONTENT_LENGTH)
n'était configurée sur l'application Flask — un corps de requête énorme
(plusieurs centaines de Mo/quelques Go) était intégralement reçu et
matérialisé en mémoire avant qu'un contrôle métier (15 Mo pour un PDF
chatbot, 5 Mo pour une pièce jointe support) ne le rejette, ouvrant un risque
de saturation mémoire du worker Gunicorn avec seulement quelques requêtes
concurrentes.

Correctif : webapp/config.py::MAX_CONTENT_LENGTH (20 Mo, défaut, couvre la
plus grosse limite métier existante avec une marge d'overhead multipart),
câblé dans app.config (server.py), avec un gestionnaire d'erreur JSON pour le
413 renvoyé par Flask/Werkzeug. Les limites métier existantes (15 Mo PDF,
5 Mo pièce jointe support) restent inchangées et s'appliquent en plus, pour
les corps de requête qui passent sous le plafond global.
"""
import io
import random
import unittest

import fitz  # PyMuPDF — même bibliothèque que chatbot/attachments.py

import config
import db
import server
from plan_service import Plan


def _register(client):
    email = f"upload{random.randint(1_000_000, 9_999_999)}@gmail.com"
    username = f"upload{random.randint(100_000, 999_999)}"
    resp = client.post("/api/auth/register", json={
        "email": email, "username": username, "pseudo": "Test",
        "birth_date": "2000-01-01",
        "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
        "accept_terms": True, "accept_privacy": True,
    })
    user = resp.get_json()["user"]
    csrf = client.get_cookie("nm_csrf").value
    return user, {"X-CSRF-Token": csrf}


def _set_plan(user_id, plan):
    db.set_stripe_subscription(user_id, "sub_test", plan.value, "active")


def _minimal_valid_pdf_bytes():
    """Un vrai PDF exploitable par fitz.open (pas un simple en-tête
    "%PDF-1.4" statique) : une page vide générée par PyMuPDF lui-même,
    garantie compatible avec chatbot/attachments.py::extract_pdf_text."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Contenu de test.")
    return doc.tobytes()


class TestMaxContentLengthConfigure(unittest.TestCase):
    """La configuration globale est bien positionnée et câblée sur l'app."""

    def test_max_content_length_configure_par_defaut(self):
        self.assertEqual(config.MAX_CONTENT_LENGTH, 20 * 1024 * 1024)

    def test_app_flask_utilise_bien_cette_valeur(self):
        self.assertEqual(server.app.config["MAX_CONTENT_LENGTH"], config.MAX_CONTENT_LENGTH)


class TestUploadPdfChatbot(unittest.TestCase):
    ENDPOINT = "/api/chatbot/attachments/pdf"

    def setUp(self):
        self.client = server.app.test_client()
        self.user, self.headers = _register(self.client)
        _set_plan(self.user["id"], Plan.ULTRA)  # Feature.ADVANCED_AI = Ultra uniquement

    def _post_pdf(self, content, filename="doc.pdf"):
        return self.client.post(
            self.ENDPOINT,
            data={"file": (io.BytesIO(content), filename)},
            content_type="multipart/form-data",
            headers=self.headers,
        )

    def test_upload_normal_fonctionne(self):
        resp = self._post_pdf(_minimal_valid_pdf_bytes())
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertIn("text", body)
        self.assertFalse(body["truncated"])

    def test_upload_juste_au_dessus_de_la_limite_metier_15mo_est_refuse_400(self):
        """Sous le plafond global (20 Mo) mais au-dessus de la limite métier
        (15 Mo) : doit rester un 400 métier explicite, pas un 413 générique —
        la limite globale ne doit jamais remplacer les limites métier."""
        oversized_pdf = b"x" * (15 * 1024 * 1024 + 1)
        resp = self._post_pdf(oversized_pdf)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("15 Mo", resp.get_json()["error"])

    def test_upload_enorme_au_dessus_du_plafond_global_est_refuse_413(self):
        """Au-dessus du plafond global MAX_CONTENT_LENGTH (20 Mo) : rejeté par
        Flask/Werkzeug lui-même en 413, avant tout traitement métier — c'est
        exactement le scénario de saturation mémoire corrigé ici."""
        huge_payload = b"x" * (config.MAX_CONTENT_LENGTH + 1024 * 1024)
        resp = self._post_pdf(huge_payload)
        self.assertEqual(resp.status_code, 413)

    def test_reponse_413_est_un_json_coherent_avec_le_reste_de_lapi(self):
        huge_payload = b"x" * (config.MAX_CONTENT_LENGTH + 1024 * 1024)
        resp = self._post_pdf(huge_payload)
        self.assertEqual(resp.status_code, 413)
        self.assertEqual(resp.content_type, "application/json")
        self.assertIn("error", resp.get_json())

    def test_fichier_non_pdf_toujours_refuse_avant_meme_la_taille(self):
        resp = self._post_pdf(b"contenu quelconque", filename="doc.txt")
        self.assertEqual(resp.status_code, 400)


class TestUploadSupportAttachment(unittest.TestCase):
    """Le plafond global protège aussi les routes support, en plus de la
    limite métier existante (5 Mo/pièce jointe, déjà testée par
    test_server_support.py::TestValidationPiecesJointes — non dupliquée ici)."""

    def setUp(self):
        self.client = server.app.test_client()
        self.user, self.headers = _register(self.client)
        resp = self.client.post("/api/support/tickets", json={
            "subject": "Test upload", "category": "technique", "body": "Un souci.",
        }, headers=self.headers)
        self.ticket_id = resp.get_json()["id"]

    def test_upload_normal_fonctionne(self):
        resp = self.client.post(
            f"/api/support/tickets/{self.ticket_id}/messages",
            data={"body": "Voici une capture", "attachments": (io.BytesIO(b"petit contenu"), "capture.png")},
            content_type="multipart/form-data",
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 201)

    def test_upload_enorme_au_dessus_du_plafond_global_est_refuse_413(self):
        huge_payload = b"x" * (config.MAX_CONTENT_LENGTH + 1024 * 1024)
        resp = self.client.post(
            f"/api/support/tickets/{self.ticket_id}/messages",
            data={"body": "Fichier énorme", "attachments": (io.BytesIO(huge_payload), "enorme.png")},
            content_type="multipart/form-data",
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 413)


if __name__ == "__main__":
    unittest.main()
