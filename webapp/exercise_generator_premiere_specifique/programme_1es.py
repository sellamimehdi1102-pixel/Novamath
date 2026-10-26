"""Adaptation des générateurs de la Première spécifique au manuel « Première ES/L »
(2026-10-26, voir PREMIERE_SPECIFIQUE_SUIVI.md).

Les modules historiques du package ne sont PAS modifiés : la table ADAPTATION
indique, pour chacune de leurs familles conservées, son chapitre et sa notion
dans les 9 chapitres du manuel ; une famille absente de la table est hors
périmètre (retirée du curriculum actif, code conservé). Les modules créés
pour l'adaptation (*_1es.py) sont repris tels quels.

Deux usages, une seule source de vérité :
- `adapter_pool(pool_brut)` : filtre et rattache le pool généré
  (tools/generate_premiere_specifique_exercises.py) — identifiants et contenus
  des exercices conservés inchangés ;
- `VUES` : objets au contrat d'un module générateur (FAMILIES, CHAPTER_ID,
  generate_one), un par (module, chapitre), pour la génération à la demande
  (exercise_generator/registry.py, entrée "premiere_specifique").
"""
from dataclasses import dataclass

from exercise_generator_premiere_specifique import (
    automatismes, derivation_2026, derivatives, evenements_1es, fonctions_reference_1es, loi_binomiale_1es,
    pourcentages_1es, second_degre, second_degre_formes, statistiques_1es, suites, tangente, variables_aleatoires,
    variations,
)

CH1, CH2, CH3, CH4, CH5, CH6, CH7, CH8, CH9 = (f"Chapitre_{n}" for n in range(1, 10))

NOUVEAUX_MODULES = (pourcentages_1es, fonctions_reference_1es, statistiques_1es, evenements_1es, loi_binomiale_1es)


def _notion_de(module, famille):
    """Même règle que exercise_generator/registry.py::_notion_of."""
    return getattr(famille, "notion", None) or module.NOTION


def _meme_notion(module, chapitre, *familles):
    return {f.id: (chapitre, _notion_de(module, f)) for f in module.FAMILIES if f.id in familles}


# module -> {famille: (chapitre, notion)} ; seules les familles listées sont servies.
ADAPTATION = {
    # Ch. 1 Pourcentages — évolutions et taux.
    automatismes: {
        **_meme_notion(automatismes, CH1, "appliquer_taux", "valeur_initiale", "calculer_taux", "evolutions_successives", "taux_reciproque"),
        # Ch. 2 Fonctions numériques (la famille « droite », Seconde, est hors manuel).
        "image_antecedent": (CH2, "Rappels sur les fonctions"),
        "lecture_variations": (CH2, "Rappels sur les fonctions"),
        # Ch. 3 : « Calcul numérique et algébrique » n'est plus une notion
        # (2026-10-26) ; les familles utiles sont rattachées aux notions qui
        # s'en servent, « developper » sort du curriculum actif.
        "produit_nul": (CH3, "Équations du second degré"),
        "factoriser": (CH3, "Racines et factorisation d'un trinôme"),
        "signe_affine": (CH3, "Signe du trinôme et inéquations du second degré"),
        # Ch. 4 Statistiques et Ch. 8 événements.
        "statistiques": (CH4, "Notation Σ et indicateurs de tendance centrale"),
        "tableau_croise": (CH8, "Rappels de probabilités : événements"),
    },
    # Ch. 3 Polynômes du second degré (somme et produit des racines, position
    # relative et modélisation : hors manuel).
    second_degre: {
        **_meme_notion(second_degre, CH3, "resolution", "signe_discriminant", "equation_depuis_racines",
                       "contexte_rectangle", "comparer_methodes", "verifier_resolution", "corriger_erreur", "contexte_projectile", "parametre"),
        # « Factoriser après avoir déterminé les racines » relève de la notion
        # « Racines et factorisation » (rattachement corrigé le 2026-10-26).
        "factorisation": (CH3, "Racines et factorisation d'un trinôme"),
    },
    second_degre_formes: _meme_notion(second_degre_formes, CH3, "canonique_lecture", "canonique_completion", "canonique_general", "sommet_et_point",
                                      "comparer_images", "inequation_factorisee", "inequation_developpee", "inequation_ramener", "inequation_parametre"),
    # Ch. 5 Dérivation (dérivées de fonctions composées et approximation affine : hors manuel).
    derivatives: _meme_notion(derivatives, CH5, "constante", "affine", "polynome_simple", "polynome_sup", "produit_simple", "fraction_simple",
                              "coeff_fractionnaire", "fraction_rationnelle", "produit_complexe", "quotient_complexe", "simplification_prealable"),
    tangente: _meme_notion(tangente, CH5, *(f.id for f in tangente.FAMILIES)),
    derivation_2026: _meme_notion(derivation_2026, CH5, "tangente_horizontale", "lire_pente_tangente", "vitesse_instantanee", "tangente_parallele",
                                  "tangentes_par_un_point", "puissance_negative", "regle_inverse", "produit_racine"),
    # Ch. 6 Dérivation et variations (√(2x) : dérivée composée, hors manuel).
    variations: _meme_notion(variations, CH6, *(f.id for f in variations.FAMILIES if f.id != "variations_racine")),
    # Ch. 7 Suites (sommes de termes et limites : hors manuel).
    suites: _meme_notion(suites, CH7, "generalites_explicite", "generalites_recurrence", "generalites_inverse", "generalites_interpretation",
                         "generalites_vrai_faux", "arith_terme_general", "arith_retrouver_raison", "arith_probleme_contextualise",
                         "arith_demonstration", "geo_terme_general", "geo_retrouver_raison", "geo_probleme_contextualise", "geo_demonstration",
                         "variation_difference", "variation_quotient", "variation_parametre", "variation_interpretation", "variation_vrai_faux"),
    # Ch. 8 Variables aléatoires (transformation affine Y = aX + b : hors manuel).
    variables_aleatoires: _meme_notion(variables_aleatoires, CH8, "completer_loi", "jeu_esperance", "esperance", "variance"),
}
for _m in NOUVEAUX_MODULES:
    ADAPTATION[_m] = {f.id: (_m.CHAPTER_ID, _notion_de(_m, f)) for f in _m.FAMILIES}
