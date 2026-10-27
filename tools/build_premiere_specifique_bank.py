"""Réécrit exercises_bank_premiere_specifique.json (classe « Première spécifique »)
à partir des modules tools/premiere_specifique/banque_chNN.py listés dans
premiere_specifique/chapitres.py. N'écrit jamais dans la banque de la
Première historique (exercises_bank_premiere.json).

Adaptation au manuel « Première ES/L » (2026-10-26) : les chapitres sont
renumérotés, la banque est donc reconstruite en entier, dans l'ordre des
chapitres. Garde-fous (fichier non écrit si l'un échoue) :
- contrôles de premiere_specifique.banque_commun.check_chapter (valeurs
  recalculées, quiz, identifiants, écritures fautives) ;
- un identifiant de la banque actuelle ne peut disparaître que s'il est
  déclaré hors périmètre (EXERCICES_HORS_PERIMETRE d'un module) ou s'il
  appartient à un chapitre mis en réserve (chapitres.RESERVE) ;
- aucun identifiant ni énoncé en double dans toute la banque.

Usage : python tools/build_premiere_specifique_bank.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from premiere_specifique.banque_commun import build_chapter, check_chapter  # noqa: E402
from premiere_specifique.chapitres import banque_modules, reserve_modules  # noqa: E402

BANK_PATH = ROOT / "exercises_bank_premiere_specifique.json"


def main(argv) -> int:
    if argv:
        print("Usage : python tools/build_premiere_specifique_bank.py (la banque est toujours reconstruite en entier)", file=sys.stderr)
        return 2
    old_ids = {e["id"] for e in json.loads(BANK_PATH.read_text(encoding="utf-8"))}
    problems, bank, retires = [], [], set()
    for number, banque in banque_modules():
        chapter_id = f"Chapitre_{number}"
        problems += [f"[{chapter_id}] {p}" for p in check_chapter(banque)]
        bank += build_chapter(banque)
        retires |= {e.id for e in getattr(banque, "EXERCICES_HORS_PERIMETRE", ())}
    for _n, _cours, banque in reserve_modules():
        retires |= {e.id for e in banque.EXERCISES}
    lost = old_ids - {e["id"] for e in bank} - retires
    if lost:
        problems.append(f"identifiants supprimés sans justification : {sorted(lost)[:10]}")
    ids = [e["id"] for e in bank]
    if len(ids) != len(set(ids)):
        problems.append("identifiants dupliqués dans la banque")
    enonces = [e["enonce"] for e in bank]
    if len(enonces) != len(set(enonces)):
        problems.append("énoncés dupliqués dans la banque")
    if problems:
        print("ERREUR — banque non écrite :", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    BANK_PATH.write_text(json.dumps(bank, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK — {len(bank)} exercices -> {BANK_PATH.name} ({len(old_ids - set(ids))} retirés du curriculum actif)")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main(sys.argv[1:]))
