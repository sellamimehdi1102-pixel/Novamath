"""
Suite SEC-04 : consent_service.py — calcul d'âge, seuil légal des 15 ans,
cycle de vie du consentement parental, consentement cookies, versions de
politique. Aucun appel réseau réel (email_service.send_email est sans effet
tant qu'EMAIL_SMTP_HOST n'est pas configuré, voir email_service.is_configured).
"""
import random
import unittest
from datetime import date
from unittest.mock import patch

import consent_service as cs
import db


def _mk_user(prefix="consent"):
    n = random.randint(1_000_000, 999_999_999)
    email = f"{prefix}{n}@gmail.com"
    username = f"{prefix}{n}"[:25]
    user_id = db.create_user(email, username, "Test", "hash")
    return db.get_user_by_id(user_id)


class TestComputeAge(unittest.TestCase):
    def test_age_le_jour_exact_de_l_anniversaire(self):
        today = date(2026, 6, 15)
        self.assertEqual(cs.compute_age("2010-06-15", on_date=today), 16)

    def test_age_la_veille_de_l_anniversaire(self):
        today = date(2026, 6, 14)
        self.assertEqual(cs.compute_age("2010-06-15", on_date=today), 15)

    def test_age_le_lendemain_de_l_anniversaire(self):
        today = date(2026, 6, 16)
        self.assertEqual(cs.compute_age("2010-06-15", on_date=today), 16)

    def test_annee_bissextile_29_fevrier(self):
        # Né un 29 février : anniversaire "célébré" le 1er mars les années non
        # bissextiles côté calendrier civil, mais la comparaison stricte
        # (mois, jour) traite le 28 février comme "avant" l'anniversaire.
        today = date(2027, 2, 28)
        self.assertEqual(cs.compute_age("2012-02-29", on_date=today), 14)

    def test_age_zero_le_jour_de_naissance(self):
        today = date(2026, 1, 1)
        self.assertEqual(cs.compute_age("2026-01-01", on_date=today), 0)


class TestRequiresParentalConsent(unittest.TestCase):
    def test_exactement_15_ans_ne_necessite_pas_de_consentement(self):
        today = date(2026, 6, 15)
        self.assertFalse(cs.requires_parental_consent("2011-06-15", on_date=today))

    def test_14_ans_necessite_un_consentement(self):
        today = date(2026, 6, 14)
        self.assertTrue(cs.requires_parental_consent("2011-06-15", on_date=today))

    def test_majeur_ne_necessite_pas_de_consentement(self):
        today = date(2026, 6, 15)
        self.assertFalse(cs.requires_parental_consent("2000-01-01", on_date=today))

    def test_veille_du_15e_anniversaire_necessite_encore_un_consentement(self):
        today = date(2026, 6, 14)
        self.assertTrue(cs.requires_parental_consent("2011-06-15", on_date=today))

    def test_lendemain_du_15e_anniversaire_ne_necessite_plus_de_consentement(self):
        today = date(2026, 6, 16)
        self.assertFalse(cs.requires_parental_consent("2011-06-15", on_date=today))


class TestCreateConsentRequest(unittest.TestCase):
    def test_cree_un_token_et_indique_si_le_smtp_est_configure(self):
        user = _mk_user()
        # Le second élément reflète email_service.is_configured() (pas le
        # résultat de l'envoi, voir create_consent_request) — forcé ici
        # indépendamment du .env réellement chargé dans le process de test
        # (peut contenir de vrais identifiants SMTP).
        with patch("email_service.is_configured", return_value=False):
            token, configured = cs.create_consent_request(user, "parent@example.com")
        self.assertTrue(token)
        self.assertFalse(configured)

    def test_le_compte_reste_en_base_avec_le_bon_statut_pending(self):
        n = random.randint(1_000_000, 999_999_999)
        user = db.get_user_by_id(
            db.create_user(f"pending{n}@gmail.com", f"pending{n}"[:25], "Test", "hash",
                            account_status="pending_parental_consent")
        )
        self.assertEqual(user["account_status"], "pending_parental_consent")

    def test_journalise_la_demande(self):
        user = _mk_user()
        before = db.count_security_events("parental_consent_requested")
        cs.create_consent_request(user, "parent2@example.com")
        after = db.count_security_events("parental_consent_requested")
        self.assertEqual(after, before + 1)

    def test_la_demande_est_bien_associee_au_bon_utilisateur(self):
        user = _mk_user()
        token, _ = cs.create_consent_request(user, "parent3@example.com")
        row = db.get_parental_consent_request(token)
        self.assertEqual(row["user_id"], user["id"])
        self.assertEqual(row["status"], "pending")


