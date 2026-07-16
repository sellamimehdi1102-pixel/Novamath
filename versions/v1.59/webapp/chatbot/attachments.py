"""
Extraction de texte pour les pièces jointes du chatbot (PDF). Le texte extrait
est simplement inséré dans le message de l'élève avant envoi — aucun contenu
de fichier n'est stocké côté serveur au-delà du traitement de la requête.

Les images ne sont volontairement PAS traitées ici : le fournisseur IA par
défaut (Ollama/Mistral) est un modèle texte, sans capacité de vision, et
aucune bibliothèque d'OCR n'est installée sur ce projet. Mieux vaut ne pas
prétendre analyser une image que de le faire silencieusement mal — voir
chatbot.js, qui informe clairement l'élève de cette limite.
"""
import fitz  # PyMuPDF

MAX_PDF_PAGES = 30
MAX_PDF_CHARS = 6000


class AttachmentError(ValueError):
    pass


def extract_pdf_text(file_bytes):
    """Renvoie le texte extrait d'un PDF (tronqué à MAX_PDF_CHARS). Lève
    AttachmentError si le fichier n'est pas un PDF exploitable."""
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        raise AttachmentError("Ce fichier ne semble pas être un PDF valide.") from exc

    if doc.page_count == 0:
        raise AttachmentError("Ce PDF ne contient aucune page.")
    if doc.page_count > MAX_PDF_PAGES:
        raise AttachmentError(f"Ce PDF a trop de pages (max {MAX_PDF_PAGES}).")

    pages_text = []
    for page in doc:
        pages_text.append(page.get_text())
    doc.close()

    text = "\n".join(pages_text).strip()
    if not text:
        raise AttachmentError(
            "Aucun texte n'a pu être extrait de ce PDF (probablement une image scannée sans OCR)."
        )
    truncated = len(text) > MAX_PDF_CHARS
    return text[:MAX_PDF_CHARS], truncated
