"""
Agrégation financière Stripe — Phase 2A de l'audit admin (2026-10-21).
LECTURE SEULE, jamais d'écriture Stripe ni base. Toute fonction qui
interroge Stripe réellement appelle stripe_access_guard.
ensure_safe_to_query_stripe(confirmed) EXPLICITEMENT en première ligne,
avant le moindre appel réseau — cette protection n'est JAMAIS supposée
acquise par ailleurs (voir sa docstring).

Objets Stripe utilisés, et pourquoi :
- Invoice (status="paid") : revenu BRUT réellement encaissé sur la
  période — `amount_paid`, jamais `amount_due` (facture pas encore payée)
  ni `total` (montant théorique avant application d'un éventuel solde
  crédit/coupon). Une Invoice "paid" est un encaissement réel ; ce module
  n'utilise PAS Charge.list en parallèle, pour ne jamais compter deux fois
  le même encaissement (Charge et Invoice décrivent souvent le même
  paiement sous deux angles différents côté Stripe).
- Refund : montants réellement remboursés sur la période demandée — le
  filtre `created` porte sur la date du REMBOURSEMENT, qui peut être
  largement postérieure à celle du paiement d'origine (hors de la même
  fenêtre). Remboursement total ou partiel traités de façon identique : le
  montant exact remboursé est déjà dans `amount`, jamais recalculé à
  partir du montant de la facture.
- PaymentIntent : seule source qui expose un paiement en ÉCHEC (une
  Invoice "paid" n'existe par construction que pour un paiement réussi) —
  utilisée uniquement pour la liste "derniers paiements", jamais pour le
  calcul du revenu (qui reste basé sur Invoice, voir ci-dessus).

Non utilisé dans cette phase (limitation documentée, jamais simulée) :
- Balance Transaction : seule source fiable des FRAIS Stripe réels
  (commission prélevée par transaction) — nécessiterait un appel
  supplémentaire par transaction (ou le paramètre `expand`), non
  implémenté ici. "Net" dans ce module signifie donc explicitement "brut
  moins remboursements", JAMAIS "net des frais Stripe" — voir le champ
  `net_of_refunds_only` toujours renvoyé à True dans le rapport, pour que
  le frontend ne puisse jamais afficher ce nombre comme un vrai net
  commercial.

Multi-devises : jamais sommées entre elles — chaque agrégat est un dict
{currency: montant_en_centimes}, jamais un total toutes devises confondues
(une addition naïve de centimes EUR et USD n'aurait aucun sens).

Fuseaux horaires : toutes les bornes de période sont calculées en UTC,
jamais dans le fuseau horaire du navigateur de l'admin connecté — évite
toute ambiguïté de "début/fin de journée" selon l'endroit où l'admin se
trouve. Stripe lui-même horodate `created` en UTC (epoch Unix), cohérent.

Pagination : plafonnée à MAX_PAGES pages par appel (jamais une boucle
illimitée) — un rapport qui atteint cette limite le signale explicitement
(`"capped": True`), jamais un total silencieusement partiel présenté comme
complet.
"""
import logging
from datetime import datetime, timedelta, timezone

import stripe_access_guard
import stripe_service

logger = logging.getLogger("stripe_financial_service")

# Nombre de pages Stripe (100 objets/page) interrogées au maximum par appel —
# même logique de plafond que stripe_reconciliation_service.DEFAULT_BATCH_SIZE,
# ici appliquée à la PROFONDEUR de pagination plutôt qu'à un lot unique :
# Mathadap n'a aujourd'hui aucun volume justifiant plus de 2000
# factures/remboursements sur une période ; au-delà, le rapport se signale
# explicitement incomplet plutôt que de boucler indéfiniment.
MAX_PAGES = 20
PAGE_SIZE = 100