for _m, _table in ADAPTATION.items():
    _inconnues = set(_table) - {f.id for f in _m.FAMILIES}
    assert not _inconnues, (_m.__name__, _inconnues)

# Clé du pool brut : (chapitre d'origine du module, famille) — unique, vérifié.
_PAR_ORIGINE = {}
for _m, _table in ADAPTATION.items():
    for _fid, _cible in _table.items():
        assert (_m.CHAPTER_ID, _fid) not in _PAR_ORIGINE, (_m.CHAPTER_ID, _fid)
        _PAR_ORIGINE[(_m.CHAPTER_ID, _fid)] = _cible


def adapter_pool(pool_brut):
    """Exercices du pool brut conservés, rattachés à leur chapitre et à leur notion
    du manuel ; l'ordre, les identifiants et les contenus ne changent pas."""
    out = []
    for ex in pool_brut:
        cible = _PAR_ORIGINE.get((ex["chapter_id"], ex["family"]))
        if cible is not None:
            out.append({**ex, "chapter_id": cible[0], "notion": cible[1]})
    return out


@dataclass(frozen=True)
class _FamilleVue:
    id: str
    level: int
    label: str
    notion: str


class Vue:
    """Une partie d'un module générateur, vue au contrat d'un module :
    familles conservées d'un même chapitre, avec leur notion du manuel."""

    def __init__(self, module, chapitre, table):
        self.module, self.CHAPTER_ID = module, chapitre
        self._notions = {fid: notion for fid, (ch, notion) in table.items() if ch == chapitre}
        self.FAMILIES = [_FamilleVue(f.id, f.level, f.label, self._notions[f.id]) for f in module.FAMILIES if f.id in self._notions]
        self.NOTION = None
        self.__name__ = f"{module.__name__}[{chapitre}]"

    def generate_one(self, family_id, seed=None):
        if family_id not in self._notions:
            raise KeyError(family_id)
        ex = self.module.generate_one(family_id, seed=seed)
        return {**ex, "chapter_id": self.CHAPTER_ID, "notion": self._notions[family_id]}


VUES = tuple(Vue(m, ch, table) for m, table in ADAPTATION.items() for ch in sorted({c for c, _n in table.values()}, key=lambda c: int(c.split("_")[1])))


def familles_retirees():
    """{module: [familles hors périmètre]} — pour le suivi et les tests."""
    return {m.__name__.split(".")[-1]: [f.id for f in m.FAMILIES if f.id not in ADAPTATION.get(m, {})]
            for m in (automatismes, second_degre, second_degre_formes, derivatives, tangente, derivation_2026, variations, suites, variables_aleatoires)}
