"""
Envoi d'email pour NovaMath — SEC-04.

Architecture stricte, identique aux autres services :

    consent_service.py / privacy_service.py  →  email_service.py  →  config.py

jamais l'inverse. Ce module ne connaît rien de la base de données ni de la
logique métier RGPD : il expose uniquement `send_email()` (transport SMTP
générique) et des fonctions `build_*_email()` (contenu HTML/texte des emails
NovaMath) : consentement parental, mise à jour de politique, et
réinitialisation de mot de passe (voir auth.py::forgot_password).

Aucune nouvelle dépendance : `smtplib`/`email` (bibliothèque standard Python)
suffisent à un envoi SMTP classique (TLS/STARTTLS), sans les particularités
propriétaires d'un fournisseur tiers.

Configuration absente (EMAIL_SMTP_HOST non positionnée) : `send_email()` ne
lève jamais d'erreur, renvoie `sent=False` — même philosophie que
TWO_FACTOR_SECRET_KEY/STRIPE_SECRET_KEY absentes ailleurs dans le projet. Les
appelants (consent_service.py, auth.py::forgot_password) suivent alors le
même filet : le lien concerné (consentement ou réinitialisation) est renvoyé
en clair dans la réponse JSON UNIQUEMENT dans ce cas (jamais journalisé), pour
rester utilisable en développement sans SMTP configuré. Dès que le SMTP est
configuré, ce filet ne s'active plus jamais : le lien part uniquement par
email, jamais dans une réponse API (un token de réinitialisation est un
secret au même titre qu'un mot de passe)."""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import config

logger = logging.getLogger("email_service")


class EmailNotConfigured(Exception):
    """Levée uniquement si un appelant utilise send_email(required=True) sans
    configuration SMTP — par défaut send_email() ne lève jamais, voir sa
    docstring."""


def is_configured():
    return bool(config.EMAIL_SMTP_HOST and config.EMAIL_FROM_ADDRESS)


def send_email(to, subject, html_body, text_body, required=False):
    """Envoie un email SMTP ; renvoie True si réellement envoyé, False sinon
    (configuration absente). Ne journalise jamais le contenu de l'email (peut
    contenir un lien de consentement secret) — uniquement l'événement
    d'envoi/échec, sans destinataire ni corps."""
    if not is_configured():
        if required:
            raise EmailNotConfigured("Aucun service d'envoi d'email n'est configuré (EMAIL_SMTP_HOST).")
        logger.info("Email non envoyé (SMTP non configuré) : sujet='%s'.", subject)
        return False

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = f"{config.EMAIL_FROM_NAME} <{config.EMAIL_FROM_ADDRESS}>"
    message["To"] = to
    message.attach(MIMEText(text_body, "plain", "utf-8"))
    message.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(config.EMAIL_SMTP_HOST, config.EMAIL_SMTP_PORT, timeout=10) as smtp:
            if config.EMAIL_SMTP_USE_TLS:
                smtp.starttls()
            if config.EMAIL_SMTP_USERNAME and config.EMAIL_SMTP_PASSWORD:
                smtp.login(config.EMAIL_SMTP_USERNAME, config.EMAIL_SMTP_PASSWORD)
            smtp.sendmail(config.EMAIL_FROM_ADDRESS, [to], message.as_string())
        logger.info("Email envoyé avec succès : sujet='%s'.", subject)
        return True
    except (smtplib.SMTPException, OSError):
        logger.warning("Échec d'envoi d'email (sujet='%s') — voir la trace ci-dessous.", subject, exc_info=True)
        return False