# Statuts PaymentIntent considérés comme un échec pour la liste "derniers
# paiements" — "requires_payment_method" après un premier essai est l'état
# réel d'un paiement par carte refusée (Stripe attend un nouveau moyen de
# paiement) ; "canceled" un abandon explicite. "requires_action"/
# "processing" ne sont ni un succès ni un échec (3-D Secure en cours,
# traitement asynchrone) — jamais classés dans l'un ou l'autre.
_FAILED_PAYMENT_STATUSES = ("requires_payment_method", "canceled")


class StripeFinancialDataUnavailable(Exception):
    """Levée si Stripe n'est pas configuré du tout (pas de clé/placeholder)
    — jamais un rapport vide trompeur, voir server.py pour la réponse HTTP
    associée (501, même convention que le reste des routes Stripe)."""


def _paginate(list_fn, **kwargs):
    """Boucle `has_more`/`starting_after` générique, plafonnée à MAX_PAGES.
    Renvoie (items, capped) — `capped=True` si la limite a été atteinte
    alors que Stripe indiquait encore `has_more=True`."""
    items = []
    starting_after = None
    capped = False
    for page_index in range(MAX_PAGES):
        page = list_fn(limit=PAGE_SIZE, starting_after=starting_after, **kwargs)
        data = page.get("data", [])
        items.extend(data)
        has_more = bool(page.get("has_more")) and bool(data)
        if not has_more:
            break
        starting_after = data[-1]["id"]
        if page_index == MAX_PAGES - 1:
            capped = True
    return items, capped


def _require_configured():
    if not stripe_service.is_configured():
        raise StripeFinancialDataUnavailable(
            "Stripe n'est pas configuré (STRIPE_SECRET_KEY absente ou valeur "
            "placeholder) — aucune donnée financière disponible."
        )


def _utc_window(days):
    """(gte, lte) en timestamp Unix UTC pour les `days` derniers jours,
    bornes incluses jusqu'à l'instant présent — jamais calculé dans un
    fuseau horaire local (voir docstring du module)."""
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)
    return int(start.timestamp()), int(now.timestamp())


def _plan_for_invoice(invoice):
    """Tentative d'attribution Premium/Ultra d'une Invoice, via le Price ID
    de sa première ligne — best-effort délibéré (voir docstring module) :
    une structure de ligne inattendue (format d'API différent, facture sans
    ligne d'abonnement) renvoie "inconnu" plutôt que de faire échouer tout
    le rapport pour une seule facture atypique."""
    try:
        price_id = invoice["lines"]["data"][0]["price"]["id"]
    except (KeyError, IndexError, TypeError):
        return "inconnu"
    try:
        return stripe_service.plan_from_price_id(price_id).value
    except Exception:  # defensive — ne doit jamais faire échouer le rapport
        return "inconnu"


def get_revenue_report(days=30, confirmed=False):
    """Revenu BRUT/remboursé/net-de-remboursements sur les `days` derniers
    jours, par devise, avec ventilation Premium/Ultra en best-effort (voir
    _plan_for_invoice). Aucun appel Stripe tant que le garde-fou n'a pas
    validé l'environnement (voir stripe_access_guard)."""
    mode = stripe_access_guard.ensure_safe_to_query_stripe(confirmed)
    _require_configured()

    gte, lte = _utc_window(days)
    invoices, invoices_capped = _paginate(
        stripe_service.list_all_invoices, created_gte=gte, created_lte=lte, status="paid"
    )
    refunds, refunds_capped = _paginate(
        stripe_service.list_all_refunds, created_gte=gte, created_lte=lte
    )

    gross_by_currency = {}
    gross_by_plan_cents = {}
    for inv in invoices:
        currency = inv.get("currency")
        amount = inv.get("amount_paid") or 0
        gross_by_currency[currency] = gross_by_currency.get(currency, 0) + amount
        plan = _plan_for_invoice(inv)
        gross_by_plan_cents[plan] = gross_by_plan_cents.get(plan, 0) + amount

    refunded_by_currency = {}
    for ref in refunds:
        currency = ref.get("currency")
        refunded_by_currency[currency] = refunded_by_currency.get(currency, 0) + (ref.get("amount") or 0)

    net_by_currency = {
        c: gross_by_currency.get(c, 0) - refunded_by_currency.get(c, 0)
        for c in set(gross_by_currency) | set(refunded_by_currency)
    }

    return {
        "mode": mode,
        "window_days": days,
        "period_start": gte,
        "period_end": lte,
        "gross_revenue_cents_by_currency": gross_by_currency,
        "gross_revenue_cents_by_plan": gross_by_plan_cents,
        "refunded_cents_by_currency": refunded_by_currency,
        "net_of_refunds_cents_by_currency": net_by_currency,
        "net_of_refunds_only": True,
        "invoices_checked": len(invoices),
        "refunds_checked": len(refunds),
        "capped": invoices_capped or refunds_capped,
    }


