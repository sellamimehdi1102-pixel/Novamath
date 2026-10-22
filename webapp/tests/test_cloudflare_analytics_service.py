"""
Suite Phase 2 Cloudflare — finalisation après introspection réelle du schéma
(2026-10-21) — cloudflare_analytics_service.py. AUCUN appel réseau réel :
requests.post est systématiquement mocké (et de toute façon bloqué par le
garde-fou réseau global de conftest.py, voir test_isolation_reseau_api.py).

Couvre :
  - l'absence de configuration ;
  - visites (sum.visits) ET pages vues (count), avec comparaison période
    précédente, calculées en UN SEUL appel réseau (aliases "current"/
    "previous") ;
  - le regroupement quotidien via `dimensions { date }` en UN SEUL appel ;
  - les 5 classements (pages/pays/référents/navigateurs/appareils) en UN
    SEUL appel (5 alias) ;
  - les réponses GraphQL PARTIELLES (un alias en erreur n'invalide pas les
    autres) et les erreurs GraphQL TOTALES ;
  - les périodes réellement sans trafic (liste vide = donnée valide, jamais
    une erreur) ;
  - le cache TTL (pas de second appel réseau avant expiration) ;
  - la note d'échantillonnage au-delà de 7 jours.
"""
import unittest
from datetime import timedelta
from unittest.mock import MagicMock, patch

import requests

import cloudflare_analytics_service as svc
import config


def _patch_config(token="tok", account="acct", site="site"):
    return patch.multiple(
        config,
        CLOUDFLARE_API_TOKEN=token,
        CLOUDFLARE_ACCOUNT_TAG=account,
        CLOUDFLARE_SITE_TAG=site,
    )