def _wrap_html(title, body_html, button_label=None, button_url=None):
    button_html = ""
    if button_label and button_url:
        button_html = f"""
        <p style="text-align:center;margin:32px 0;">
          <a href="{button_url}" style="background:#7c5cff;color:#fff;padding:12px 28px;
             border-radius:8px;text-decoration:none;font-weight:600;">{button_label}</a>
        </p>"""
    return f"""<!doctype html>
<html><body style="font-family:Arial,sans-serif;background:#f4f4f7;padding:24px;">
  <div style="max-width:520px;margin:0 auto;background:#fff;border-radius:12px;padding:32px;">
    <h2 style="color:#1a1a2e;">{title}</h2>
    <div style="color:#333;line-height:1.6;">{body_html}</div>
    {button_html}
    <p style="color:#999;font-size:12px;margin-top:32px;">NovaMath — Cet email a été envoyé automatiquement, merci de ne pas y répondre.</p>
  </div>
</body></html>"""


def build_parental_consent_request_email(child_pseudo, consent_url, expires_at):
    subject = f"NovaMath — Autorisation parentale pour {child_pseudo}"
    html = _wrap_html(
        "Autorisation parentale requise",
        f"""<p>Bonjour,</p>
        <p>Le compte NovaMath de <strong>{child_pseudo}</strong> nécessite votre autorisation
        pour être activé, conformément à la réglementation française sur la protection
        des mineurs (RGPD).</p>
        <p>Ce lien expire le {expires_at}.</p>""",
        button_label="Examiner la demande",
        button_url=consent_url,
    )
    text = (
        f"Le compte NovaMath de {child_pseudo} nécessite votre autorisation parentale.\n"
        f"Lien : {consent_url}\nCe lien expire le {expires_at}."
    )
    return subject, html, text


def build_parental_consent_confirmed_email(child_pseudo):
    subject = "NovaMath — Compte activé"
    html = _wrap_html(
        "Compte activé",
        f"<p>Bonjour {child_pseudo},</p><p>Ton parent a autorisé ton compte NovaMath : "
        "tu peux maintenant te connecter et profiter de toutes les fonctionnalités.</p>",
    )
    text = f"Bonjour {child_pseudo}, ton parent a autorisé ton compte NovaMath : tu peux maintenant te connecter."
    return subject, html, text


def build_parental_consent_refused_email(child_pseudo):
    subject = "NovaMath — Autorisation refusée"
    html = _wrap_html(
        "Autorisation refusée",
        f"<p>Bonjour {child_pseudo},</p><p>Ton parent n'a pas autorisé la création de ton "
        "compte NovaMath. Il restera inaccessible.</p>",
    )
    text = f"Bonjour {child_pseudo}, ton parent n'a pas autorisé la création de ton compte NovaMath."
    return subject, html, text


def build_password_reset_email(pseudo, reset_url):
    subject = "NovaMath — Réinitialisation de mot de passe"
    html = _wrap_html(
        "Réinitialisation de mot de passe",
        f"""<p>Bonjour {pseudo},</p>
        <p>Tu as demandé la réinitialisation de ton mot de passe NovaMath. Si tu n'es
        pas à l'origine de cette demande, ignore simplement cet email : ton mot de
        passe actuel reste inchangé.</p>""",
        button_label="Réinitialiser mon mot de passe",
        button_url=reset_url,
    )
    text = (
        f"Bonjour {pseudo}, tu as demandé la réinitialisation de ton mot de passe NovaMath.\n"
        f"Lien : {reset_url}\nSi tu n'es pas à l'origine de cette demande, ignore cet email."
    )
    return subject, html, text


def build_policy_updated_email(pseudo):
    subject = "NovaMath — Mise à jour de la politique de confidentialité"
    html = _wrap_html(
        "Politique de confidentialité mise à jour",
        f"<p>Bonjour {pseudo},</p><p>Nos conditions d'utilisation et/ou notre politique de "
        "confidentialité ont été mises à jour. Une nouvelle acceptation te sera demandée "
        "à ta prochaine connexion.</p>",
    )
    text = f"Bonjour {pseudo}, nos conditions/politique de confidentialité ont été mises à jour."
    return subject, html, text
