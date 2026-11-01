"""Applique tools/calibrage_pedagogique.py aux banques générées déjà servies
(exercises_generated_<classe>.json), sans les régénérer.

Seuls `difficulty`, `difficulty_label` et `difficulty_emoji` changent : le
script refuse d'écrire si un identifiant, un énoncé ou l'ordre des exercices
diffère. Idempotent (une seconde exécution ne change rien). Les scripts
tools/generate_*_exercises.py appliquent le même calibrage avant écriture :
une régénération future produit les mêmes niveaux.

Usage : python tools/recalibrer_banques_generees.py [classe ...]
        (par défaut : troisieme seconde premiere premiere_specifique)
"""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from calibrage_pedagogique import calibrer  # noqa: E402

CLASSES = ("troisieme", "seconde", "premiere", "premiere_specifique")
_CHAMPS_NIVEAU = ("difficulty", "difficulty_label", "difficulty_emoji")


def recalibrer(class_level: str) -> int:
    path = ROOT / f"exercises_generated_{class_level}.json"
    avant = json.loads(path.read_text(encoding="utf-8"))
    apres = json.loads(path.read_text(encoding="utf-8"))
    changes = calibrer(apres, class_level)
    for a, b in zip(avant, apres):
        if {k: v for k, v in a.items() if k not in _CHAMPS_NIVEAU} != {k: v for k, v in b.items() if k not in _CHAMPS_NIVEAU}:
            raise SystemExit(f"ERREUR — contenu modifié pour l'exercice {a.get('id')} : rien n'est écrit")
    if len(avant) != len(apres):
        raise SystemExit("ERREUR — nombre d'exercices modifié : rien n'est écrit")
    if changes:
        path.write_text(json.dumps(apres, ensure_ascii=False, indent=2), encoding="utf-8")
    niveaux = Counter(e["difficulty"] for e in apres)
    print(f"{class_level} : {changes} niveau(x) corrigé(s) ; répartition {dict(sorted(niveaux.items()))}")
    return changes


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    for c in sys.argv[1:] or CLASSES:
        recalibrer(c)
