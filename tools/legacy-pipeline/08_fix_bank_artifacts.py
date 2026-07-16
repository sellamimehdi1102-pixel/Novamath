"""
Corrections ponctuelles de exercises_bank.json et exercises_bank_reformulations.json,
appliquées une fois (2026-07-13, finalisation onglet Cours) :

1. Suppression de l'étape "Note en programmation" (jargon Python/SymPy) glissée
   par erreur dans les solution_steps d'un exercice — hors sujet dans un
   exercice de maths destiné à des lycéens.
2. Remplacement de l'astérisque "informatique" a*b par le signe de
   multiplication mathématique × dans les champs texte libre (solution_steps),
   qui ne sont pas entourés de $...$ (donc jamais passés par KaTeX).

exercises_bank_natural.json n'est PAS modifié ici : il est entièrement
régénéré par 07_naturalize_exercises.py à partir de exercises_bank.json.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
STAR_RE = re.compile(r"(?<=[0-9)])\*(?=[0-9(])")


def clean_steps(steps):
    if isinstance(steps, list):
        return [s for s in steps if "Note en programmation" not in s]
    return steps


def fix_text(value):
    if isinstance(value, str):
        return STAR_RE.sub("×", value)
    return value


def fix_bank(path):
    with open(path, "r", encoding="utf-8") as f:
        bank = json.load(f)

    n_removed = 0
    n_star = 0
    for ex in bank:
        steps = ex.get("solution_steps")
        if isinstance(steps, list):
            before = len(steps)
            steps = clean_steps(steps)
            n_removed += before - len(steps)
            new_steps = []
            for s in steps:
                fixed = fix_text(s)
                if fixed != s:
                    n_star += 1
                new_steps.append(fixed)
            ex["solution_steps"] = new_steps
        for field in ("enonce", "hint", "answer"):
            if field in ex:
                fixed = fix_text(ex[field])
                if fixed != ex[field]:
                    n_star += 1
                ex[field] = fixed

    with open(path, "w", encoding="utf-8") as f:
        json.dump(bank, f, ensure_ascii=False, indent=2)

    print(f"{path.name} : {n_removed} étape(s) hors-sujet supprimée(s), {n_star} champ(s) avec * corrigé(s)")


if __name__ == "__main__":
    fix_bank(ROOT / "exercises_bank.json")
    fix_bank(ROOT / "exercises_bank_reformulations.json")
