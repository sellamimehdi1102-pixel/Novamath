"""Utilitaires des anciennes pages /maths-<classe> (supprimées, désormais
redirigées par server.py) : correspondance URL -> classe et titres de chapitres
lisibles. Aucun contenu de page n'est plus rendu ici."""

import json
import re
from pathlib import Path

# Titres de secours des chapitres (« Chapitre 3 » → « Dérivation : ... »),
# déduits des notions — même table que l'application (cartes de chapitres,
# lecteur de cours) : lue directement dans ce fichier JS pour ne jamais
# maintenir deux copies divergentes.
_CHAPTER_TITLE_JS = Path(__file__).parent / "static" / "js" / "chapterTitleByNotions.js"
_GENERIC_TITLE_RE = re.compile(r"^chapitre\s+\d+$", re.IGNORECASE)
_NOTION_THEME_ENTRY_RE = re.compile(r'^\s*("(?:[^"\\]|\\.)*")\s*:\s*("(?:[^"\\]|\\.)*")\s*,?\s*$')
_notion_theme_cache = None


def _notion_theme():
    global _notion_theme_cache
    if _notion_theme_cache is None:
        source = _CHAPTER_TITLE_JS.read_text(encoding="utf-8")
        start = source.index("const NOTION_THEME = {")
        end = source.index("};", start)
        table = {}
        for line in source[start:end].splitlines()[1:]:
            match = _NOTION_THEME_ENTRY_RE.match(line)
            if match:
                table[json.loads(match.group(1))] = json.loads(match.group(2))
        _notion_theme_cache = table
    return _notion_theme_cache


def resolve_chapter_title(raw_title, notion_labels):
    """Port fidèle de chapterTitleByNotions.js::resolveChapterTitle : garde le
    titre fourni s'il n'est pas générique, sinon le thème le plus fréquent
    parmi les notions (premier rencontré en cas d'égalité)."""
    if raw_title and not _GENERIC_TITLE_RE.match(raw_title):
        return raw_title
    themes = _notion_theme()
    counts = {}
    for label in notion_labels or []:
        theme = themes.get(label)
        if theme:
            counts[theme] = counts.get(theme, 0) + 1
    best, best_count = None, 0
    for theme, count in counts.items():
        if count > best_count:
            best, best_count = theme, count
    return best or raw_title


# Anciennes URL publiques -> identifiant de classe (curriculum_registry.py).
SLUG_TO_CLASS_LEVEL = {
    "maths-quatrieme": "quatrieme",
    "maths-troisieme": "troisieme",
    "maths-seconde": "seconde",
    "maths-premiere-specialite": "premiere",
    "maths-premiere-specifique": "premiere_specifique",
}
