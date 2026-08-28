"""
Suite d'intégration du branchement quota_service.py sur les vraies routes du
chatbot (webapp/server.py + chatbot/conversation_manager.py) : le quota de
messages IA (QuotaType.CHAT_MESSAGES) devient enfin effectif.

Complète (sans le dupliquer) tests/test_quota_service.py, qui couvre déjà
exhaustivement consume()/can_consume()/concurrence au niveau du service pur —
ici on vérifie le CÂBLAGE : le format HTTP 429 exact, la route GET /api/quota,
qu'aucune route hors chat ne consomme, qu'un message réel en consomme
exactement un (jamais deux, jamais zéro), et la réinitialisation quotidienne.

Même convention que tests/test_server_feature_gating.py : pas d'isolation de
base (server.app.test_client() contre la vraie data/novamath.db, utilisateurs
de test à email/username aléatoires) — cohérent avec les autres suites qui
pilotent server.py de bout en bout.
"""
import random
import unittest
from datetime import datetime, timezone

import db
import server
from plan_service import Plan
from quota_service import QuotaType


def _today():
    return datetime.now(timezone.utc).date().isoformat()


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


def _set_plan(user_id, plan):
    db.set_stripe_subscription(user_id, "sub_test", plan.value, "active")


def _seed_usage(user_id, amount, day=None, quota=QuotaType.CHAT_MESSAGES):
    """Consomme `amount` unités directement en base (même table que
    quota_service.consume) — contourne le pipeline IA pour amener rapidement
    le compteur près de la limite, inutile de le rejouer réellement."""
    db.increment_daily_usage(user_id, quota.value, day or _today(), amount)


def _create_conversation(client, headers):
    resp = client.post("/api/chatbot/conversations", headers=headers)
    return resp.get_json()["conversation"]["id"]


def _send_message(client, headers, conv_id, text="Bonjour"):
    return client.post(
        f"/api/chatbot/conversations/{conv_id}/messages",
        json={"message": text}, headers=headers,
    )


def _used(client):
    return client.get("/api/quota").get_json()["chat_messages"]["used"]


