"""Chapitres de Quatrième rédigés à partir des sources de ce dossier
(le chapitre 8, pilote, garde ses sources historiques — voir __init__.py).

(numéro, module de cours, module de banque) — un chapitre n'apparaît ici
qu'une fois son cours ET sa banque écrits ; son titre est alors retiré de
`planned_chapter_titles` (curriculum_registry.py).
"""
import importlib

CHAPITRES = (
    (1, "cours_ch01", "banque_ch01"),
    (2, "cours_ch02", "banque_ch02"),
    (3, "cours_ch03", "banque_ch03"),
    (4, "cours_ch04", "banque_ch04"),
    (5, "cours_ch05", "banque_ch05"),
    (6, "cours_ch06", "banque_ch06"),
    (7, "cours_ch07", "banque_ch07"),
    (14, "cours_ch14", "banque_ch14"),
    (9, "cours_ch09", "banque_ch09"),
    (10, "cours_ch10", "banque_ch10"),
    (12, "cours_ch12", "banque_ch12"),
    (11, "cours_ch11", "banque_ch11"),
    (13, "cours_ch13", "banque_ch13"),
    (15, "cours_ch15", "banque_ch15"),
    (16, "cours_ch16", "banque_ch16"),
    (17, "cours_ch17", "banque_ch17"),
)


def modules():
    """[(numéro, module cours, module banque)] importés."""
    return [
        (number, importlib.import_module(f"quatrieme.{cours}"), importlib.import_module(f"quatrieme.{banque}"))
        for number, cours, banque in CHAPITRES
    ]
