"""
Garde-fou d'accès Stripe PRODUCTION, partagé par TOUTE route qui s'apprête à
faire un appel réseau réel vers Stripe — audit admin Phase 2A (2026-10-21).

Contexte : la Phase 1 avait ajouté une protection équivalente, mais codée en
dur UNIQUEMENT dans stripe_reconciliation_service.py. La consigne explicite
de cette phase est de ne JAMAIS supposer qu'une nouvelle route financière
est protégée "par association" avec la réconciliation — ce module existe
pour que toute nouvelle fonction Stripe en invoque EXPLICITEMENT une
instance, en première ligne, avant le moindre appel réseau.

Deux niveaux, identiques en esprit à ceux de stripe_reconciliation_service.py :

1. Blocage DUR, non contournable par aucun paramètre de requête : Stripe en
   mode "production" (clé sk_live_...) alors que ce serveur ne tourne pas
   lui-même en production (`config.IS_PRODUCTION` est False, dérivé de
   FLASK_ENV) — un poste de développement local n'a jamais de raison
   légitime d'appeler Stripe production (voir l'incident réel du
   2026-10-20 qui a motivé toute cette phase de sécurisation).
2. Confirmation EXPLICITE obligatoire (`confirmed=True`) si Stripe ET ce
   serveur sont tous deux en production — une lecture de données
   financières réelles reste un geste volontaire, jamais le comportement
   par défaut d'un simple chargement de page.

stripe_reconciliation_service.py conserve ses propres exceptions
(StripeReconciliationBlocked/ConfirmationRequired), déjà testées et en
production de fait — ce module n'y est pas branché dans cette phase pour ne
prendre aucun risque de régression sur du code déjà vérifié ; tout nouveau
code (stripe_financial_service.py) doit en revanche appeler CE module.
"""
import config
import stripe_service


class StripeAccessBlocked(Exception):
    """Mode PRODUCTION + serveur non-production : blocage dur. server.py
    répond 403, quelle que soit la valeur de `confirmed` envoyée."""


class StripeAccessConfirmationRequired(Exception):
    """Mode PRODUCTION + serveur production, mais confirmation manquante.
    server.py répond 409 — l'appelant peut relancer avec confirmed=True."""


def ensure_safe_to_query_stripe(confirmed=False):
    """A appeler EXPLICITEMENT, en première ligne, par toute fonction de
    service qui s'apprête à faire un appel réseau réel vers Stripe (lecture
    seule ou non). Renvoie le mode courant ("test"/"production"/
    "etat_inconnu") si l'appel peut continuer ; lève sinon.

    Ne gère PAS le cas "non_configure" (absence de clé) : laissé à
    l'appelant, qui lève généralement sa propre exception dédiée pour ce
    cas (voir stripe_reconciliation_service.StripeReconciliationUnavailable)
    — ce module ne traite que la distinction test/production, jamais la
    configuration elle-même."""
    mode = stripe_service.operating_mode()
    if mode == "production":
        if not config.IS_PRODUCTION:
            raise StripeAccessBlocked(
                "Stripe est configuré en mode PRODUCTION mais ce serveur tourne "
                "en environnement de développement (FLASK_ENV != 'production') — "
                "aucun appel réel vers Stripe production n'est autorisé depuis ce poste."
            )
        if not confirmed:
            raise StripeAccessConfirmationRequired(
                "Confirmation explicite requise avant d'interroger Stripe en mode PRODUCTION "
                "(des données financières réelles seraient lues)."
            )
    return mode
