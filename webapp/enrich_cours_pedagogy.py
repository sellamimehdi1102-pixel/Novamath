"""
Enrichit EN PLACE les cours déjà curatés à la main (actuellement : Seconde,
static/data/cours/chapitre_*.json) avec les nouveaux champs pédagogiques
(intro plus riche, explicationSimple, intuition, exemplesConcrets, exemples
enrichis d'une explication/conclusion) — sans jamais toucher au contenu
mathématique déjà écrit (definition, formules, reglesImportantes, methode,
figure...), qui reste tel quel.

Contrairement à `generate_cours_from_bank.py` (qui régénère Première depuis
sa banque d'exercices, seule source de vérité pour cette classe), ce script
ne repart d'aucune banque : le fichier de cours existant EST la source, et
seuls des champs manquants lui sont ajoutés.

Usage : python enrich_cours_pedagogy.py <class_level> [chapitre_N]
(depuis webapp/). Sans argument de chapitre : tous les chapitres du dossier.
"""
import json
import sys

import curriculum_registry
import figure_builder
import pedagogy_templates as pedago


def _enrich_notion(notion):
    category = pedago.detect_category(notion.get("id", ""), notion.get("title", ""), notion.get("tags"))

    notion["intro"] = pedago.build_intro(notion.get("title", ""), category)
    notion.setdefault("explicationSimple", pedago.build_explication_simple(category))
    notion.setdefault("intuition", pedago.build_intuition(category))
    notion.setdefault("exemplesConcrets", pedago.build_exemples_concrets(category))
    if not notion.get("astuce"):
        notion["astuce"] = pedago.build_astuce_fallback(category)
    if not notion.get("figure"):
        notion["figure"] = figure_builder.build_figure(category, notion.get("id", ""), notion.get("title", ""))

    for ex in notion.get("exemples") or []:
        ex.setdefault(
            "explication",
            "Lisons d'abord attentivement l'énoncé, puis appliquons la méthode vue juste au-dessus, étape par étape.",
        )
        ex.setdefault("conclusion", f"Nous obtenons ainsi : {ex.get('reponse', '')}")
    return notion


def enrich(class_level, chapter_filter=None):
    profile = curriculum_registry.CURRICULUM_REGISTRY[class_level]
    if profile.courses_dir is None or not profile.courses_dir.exists():
        raise SystemExit(f"Aucun dossier de cours pour {class_level!r}.")

    pattern = f"{chapter_filter}.json" if chapter_filter else "chapitre_*.json"
    files = sorted(profile.courses_dir.glob(pattern))
    if not files:
        raise SystemExit(f"Aucun fichier trouvé pour le motif {pattern!r} dans {profile.courses_dir}.")

    written = []
    for path in files:
        chapter = json.loads(path.read_text(encoding="utf-8"))
        chapter["notions"] = [_enrich_notion(n) for n in chapter.get("notions", [])]
        path.write_text(json.dumps(chapter, ensure_ascii=False, indent=2), encoding="utf-8")
        written.append(path)
    return written


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        raise SystemExit("Usage : python enrich_cours_pedagogy.py <class_level> [chapitre_N]")
    class_level_arg = sys.argv[1]
    chapter_arg = sys.argv[2] if len(sys.argv) == 3 else None
    if class_level_arg not in curriculum_registry.CURRICULUM_REGISTRY:
        raise SystemExit(f"Classe inconnue du registre : {class_level_arg!r}")
    written_files = enrich(class_level_arg, chapter_arg)
    print(f"{len(written_files)} fichier(s) enrichi(s) :")
    for f in written_files:
        print(f"  - {f}")

    from chatbot.validate_cours_schema import validate_all
    errors, stats = validate_all(cours_dir=curriculum_registry.CURRICULUM_REGISTRY[class_level_arg].courses_dir)
    print(f"\n{stats['chapters']} chapitres, {stats['notions']} notions validés.")
    if errors:
        print(f"{len(errors)} erreur(s) :")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print("Aucune erreur de schéma.")
