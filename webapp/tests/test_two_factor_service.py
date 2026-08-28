"""
Suite unitaire de two_factor_service.py — SEC-03 : génération du secret,
chiffrement/déchiffrement, URI otpauth/QR code, activation/désactivation,
vérification TOTP (fenêtre de tolérance, expiration, anti-rejeu), recovery
codes (génération/hachage/consommation/suppression), défis de connexion,
verrouillage temporaire après échecs répétés.

Base SQLite isolée dans un répertoire temporaire (db.DATA_DIR/db.DB_PATH
monkeypatchés) et clé de chiffrement de test dédiée (config.TWO_FACTOR_
SECRET_KEY monkeypatchée) — même pattern que tests/test_quota_service.py /
tests/test_backup_service.py : aucune interférence avec data/novamath.db ni
une éventuelle clé réelle.
"""
import base64
import io
import shutil
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pyotp
from cryptography.fernet import Fernet
from PIL import Image

import config
import db
import two_factor_service as tfs


class TwoFactorServiceTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = tempfile.mkdtemp()
        self._data_dir_backup = db.DATA_DIR
        self._db_path_backup = db.DB_PATH
        self._key_backup = config.TWO_FACTOR_SECRET_KEY

        db.DATA_DIR = Path(self._tmp_dir)
        db.DB_PATH = db.DATA_DIR / "novamath.db"
        db.init_db()
        config.TWO_FACTOR_SECRET_KEY = Fernet.generate_key().decode()

    def tearDown(self):
        db.DATA_DIR = self._data_dir_backup
        db.DB_PATH = self._db_path_backup
        config.TWO_FACTOR_SECRET_KEY = self._key_backup
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def _make_user(self, email="user2fa@gmail.com", username="user2fa"):
        user_id = db.create_user(email, username, "Test", "hash")
        return db.get_user_by_id(user_id)


class TestEncryption(TwoFactorServiceTestCase):
    def test_round_trip(self):
        secret = pyotp.random_base32()
        encrypted = tfs._encrypt_secret(secret)
        self.assertNotEqual(encrypted, secret)
        self.assertEqual(tfs._decrypt_secret(encrypted), secret)

    def test_secret_jamais_stocke_en_clair_en_base(self):
        user = self._make_user()
        result = tfs.begin_setup(user)
        stored = db.get_user_by_id(user["id"])["two_factor_secret"]
        self.assertNotIn(result["secret"], stored)
        self.assertNotEqual(stored, result["secret"])

    def test_leve_not_configured_si_cle_absente(self):
        config.TWO_FACTOR_SECRET_KEY = None
        with self.assertRaises(tfs.TwoFactorNotConfigured):
            tfs._encrypt_secret("ABCDEFGH")

    def test_leve_not_configured_si_cle_invalide(self):
        config.TWO_FACTOR_SECRET_KEY = "clé-invalide-pas-du-tout-fernet"
        with self.assertRaises(tfs.TwoFactorNotConfigured):
            tfs._encrypt_secret("ABCDEFGH")

    def test_leve_not_configured_si_dechiffrement_avec_mauvaise_cle(self):
        secret = pyotp.random_base32()
        encrypted = tfs._encrypt_secret(secret)
        config.TWO_FACTOR_SECRET_KEY = Fernet.generate_key().decode()  # autre clé
        with self.assertRaises(tfs.TwoFactorNotConfigured):
            tfs._decrypt_secret(encrypted)

    def test_deux_secrets_donnent_des_chiffres_differents(self):
        s1, s2 = tfs._encrypt_secret("AAAAAAAA"), tfs._encrypt_secret("AAAAAAAA")
        # Fernet inclut un nonce/timestamp : même texte clair, sortie différente.
        self.assertNotEqual(s1, s2)


