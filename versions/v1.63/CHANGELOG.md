# NovaMath v1.63

**Date** : 2026-07-16

**Nom de la mise à jour** : Stripe Billing complet : portail client, cycle de vie abonnement, changement de plan

Termine Stripe Billing avant mise en production : Portail client Stripe (`/api/billing/customer-portal`), statut d'abonnement complet dérivé de Stripe (`/api/billing/status`), changement de plan respectant Stripe Billing (upgrade Premium→Ultra immédiat avec proration, downgrade Ultra→Premium programmé à la prochaine période via Subscription Schedule), et 8 nouveaux événements webhook. Le webhook reste l'unique source de vérité qui écrit `users.plan` — aucune des nouvelles routes n'écrit en base.

## Nouveautés
- `billing_service.py` (nouveau service) : `get_billing_status()`, `create_portal_session()`, `change_plan()`.
- `stripe_service.py` : `create_billing_portal_session()`, `list_payment_methods()`, `list_invoices()`, `schedule_downgrade()`.
- Routes `GET /api/billing/status`, `POST /api/billing/customer-portal`, `POST /api/billing/change-plan` dans `server.py`.
- `stripe_webhook_service.py` : support de `invoice.finalized`, `invoice.payment_succeeded`, `invoice.upcoming`, `customer.subscription.trial_will_end`, `checkout.session.expired`, `payment_method.attached/updated/detached`.
- Page Abonnement : carte de statut (plan/statut/date de renouvellement ou d'annulation) + bouton "Gérer mon abonnement" pour les comptes Premium/Ultra ; boutons "Changer vers Premium/Ultra" sur les autres cartes.
- Page Profil : section "Abonnement" (plan, statut, dates, moyen de paiement, adresse de facturation, historique des factures, bouton "Gérer mon abonnement").

## Corrections
- (aucune — fonctionnalité nouvelle, aucune régression sur l'existant)

## Optimisations
- (aucune)

## Fichiers modifiés
- Nouveaux : `webapp/billing_service.py`, `webapp/tests/test_billing_service.py`, `webapp/tests/test_server_billing.py`.
- Modifiés : `webapp/stripe_service.py`, `webapp/stripe_webhook_service.py`, `webapp/server.py`, `webapp/static/js/api.js`, `webapp/static/js/abonnement.js`, `webapp/static/abonnement.html`, `webapp/static/css/abonnement.css`, `webapp/static/js/profil.js`, `webapp/static/profil.html`, `webapp/static/css/profil.css`, `webapp/tests/test_stripe_service.py`, `webapp/tests/test_stripe_webhook_service.py`.

## Bugs connus
- Aucun connu à ce jour.

## Temps estimé de développement
- Environ 1 session de développement assistée.
