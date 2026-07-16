"""
Moteur de récupération de contexte (RAG) : retrouve, dans les cours NovaMath
déjà écrits (webapp/static/data/cours/*.json — définitions, règles
importantes, méthodes, erreurs fréquentes, points à retenir), les notions
pertinentes pour la question de l'élève, SANS jamais envoyer les cours en
entier au LLM. Deux usages :

1. Question factuelle claire ("c'est quoi...", "définition de...") avec une
   correspondance forte sur une seule notion -> réponse instantanée directe,
   sans appel au LLM (voir conversation_manager.py, entre le Math Engine et
   le Provider Manager).
2. Sinon -> les meilleures notions retrouvées sont injectées comme contexte
   compact dans le prompt système (prompt_builder.py), pour que le LLM
   explique en s'appuyant sur le cours réel plutôt que d'inventer, tout en
   limitant fortement le nombre de tokens envoyés.

Implémentation volontairement simple (TF-IDF + similarité cosinus, scikit-learn
déjà une dépendance du projet) : pas de base vectorielle ni d'embeddings à
héberger, adapté à un corpus de quelques centaines de notions.
"""
import json
import re
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

COURS_DIR = Path(__file__).resolve().parent.parent / "static" / "data" / "cours"

# scikit-learn ne fournit pas de liste de mots vides français prête à l'emploi
# (seulement 'english') : sans elle, des mots très fréquents ("de", "la",
# "un"...) peuvent dominer la similarité sur ce corpus de quelques dizaines
# de notions et fausser le classement au profit du document le plus long.
FRENCH_STOPWORDS = [
    "au", "aux", "avec", "ce", "ces", "dans", "de", "des", "du", "elle", "en",
    "et", "eux", "il", "ils", "je", "la", "le", "les", "leur", "lui", "ma",
    "mais", "me", "même", "mes", "moi", "mon", "ne", "nos", "notre", "nous",
    "on", "ou", "où", "par", "pas", "pour", "qu", "que", "qui", "sa", "se",
    "ses", "son", "sur", "ta", "te", "tes", "toi", "ton", "tu", "un", "une",
    "vos", "votre", "vous", "c", "d", "j", "l", "à", "n", "s", "y", "été",
    "être", "avoir", "est", "sont", "ai", "as", "avons", "avez", "ont",
    "toujours", "jamais", "souvent", "quand", "comment", "pourquoi", "cette",
    "cet", "ceux", "celle", "celles", "leurs", "plus", "aussi", "alors",
]

DEFINITION_RE = re.compile(
    r"\b(c'est quoi|qu'est[- ]ce que|définition de|défini[st]|que veut dire|"
    r"rappelle[- ]moi|propriété de|règle de|théorème de|formule de)\b",
    re.IGNORECASE,
)

_index = None  # (vectorizer, matrix, notions) — construit une seule fois, en mémoire


def _load_notions():
    notions = []
    if not COURS_DIR.exists():
        return notions
    for path in sorted(COURS_DIR.glob("chapitre_*.json")):
        try:
            with open(path, "r", encoding="utf-8") as f:
                chapter = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        for notion in chapter.get("notions", []):
            text_parts = [
                notion.get("title", ""),
                notion.get("definition", ""),
                " ".join(notion.get("reglesImportantes", []) or []),
                " ".join(notion.get("aRetenir", []) or []),
                notion.get("astuce", "") or "",
            ]
            notions.append({
                "chapter_title": chapter.get("title", ""),
                "title": notion.get("title", ""),
                "definition": notion.get("definition", ""),
                "regles": notion.get("reglesImportantes", []) or [],
                "a_retenir": notion.get("aRetenir", []) or [],
                "erreurs": notion.get("erreursFrequentes", []) or [],
                "text": " ".join(p for p in text_parts if p),
            })
    return notions


def _get_index():
    global _index
    if _index is None:
        notions = _load_notions()
        if not notions:
            _index = (None, None, [])
        else:
            vectorizer = TfidfVectorizer(strip_accents="unicode", lowercase=True, stop_words=FRENCH_STOPWORDS)
            matrix = vectorizer.fit_transform([n["text"] for n in notions])
            _index = (vectorizer, matrix, notions)
    return _index


def search(query, top_k=3, min_score=0.12):
    """Renvoie jusqu'à `top_k` notions pertinentes (score décroissant), en
    excluant celles sous `min_score` (évite d'injecter du bruit si la
    question ne correspond à rien de précis dans les cours)."""
    vectorizer, matrix, notions = _get_index()
    if vectorizer is None or not (query or "").strip():
        return []
    query_vec = vectorizer.transform([query])
    scores = cosine_similarity(query_vec, matrix).ravel()
    ranked = sorted(range(len(notions)), key=lambda i: scores[i], reverse=True)
    results = []
    for i in ranked[:top_k]:
        if scores[i] < min_score:
            break
        results.append({**notions[i], "score": float(scores[i])})
    return results


def try_answer_definition(user_message):
    """Réponse directe (sans LLM) si la question est clairement une demande
    de définition/rappel ET qu'une notion correspond nettement mieux que les
    autres. Sinon None (le pipeline continue vers le contexte RAG + LLM)."""
    text = (user_message or "").strip()
    if not text or not DEFINITION_RE.search(text):
        return None
    # min_score=0 ici : on a besoin du DEUXIÈME résultat même faible pour
    # juger de l'ambiguïté (un filtrage précoce le ferait disparaître et
    # romprait la comparaison d'écart ci-dessous).
    matches = search(text, top_k=2, min_score=0.0)
    if not matches or matches[0]["score"] < 0.22:
        return None
    if len(matches) >= 2 and matches[0]["score"] - matches[1]["score"] < 0.12:
        return None  # ambigu entre deux notions -> laisser le LLM départager avec le contexte RAG
    best = matches[0]
    lines = [f"**{best['title']}** *({best['chapter_title']})*", "", best["definition"]]
    if best["regles"]:
        lines.append("")
        lines.append("**Règles importantes :**")
        lines.extend(f"- {r}" for r in best["regles"])
    if best["a_retenir"]:
        lines.append("")
        lines.append("**À retenir :**")
        lines.extend(f"- {r}" for r in best["a_retenir"])
    return "\n".join(lines)


def context_block(user_message, top_k=3):
    """Bloc de contexte compact à injecter dans le prompt système (RAG) :
    quelques notions pertinentes, jamais le cours entier. Chaîne vide si rien
    de pertinent n'est trouvé (le LLM répond alors sans grounding documentaire)."""
    matches = search(user_message, top_k=top_k)
    if not matches:
        return ""
    blocks = []
    for m in matches:
        block = [f"### {m['title']} ({m['chapter_title']})", m["definition"]]
        if m["regles"]:
            block.append("Règles : " + " ; ".join(m["regles"]))
        if m["erreurs"]:
            block.append("Erreurs fréquentes : " + " ; ".join(m["erreurs"]))
        blocks.append("\n".join(block))
    return "\n\n".join(blocks)
