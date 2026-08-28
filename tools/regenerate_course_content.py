"""
Outil d'aide à la mise à jour du module Cours quand un PDF de programme
change (Chapitres/Chapitre_N.pdf remplacé par une nouvelle version).

Ce script NE régénère PAS automatiquement le contenu pédagogique JSON
(webapp/static/data/cours/chapitre_N.json) : reconstruire un cours clair à
partir d'un PDF est un travail de rédaction (définitions, exemples,
méthodes...), pas une extraction mécanique — voir la section "Génération de
contenu" du plan du module Cours. Ce script se limite à la partie
mécanique et sûre : réextraire le texte brut du PDF pour servir de base de
relecture avant de mettre à jour le JSON à la main (ou avec l'aide de
Claude).

Usage :
    python tools/regenerate_course_content.py Chapitre_5
    python tools/regenerate_course_content.py --all
"""
import argparse
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHAPITRES_DIR = ROOT / "Chapitres"
TEXTS_DIR = ROOT / "texts"
# Chantier "Répartition du contenu des cours par plan" (2026-08-26) : déplacé
# hors de webapp/static/ (voir webapp/curriculum_registry.COURSE_CONTENT_DIR)
# — ce script ne lit/écrit jamais ce fichier lui-même (seulement affiché à
# l'utilisateur comme suggestion, voir plus bas), donc un chemin littéral
# reste suffisant ici plutôt qu'un import de curriculum_registry.
COURS_DATA_DIR = ROOT / "webapp" / "course_content" / "cours"


def clean_text(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"^\s*\d+\s*$", "", text, flags=re.MULTILINE)
    return text.strip()


def extract_pdf(chapter_id: str) -> Path:
    try:
        import fitz  # PyMuPDF, même dépendance que 01_extract_pdfs.py
    except ImportError:
        print("PyMuPDF (fitz) n'est pas installé. Installez-le avec : pip install pymupdf")
        sys.exit(1)

    pdf_path = CHAPITRES_DIR / f"{chapter_id}.pdf"
    if not pdf_path.exists():
        print(f"PDF introuvable : {pdf_path}")
        sys.exit(1)

    TEXTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = TEXTS_DIR / f"{chapter_id}.txt"

    doc = fitz.open(pdf_path)
    full_text = [f"--- PAGE {i + 1} ---\n{page.get_text('text')}" for i, page in enumerate(doc)]
    doc.close()

    combined = clean_text("\n".join(full_text))
    output_path.write_text(combined, encoding="utf-8")
    print(f"  ✓ {pdf_path.name} → {output_path} ({len(combined):,} caractères)")
    return output_path


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("chapter_id", nargs="?", help='Ex: "Chapitre_5"')
    parser.add_argument("--all", action="store_true", help="Réextraire les 12 chapitres")
    args = parser.parse_args()

    if not args.chapter_id and not args.all:
        parser.print_help()
        sys.exit(1)

    chapter_ids = (
        [f"Chapitre_{i}" for i in range(1, 13)]
        if args.all
        else [args.chapter_id]
    )

    for chapter_id in chapter_ids:
        txt_path = extract_pdf(chapter_id)
        num = chapter_id.replace("Chapitre_", "")
        json_path = COURS_DATA_DIR / f"chapitre_{num}.json"
        print(f"    → Relire {txt_path} et mettre à jour {json_path} à la main")
        print(f"      (ou demander à Claude : « relis {txt_path.name} et mets à jour {json_path.name} »)")

    print("\nRappel : le contenu JSON n'est jamais écrasé automatiquement par ce script.")


if __name__ == "__main__":
    main()
