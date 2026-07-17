# NovaMath v1.70

**Date** : 2026-07-17

**Nom de la mise à jour** : SEC-04 : conformite RGPD et protection des mineurs

## Nouveautés
- Date de naissance obligatoire à l'inscription, âge calculé automatiquement (jamais demandé directement) — seuil légal français de 15 ans (art. 8 RGPD / art. 45 Loi Informatique et Libertés).
- Consentement parental complet pour les moins de 15 ans : compte créé `pending_parental_consent` (aucun accès chatbot/Premium/exercices/données tant que non résolu), lien signé envoyé par email au parent, page publique `/parent/consent/<token>` (accepter/refuser), renvoi d'email, expiration du lien.
- Nouveau `webapp/email_service.py` : premier vrai service d'envoi d'email SMTP du projet (stdlib, aucune dépendance ajoutée), avec filet de secours dev (lien en clair, comme `dev_reset_link`) si non configuré.
- Nouveau `webapp/consent_service.py` : âge, seuil légal, cycle de vie du consentement parental, consentement cookies, versionnement des CGU/politique de confidentialité avec ré-acceptation forcée.
- Nouveau `webapp/privacy_service.py` : agrégation RGPD (export, historique des consentements) — la suppression de compte et la rectification de profil existaient déjà (`DELETE`/`PUT /api/auth/me`), désormais journalisées explicitement `gdpr_delete_account`/`gdpr_rectification`.
- Export RGPD (`GET /api/data/export`, déjà existant) étendu : historique de consentement, demandes de consentement parental, préférences cookies, journal de sécurité, progression Cours.
- Bandeau de consentement cookies (nécessaires/statistiques/marketing), jamais réaffiché une fois un choix enregistré, modifiable depuis Paramètres.
- Nouvelles tables `parental_consent_requests`, `consent_records` (preuve RGPD immuable, jamais supprimée), `cookie_consents` ; nouvelles colonnes `users.birth_date/account_status/terms_accepted_version/privacy_accepted_version` — migration idempotente.

## Corrections
- Aucune (chantier additif, aucune régression sur les 1306 tests existants).

## Optimisations
- Aucune (hors périmètre de ce chantier).

## Fichiers modifiés
- Créés : `webapp/consent_service.py`, `webapp/privacy_service.py`, `webapp/email_service.py`, `webapp/static/parent-consent.html`, `webapp/static/js/parentConsent.js`, `webapp/static/js/cookieConsent.js`, 9 fichiers de tests.
- Modifiés : `webapp/db.py`, `webapp/config.py`, `webapp/auth.py`, `webapp/server.py`, `.env.example`, `webapp/static/js/authModalsTemplate.js`, `webapp/static/js/auth.js`, `webapp/static/js/api.js`, `webapp/static/js/settings.js`, `webapp/static/css/base.css`, `webapp/tests/test_database_service.py` et 8 fichiers de tests existants.

## Bugs connus
- Aucun service SMTP réel configuré par défaut : à renseigner (`EMAIL_SMTP_*`) avant mise en production.

## Validation finale
- `npm run lint` : OK — `npm run build` : OK (parent-consent.html ajouté aux pages Vite) — `npm test` : OK (252/252) — `pytest` : OK (1306 passés, 0 échec).

## Temps estimé de développement
- Une session (exploration architecture + implémentation backend/frontend/tests complète + validation Node.js).
