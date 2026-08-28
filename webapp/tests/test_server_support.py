"""
Suite Release Candidate — support (tickets utilisateur + panneau admin).

Le rapport d'audit précédent indiquait une ABSENCE de tests sur ce périmètre,
pas un bug constaté dans le code : après relecture complète de server.py
(routes /api/support/*, /api/admin/support/*) et support_attachment_
service.py, les contrôles d'accès existants sont corrects — _user_owns_
ticket_or_404, la vérification d'appartenance dans
api_support_attachment_download, et support_service.set_satisfaction_rating
imposent tous une vérification `ticket["user_id"] == request.current_user
["id"]`. Aucune modification de code métier ici (conforme à la consigne) :
uniquement les tests manquants, en particulier la preuve qu'un utilisateur
ne peut JAMAIS accéder aux tickets/pièces jointes d'un autre.
"""
import io
import random
import unittest

import db
import server


def _register(client):
    email = f"support{random.randint(1_000_000, 9_999_999)}@gmail.com"
    username = f"support{random.randint(100_000, 999_999)}"
    resp = client.post("/api/auth/register", json={
        "email": email, "username": username, "pseudo": "Test",
        "birth_date": "2000-01-01",
        "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
        "accept_terms": True, "accept_privacy": True,
    })
    user = resp.get_json()["user"]
    csrf = client.get_cookie("nm_csrf").value
    return user, {"X-CSRF-Token": csrf}


def _make_support_admin(user_id):
    """Promeut un compte au rôle interne minimum requis par le module
    "support" (voir server.py::_SUPPORT_MODULE_ROLE) — même mécanisme que le
    reste du projet (role_service, table users.role, valeur brute str)."""
    db.set_user_role(user_id, server._SUPPORT_MODULE_ROLE.value)


class SupportTestCase(unittest.TestCase):
    def setUp(self):
        self.client_a = server.app.test_client()
        self.user_a, self.headers_a = _register(self.client_a)
        self.client_b = server.app.test_client()
        self.user_b, self.headers_b = _register(self.client_b)

    def _create_ticket(self, client, headers, subject="Souci de connexion", body="Ça ne marche pas."):
        resp = client.post("/api/support/tickets", json={
            "subject": subject, "category": "technique", "body": body,
        }, headers=headers)
        self.assertEqual(resp.status_code, 201)
        return resp.get_json()["id"]


class TestCreationEtConsultationTicket(SupportTestCase):
    def test_creation_ticket_valide(self):
        ticket_id = self._create_ticket(self.client_a, self.headers_a)
        resp = self.client_a.get(f"/api/support/tickets/{ticket_id}", headers=self.headers_a)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["id"], ticket_id)

    def test_creation_sans_sujet_est_refusee(self):
        resp = self.client_a.post("/api/support/tickets", json={
            "subject": "", "category": "technique", "body": "Un souci.",
        }, headers=self.headers_a)
        self.assertEqual(resp.status_code, 400)

    def test_creation_categorie_invalide_est_refusee(self):
        resp = self.client_a.post("/api/support/tickets", json={
            "subject": "Sujet", "category": "pas-une-vraie-categorie", "body": "Un souci.",
        }, headers=self.headers_a)
        self.assertEqual(resp.status_code, 400)

    def test_liste_des_tickets_ne_contient_que_les_siens(self):
        ticket_a = self._create_ticket(self.client_a, self.headers_a)
        self._create_ticket(self.client_b, self.headers_b)
        resp = self.client_a.get("/api/support/tickets", headers=self.headers_a)
        ids = [t["id"] for t in resp.get_json()]
        self.assertIn(ticket_a, ids)
        self.assertEqual(len(ids), 1)

    def test_anonyme_est_rejete(self):
        anon = server.app.test_client()
        resp = anon.get("/api/support/tickets")
        self.assertEqual(resp.status_code, 401)


class TestControleAccesInterUtilisateurs(SupportTestCase):
    """Cœur du correctif : preuve que le contrôle d'accès déjà présent dans
    le code fonctionne réellement — un utilisateur B ne peut JAMAIS agir sur
    le ticket d'un utilisateur A, sur aucune des routes."""

    def setUp(self):
        super().setUp()
        self.ticket_id = self._create_ticket(self.client_a, self.headers_a)

    def test_b_ne_peut_pas_consulter_le_ticket_de_a(self):
        resp = self.client_b.get(f"/api/support/tickets/{self.ticket_id}", headers=self.headers_b)
        self.assertEqual(resp.status_code, 404)

    def test_b_ne_peut_pas_repondre_au_ticket_de_a(self):
        resp = self.client_b.post(
            f"/api/support/tickets/{self.ticket_id}/messages", json={"body": "Intrusion"}, headers=self.headers_b,
        )
        self.assertEqual(resp.status_code, 404)
        # Le ticket de A ne doit avoir reçu aucun message de B.
        detail = self.client_a.get(f"/api/support/tickets/{self.ticket_id}", headers=self.headers_a).get_json()
        self.assertTrue(all(m["author_id"] != self.user_b["id"] for m in detail["messages"]))

    def test_b_ne_peut_pas_noter_la_satisfaction_du_ticket_de_a(self):
        resp = self.client_b.post(
            f"/api/support/tickets/{self.ticket_id}/satisfaction", json={"rating": 1}, headers=self.headers_b,
        )
        self.assertEqual(resp.status_code, 400)

    def test_b_ne_peut_pas_telecharger_une_piece_jointe_du_ticket_de_a(self):
        """Scénario central de l'audit Release Candidate : IDOR potentiel sur
        le téléchargement de pièce jointe via un attachment_id deviné/énuméré."""
        upload = self.client_a.post(
            f"/api/support/tickets/{self.ticket_id}/messages",
            data={"body": "Voici une capture", "attachments": (io.BytesIO(b"contenu-image-factice"), "capture.png")},
            content_type="multipart/form-data",
            headers=self.headers_a,
        )
        self.assertEqual(upload.status_code, 201)
        detail = self.client_a.get(f"/api/support/tickets/{self.ticket_id}", headers=self.headers_a).get_json()
        attachment_id = detail["messages"][-1]["attachments"][0]["id"]

        # A peut télécharger sa propre pièce jointe.
        own = self.client_a.get(f"/api/support/attachments/{attachment_id}", headers=self.headers_a)
        self.assertEqual(own.status_code, 200)

        # B ne peut pas, même en connaissant l'id exact.
        intrusion = self.client_b.get(f"/api/support/attachments/{attachment_id}", headers=self.headers_b)
        self.assertEqual(intrusion.status_code, 404)

    def test_attachment_id_inexistant_renvoie_404(self):
        resp = self.client_a.get("/api/support/attachments/999999", headers=self.headers_a)
        self.assertEqual(resp.status_code, 404)