class TestGenerationSecretEtUri(TwoFactorServiceTestCase):
    def test_secret_est_du_base32_valide(self):
        user = self._make_user()
        result = tfs.begin_setup(user)
        # pyotp.random_base32() ne produit que des caractères base32 standard.
        self.assertTrue(all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567" for c in result["secret"]))

    def test_deux_appels_generent_des_secrets_differents(self):
        user = self._make_user()
        first = tfs.begin_setup(user)
        second = tfs.begin_setup(db.get_user_by_id(user["id"]))
        self.assertNotEqual(first["secret"], second["secret"])

    def test_otpauth_uri_contient_issuer_et_email(self):
        user = self._make_user(email="alice@gmail.com")
        result = tfs.begin_setup(user)
        self.assertTrue(result["otpauth_uri"].startswith("otpauth://totp/"))
        self.assertIn("issuer=NovaMath", result["otpauth_uri"])
        self.assertIn("alice%40gmail.com", result["otpauth_uri"])

    def test_otpauth_uri_respecte_two_factor_issuer_configure(self):
        original_issuer = config.TWO_FACTOR_ISSUER
        config.TWO_FACTOR_ISSUER = "MonAppTest"
        try:
            user = self._make_user()
            result = tfs.begin_setup(user)
            self.assertIn("issuer=MonAppTest", result["otpauth_uri"])
        finally:
            config.TWO_FACTOR_ISSUER = original_issuer

    def test_setup_ne_active_pas_la_2fa(self):
        user = self._make_user()
        tfs.begin_setup(user)
        self.assertFalse(db.get_user_by_id(user["id"])["two_factor_enabled"])

    def test_setup_leve_already_enabled_si_deja_actif(self):
        user = self._make_user()
        setup = tfs.begin_setup(user)
        user = db.get_user_by_id(user["id"])
        tfs.confirm_setup(user, pyotp.TOTP(setup["secret"]).now())
        with self.assertRaises(tfs.TwoFactorAlreadyEnabled):
            tfs.begin_setup(db.get_user_by_id(user["id"]))


class TestQrCode(TwoFactorServiceTestCase):
    def test_qr_code_est_un_data_uri_png(self):
        uri = tfs.provisioning_uri(pyotp.random_base32(), "test@gmail.com")
        qr = tfs.generate_qr_code_data_uri(uri)
        self.assertTrue(qr.startswith("data:image/png;base64,"))

    def test_qr_code_est_une_image_png_valide(self):
        uri = tfs.provisioning_uri(pyotp.random_base32(), "test@gmail.com")
        qr = tfs.generate_qr_code_data_uri(uri)
        raw = base64.b64decode(qr.split(",", 1)[1])
        img = Image.open(io.BytesIO(raw))
        self.assertEqual(img.format, "PNG")

    def test_qr_codes_differents_pour_deux_secrets_differents(self):
        uri1 = tfs.provisioning_uri(pyotp.random_base32(), "a@gmail.com")
        uri2 = tfs.provisioning_uri(pyotp.random_base32(), "b@gmail.com")
        self.assertNotEqual(
            tfs.generate_qr_code_data_uri(uri1), tfs.generate_qr_code_data_uri(uri2),
        )


class TestVerificationTotp(TwoFactorServiceTestCase):
    def test_code_valide_est_accepte(self):
        secret = pyotp.random_base32()
        code = pyotp.TOTP(secret).now()
        ok, counter = tfs._verify_totp_code(secret, code, last_counter=None)
        self.assertTrue(ok)
        self.assertIsInstance(counter, int)

    def test_code_incorrect_est_refuse(self):
        secret = pyotp.random_base32()
        real_code = pyotp.TOTP(secret).now()
        wrong = "000000" if real_code != "000000" else "111111"
        ok, _ = tfs._verify_totp_code(secret, wrong, last_counter=None)
        self.assertFalse(ok)

    def test_format_invalide_est_refuse_sans_lever(self):
        secret = pyotp.random_base32()
        for bad in ("", "12345", "1234567", "abcdef", None, "12 345"):
            with self.subTest(bad=bad):
                ok, _ = tfs._verify_totp_code(secret, bad, last_counter=None)
                self.assertFalse(ok)

    def test_tolerance_fenetre_precedente_et_suivante(self):
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        now_counter = tfs._totp_counter_now()
        prev_code = totp.at((now_counter - 1) * tfs.TOTP_STEP_SECONDS)
        next_code = totp.at((now_counter + 1) * tfs.TOTP_STEP_SECONDS)
        self.assertTrue(tfs._verify_totp_code(secret, prev_code, None)[0])
        self.assertTrue(tfs._verify_totp_code(secret, next_code, None)[0])

    def test_code_trop_ancien_expire_est_refuse(self):
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        now_counter = tfs._totp_counter_now()
        old_code = totp.at((now_counter - 5) * tfs.TOTP_STEP_SECONDS)
        ok, _ = tfs._verify_totp_code(secret, old_code, None)
        self.assertFalse(ok)

    def test_rejeu_du_meme_code_est_refuse(self):
        secret = pyotp.random_base32()
        code = pyotp.TOTP(secret).now()
        ok1, counter = tfs._verify_totp_code(secret, code, last_counter=None)
        self.assertTrue(ok1)
        ok2, _ = tfs._verify_totp_code(secret, code, last_counter=counter)
        self.assertFalse(ok2)

    def test_code_dune_fenetre_anterieure_au_dernier_compteur_est_refuse(self):
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        now_counter = tfs._totp_counter_now()
        older_code = totp.at((now_counter - 1) * tfs.TOTP_STEP_SECONDS)
        # last_counter déjà au pas courant : un code plus ancien reste refusé.
        ok, _ = tfs._verify_totp_code(secret, older_code, last_counter=now_counter)
        self.assertFalse(ok)

    def test_nouveau_code_apres_le_dernier_compteur_est_accepte(self):
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        now_counter = tfs._totp_counter_now()
        future_code = totp.at((now_counter + 1) * tfs.TOTP_STEP_SECONDS)
        ok, new_counter = tfs._verify_totp_code(secret, future_code, last_counter=now_counter - 1)
        self.assertTrue(ok)
        self.assertEqual(new_counter, now_counter + 1)


class TestConfirmSetup(TwoFactorServiceTestCase):
    def _begin(self, user):
        setup = tfs.begin_setup(user)
        return setup["secret"], db.get_user_by_id(user["id"])

    def test_active_avec_un_code_valide(self):
        user = self._make_user()
        secret, user = self._begin(user)
        codes = tfs.confirm_setup(user, pyotp.TOTP(secret).now())
        self.assertEqual(len(codes), tfs.RECOVERY_CODE_COUNT)
        self.assertTrue(db.get_user_by_id(user["id"])["two_factor_enabled"])

    def test_enregistre_two_factor_enabled_at(self):
        user = self._make_user()
        secret, user = self._begin(user)
        tfs.confirm_setup(user, pyotp.TOTP(secret).now())
        self.assertIsNotNone(db.get_user_by_id(user["id"])["two_factor_enabled_at"])

    def test_code_invalide_najamais_active(self):
        user = self._make_user()
        secret, user = self._begin(user)
        with self.assertRaises(tfs.InvalidTotpCode):
            tfs.confirm_setup(user, "000000" if pyotp.TOTP(secret).now() != "000000" else "111111")
        self.assertFalse(db.get_user_by_id(user["id"])["two_factor_enabled"])

    def test_sans_setup_prealable_leve_no_pending_setup(self):
        user = self._make_user()
        with self.assertRaises(tfs.NoPendingSetup):
            tfs.confirm_setup(user, "123456")

    def test_genere_exactement_dix_recovery_codes_uniques(self):
        user = self._make_user()
        secret, user = self._begin(user)
        codes = tfs.confirm_setup(user, pyotp.TOTP(secret).now())
        self.assertEqual(len(set(codes)), 10)

    def test_recovery_codes_stockes_haches_jamais_en_clair(self):
        user = self._make_user()
        secret, user = self._begin(user)
        codes = tfs.confirm_setup(user, pyotp.TOTP(secret).now())
        stored_hashes = {c["code_hash"] for c in db.get_recovery_codes(user["id"])}
        self.assertEqual(stored_hashes, {tfs._hash_recovery_code(c) for c in codes})
        for code in codes:
            self.assertNotIn(code, stored_hashes)


class TestDisable(TwoFactorServiceTestCase):
    def _enabled_user(self):
        user = self._make_user()
        setup = tfs.begin_setup(user)
        user = db.get_user_by_id(user["id"])
        tfs.confirm_setup(user, pyotp.TOTP(setup["secret"]).now())
        return db.get_user_by_id(user["id"]), setup["secret"]

    def test_desactive_avec_un_code_valide(self):
        user, secret = self._enabled_user()
        totp = pyotp.TOTP(secret)
        now_counter = tfs._totp_counter_now()
        code = totp.at((now_counter + 1) * tfs.TOTP_STEP_SECONDS)
        tfs.disable(user, code)
        self.assertFalse(db.get_user_by_id(user["id"])["two_factor_enabled"])

    def test_desactivation_efface_le_secret(self):
        user, secret = self._enabled_user()
        totp = pyotp.TOTP(secret)
        now_counter = tfs._totp_counter_now()
        code = totp.at((now_counter + 1) * tfs.TOTP_STEP_SECONDS)
        tfs.disable(user, code)
        self.assertIsNone(db.get_user_by_id(user["id"])["two_factor_secret"])

    def test_desactivation_supprime_les_recovery_codes(self):
        user, secret = self._enabled_user()
        self.assertGreater(db.count_recovery_codes(user["id"]), 0)
        totp = pyotp.TOTP(secret)
        now_counter = tfs._totp_counter_now()
        code = totp.at((now_counter + 1) * tfs.TOTP_STEP_SECONDS)
        tfs.disable(user, code)
        self.assertEqual(db.count_recovery_codes(user["id"]), 0)

    def test_code_invalide_ne_desactive_pas(self):
        user, secret = self._enabled_user()
        with self.assertRaises(tfs.InvalidTotpCode):
            tfs.disable(user, "000000" if pyotp.TOTP(secret).now() != "000000" else "111111")
        self.assertTrue(db.get_user_by_id(user["id"])["two_factor_enabled"])

    def test_sur_compte_sans_2fa_leve_not_enabled(self):
        user = self._make_user()
        with self.assertRaises(tfs.TwoFactorNotEnabled):
            tfs.disable(user, "123456")


class TestRecoveryCodesRemaining(TwoFactorServiceTestCase):
    def test_dix_apres_activation(self):
        user = self._make_user()
        setup = tfs.begin_setup(user)
        user = db.get_user_by_id(user["id"])
        tfs.confirm_setup(user, pyotp.TOTP(setup["secret"]).now())
        self.assertEqual(tfs.recovery_codes_remaining(db.get_user_by_id(user["id"])), 10)

    def test_zero_avant_activation(self):
        user = self._make_user()
        self.assertEqual(tfs.recovery_codes_remaining(user), 0)


class LoginChallengeTestCase(TwoFactorServiceTestCase):
    def _enabled_user(self):
        user = self._make_user()
        setup = tfs.begin_setup(user)
        user = db.get_user_by_id(user["id"])
        codes = tfs.confirm_setup(user, pyotp.TOTP(setup["secret"]).now())
        return db.get_user_by_id(user["id"]), setup["secret"], codes


class TestCreateAndLoadChallenge(LoginChallengeTestCase):
    def test_token_est_resoluble(self):
        user, _, _ = self._enabled_user()
        token = tfs.create_login_challenge(user, remember=True)
        challenge = tfs._load_challenge(token)
        self.assertEqual(challenge["user_id"], user["id"])
        self.assertEqual(challenge["remember"], 1)

    def test_remember_false_est_persiste(self):
        user, _, _ = self._enabled_user()
        token = tfs.create_login_challenge(user, remember=False)
        self.assertEqual(tfs._load_challenge(token)["remember"], 0)

    def test_token_inconnu_leve_invalid_challenge(self):
        with self.assertRaises(tfs.InvalidChallenge):
            tfs._load_challenge("jeton-inexistant")

    def test_token_expire_leve_invalid_challenge(self):
        user, _, _ = self._enabled_user()
        token = db.create_two_factor_challenge(user["id"], remember=False, minutes=-1)
        with self.assertRaises(tfs.InvalidChallenge):
            tfs._load_challenge(token)


class TestVerifyLoginChallenge(LoginChallengeTestCase):
    def _future_code(self, secret, offset=1):
        totp = pyotp.TOTP(secret)
        now_counter = tfs._totp_counter_now()
        return totp.at((now_counter + offset) * tfs.TOTP_STEP_SECONDS)

    def test_code_valide_resout_le_defi_et_le_consomme(self):
        user, secret, _ = self._enabled_user()
        token = tfs.create_login_challenge(user, remember=True)
        resolved_user, remember = tfs.verify_login_challenge(token, self._future_code(secret))
        self.assertEqual(resolved_user["id"], user["id"])
        self.assertTrue(remember)
        with self.assertRaises(tfs.InvalidChallenge):
            tfs._load_challenge(token)

    def test_code_invalide_ne_consomme_pas_le_defi(self):
        user, secret, _ = self._enabled_user()
        token = tfs.create_login_challenge(user, remember=False)
        with self.assertRaises(tfs.InvalidTotpCode):
            tfs.verify_login_challenge(token, "000000" if pyotp.TOTP(secret).now() != "000000" else "111111")
        self.assertIsNotNone(tfs._load_challenge(token))

    def test_exception_invalid_totp_porte_le_user_id(self):
        user, secret, _ = self._enabled_user()
        token = tfs.create_login_challenge(user, remember=False)
        wrong = "000000" if pyotp.TOTP(secret).now() != "000000" else "111111"
        try:
            tfs.verify_login_challenge(token, wrong)
            self.fail("InvalidTotpCode attendue")
        except tfs.InvalidTotpCode as e:
            self.assertEqual(e.user_id, user["id"])

    def test_token_invalide_leve_invalid_challenge_avant_toute_verification(self):
        with self.assertRaises(tfs.InvalidChallenge):
            tfs.verify_login_challenge("jeton-inexistant", "123456")

    def test_verrouillage_apres_trop_dechecs(self):
        user, secret, _ = self._enabled_user()
        wrong = "000000" if pyotp.TOTP(secret).now() != "000000" else "111111"
        for _ in range(tfs.MAX_ATTEMPTS):
            token = tfs.create_login_challenge(user, remember=False)
            with self.assertRaises(tfs.InvalidTotpCode):
                tfs.verify_login_challenge(token, wrong)
            db.log_security_event("two_factor_verify_failed", user_id=user["id"])
        token = tfs.create_login_challenge(user, remember=False)
        with self.assertRaises(tfs.TooManyAttempts):
            tfs.verify_login_challenge(token, self._future_code(secret))


class TestVerifyRecoveryChallenge(LoginChallengeTestCase):
    def test_code_valide_resout_et_supprime_le_code(self):
        user, secret, codes = self._enabled_user()
        token = tfs.create_login_challenge(user, remember=True)
        resolved_user, remember = tfs.verify_recovery_challenge(token, codes[0])
        self.assertEqual(resolved_user["id"], user["id"])
        self.assertTrue(remember)
        self.assertEqual(db.count_recovery_codes(user["id"]), 9)

    def test_meme_code_ne_peut_pas_etre_reutilise(self):
        user, secret, codes = self._enabled_user()
        token1 = tfs.create_login_challenge(user, remember=False)
        tfs.verify_recovery_challenge(token1, codes[0])
        token2 = tfs.create_login_challenge(user, remember=False)
        with self.assertRaises(tfs.InvalidRecoveryCode):
            tfs.verify_recovery_challenge(token2, codes[0])

    def test_code_invalide_leve_invalid_recovery_code(self):
        user, secret, codes = self._enabled_user()
        token = tfs.create_login_challenge(user, remember=False)
        with self.assertRaises(tfs.InvalidRecoveryCode):
            tfs.verify_recovery_challenge(token, "0000-0000-0000-0000")
        self.assertEqual(db.count_recovery_codes(user["id"]), 10)

    def test_code_vide_est_refuse(self):
        user, secret, codes = self._enabled_user()
        token = tfs.create_login_challenge(user, remember=False)
        with self.assertRaises(tfs.InvalidRecoveryCode):
            tfs.verify_recovery_challenge(token, "")

    def test_exception_porte_le_user_id(self):
        user, secret, codes = self._enabled_user()
        token = tfs.create_login_challenge(user, remember=False)
        try:
            tfs.verify_recovery_challenge(token, "0000-0000-0000-0000")
            self.fail("InvalidRecoveryCode attendue")
        except tfs.InvalidRecoveryCode as e:
            self.assertEqual(e.user_id, user["id"])

    def test_chaque_code_reste_independant(self):
        user, secret, codes = self._enabled_user()
        token1 = tfs.create_login_challenge(user, remember=False)
        tfs.verify_recovery_challenge(token1, codes[0])
        token2 = tfs.create_login_challenge(user, remember=False)
        # Le deuxième code, jamais utilisé, doit rester valide.
        tfs.verify_recovery_challenge(token2, codes[1])
        self.assertEqual(db.count_recovery_codes(user["id"]), 8)


class TestVerrouillageTemporaire(LoginChallengeTestCase):
    def test_ensure_not_locked_out_ne_leve_pas_sous_le_seuil(self):
        user, _, _ = self._enabled_user()
        for _ in range(tfs.MAX_ATTEMPTS - 1):
            db.log_security_event("two_factor_verify_failed", user_id=user["id"])
        tfs._ensure_not_locked_out(user["id"])  # ne doit pas lever

    def test_ensure_not_locked_out_leve_au_seuil(self):
        user, _, _ = self._enabled_user()
        for _ in range(tfs.MAX_ATTEMPTS):
            db.log_security_event("two_factor_verify_failed", user_id=user["id"])
        with self.assertRaises(tfs.TooManyAttempts):
            tfs._ensure_not_locked_out(user["id"])

    def test_retry_after_minutes_correspond_a_lockout_minutes(self):
        user, _, _ = self._enabled_user()
        for _ in range(tfs.MAX_ATTEMPTS):
            db.log_security_event("two_factor_verify_failed", user_id=user["id"])
        try:
            tfs._ensure_not_locked_out(user["id"])
            self.fail("TooManyAttempts attendue")
        except tfs.TooManyAttempts as e:
            self.assertEqual(e.retry_after_minutes, tfs.LOCKOUT_MINUTES)

    def test_echecs_anciens_ne_comptent_plus(self):
        """Un échec journalisé il y a plus de LOCKOUT_MINUTES ne doit plus
        compter dans le verrouillage — vérifié en insérant directement une
        ligne horodatée dans le passé (contourne db.log_security_event, qui
        utilise toujours "maintenant")."""
        user, _, _ = self._enabled_user()
        old_ts = (datetime.now(timezone.utc) - timedelta(minutes=tfs.LOCKOUT_MINUTES + 5)).isoformat()
        conn = db.get_connection()
        try:
            for _ in range(tfs.MAX_ATTEMPTS):
                conn.execute(
                    "INSERT INTO security_events (event_type, user_id, ip, created_at) VALUES (?, ?, ?, ?)",
                    ("two_factor_verify_failed", user["id"], None, old_ts),
                )
            conn.commit()
        finally:
            conn.close()
        tfs._ensure_not_locked_out(user["id"])  # ne doit pas lever

    def test_verrouillage_scope_par_utilisateur(self):
        user_a, _, _ = self._enabled_user()
        user_b = self._make_user(email="autre2fa@gmail.com", username="autre2fa")
        for _ in range(tfs.MAX_ATTEMPTS):
            db.log_security_event("two_factor_verify_failed", user_id=user_a["id"])
        tfs._ensure_not_locked_out(user_b["id"])  # ne doit pas lever


class TestConcurrence(TwoFactorServiceTestCase):
    def test_verification_totp_thread_safe(self):
        """_verify_totp_code() est une fonction pure (aucun état partagé) —
        vérifie qu'appeler massivement en parallèle ne provoque ni exception
        ni résultat incohérent."""
        secret = pyotp.random_base32()
        code = pyotp.TOTP(secret).now()
        results = []
        lock = threading.Lock()

        def worker():
            ok, _ = tfs._verify_totp_code(secret, code, None)
            with lock:
                results.append(ok)

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertTrue(all(results))

    def test_consommation_recovery_code_concurrente_ne_reussit_quune_fois(self):
        user = self._make_user()
        setup = tfs.begin_setup(user)
        user = db.get_user_by_id(user["id"])
        codes = tfs.confirm_setup(user, pyotp.TOTP(setup["secret"]).now())
        tokens = [tfs.create_login_challenge(db.get_user_by_id(user["id"]), False) for _ in range(10)]

        successes, failures = [], []
        lock = threading.Lock()

        def worker(token):
            try:
                tfs.verify_recovery_challenge(token, codes[0])
                with lock:
                    successes.append(1)
            except tfs.InvalidRecoveryCode:
                with lock:
                    failures.append(1)

        threads = [threading.Thread(target=worker, args=(t,)) for t in tokens]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(successes), 1)
        self.assertEqual(len(failures), 9)


if __name__ == "__main__":
    unittest.main()
