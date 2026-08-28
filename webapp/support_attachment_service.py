"""
Pièces jointes des tickets de support — stockage sur disque, dans
data/support_attachments/<ticket_id>/<uuid>_<nom_original> (même racine
`data/` que db.DATA_DIR, jamais dans webapp/static/ qui est servi tel quel :
un fichier joint ne doit jamais être accessible par une URL devinable).

Architecture stricte, identique au reste du projet :

    server.py  →  support_attachment_service.py  →  support_service.py (métadonnées) / disque (contenu)

Validation stricte AVANT écriture sur disque : extension whitelistée et
taille maximale — un fichier refusé n'est jamais écrit, jamais partiellement
sauvegardé."""
import mimetypes
import uuid

from werkzeug.utils import secure_filename

import db
import support_service

ATTACHMENTS_DIR = db.DATA_DIR / "support_attachments"

# Types de fichiers utiles à un ticket de support (capture d'écran d'un bug,
# justificatif de paiement, log texte) — jamais un exécutable ni un script,
# volontairement restrictif.
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "pdf", "txt", "log", "csv"}
MAX_SIZE_BYTES = 5 * 1024 * 1024  # 5 Mo


class AttachmentRejected(ValueError):
    """Fichier refusé (extension interdite ou trop volumineux) — jamais une
    exception SQL/disque brute, toujours un message explicite pour
    l'utilisateur."""


def _extension(filename):
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def _content_type_for_extension(extension):
    """Content-Type dérivé UNIQUEMENT de l'extension déjà validée contre
    ALLOWED_EXTENSIONS (jamais du Content-Type envoyé par le navigateur, non
    fiable — voir save_attachment). "application/octet-stream" si le module
    standard `mimetypes` ne connaît pas l'extension (ex: .log)."""
    return mimetypes.guess_type(f"file.{extension}")[0] or "application/octet-stream"


def save_attachment(message_id, ticket_id, file_storage):
    """`file_storage` : objet Werkzeug FileStorage (request.files['...']).
    Valide extension + taille AVANT toute écriture disque, puis enregistre
    les métadonnées via support_service.add_attachment(). Lève
    AttachmentRejected si le fichier ne respecte pas la politique — jamais
    silencieusement ignoré."""
    original_filename = secure_filename(file_storage.filename or "")
    if not original_filename:
        raise AttachmentRejected("Nom de fichier invalide.")
    extension = _extension(original_filename)
    if extension not in ALLOWED_EXTENSIONS:
        raise AttachmentRejected(
            f"Type de fichier non autorisé ({extension or 'sans extension'}) — extensions acceptées : "
            f"{', '.join(sorted(ALLOWED_EXTENSIONS))}."
        )

    file_storage.stream.seek(0, 2)  # fin du flux, pour connaître la taille réelle sans tout charger en mémoire
    size_bytes = file_storage.stream.tell()
    file_storage.stream.seek(0)
    if size_bytes > MAX_SIZE_BYTES:
        raise AttachmentRejected(f"Fichier trop volumineux ({size_bytes} octets, max {MAX_SIZE_BYTES}).")
    if size_bytes == 0:
        raise AttachmentRejected("Fichier vide.")

    ticket_dir = ATTACHMENTS_DIR / str(ticket_id)
    ticket_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}_{original_filename}"
    stored_path = ticket_dir / stored_name
    file_storage.save(stored_path)

    relative_path = str(stored_path.relative_to(db.DATA_DIR))
    return support_service.add_attachment(
        message_id, original_filename, relative_path, size_bytes, _content_type_for_extension(extension),
    )


def resolve_attachment_path(attachment_id):
    """Chemin absolu réel sur disque pour `attachment_id`, ou None si
    l'attachment est inconnu OU si le fichier a disparu du disque (jamais une
    exception brute — l'appelant décide du 404)."""
    row = db.get_support_ticket_attachment(attachment_id)
    if row is None:
        return None
    absolute_path = db.DATA_DIR / row["stored_path"]
    if not absolute_path.is_file():
        return None
    return absolute_path, row["original_filename"], row["content_type"]