class TestValidationPiecesJointes(SupportTestCase):
    def setUp(self):
        super().setUp()
        self.ticket_id = self._create_ticket(self.client_a, self.headers_a)

    def test_extension_non_autorisee_est_refusee(self):
        resp = self.client_a.post(
            f"/api/support/tickets/{self.ticket_id}/messages",
            data={"body": "Voici un script", "attachments": (io.BytesIO(b"echo hack"), "script.sh")},
            content_type="multipart/form-data",
            headers=self.headers_a,
        )
        self.assertEqual(resp.status_code, 400)

    def test_fichier_trop_volumineux_est_refuse(self):
        import support_attachment_service
        oversized = b"x" * (support_attachment_service.MAX_SIZE_BYTES + 1)
        resp = self.client_a.post(
            f"/api/support/tickets/{self.ticket_id}/messages",
            data={"body": "Fichier énorme", "attachments": (io.BytesIO(oversized), "gros.png")},
            content_type="multipart/form-data",
            headers=self.headers_a,
        )
        self.assertEqual(resp.status_code, 400)

    def test_fichier_vide_est_refuse(self):
        resp = self.client_a.post(
            f"/api/support/tickets/{self.ticket_id}/messages",
            data={"body": "Fichier vide", "attachments": (io.BytesIO(b""), "vide.png")},
            content_type="multipart/form-data",
            headers=self.headers_a,
        )
        self.assertEqual(resp.status_code, 400)

    def test_message_sans_fichier_fonctionne_normalement(self):
        resp = self.client_a.post(
            f"/api/support/tickets/{self.ticket_id}/messages", json={"body": "Juste du texte"}, headers=self.headers_a,
        )
        self.assertEqual(resp.status_code, 201)


class TestNotesInternesJamaisExposeesAUnUtilisateur(SupportTestCase):
    def test_notes_absentes_de_la_reponse_utilisateur(self):
        ticket_id = self._create_ticket(self.client_a, self.headers_a)
        detail = self.client_a.get(f"/api/support/tickets/{ticket_id}", headers=self.headers_a).get_json()
        self.assertNotIn("notes", detail)


class TestPanneauAdminSupport(SupportTestCase):
    def setUp(self):
        super().setUp()
        self.ticket_id = self._create_ticket(self.client_a, self.headers_a)
        self.admin_client = server.app.test_client()
        self.admin_user, self.admin_headers = _register(self.admin_client)
        _make_support_admin(self.admin_user["id"])

    def test_utilisateur_normal_ne_peut_pas_acceder_au_panneau_admin_support(self):
        resp = self.client_a.get("/api/admin/support/tickets", headers=self.headers_a)
        self.assertEqual(resp.status_code, 403)

    def test_anonyme_ne_peut_pas_acceder_au_panneau_admin_support(self):
        anon = server.app.test_client()
        resp = anon.get("/api/admin/support/tickets")
        self.assertEqual(resp.status_code, 401)

    def test_admin_support_peut_lister_tous_les_tickets(self):
        resp = self.admin_client.get("/api/admin/support/tickets", headers=self.admin_headers)
        self.assertEqual(resp.status_code, 200)
        ids = [t["id"] for t in resp.get_json()["items"]]
        self.assertIn(self.ticket_id, ids)

    def test_admin_support_peut_repondre_a_nimporte_quel_ticket(self):
        resp = self.admin_client.post(
            f"/api/admin/support/tickets/{self.ticket_id}/messages",
            json={"body": "Réponse du support"}, headers=self.admin_headers,
        )
        self.assertEqual(resp.status_code, 201)

    def test_notes_internes_visibles_par_ladmin_uniquement(self):
        self.admin_client.post(
            f"/api/admin/support/tickets/{self.ticket_id}/notes",
            json={"body": "Note interne confidentielle"}, headers=self.admin_headers,
        )
        admin_detail = self.admin_client.get(
            f"/api/admin/support/tickets/{self.ticket_id}", headers=self.admin_headers,
        ).get_json()
        self.assertTrue(any("confidentielle" in n["body"] for n in admin_detail["notes"]))

        user_detail = self.client_a.get(f"/api/support/tickets/{self.ticket_id}", headers=self.headers_a).get_json()
        self.assertNotIn("notes", user_detail)


if __name__ == "__main__":
    unittest.main()