def _resp(payload, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = payload
    return resp


def _overview_payload(current=(42, 10), previous=(30, 8), omit=None, errors=None):
    accounts = {}
    if omit != "current":
        accounts["current"] = [{"count": current[0], "sum": {"visits": current[1]}}]
    if omit != "previous":
        accounts["previous"] = [{"count": previous[0], "sum": {"visits": previous[1]}}]
    payload = {"data": {"viewer": {"accounts": [accounts]}}}
    if errors:
        payload["errors"] = errors
    return payload


def _daily_payload(rows, omit=False, errors=None):
    accounts = {}
    if not omit:
        accounts["daily"] = [
            {"count": r["pageviews"], "sum": {"visits": r["visits"]}, "dimensions": {"date": r["date"]}}
            for r in rows
        ]
    payload = {"data": {"viewer": {"accounts": [accounts]}}}
    if errors:
        payload["errors"] = errors
    return payload


# Alias -> clé de dimension, dérivé de _RANKING_SPECS (service réel) pour ne
# jamais dupliquer indépendamment la correspondance dans les tests.
_DIM_BY_ALIAS = {alias: dim for _result_key, alias, dim in svc._RANKING_SPECS}


def _rankings_payload(**per_alias):
    """per_alias : alias GraphQL (topPages/topCountries/topReferrers/
    topBrowsers/topDevices) -> liste de (label, count, visits). Alias absent
    du kwarg = omis de la réponse (simulate champ manquant)."""
    accounts = {}
    for alias, rows in per_alias.items():
        accounts[alias] = [
            {"count": c, "sum": {"visits": v}, "dimensions": {_DIM_BY_ALIAS[alias]: label}} for label, c, v in rows
        ]
    return {"data": {"viewer": {"accounts": [accounts]}}}

ALL_RANKINGS_FULL = {
    "topPages": [("/cours", 100, 40), ("/exercices", 80, 30)],
    "topCountries": [("FR", 150, 60), ("BE", 20, 8)],
    "topReferrers": [("google.com", 50, 20), ("", 10, 4)],
    "topBrowsers": [("Chrome", 120, 50), ("Firefox", 30, 12)],
    "topDevices": [("desktop", 140, 55), ("mobile", 30, 10)],
}


class TestIsConfigured(unittest.TestCase):
    def test_toutes_variables_absentes(self):
        with patch.multiple(config, CLOUDFLARE_API_TOKEN=None, CLOUDFLARE_ACCOUNT_TAG=None, CLOUDFLARE_SITE_TAG=None):
            self.assertFalse(svc.is_configured())

    def test_une_seule_variable_absente_reste_non_configure(self):
        with patch.multiple(config, CLOUDFLARE_API_TOKEN="tok", CLOUDFLARE_ACCOUNT_TAG="acct", CLOUDFLARE_SITE_TAG=None):
            self.assertFalse(svc.is_configured())

    def test_les_trois_variables_presentes(self):
        with _patch_config():
            self.assertTrue(svc.is_configured())


class TestResolveWindow(unittest.TestCase):
    def test_fenetre_invalide_retombe_sur_30j(self):
        window, since_dt, until_dt = svc.resolve_window("invalide")
        self.assertEqual(window, "30j")
        self.assertEqual(until_dt - since_dt, timedelta(days=30))

    def test_7j(self):
        window, since_dt, until_dt = svc.resolve_window("7j")
        self.assertEqual(window, "7j")
        self.assertEqual(until_dt - since_dt, timedelta(days=7))

    def test_90j(self):
        window, since_dt, until_dt = svc.resolve_window("90j")
        self.assertEqual(window, "90j")
        self.assertEqual(until_dt - since_dt, timedelta(days=90))


class TestSamplingNote(unittest.TestCase):
    def test_aucune_note_a_7_jours(self):
        self.assertIsNone(svc._sampling_note("7j"))

    def test_note_au_dela_de_7_jours(self):
        self.assertIn("échantillon", svc._sampling_note("30j"))
        self.assertIn("échantillon", svc._sampling_note("90j"))


class TestListFilters(unittest.TestCase):
    def test_structure(self):
        result = svc.list_filters()
        self.assertEqual(result["default"], "30j")
        self.assertEqual([w["value"] for w in result["windows"]], ["7j", "30j", "90j"])


class TestNonConfigure(unittest.TestCase):
    def setUp(self):
        svc.clear_cache()

    @patch("requests.post")
    def test_overview_sans_configuration(self, mock_post):
        with patch.multiple(config, CLOUDFLARE_API_TOKEN=None, CLOUDFLARE_ACCOUNT_TAG=None, CLOUDFLARE_SITE_TAG=None):
            payload, error = svc.overview("30j")
        self.assertIsNone(error)
        for key in ("pageviews", "pageviews_previous_period", "visits", "visits_previous_period"):
            self.assertFalse(payload[key]["available"], key)
            self.assertEqual(payload[key]["status"], "not_configured", key)
        mock_post.assert_not_called()

    @patch("requests.post")
    def test_charts_sans_configuration(self, mock_post):
        with patch.multiple(config, CLOUDFLARE_API_TOKEN=None, CLOUDFLARE_ACCOUNT_TAG=None, CLOUDFLARE_SITE_TAG=None):
            payload, error = svc.charts("7j")
        self.assertIsNone(error)
        self.assertFalse(payload["daily"]["available"])
        mock_post.assert_not_called()

    @patch("requests.post")
    def test_rankings_sans_configuration(self, mock_post):
        with patch.multiple(config, CLOUDFLARE_API_TOKEN=None, CLOUDFLARE_ACCOUNT_TAG=None, CLOUDFLARE_SITE_TAG=None):
            payload, error = svc.rankings("30j")
        self.assertIsNone(error)
        for result_key, _alias, _dim in svc._RANKING_SPECS:
            self.assertFalse(payload[result_key]["available"], result_key)
        mock_post.assert_not_called()


class TestOverviewConfigure(unittest.TestCase):
    def setUp(self):
        svc.clear_cache()

    @patch("requests.post")
    def test_visites_et_pages_vues_en_un_seul_appel(self, mock_post):
        mock_post.return_value = _resp(_overview_payload(current=(42, 10), previous=(30, 8)))
        with _patch_config():
            payload, error = svc.overview("7j")
        self.assertIsNone(error)
        self.assertEqual(payload["pageviews"]["value"], 42)
        self.assertEqual(payload["visits"]["value"], 10)
        self.assertEqual(payload["pageviews_previous_period"]["value"], 30)
        self.assertEqual(payload["visits_previous_period"]["value"], 8)
        self.assertEqual(mock_post.call_count, 1)

    def test_note_definition_visites_toujours_presente(self):
        with _patch_config(), patch("requests.post", return_value=_resp(_overview_payload())):
            svc.clear_cache()
            payload, _error = svc.overview("7j")
        self.assertIn("visiteurs uniques", payload["visits"]["note"])

    @patch("requests.post")
    def test_jeton_envoye_en_bearer_jamais_dans_le_corps(self, mock_post):
        mock_post.return_value = _resp(_overview_payload())
        with _patch_config(token="secret-token-xyz"):
            svc.overview("7j")
        _args, kwargs = mock_post.call_args
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer secret-token-xyz")
        self.assertNotIn("secret-token-xyz", kwargs.get("json", {}).get("query", ""))

    @patch("requests.post")
    def test_periode_sans_trafic_est_zero_jamais_une_erreur(self, mock_post):
        mock_post.return_value = _resp(_overview_payload(current=(0, 0), previous=(0, 0)))
        with _patch_config():
            payload, error = svc.overview("7j")
        self.assertIsNone(error)
        self.assertTrue(payload["pageviews"]["available"])
        self.assertEqual(payload["pageviews"]["value"], 0)

    @patch("requests.post")
    def test_timeout(self, mock_post):
        mock_post.side_effect = requests.Timeout("trop lent")
        with _patch_config():
            payload, error = svc.overview("7j")
        self.assertIsNone(error)
        self.assertFalse(payload["pageviews"]["available"])
        self.assertFalse(payload["visits"]["available"])
        self.assertIn("délai", payload["pageviews"]["reason"].lower())

    @patch("requests.post")
    def test_erreur_reseau(self, mock_post):
        mock_post.side_effect = requests.ConnectionError("refused")
        with _patch_config():
            payload, _error = svc.overview("7j")
        self.assertFalse(payload["pageviews"]["available"])

    @patch("requests.post")
    def test_statut_http_non_200(self, mock_post):
        mock_post.return_value = _resp(_overview_payload(), status_code=500)
        with _patch_config():
            payload, _error = svc.overview("7j")
        self.assertFalse(payload["pageviews"]["available"])
        self.assertIn("500", payload["pageviews"]["reason"])

    @patch("requests.post")
    def test_erreur_graphql_totale_sans_donnee(self, mock_post):
        mock_post.return_value = _resp({"errors": [{"message": "invalid siteTag"}], "data": None})
        with _patch_config():
            payload, _error = svc.overview("7j")
        self.assertFalse(payload["pageviews"]["available"])
        self.assertFalse(payload["visits"]["available"])

    @patch("requests.post")
    def test_erreur_graphql_partielle_naffecte_que_lalias_concerne(self, mock_post):
        # "current" absent de la réponse (simule une erreur GraphQL partielle
        # sur cet alias), "previous" reste exploitable.
        mock_post.return_value = _resp(
            _overview_payload(previous=(30, 8), omit="current", errors=[{"message": "partial failure on current"}])
        )
        with _patch_config():
            payload, _error = svc.overview("7j")
        self.assertFalse(payload["pageviews"]["available"])
        self.assertFalse(payload["visits"]["available"])
        self.assertTrue(payload["pageviews_previous_period"]["available"])
        self.assertEqual(payload["pageviews_previous_period"]["value"], 30)

    @patch("requests.post")
    def test_forme_de_donnees_inattendue(self, mock_post):
        mock_post.return_value = _resp({"data": {"viewer": {"accounts": [{"current": [{"count": "pas-un-nombre"}]}]}}})
        with _patch_config():
            payload, _error = svc.overview("7j")
        self.assertFalse(payload["pageviews"]["available"])

    def test_sampling_note_present_au_dela_de_7_jours(self):
        with _patch_config(), patch("requests.post", return_value=_resp(_overview_payload())):
            svc.clear_cache()
            payload, _error = svc.overview("30j")
        self.assertIsNotNone(payload["sampling_note"])

    def test_sampling_note_absent_a_7_jours(self):
        with _patch_config(), patch("requests.post", return_value=_resp(_overview_payload())):
            svc.clear_cache()
            payload, _error = svc.overview("7j")
        self.assertIsNone(payload["sampling_note"])


class TestChartsConfigure(unittest.TestCase):
    def setUp(self):
        svc.clear_cache()

    @patch("requests.post")
    def test_evolution_quotidienne_un_seul_appel_reseau(self, mock_post):
        rows = [
            {"date": "2026-10-14", "pageviews": 5, "visits": 2},
            {"date": "2026-10-15", "pageviews": 7, "visits": 3},
        ]
        mock_post.return_value = _resp(_daily_payload(rows))
        with _patch_config():
            payload, error = svc.charts("7j")
        self.assertIsNone(error)
        self.assertTrue(payload["daily"]["available"])
        self.assertEqual(payload["daily"]["value"], rows)
        self.assertEqual(mock_post.call_count, 1)

    @patch("requests.post")
    def test_tri_defensif_par_date_meme_si_cloudflare_renvoie_desordonne(self, mock_post):
        rows = [
            {"date": "2026-10-15", "pageviews": 7, "visits": 3},
            {"date": "2026-10-14", "pageviews": 5, "visits": 2},
        ]
        mock_post.return_value = _resp(_daily_payload(rows))
        with _patch_config():
            payload, _error = svc.charts("7j")
        dates = [d["date"] for d in payload["daily"]["value"]]
        self.assertEqual(dates, sorted(dates))

    @patch("requests.post")
    def test_aucun_trafic_liste_vide_valide_avec_note(self, mock_post):
        mock_post.return_value = _resp(_daily_payload([]))
        with _patch_config():
            payload, _error = svc.charts("7j")
        self.assertTrue(payload["daily"]["available"])
        self.assertEqual(payload["daily"]["value"], [])
        self.assertIn("Aucune donnée", payload["daily"]["note"])

    @patch("requests.post")
    def test_champ_daily_absent_de_la_reponse(self, mock_post):
        mock_post.return_value = _resp(_daily_payload([], omit=True))
        with _patch_config():
            payload, _error = svc.charts("7j")
        self.assertFalse(payload["daily"]["available"])

    @patch("requests.post")
    def test_timeout(self, mock_post):
        mock_post.side_effect = requests.Timeout("trop lent")
        with _patch_config():
            payload, _error = svc.charts("7j")
        self.assertFalse(payload["daily"]["available"])


class TestRankingsConfigure(unittest.TestCase):
    def setUp(self):
        svc.clear_cache()

    @patch("requests.post")
    def test_5_classements_en_un_seul_appel_reseau(self, mock_post):
        mock_post.return_value = _resp(_rankings_payload(**ALL_RANKINGS_FULL))
        with _patch_config():
            payload, error = svc.rankings("30j")
        self.assertIsNone(error)
        self.assertEqual(mock_post.call_count, 1)

        self.assertTrue(payload["top_pages"]["available"])
        self.assertEqual(payload["top_pages"]["value"][0], {"label": "/cours", "pageviews": 100, "visits": 40})

        self.assertTrue(payload["top_countries"]["available"])
        self.assertEqual(payload["top_countries"]["value"][0]["label"], "FR")

        self.assertTrue(payload["top_referrers"]["available"])
        # Label vide ("direct", jamais de référent) remplacé par un libellé explicite.
        self.assertEqual(payload["top_referrers"]["value"][1]["label"], "(inconnu)")

        self.assertTrue(payload["top_browsers"]["available"])
        self.assertEqual(payload["top_browsers"]["value"][0]["label"], "Chrome")

        self.assertTrue(payload["top_devices"]["available"])
        self.assertEqual(payload["top_devices"]["value"][0]["label"], "desktop")

    @patch("requests.post")
    def test_limite_a_10_resultats_demandee_cote_serveur(self, mock_post):
        mock_post.return_value = _resp(_rankings_payload(**ALL_RANKINGS_FULL))
        with _patch_config():
            svc.rankings("30j")
        _args, kwargs = mock_post.call_args
        self.assertEqual(kwargs["json"]["variables"]["limit"], 10)

    @patch("requests.post")
    def test_tri_count_desc_demande_dans_la_requete(self, mock_post):
        mock_post.return_value = _resp(_rankings_payload(**ALL_RANKINGS_FULL))
        with _patch_config():
            svc.rankings("30j")
        _args, kwargs = mock_post.call_args
        self.assertIn("count_DESC", kwargs["json"]["query"])

    @patch("requests.post")
    def test_un_classement_en_erreur_partielle_naffecte_pas_les_autres(self, mock_post):
        partial = dict(ALL_RANKINGS_FULL)
        del partial["topCountries"]  # simule un alias manquant (erreur GraphQL partielle)
        resp_payload = _rankings_payload(**partial)
        resp_payload["errors"] = [{"message": "partial failure on topCountries"}]
        mock_post.return_value = _resp(resp_payload)
        with _patch_config():
            payload, _error = svc.rankings("30j")
        self.assertFalse(payload["top_countries"]["available"])
        self.assertTrue(payload["top_pages"]["available"])
        self.assertTrue(payload["top_browsers"]["available"])

    @patch("requests.post")
    def test_aucun_trafic_sur_un_classement_liste_vide_valide(self, mock_post):
        empty = {k: [] for k in ALL_RANKINGS_FULL}
        mock_post.return_value = _resp(_rankings_payload(**empty))
        with _patch_config():
            payload, _error = svc.rankings("30j")
        self.assertTrue(payload["top_pages"]["available"])
        self.assertEqual(payload["top_pages"]["value"], [])
        self.assertIn("Aucune donnée", payload["top_pages"]["note"])

    @patch("requests.post")
    def test_erreur_http_sur_les_5_classements(self, mock_post):
        mock_post.return_value = _resp(_rankings_payload(**ALL_RANKINGS_FULL), status_code=503)
        with _patch_config():
            payload, _error = svc.rankings("30j")
        for result_key, _alias, _dim in svc._RANKING_SPECS:
            self.assertFalse(payload[result_key]["available"], result_key)


class TestStatusField(unittest.TestCase):
    """Champ discriminant `status` (Chantier Fréquentation, 2026-10-22) —
    les 3 valeurs possibles : "not_configured", "api_error", "ok". Le
    frontend (admin-frequentation.js) ne doit plus jamais deviner la cause
    via un string-matching sur `reason`."""

    def setUp(self):
        svc.clear_cache()

    @patch("requests.post")
    def test_status_not_configured(self, mock_post):
        with patch.multiple(config, CLOUDFLARE_API_TOKEN=None, CLOUDFLARE_ACCOUNT_TAG=None, CLOUDFLARE_SITE_TAG=None):
            payload, _error = svc.overview("30j")
        self.assertEqual(payload["pageviews"]["status"], "not_configured")
        mock_post.assert_not_called()

    @patch("requests.post")
    def test_status_api_error_sur_timeout(self, mock_post):
        mock_post.side_effect = requests.Timeout("trop lent")
        with _patch_config():
            payload, _error = svc.overview("7j")
        self.assertEqual(payload["pageviews"]["status"], "api_error")
        self.assertEqual(payload["visits"]["status"], "api_error")

    @patch("requests.post")
    def test_status_api_error_sur_erreur_graphql_partielle(self, mock_post):
        mock_post.return_value = _resp(
            _overview_payload(previous=(30, 8), omit="current", errors=[{"message": "partial failure on current"}])
        )
        with _patch_config():
            payload, _error = svc.overview("7j")
        self.assertEqual(payload["pageviews"]["status"], "api_error")
        self.assertEqual(payload["pageviews_previous_period"]["status"], "ok")

    @patch("requests.post")
    def test_status_ok_meme_pour_une_valeur_reelle_a_zero(self, mock_post):
        mock_post.return_value = _resp(_overview_payload(current=(0, 0), previous=(0, 0)))
        with _patch_config():
            payload, _error = svc.overview("7j")
        self.assertTrue(payload["pageviews"]["available"])
        self.assertEqual(payload["pageviews"]["value"], 0)
        self.assertEqual(payload["pageviews"]["status"], "ok")

    @patch("requests.post")
    def test_status_api_error_sur_charts(self, mock_post):
        mock_post.side_effect = requests.ConnectionError("refused")
        with _patch_config():
            payload, _error = svc.charts("7j")
        self.assertEqual(payload["daily"]["status"], "api_error")

    @patch("requests.post")
    def test_status_not_configured_sur_rankings(self, mock_post):
        with patch.multiple(config, CLOUDFLARE_API_TOKEN=None, CLOUDFLARE_ACCOUNT_TAG=None, CLOUDFLARE_SITE_TAG=None):
            payload, _error = svc.rankings("30j")
        for result_key, _alias, _dim in svc._RANKING_SPECS:
            self.assertEqual(payload[result_key]["status"], "not_configured", result_key)

    @patch("requests.post")
    def test_status_api_error_sur_rankings(self, mock_post):
        mock_post.return_value = _resp(_rankings_payload(**ALL_RANKINGS_FULL), status_code=503)
        with _patch_config():
            payload, _error = svc.rankings("30j")
        for result_key, _alias, _dim in svc._RANKING_SPECS:
            self.assertEqual(payload[result_key]["status"], "api_error", result_key)


class TestCacheTTL(unittest.TestCase):
    def setUp(self):
        svc.clear_cache()

    @patch("requests.post")
    def test_deux_appels_identiques_un_seul_vrai_appel_reseau(self, mock_post):
        mock_post.return_value = _resp(_overview_payload())
        with _patch_config():
            svc.overview("7j")
            call_count_after_first = mock_post.call_count
            svc.overview("7j")
        self.assertEqual(mock_post.call_count, call_count_after_first)

    @patch("requests.post")
    def test_cache_expire_redeclenche_un_appel_reseau(self, mock_post):
        mock_post.return_value = _resp(_overview_payload())
        with _patch_config():
            svc.overview("7j")
            first_call_count = mock_post.call_count
            with patch("time.monotonic", return_value=1e15):
                svc.overview("7j")
                self.assertGreater(mock_post.call_count, first_call_count)

    @patch("requests.post")
    def test_cache_distinct_par_type_de_requete(self, mock_post):
        # overview()/charts()/rankings() portent sur des clés de cache
        # différentes : les 3 doivent chacune déclencher leur propre appel.
        mock_post.side_effect = [
            _resp(_overview_payload()),
            _resp(_daily_payload([])),
            _resp(_rankings_payload(**{k: [] for k in ALL_RANKINGS_FULL})),
        ]
        with _patch_config():
            svc.overview("7j")
            svc.charts("7j")
            svc.rankings("7j")
        self.assertEqual(mock_post.call_count, 3)

    def test_clear_cache_vide_bien_le_cache(self):
        svc._cache_set(("k",), "v")
        svc.clear_cache()
        self.assertIsNone(svc._cache_get(("k",)))


if __name__ == "__main__":
    unittest.main()
