"""
Applique le même moteur de conversion LaTeX -> notation mathématique lisible
(voir 07_naturalize_exercises.py) au fichier exercises_bank_reformulations.json :
ses champs enonce/hint/answer/solution_steps (copies de exercises_bank.json)
ET son champ natural_variants (reformulations d'énoncé propres à ce fichier).

Modifie exercises_bank_reformulations.json sur place (contrairement à
07_naturalize_exercises.py qui ne fait que lire exercises_bank.json et écrire
un nouveau fichier) : ce fichier n'a pas de "source" séparée, on le nettoie
donc directement.
"""
import json
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
TARGET_PATH = ROOT / "exercises_bank_reformulations.json"

spec = importlib.util.spec_from_file_location(
    "naturalize_exercises", Path(__file__).resolve().parent / "07_naturalize_exercises.py"
)
naturalize_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(naturalize_mod)
naturalize_text = naturalize_mod.naturalize_text


def main():
    with open(TARGET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    for ex in data:
        for field in ("enonce", "hint", "answer"):
            if field in ex:
                ex[field] = naturalize_text(ex[field])
        steps = ex.get("solution_steps")
        if isinstance(steps, list):
            ex["solution_steps"] = [naturalize_text(s) for s in steps]
        variants = ex.get("natural_variants")
        if isinstance(variants, list):
            ex["natural_variants"] = [naturalize_text(v) for v in variants]

    with open(TARGET_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"{len(data)} exercices nettoyes dans {TARGET_PATH.name}")


if __name__ == "__main__":
    main()
