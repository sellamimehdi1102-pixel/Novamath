"""Détecte les cours dont le contenu textuel est suspect : définition
générique (indice d'exercice au lieu d'une vraie définition), texte
identique recopié entre plusieurs notions, ou erreursFrequentes vide.

Usage : python -m chatbot.check_cours_generic_content [classe|dossier ...]
(depuis webapp/ ; sans argument : tous les programmes du registre).
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

# Formulations typiques d'un indice de résolution d'exercice plutôt que
# d'une définition du concept (verbe à l'impératif ciblant un calcul précis,
# souvent avec une valeur numérique ou une lettre d'exercice).
INDICE_PATTERNS = [
    r"^(Calcule|Exprime|Traduis|Convertis|Utilise|Applique|Cherche|Ajoute|Retranche|Divise|Multiplie|Isole|Développe|Regroupe|Range|Compare|Vérifie)\b",
    r"\bpuis\b.*\bpour\b",
    r"^On (calcule|détermine|remplace|utilise|développe|résout)\b",
]
INDICE_RE = re.compile("|".join(INDICE_PATTERNS))

GENERIC_INTRO_PATTERNS = [
    r"^Dans cette leçon, tu vas apprendre à utiliser\s*:",
    r"^Aujourd'hui, nous allons apprendre\s*:",
    r"^Imagine que cette notion est un nouvel outil",
    r"^Imagine une machine\s*:",
]
GENERIC_INTRO_RE = re.compile("|".join(GENERIC_INTRO_PATTERNS))

GENERIC_OBJECTIF_RE = re.compile(r"^À la fin de ce cours, tu sauras résoudre des exercices sur\b")


def load_notions(cours_dir: Path):
    for chapitre_file in sorted(cours_dir.glob("chapitre_*.json")):
        try:
            data = json.loads(chapitre_file.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover
            print(f"  [ERREUR JSON] {chapitre_file}: {exc}")
            continue
        for notion in data.get("notions", []):
            yield chapitre_file.name, data.get("chapterId", chapitre_file.stem), notion


def audit_dir(cours_dir: Path) -> dict:
    findings = {
        "indice_definition": [],
        "generic_intro": [],
        "generic_objectif": [],
        "empty_erreurs": [],
        "duplicate_definition": [],
    }
    definition_owners: dict[str, list[str]] = defaultdict(list)

    for filename, chapter_id, notion in load_notions(cours_dir):
        nid = notion.get("id", "?")
        label = f"{chapter_id}::{nid}"
        definition = (notion.get("definition") or "").strip()
        intro = (notion.get("intro") or "").strip()
        objectif = (notion.get("objectif") or "").strip()
        erreurs = notion.get("erreursFrequentes") or []

        if definition and INDICE_RE.search(definition):
            findings["indice_definition"].append((label, definition[:90]))
        if intro and GENERIC_INTRO_RE.search(intro):
            findings["generic_intro"].append((label, intro[:90]))
        if objectif and GENERIC_OBJECTIF_RE.search(objectif):
            findings["generic_objectif"].append((label, objectif[:90]))
        if not erreurs:
            findings["empty_erreurs"].append(label)
        if definition:
            definition_owners[definition].append(label)

    for definition, owners in definition_owners.items():
        if len(owners) > 1:
            findings["duplicate_definition"].append((definition[:90], owners))

    return findings


def default_dirs() -> list[Path]:
    """Dossiers de cours de TOUS les programmes déclarés (publiés ou en
    préparation), lus dans curriculum_registry — jamais une liste codée en
    dur : l'ancienne liste pointait vers webapp/static/data/cours*/, vidés
    depuis le déplacement des cours dans webapp/course_content/ (chantier
    "Répartition du contenu des cours par plan"), si bien que cet audit
    parcourait des dossiers inexistants et annonçait 0 problème."""
    import curriculum_registry

    return [
        p.courses_dir for p in curriculum_registry.CURRICULUM_REGISTRY_ALL.values()
        if p.courses_dir is not None
    ]


def resolve_target(arg: str) -> Path:
    """Un argument est soit un id de programme du registre (ex. "troisieme"),
    soit un chemin de dossier."""
    import curriculum_registry

    profile = curriculum_registry.CURRICULUM_REGISTRY_ALL.get(arg)
    if profile is not None and profile.courses_dir is not None:
        return profile.courses_dir
    return Path(arg)


def main(argv: list[str]) -> int:
    dirs = [resolve_target(a) for a in argv] if argv else default_dirs()

    total = defaultdict(int)
    missing = []
    for d in dirs:
        print(f"\n=== {d} ===")
        if not d.is_dir():
            # Jamais un "0 problème" silencieux sur un dossier absent.
            print("  [ERREUR] dossier introuvable — rien n'a été audité")
            missing.append(d)
            continue
        findings = audit_dir(d)
        for key in ("indice_definition", "generic_intro", "generic_objectif", "empty_erreurs"):
            items = findings[key]
            print(f"  {key}: {len(items)}")
            for item in items[:5]:
                print(f"    - {item}")
            if len(items) > 5:
                print(f"    ... (+{len(items) - 5})")
            total[key] += len(items)
        dup = findings["duplicate_definition"]
        print(f"  duplicate_definition (groupes): {len(dup)}")
        for text, owners in dup[:5]:
            print(f"    - {text!r} partagé par {len(owners)} notions: {owners[:4]}{'...' if len(owners) > 4 else ''}")
        total["duplicate_definition_groups"] += len(dup)

    print("\n=== TOTAL ===")
    for key, count in total.items():
        print(f"  {key}: {count}")
    if missing:
        print(f"\n{len(missing)} dossier(s) introuvable(s) : {', '.join(str(d) for d in missing)}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
