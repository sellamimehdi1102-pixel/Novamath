"""Non-régression de l'écriture mathématique des exercices servis (Troisième,
Seconde, Première historique) — chantier « corrections d'écriture
mathématique », 2026-10-26.

Vérifie, sur le texte réellement servi (banque curée, banque « natural »
prioritaire champ par champ, pool généré), l'absence des défauts corrigés :
doubles signes (« 0 - -2 », « 17 + -2h »), produit par un négatif non
parenthésé (« a × -5 »), formule en bloc pour un simple nom (« $$ABC$$ »),
LaTeX corrompu (« \\$alpha », caractères de contrôle), constante ±1 masquée
(« + = 0 »). Les ids, réponses et notions ne sont pas concernés ici (voir les
tests propres à chaque générateur).
"""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SERVED = {
    "troisieme": ("exercises_bank_troisieme.json", None, "exercises_generated_troisieme.json"),
    "seconde": ("exercises_bank.json", "exercises_bank_natural.json", "exercises_generated_seconde.json"),
    "premiere": ("exercises_bank_premiere.json", None, "exercises_generated_premiere.json"),
}

FORBIDDEN = {
    "produit par un négatif non parenthésé": re.compile(r"(?:\\times|\\cdot|×)\s*-\s*(?:\d|\\d?frac)"),
    "« + » suivi d'un négatif": re.compile(r"\+\s*-\s*(?:\d|\\d?frac)"),
    "« - » suivi d'un négatif": re.compile(r"[\w)\]}]\s*-\s*-\s*(?:\d|\\d?frac)"),
    "nom en formule bloc": re.compile(r"\$\$[A-Z]{3}\$\$"),
    "antislash-dollar corrompu": re.compile(r"\\\$[a-zA-Z]"),
    "caractère de contrôle": re.compile(r"[\x00-\x08\x0b-\x1f\x7f]"),
    "constante masquée": re.compile(r"[+-]\s+=\s*0"),
}


def _texts(entry):
    out = [entry.get(f) for f in ("enonce", "hint", "answer")]
    out += list(entry.get("solution_steps") or [])
    return [t for t in out if isinstance(t, str)]


def _served(cls):
    bank_f, natural_f, gen_f = SERVED[cls]
    bank = json.loads((ROOT / bank_f).read_text(encoding="utf-8"))
    natural = {}
    if natural_f:
        natural = {e["id"]: e for e in json.loads((ROOT / natural_f).read_text(encoding="utf-8")) if "id" in e}
    for e in bank:
        merged = dict(e)
        merged.update({k: v for k, v in natural.get(e["id"], {}).items() if k in ("enonce", "hint", "answer", "solution_steps")})
        yield merged
    yield from json.loads((ROOT / gen_f).read_text(encoding="utf-8"))


class TestNotationMathematiqueExercices(unittest.TestCase):
    def test_aucun_defaut_de_notation_dans_les_exercices_servis(self):
        for cls in SERVED:
            problems = []
            for e in _served(cls):
                for t in _texts(e):
                    for label, rx in FORBIDDEN.items():
                        m = rx.search(t)
                        if m:
                            problems.append(f"{e['id']} ({label}) : …{t[max(0, m.start() - 30):m.end() + 20]}…")
            with self.subTest(classe=cls):
                self.assertEqual(problems, [], "\n".join(problems[:20]))


if __name__ == "__main__":
    unittest.main()