def get_revenue_series(months=6, confirmed=False):
    """Série mensuelle de revenu brut/net, UNE SEULE passe de pagination sur
    toute la fenêtre (jamais un appel Stripe par mois) — les factures sont
    ensuite regroupées par mois calendaire UTC en Python. Mois au format
    "YYYY-MM", triés du plus ancien au plus récent."""
    mode = stripe_access_guard.ensure_safe_to_query_stripe(confirmed)
    _require_configured()

    gte, lte = _utc_window(months * 31)
    invoices, invoices_capped = _paginate(
        stripe_service.list_all_invoices, created_gte=gte, created_lte=lte, status="paid"
    )
    refunds, refunds_capped = _paginate(
        stripe_service.list_all_refunds, created_gte=gte, created_lte=lte
    )

    gross_by_month = {}
    for inv in invoices:
        month = datetime.fromtimestamp(inv.get("created", 0), tz=timezone.utc).strftime("%Y-%m")
        gross_by_month[month] = gross_by_month.get(month, 0) + (inv.get("amount_paid") or 0)

    refunded_by_month = {}
    for ref in refunds:
        month = datetime.fromtimestamp(ref.get("created", 0), tz=timezone.utc).strftime("%Y-%m")
        refunded_by_month[month] = refunded_by_month.get(month, 0) + (ref.get("amount") or 0)

    months_sorted = sorted(set(gross_by_month) | set(refunded_by_month))
    series = [
        {
            "month": m,
            "gross_revenue_cents": gross_by_month.get(m, 0),
            "refunded_cents": refunded_by_month.get(m, 0),
            "net_of_refunds_cents": gross_by_month.get(m, 0) - refunded_by_month.get(m, 0),
        }
        for m in months_sorted
    ]

    return {
        "mode": mode,
        "months_requested": months,
        "series": series,
        "net_of_refunds_only": True,
        "capped": invoices_capped or refunds_capped,
    }


def get_payments_report(limit=20, confirmed=False):
    """Derniers paiements (PaymentIntents), succès ET échecs — une seule
    page Stripe (jamais de pagination multi-appels pour une simple liste
    "derniers paiements", contrairement aux rapports de revenu ci-dessus)."""
    mode = stripe_access_guard.ensure_safe_to_query_stripe(confirmed)
    _require_configured()

    limit = max(min(int(limit), 100), 1)
    page = stripe_service.list_all_payment_intents(limit=limit)
    payments = [
        {
            "id": pi["id"],
            "amount": pi.get("amount"),
            "currency": pi.get("currency"),
            "status": pi.get("status"),
            "created": pi.get("created"),
        }
        for pi in page.get("data", [])
    ]
    return {
        "mode": mode,
        "payments": payments,
        "has_more": bool(page.get("has_more")),
        "succeeded_count": sum(1 for p in payments if p["status"] == "succeeded"),
        "failed_count": sum(1 for p in payments if p["status"] in _FAILED_PAYMENT_STATUSES),
    }
