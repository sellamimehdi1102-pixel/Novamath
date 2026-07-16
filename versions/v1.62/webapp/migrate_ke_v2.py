"""
Migration automatique vers le schéma Knowledge Engine v2 complet, pour les
12 chapitres de static/data/cours/chapitre_*.json (y compris re-passage sûr
sur le chapitre pilote, Chapitre_1, pour qu'il atteigne le même schéma
complet que les autres — voir REQUIRED_V2_LIST_FIELDS/REQUIRED_V2_STRING_FIELDS
dans chatbot/validate_cours_schema.py).

Principe strict : ADDITIF UNIQUEMENT.
- Un champ déjà présent avec un contenu réel n'est JAMAIS modifié ni écrasé
  (setdefault, jamais d'affectation directe sur un champ potentiellement
  déjà enrichi à la main).
- Les champs historiques (definition, methode.etapes, exemples[], titre,
  reglesImportantes, erreursFrequentes, astuce, aRetenir, figure,
  quizExerciseIds) ne sont JAMAIS touchés — le frontend (static/js/cours.js)
  lit le JSON brut, aucune régression tolérée.
- Chaque nouveau champ est soit dérivé d'une donnée RÉELLE déjà existante
  (voir le tableau dans le rapport de migration), soit une structure vide
  explicite (liste/chaîne vide) quand aucune source fiable n'existe —
  jamais de contenu pédagogique fabriqué/halluciné.

Usage : python migrate_ke_v2.py (depuis webapp/). Traite un chapitre à la
fois et VALIDE après chaque chapitre (validate_cours_schema +
validate_topic_crosswalk) — s'arrête immédiatement si un chapitre migré ne
passe pas la validation, avant d'écrire la suite.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import canonical_ids
from chatbot.knowledge_engine import COURS_DIR, DIFFICULTE_LEVELS
from chatbot.validate_cours_schema import validate_all as validate_cours_schema
from validate_topic_crosswalk import validate as validate_topic_crosswalk


def _difficulte_heuristique(index, total):
    """Heuristique de POSITION (1er exemple = facile, dernier = difficile,
    milieu = moyen) — PAS une évaluation pédagogique réelle. Documentée
    explicitement comme telle dans le rapport final ; à valider par un
    professeur avant de s'appuyer dessus pour un Parameter Resolver."""
    if total <= 1:
        return "moyen"
    ratio = index / (total - 1)
    if ratio < 0.34:
        return "facile"
    if ratio > 0.66:
        return "difficile"
    return "moyen"


