# 01_extract_pdfs.py
# Ce script extrait le texte des fichiers PDF situés dans le dossier "Chapitres"
# et enregistre ce texte nettoyé dans des fichiers .txt dans le dossier "texts".

import fitz  # PyMuPDF : outil pour ouvrir et lire le contenu des fichiers PDF.
import os   # Bibliothèque standard pour gérer fichiers et dossiers.
import re   # Expressions régulières pour nettoyer le texte extrait.

# Dossier source contenant les fichiers PDF à traiter.
# Le script lit chaque fichier .pdf dans ce dossier.
CHAPITRES_DIR = "Chapitres"
# Dossier de sortie dans lequel chaque PDF sera transformé en .txt.
OUTPUT_DIR = "texts"
# Crée le dossier de sortie si nécessaire, sans erreur si le dossier existe déjà.
os.makedirs(OUTPUT_DIR, exist_ok=True)

def clean_text(text: str) -> str:
    """Nettoie le texte brut extrait d'un PDF.

    Le texte issu d'un PDF contient souvent des éléments indésirables :
    - plusieurs sauts de ligne consécutifs (espaces verticaux inutiles),
    - séquences d'espaces ou de tabulations répétées,
    - numéros de page isolés qui apparaissent seuls sur une ligne.

    Cette fonction transforme ces artefacts en un texte plus lisible.
    """
    # Remplace les blocs de 3 sauts de ligne ou plus par seulement 2 sauts de ligne.
    # Cela évite des espaces trop grands entre les paragraphes.
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Remplace les espaces/tabs répétés par un seul espace.
    # Ex : "Bonjour    monde" devient "Bonjour monde".
    text = re.sub(r'[ \t]{2,}', ' ', text)

    # Supprime les lignes qui ne contiennent qu'un nombre entier.
    # Les numéros de page sont souvent extraits comme une ligne indépendante.
    text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)

    # Supprime les espaces en début et fin de chaîne.
    return text.strip()

def extract_pdf(pdf_path: str, output_path: str):
    """Lit un PDF page par page, assemble le texte, le nettoie et l'écrit en .txt."""
    # Ouvre le fichier PDF pour extraire son contenu.
    doc = fitz.open(pdf_path)
    full_text = []

    # Parcourt chaque page du document.
    for page_num, page in enumerate(doc):
        # Récupère le texte brut de la page.
        # Le mode "text" préserve l'ordre de lecture des paragraphes.
        text = page.get_text("text")
        # Ajoute un en-tête de page pour repérer le début de chaque page.
        full_text.append(f"--- PAGE {page_num + 1} ---\n{text}")

    # Ferme le document PDF lorsque l'extraction est terminée.
    doc.close()

    # Concatène le texte de toutes les pages en une seule chaîne.
    combined = "\n".join(full_text)
    # Lance le nettoyage pour supprimer les artefacts de PDF.
    combined = clean_text(combined)

    # Sauvegarde le texte nettoyé dans le fichier de sortie.
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(combined)

    # Affiche un message de progression incluant le nom du fichier traité
    # et le nombre de caractères de texte généré.
    print(f"  ✓ {os.path.basename(pdf_path)} → {output_path} ({len(combined):,} chars)")

# Recherche de tous les fichiers PDF dans le dossier source.
# La liste est triée pour garantir un ordre de traitement déterministe.
pdf_files = sorted([f for f in os.listdir(CHAPITRES_DIR) if f.endswith(".pdf")])
print(f"Found {len(pdf_files)} PDFs:")
for pdf_file in pdf_files:
    pdf_path = os.path.join(CHAPITRES_DIR, pdf_file)
    txt_name = os.path.splitext(pdf_file)[0] + ".txt"
    output_path = os.path.join(OUTPUT_DIR, txt_name)
    extract_pdf(pdf_path, output_path)

print("\nDone! Check the 'texts/' folder.")