class ChatbotQuotaTestCase(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()
        self.user, self.headers = _register(self.client)
        self.conv_id = _create_conversation(self.client, self.headers)


class TestEnvoiDeMessageConsommeLeQuota(ChatbotQuotaTestCase):
    def test_un_message_reel_consomme_exactement_une_unite(self):
        """Jamais deux, jamais zéro : un seul POST /messages doit incrémenter
        le compteur d'exactement 1, pas plus, pas moins."""
        resp = _send_message(self.client, self.headers, self.conv_id)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(_used(self.client), 1)

    def test_deux_messages_consomment_exactement_deux_unites(self):
        _send_message(self.client, self.headers, self.conv_id, "Premier message")
        _send_message(self.client, self.headers, self.conv_id, "Deuxième message")
        self.assertEqual(_used(self.client), 2)

    def test_message_vide_ne_consomme_rien(self):
        resp = self.client.post(
            f"/api/chatbot/conversations/{self.conv_id}/messages",
            json={"message": "   "}, headers=self.headers,
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(_used(self.client), 0)

    def test_classe_inconnue_ne_consomme_rien(self):
        resp = self.client.post(
            f"/api/chatbot/conversations/{self.conv_id}/messages",
            json={"message": "Bonjour", "class_level": "inexistante"}, headers=self.headers,
        )
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(_used(self.client), 0)


class TestDepassementDeQuota429(ChatbotQuotaTestCase):
    def test_free_bloque_au_16e_message_avec_le_format_exact(self):
        _seed_usage(self.user["id"], 15)  # amène directement à la limite Free
        resp = _send_message(self.client, self.headers, self.conv_id)
        self.assertEqual(resp.status_code, 429)
        # required_plan="premium" (chantier "Réduction quota Free",
        # 2026-08-25) : Free (15) est désormais strictement inférieur à
        # Premium (25), donc quota_service._next_plan_with_more() recommande
        # à nouveau Premium en premier palier offrant réellement plus sur ce
        # quota précis (ce n'était plus le cas quand Free==Premium==25).
        self.assertEqual(resp.get_json(), {
            "error": "quota_exceeded",
            "quota": "chat_messages",
            "remaining": 0,
            "limit": 15,
            "required_plan": "premium",
        })

    def test_15e_message_reussit_le_16e_echoue(self):
        _seed_usage(self.user["id"], 14)
        ok = _send_message(self.client, self.headers, self.conv_id, "Le 15e")
        self.assertEqual(ok.status_code, 200)
        blocked = _send_message(self.client, self.headers, self.conv_id, "Le 16e")
        self.assertEqual(blocked.status_code, 429)

    def test_premium_bloque_a_25_avec_required_plan_ultra(self):
        _set_plan(self.user["id"], Plan.PREMIUM)
        _seed_usage(self.user["id"], 25)
        resp = _send_message(self.client, self.headers, self.conv_id)
        self.assertEqual(resp.status_code, 429)
        body = resp.get_json()
        self.assertEqual(body["limit"], 25)
        self.assertEqual(body["required_plan"], "ultra")

    def test_ultra_bloque_a_40(self):
        # Ultra n'est plus illimité sur CHAT_MESSAGES depuis le Chantier 6.
        _set_plan(self.user["id"], Plan.ULTRA)
        _seed_usage(self.user["id"], 40)
        resp = _send_message(self.client, self.headers, self.conv_id)
        self.assertEqual(resp.status_code, 429)
        body = resp.get_json()
        self.assertEqual(body["limit"], 40)

    def test_apres_429_le_compteur_ne_depasse_pas_la_limite(self):
        _seed_usage(self.user["id"], 15)
        _send_message(self.client, self.headers, self.conv_id)  # refusé, 429
        self.assertEqual(_used(self.client), 15)


class TestRegenerateEtRetry(ChatbotQuotaTestCase):
    def test_regenerate_consomme_un_message_supplementaire(self):
        _send_message(self.client, self.headers, self.conv_id)  # usage = 1
        resp = self.client.post(
            f"/api/chatbot/conversations/{self.conv_id}/regenerate",
            json={}, headers=self.headers,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(_used(self.client), 2)

    def test_regenerate_bloque_si_quota_epuise(self):
        _send_message(self.client, self.headers, self.conv_id)
        _seed_usage(self.user["id"], 14)  # usage total = 15, à la limite Free
        resp = self.client.post(
            f"/api/chatbot/conversations/{self.conv_id}/regenerate",
            json={}, headers=self.headers,
        )
        self.assertEqual(resp.status_code, 429)
        self.assertEqual(resp.get_json()["error"], "quota_exceeded")

    def test_retry_ne_consomme_rien(self):
        """retry_last rejoue la génération d'un message utilisateur déjà
        persisté SANS le dupliquer (voir conversation_manager.retry_last) —
        ne doit jamais coûter de message, même à quota déjà entamé."""
        db.add_message(self.conv_id, "user", "Message déjà persisté", mentions=None)
        resp = self.client.post(
            f"/api/chatbot/conversations/{self.conv_id}/retry",
            json={}, headers=self.headers,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(_used(self.client), 0)

    def test_retry_fonctionne_meme_quota_epuise(self):
        db.add_message(self.conv_id, "user", "Message déjà persisté", mentions=None)
        _seed_usage(self.user["id"], 15)
        resp = self.client.post(
            f"/api/chatbot/conversations/{self.conv_id}/retry",
            json={}, headers=self.headers,
        )
        self.assertEqual(resp.status_code, 200)


class TestApiQuotaRoute(ChatbotQuotaTestCase):
    def test_forme_generale_de_la_reponse(self):
        body = self.client.get("/api/quota").get_json()
        self.assertEqual(set(body.keys()), {q.value for q in QuotaType})
        for quota_payload in body.values():
            self.assertEqual(set(quota_payload.keys()), {"used", "remaining", "limit", "unlimited"})

    def test_free_chat_messages(self):
        body = self.client.get("/api/quota").get_json()
        self.assertEqual(body["chat_messages"], {
            "used": 0, "remaining": 15, "limit": 15, "unlimited": False,
        })

    def test_reflete_lusage_apres_consommation(self):
        _send_message(self.client, self.headers, self.conv_id)
        body = self.client.get("/api/quota").get_json()
        self.assertEqual(body["chat_messages"], {
            "used": 1, "remaining": 14, "limit": 15, "unlimited": False,
        })

    def test_premium_chat_messages(self):
        _set_plan(self.user["id"], Plan.PREMIUM)
        body = self.client.get("/api/quota").get_json()
        self.assertEqual(body["chat_messages"], {
            "used": 0, "remaining": 25, "limit": 25, "unlimited": False,
        })

    def test_ultra_chat_messages(self):
        # Ultra n'est plus illimité sur CHAT_MESSAGES depuis le Chantier 6
        # (limite commerciale de volume, 40/j).
        _set_plan(self.user["id"], Plan.ULTRA)
        body = self.client.get("/api/quota").get_json()
        self.assertEqual(body["chat_messages"], {
            "used": 0, "remaining": 40, "limit": 40, "unlimited": False,
        })

    def test_ultra_chat_messages_remaining_ne_descend_jamais_sous_zero(self):
        _set_plan(self.user["id"], Plan.ULTRA)
        _seed_usage(self.user["id"], 1_000)
        body = self.client.get("/api/quota").get_json()
        self.assertEqual(body["chat_messages"]["unlimited"], False)
        self.assertEqual(body["chat_messages"]["limit"], 40)
        self.assertEqual(body["chat_messages"]["remaining"], 0)
        self.assertEqual(body["chat_messages"]["used"], 1_000)

    def test_utilisateur_non_connecte_est_rejete(self):
        anon_client = server.app.test_client()
        resp = anon_client.get("/api/quota")
        self.assertEqual(resp.status_code, 401)

    def test_autres_quota_types_a_zero_par_defaut(self):
        body = self.client.get("/api/quota").get_json()
        for quota in (QuotaType.PDF_ANALYSIS, QuotaType.AI_GENERATIONS,
                      QuotaType.CUSTOM_EXERCISES, QuotaType.EXPORTS):
            with self.subTest(quota=quota):
                self.assertEqual(body[quota.value]["used"], 0)


class TestAucuneConsommationHorsEnvoi(ChatbotQuotaTestCase):
    """Toutes les routes qui ne représentent PAS un vrai message envoyé au
    moteur IA doivent laisser le quota totalement intact."""

    def test_lecture_de_lhistorique(self):
        _send_message(self.client, self.headers, self.conv_id)  # usage = 1
        before = _used(self.client)
        self.client.get(f"/api/chatbot/conversations/{self.conv_id}/messages", headers=self.headers)
        self.assertEqual(_used(self.client), before)

    def test_liste_des_conversations(self):
        self.client.get("/api/chatbot/conversations", headers=self.headers)
        self.assertEqual(_used(self.client), 0)

    def test_creation_de_conversation(self):
        # setUp en a déjà créé une — vérifie qu'aucune n'a rien consommé.
        self.assertEqual(_used(self.client), 0)

    def test_suppression_de_conversation(self):
        conv2 = _create_conversation(self.client, self.headers)
        self.client.delete(f"/api/chatbot/conversations/{conv2}", headers=self.headers)
        self.assertEqual(_used(self.client), 0)

    def test_renommage_de_conversation(self):
        self.client.patch(
            f"/api/chatbot/conversations/{self.conv_id}", json={"title": "Nouveau titre"}, headers=self.headers,
        )
        self.assertEqual(_used(self.client), 0)

    def test_health(self):
        self.client.get("/api/chatbot/health")
        self.assertEqual(_used(self.client), 0)

    def test_greeting(self):
        self.client.get("/api/chatbot/greeting")
        self.assertEqual(_used(self.client), 0)

    def test_models(self):
        self.client.get("/api/chatbot/models")
        self.assertEqual(_used(self.client), 0)

    def test_context_preview(self):
        self.client.get("/api/chatbot/context-preview")
        self.assertEqual(_used(self.client), 0)

    def test_mentions(self):
        self.client.get("/api/chatbot/mentions?q=test")
        self.assertEqual(_used(self.client), 0)

    def test_quota_legacy_route(self):
        self.client.get("/api/chatbot/quota")
        self.assertEqual(_used(self.client), 0)

    def test_nouvelle_route_quota(self):
        self.client.get("/api/quota")
        self.assertEqual(_used(self.client), 0)

    def test_upload_pdf_refuse_sans_fichier(self):
        # Feature.ADVANCED_AI (Ultra) — ici on vérifie seulement que le refus
        # (400, aucun fichier) ne touche jamais au quota de messages.
        _set_plan(self.user["id"], Plan.ULTRA)
        resp = self.client.post(
            "/api/chatbot/attachments/pdf", data={}, content_type="multipart/form-data", headers=self.headers,
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(_used(self.client), 0)

    def test_feedback_sur_message(self):
        _send_message(self.client, self.headers, self.conv_id)
        messages = self.client.get(
            f"/api/chatbot/conversations/{self.conv_id}/messages", headers=self.headers,
        ).get_json()["messages"]
        assistant_msg = next(m for m in messages if m["role"] == "assistant")
        before = _used(self.client)
        self.client.post(
            f"/api/chatbot/messages/{assistant_msg['id']}/feedback", json={"liked": True}, headers=self.headers,
        )
        self.assertEqual(_used(self.client), before)


class TestFormatLegacyChatbotQuota(ChatbotQuotaTestCase):
    """/api/chatbot/quota (ancien format) reste fonctionnel, désormais adossé
    à quota_service — plus aucune écriture dans l'ancienne table
    `chatbot_quota` (vérifié indirectement : l'usage suit bien le nouveau
    compteur)."""

    def test_forme_historique_used_limit(self):
        body = self.client.get("/api/chatbot/quota").get_json()
        self.assertEqual(set(body.keys()), {"used", "limit"})
        self.assertEqual(body, {"used": 0, "limit": 15})

    def test_suit_la_consommation_reelle(self):
        _send_message(self.client, self.headers, self.conv_id)
        body = self.client.get("/api/chatbot/quota").get_json()
        self.assertEqual(body["used"], 1)

    def test_limit_ultra(self):
        # Ultra n'est plus illimité sur CHAT_MESSAGES depuis le Chantier 6.
        _set_plan(self.user["id"], Plan.ULTRA)
        body = self.client.get("/api/chatbot/quota").get_json()
        self.assertEqual(body["limit"], 40)


class TestReinitialisationQuotidienne(ChatbotQuotaTestCase):
    def test_usage_dun_autre_jour_najoute_rien_aujourdhui(self):
        _seed_usage(self.user["id"], 15, day="2020-01-01")
        # Le quota du jour reste à 0 : aucune tâche de reset à appeler, la
        # réinitialisation est portée par la date elle-même (voir quota_service.py).
        self.assertEqual(_used(self.client), 0)
        resp = _send_message(self.client, self.headers, self.conv_id)
        self.assertEqual(resp.status_code, 200)

    def test_nouveau_jour_debloque_un_utilisateur_bloque_la_veille(self):
        _seed_usage(self.user["id"], 15, day="2020-01-01")
        db.increment_daily_usage(self.user["id"], QuotaType.CHAT_MESSAGES.value, "2020-01-01", 0)
        # L'utilisateur était à la limite hier ; aujourd'hui, une ligne
        # différente (date différente) démarre à 0 — vérifié via une vraie
        # requête HTTP, jamais bloquée par l'historique d'un autre jour.
        resp = _send_message(self.client, self.headers, self.conv_id)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(_used(self.client), 1)


class TestConversationManagerDelegation(unittest.TestCase):
    """Vérifie que chatbot/conversation_manager.py ne gère plus aucun
    compteur en propre (colonne `chatbot_quota` gelée) et délègue
    intégralement à quota_service, sur un utilisateur isolé (pas de
    dépendance à server.py ici)."""

    def setUp(self):
        self.client = server.app.test_client()
        self.user, _ = _register(self.client)

    def test_check_and_increment_quota_delegue_a_quota_service(self):
        from chatbot import conversation_manager
        total = conversation_manager.check_and_increment_quota(self.user)
        self.assertEqual(total, 1)
        self.assertEqual(_used(self.client), 1)

    def test_quota_status_format_historique(self):
        from chatbot import conversation_manager
        conversation_manager.check_and_increment_quota(self.user)
        status = conversation_manager.quota_status(self.user)
        self.assertEqual(status, {"used": 1, "limit": 15})

    def test_ancienne_table_chatbot_quota_nest_plus_alimentee(self):
        from chatbot import conversation_manager
        conversation_manager.check_and_increment_quota(self.user)
        self.assertEqual(db.get_chatbot_quota(self.user["id"], _today()), 0)


if __name__ == "__main__":
    unittest.main()