class TestGetPublicConsentInfo(unittest.TestCase):
    def test_token_inconnu_leve_invalid_consent_token(self):
        with self.assertRaises(cs.InvalidConsentToken):
            cs.get_public_consent_info("token-inexistant-xyz")

    def test_expose_le_pseudo_de_l_enfant_jamais_l_email_du_parent(self):
        user = _mk_user()
        token, _ = cs.create_consent_request(user, "parent-secret@example.com")
        info = cs.get_public_consent_info(token)
        self.assertEqual(info["child_pseudo"], user["pseudo"])
        self.assertNotIn("parent_email", info)

    def test_statut_pending_et_non_expire_par_defaut(self):
        user = _mk_user()
        token, _ = cs.create_consent_request(user, "parent4@example.com")
        info = cs.get_public_consent_info(token)
        self.assertEqual(info["status"], "pending")
        self.assertFalse(info["expired"])


class TestResolveConsent(unittest.TestCase):
    def test_acceptation_active_le_compte(self):
        user = _mk_user()
        token, _ = cs.create_consent_request(user, "parent5@example.com")
        resolved = cs.resolve_consent(token, "accepted")
        self.assertEqual(resolved["account_status"], "active")

    def test_refus_bloque_definitivement_le_compte(self):
        user = _mk_user()
        token, _ = cs.create_consent_request(user, "parent6@example.com")
        resolved = cs.resolve_consent(token, "refused")
        self.assertEqual(resolved["account_status"], "parental_consent_refused")

    def test_reutilisation_du_lien_apres_acceptation_leve_already_resolved(self):
        user = _mk_user()
        token, _ = cs.create_consent_request(user, "parent7@example.com")
        cs.resolve_consent(token, "accepted")
        with self.assertRaises(cs.ConsentAlreadyResolved):
            cs.resolve_consent(token, "accepted")

    def test_reutilisation_du_lien_apres_refus_leve_already_resolved(self):
        user = _mk_user()
        token, _ = cs.create_consent_request(user, "parent8@example.com")
        cs.resolve_consent(token, "refused")
        with self.assertRaises(cs.ConsentAlreadyResolved):
            cs.resolve_consent(token, "refused")

    def test_token_inconnu_leve_invalid_consent_token(self):
        with self.assertRaises(cs.InvalidConsentToken):
            cs.resolve_consent("token-jamais-cree", "accepted")

    def test_lien_expire_leve_consent_expired(self):
        user = _mk_user()
        token = db.create_parental_consent_request(user["id"], "parent9@example.com", days=-1)
        with self.assertRaises(cs.ConsentExpired):
            cs.resolve_consent(token, "accepted")

    def test_decision_invalide_leve_value_error(self):
        user = _mk_user()
        token, _ = cs.create_consent_request(user, "parent10@example.com")
        with self.assertRaises(ValueError):
            cs.resolve_consent(token, "autre-chose")

    def test_ecrit_une_preuve_immuable_dans_consent_records(self):
        user = _mk_user()
        token, _ = cs.create_consent_request(user, "parent11@example.com")
        cs.resolve_consent(token, "accepted", ip="1.2.3.4")
        records = db.list_consent_records(user["id"])
        matching = [r for r in records if r["consent_type"] == "parental_consent"]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0]["decision"], "accepted")
        self.assertEqual(matching[0]["ip"], "1.2.3.4")

    def test_journalise_acceptation_et_refus_differemment(self):
        user1 = _mk_user()
        token1, _ = cs.create_consent_request(user1, "parent12@example.com")
        before_accept = db.count_security_events("parental_consent_accepted")
        cs.resolve_consent(token1, "accepted")
        self.assertEqual(db.count_security_events("parental_consent_accepted"), before_accept + 1)

        user2 = _mk_user()
        token2, _ = cs.create_consent_request(user2, "parent13@example.com")
        before_refuse = db.count_security_events("parental_consent_refused")
        cs.resolve_consent(token2, "refused")
        self.assertEqual(db.count_security_events("parental_consent_refused"), before_refuse + 1)


