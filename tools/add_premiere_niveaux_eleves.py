"""Chantier 2 (2026-11-01) — niveaux Difficile (4) et Défi (5) de la Première
spécialité, plus quelques trous de niveaux 1 à 3.

Après le recalibrage pédagogique (tools/calibrage_pedagogique.py,
tools/recalibrer_premiere_historique.py), 35 notions avaient moins de 4
questions à au moins un niveau, presque toujours aux niveaux 4 et 5. Les
questions ajoutées sont rédigées à la main (tools/premiere_eleves_analyse.py,
tools/premiere_eleves_geo_proba.py) et chacune est recalculée par un contrôle
indépendant à l'import.

Même principe que tools/add_premiere_chantier2.py : ajout à la banque curée
après le plus grand identifiant existant, idempotent, aucun énoncé en double
(banque curée, banque générée, nouvelles questions), aucun identifiant pris à
la banque générée. Ordre des listes figé : n'ajouter qu'à la fin.

Usage : python tools/add_premiere_niveaux_eleves.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import add_premiere_chantier2 as precedent  # noqa: E402
from premiere_eleves_analyse import EXERCICES as ANALYSE  # noqa: E402
from premiere_eleves_geo_proba import EXERCICES as GEO_PROBA  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BANK_PATH = ROOT / "exercises_bank_premiere.json"
GENERATED_PATH = ROOT / "exercises_generated_premiere.json"
FIRST_ID = precedent.FIRST_ID + len(precedent.EXERCICES)  # 2386
EXERCICES = ANALYSE + GEO_PROBA

# Relecture pédagogique du 2026-11-01 (après ajout) : questions placées en Défi qui
# appliquent une technique classique dont la stratégie est indiquée ou standard
# (substitution X = e^x ou X = √x, nombres en progression connaissant somme et
# produit, système de conditions, paramètre) : niveau 4 (2515, application directe : 3).
RECALIBRAGE = {
    2411: 4, 2414: 4, 2424: 4, 2432: 4, 2433: 4, 2435: 4, 2453: 4, 2464: 4, 2467: 4, 2475: 4, 2493: 4,
    2512: 4, 2515: 3, 2522: 4, 2527: 4, 2530: 4, 2581: 4, 2588: 4, 2605: 4, 2616: 4, 2622: 4, 2623: 4,
}
# Contenu remplacé (identifiant conservé, jamais déployé) : 2606 portait sur
# l'indépendance mutuelle de trois événements, hors programme de Première.
# Contrôle avec le programme de Première (BO du 2 avril 2026), même problème corrigé :
# 2491 : r³ = 500/π résolu par encadrement (racine cubique non enseignée) ;
# 2608 : seuil 0,5 (n = 4) au lieu de 0,9 (n = 13) — répétition limitée à n ⩽ 4 ;
# 2630 : généralisation à n lancers remplacée par 2 et 3 lancers (n ⩽ 4).
REMPLACES = {2606, 2491, 2608, 2630}


def main() -> int:
    if FIRST_ID != 2386:
        print(f"ERREUR — premier identifiant inattendu : {FIRST_ID}", file=sys.stderr)
        return 1
    enonces = [e["enonce"] for e in EXERCICES]
    if len(set(enonces)) != len(enonces):
        print("ERREUR — énoncé en double parmi les nouvelles questions", file=sys.stderr)
        return 1
    data = json.loads(BANK_PATH.read_text(encoding="utf-8"))
    generated = json.loads(GENERATED_PATH.read_text(encoding="utf-8"))
    by_id = {e["id"]: e for e in data}
    generated_ids = {e["id"] for e in generated}
    known_enonces = {e["enonce"] for e in data if e["id"] < FIRST_ID} | {e["enonce"] for e in generated}
    added = 0
    for i, ex in enumerate(EXERCICES):
        ex = {**ex, "id": FIRST_ID + i}
        ex["difficulty"] = RECALIBRAGE.get(ex["id"], ex["difficulty"])
        if ex["id"] in generated_ids:
            print(f"ERREUR — identifiant {ex['id']} déjà utilisé par la banque générée", file=sys.stderr)
            return 1
        if ex["id"] in by_id:
            if by_id[ex["id"]] != ex and (
                ex["id"] in REMPLACES or {**by_id[ex["id"]], "difficulty": ex["difficulty"]} == ex
            ):
                by_id[ex["id"]].clear()
                by_id[ex["id"]].update(ex)  # même position, même identifiant
                added += 1
                continue
            if by_id[ex["id"]] != ex:
                print(f"ERREUR — identifiant {ex['id']} déjà pris par un autre exercice", file=sys.stderr)
                return 1
            continue
        if ex["enonce"] in known_enonces:
            print(f"ERREUR — énoncé déjà présent : {ex['enonce'][:60]}", file=sys.stderr)
            return 1
        data.append(ex)
        added += 1
    if added:
        BANK_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK — {added} exercice(s) ajouté(s), recalibré(s) ou remplacé(s) ; banque : {len(data)} exercices.")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