def migrate_notion(notion, chapter_id):
    """Applique le schéma KE v2 complet à une notion, en place. Additif
    uniquement (voir docstring du module). Renvoie la liste des champs
    effectivement ajoutés (pour le rapport)."""
    added = []

    if notion.get("schemaVersion") != 2:
        notion["schemaVersion"] = 2
        added.append("schemaVersion")

    if "topic_id" not in notion:
        notion["topic_id"] = notion["id"]
        added.append("topic_id")

    definitions = notion.setdefault("definitions", {})
    if "lycee" not in definitions or not definitions.get("lycee"):
        definitions["lycee"] = notion.get("definition", "")
        added.append("definitions.lycee")
    if "college" not in definitions:
        definitions["college"] = ""
        added.append("definitions.college (vide)")
    if "expert" not in definitions:
        definitions["expert"] = ""
        added.append("definitions.expert (vide)")

    if "formules" not in notion:
        # Dérivé des règles importantes déjà rédigées (contenu réel, pas
        # fabriqué) — seul le champ "expression" est rempli, le reste reste
        # à compléter par un professeur (structure vide sur les autres clés).
        formules = []
        for i, regle in enumerate(notion.get("reglesImportantes") or []):
            formules.append({
                "id": f"{notion['id']}-regle-{i + 1}",
                "nom": "",
                "expression": regle,
                "quand_utiliser": "",
                "quand_ne_pas_utiliser": "",
                "erreur_frequente": "",
                "astuce": "",
            })
        notion["formules"] = formules
        added.append(f"formules ({len(formules)} scaffoldées depuis reglesImportantes)" if formules else "formules (vide)")

    methode = notion.setdefault("methode", {})
    par_niveau = methode.setdefault("etapesParNiveau", {})
    if "normal" not in par_niveau:
        par_niveau["normal"] = methode.get("etapes") or []
        added.append("methode.etapesParNiveau.normal")
    if "debutant" not in par_niveau:
        par_niveau["debutant"] = []
        added.append("methode.etapesParNiveau.debutant (vide)")
    if "rapide" not in par_niveau:
        par_niveau["rapide"] = []
        added.append("methode.etapesParNiveau.rapide (vide)")

    exemples = notion.get("exemples") or []
    n = len(exemples)
    for i, ex in enumerate(exemples):
        if "id" not in ex:
            ex["id"] = f"{notion['id']}-exemple-{i + 1}"
            added.append(f"exemples[{i}].id")
        if "difficulte" not in ex:
            ex["difficulte"] = _difficulte_heuristique(i, n)
            added.append(f"exemples[{i}].difficulte (heuristique de position)")

    if "erreursFrequentesDetail" not in notion:
        detail = [
            {"description": e, "pourquoi": "", "comment_detecter": "", "comment_eviter": ""}
            for e in (notion.get("erreursFrequentes") or [])
        ]
        notion["erreursFrequentesDetail"] = detail
        added.append(f"erreursFrequentesDetail ({len(detail)} scaffoldées depuis erreursFrequentes)" if detail else "erreursFrequentesDetail (vide)")

    if "proprietes" not in notion:
        notion["proprietes"] = []
        added.append("proprietes (vide — curation humaine future)")

    if "vocabulaire_associe" not in notion:
        notion["vocabulaire_associe"] = []
        added.append("vocabulaire_associe (vide — curation humaine future)")

    if "synonymes" not in notion:
        synonymes = canonical_ids.synonyms_for_topic(chapter_id, notion["id"])
        notion["synonymes"] = synonymes
        added.append(f"synonymes ({len(synonymes)} dérivés de topic_crosswalk.json)" if synonymes else "synonymes (vide)")

    if "objectifs_pedagogiques" not in notion:
        objectif = notion.get("objectif")
        notion["objectifs_pedagogiques"] = [objectif] if objectif else []
        added.append("objectifs_pedagogiques (dérivé de « objectif »)" if objectif else "objectifs_pedagogiques (vide)")

    if "prerequis" not in notion:
        notion["prerequis"] = []
        added.append("prerequis (vide — curation humaine future)")

    if "notions_liees" not in notion:
        notion["notions_liees"] = []
        added.append("notions_liees (vide — curation humaine future)")

    if "difficulte" not in notion:
        notion["difficulte"] = ""
        added.append("difficulte notion (vide — non évaluable automatiquement)")

    if "tags" not in notion:
        notion["tags"] = []
        added.append("tags (vide — curation humaine future)")

    return added


def migrate_chapter_file(path):
    chapter = json.loads(path.read_text(encoding="utf-8"))
    report = {"chapter_id": chapter.get("chapterId"), "notions": []}
    for notion in chapter.get("notions", []):
        added = migrate_notion(notion, chapter["chapterId"])
        report["notions"].append({"notion_id": notion["id"], "fields_added": added})
    path.write_text(json.dumps(chapter, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    chapter_files = sorted(COURS_DIR.glob("chapitre_*.json"), key=lambda p: int(p.stem.split("_")[1]))
    full_report = []

    for path in chapter_files:
        print(f"--- Migration de {path.name} ---")
        report = migrate_chapter_file(path)
        full_report.append(report)

        errors, stats = validate_cours_schema()
        if errors:
            print(f"ÉCHEC de validation après {path.name} — arrêt de la migration :")
            for e in errors:
                print(f"  - {e}")
            sys.exit(1)

        cw_errors, cw_warnings, cw_stats = validate_topic_crosswalk()
        if cw_errors:
            print(f"ÉCHEC de la crosswalk après {path.name} — arrêt de la migration :")
            for e in cw_errors:
                print(f"  - {e}")
            sys.exit(1)

        print(f"  OK — {stats['notions']} notions, {stats['schema_v2_notions']} en schemaVersion 2, crosswalk valide")

    print()
    print("=" * 70)
    print(f"Migration terminée : {len(chapter_files)} chapitres traités, tous validés.")
    Path("migration_report.json").write_text(
        json.dumps(full_report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Détail écrit dans migration_report.json")


if __name__ == "__main__":
    main()