class TestResendConsentEmail(unittest.TestCase):
    def test_sans_demande_existante_leve_no_pending_consent_request(self):
        user = _mk_user()
        with self.assertRaises(cs.NoPendingConsentRequest):
            cs.resend_consent_email(user)

    def test_invalide_l_ancien_token_et_en_cree_un_nouveau(self):
        user = _mk_user()
        old_token, _ = cs.create_consent_request(user, "parent14@example.com")
        new_token, _ = cs.resend_consent_email(user)
        self.assertNotEqual(old_token, new_token)
        old_row = db.get_parental_consent_request(old_token)
        self.assertEqual(old_row["status"], "superseded")

    def test_le_nouveau_token_reste_utilisable(self):
        user = _mk_user()
        cs.create_consent_request(user, "parent15@example.com")
        new_token, _ = cs.resend_consent_email(user)
        resolved = cs.resolve_consent(new_token, "accepted")
        self.assertEqual(resolved["account_status"], "active")

    def test_ancien_token_devenu_inutilisable_apres_renvoi(self):
        user = _mk_user()
        old_token, _ = cs.create_consent_request(user, "parent16@example.com")
        cs.resend_consent_email(user)
        with self.assertRaises(cs.ConsentAlreadyResolved):
            cs.resolve_consent(old_token, "accepted")

    def test_conserve_le_meme_email_parent(self):
        user = _mk_user()
        cs.create_consent_request(user, "parent-fixe@example.com")
        new_token, _ = cs.resend_consent_email(user)
        row = db.get_parental_consent_request(new_token)
        self.assertEqual(row["parent_email"], "parent-fixe@example.com")


class TestCookieConsent(unittest.TestCase):
    def test_defaut_sans_choix_enregistre(self):
        user = _mk_user()
        result = cs.get_cookie_consent(user["id"])
        self.assertFalse(result["statistics"])
        self.assertFalse(result["marketing"])

    def test_enregistre_et_relit(self):
        user = _mk_user()
        cs.set_cookie_consent(user["id"], True, False)
        result = cs.get_cookie_consent(user["id"])
        self.assertTrue(result["statistics"])
        self.assertFalse(result["marketing"])

    def test_ecrase_le_choix_precedent(self):
        user = _mk_user()
        cs.set_cookie_consent(user["id"], True, True)
        cs.set_cookie_consent(user["id"], False, False)
        result = cs.get_cookie_consent(user["id"])
        self.assertFalse(result["statistics"])
        self.assertFalse(result["marketing"])

    def test_journalise_deux_preuves_de_consentement(self):
        user = _mk_user()
        before = len(db.list_consent_records(user["id"]))
        cs.set_cookie_consent(user["id"], True, False)
        after = len(db.list_consent_records(user["id"]))
        self.assertEqual(after, before + 2)

    def test_journalise_l_evenement_de_securite(self):
        user = _mk_user()
        before = db.count_security_events("cookie_consent_updated")
        cs.set_cookie_consent(user["id"], True, True)
        self.assertEqual(db.count_security_events("cookie_consent_updated"), before + 1)


class TestPolicyVersions(unittest.TestCase):
    def test_nouveau_compte_sans_acceptation_necessite_reacceptation(self):
        user = _mk_user()
        self.assertTrue(cs.needs_policy_reacceptance(user))

    def test_apres_acceptation_initiale_plus_besoin_de_reacceptation(self):
        user = _mk_user()
        cs.record_initial_policy_acceptance(user["id"])
        user = db.get_user_by_id(user["id"])
        self.assertFalse(cs.needs_policy_reacceptance(user))

    def test_version_obsolete_necessite_de_nouveau_une_reacceptation(self):
        user = _mk_user()
        db.set_policy_acceptance(user["id"], terms_version="0.1", privacy_version="0.1")
        user = db.get_user_by_id(user["id"])
        self.assertTrue(cs.needs_policy_reacceptance(user))

    def test_record_policy_reacceptance_journalise(self):
        user = _mk_user()
        before = db.count_security_events("policy_accepted")
        cs.record_policy_reacceptance(user["id"])
        self.assertEqual(db.count_security_events("policy_accepted"), before + 1)

    def test_record_initial_policy_acceptance_ecrit_deux_preuves(self):
        user = _mk_user()
        before = len(db.list_consent_records(user["id"]))
        cs.record_initial_policy_acceptance(user["id"])
        after = len(db.list_consent_records(user["id"]))
        self.assertEqual(after, before + 2)


if __name__ == "__main__":
    unittest.main()
