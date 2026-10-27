"""Chapitres de la Première spécifique, dans l'ordre du manuel « Première ES/L »
(adaptation du 2026-10-26, voir PREMIERE_SPECIFIQUE_SUIVI.md) :
(numéro, module de cours, module de banque).

Les modules des chapitres retirés du curriculum actif sont dans reserve/
(RESERVE ci-dessous) : ils ne sont ni construits ni servis, mais les outils de
construction les consultent pour vérifier qu'aucun contenu ne disparaît sans
avoir été explicitement retiré.
"""
import importlib

CHAPITRES = (
    (1, "cours_ch01", "banque_ch01"),   # Pourcentages
    (2, "cours_ch02", "banque_ch02"),   # Fonctions numériques
    (3, "cours_ch03", "banque_ch03"),   # Polynômes du second degré (ancien ch. 2)
    (4, "cours_ch04", "banque_ch04"),   # Statistiques
    (5, "cours_ch05", "banque_ch05"),   # Dérivation (ancien ch. 3)
    (6, "cours_ch06", "banque_ch06"),   # Dérivation et variations (ancien ch. 4)
    (7, "cours_ch07", "banque_ch07"),   # Suites numériques (ancien ch. 1)
    (8, "cours_ch08", "banque_ch08"),   # Variables aléatoires (ancien ch. 10)
    (9, "cours_ch09", "banque_ch09"),   # Loi de Bernoulli et loi binomiale
)

# Anciens chapitres hors manuel (ou sources de notions déplacées) :
# (ancien numéro, module de cours, module de banque) dans reserve/.
RESERVE = (
    (5, "cours_ch05", "banque_ch05"),   # Fonction exponentielle
    (6, "cours_ch06", "banque_ch06"),   # Trigonométrie
    (7, "cours_ch07", "banque_ch07"),   # Produit scalaire
    (8, "cours_ch08", "banque_ch08"),   # Géométrie repérée
    (9, "cours_ch09", "banque_ch09"),   # Probabilités conditionnelles (dont épreuves de Bernoulli, reprise au ch. 9)
    (11, "cours_ch11", "banque_ch11"),  # Vocabulaire ensembliste et logique
    (12, "cours_ch12", "banque_ch12"),  # Algorithmique et programmation : listes
    (13, "cours_ch13", "banque_ch13"),  # Automatismes (notions reprises aux ch. 1, 2, 3, 4 et 8)
)


def modules():
    """[(numéro, module cours, module banque)] importés."""
    return [
        (number, importlib.import_module(f"premiere_specifique.{cours}"), importlib.import_module(f"premiere_specifique.{banque}"))
        for number, cours, banque in CHAPITRES
    ]


def banque_modules():
    """Modules de banque seuls (sans importer les cours, qui dépendent des quiz)."""
    return [(number, importlib.import_module(f"premiere_specifique.{banque}")) for number, _c, banque in CHAPITRES]


def reserve_modules():
    """[(ancien numéro, module cours, module banque)] de la réserve, importés."""
    return [
        (number, importlib.import_module(f"premiere_specifique.reserve.{cours}"), importlib.import_module(f"premiere_specifique.reserve.{banque}"))
        for number, cours, banque in RESERVE
    ]
