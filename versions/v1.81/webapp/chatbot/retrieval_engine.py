"""
Moteur de recherche interne générique (TF-IDF + similarité cosinus,
scikit-learn — déjà une dépendance du projet, pas de base vectorielle à
héberger). Ce module ne connaît AUCUNE donnée métier NovaMath : il indexe des
"documents" (dicts arbitraires avec un champ "text") fournis par un appelant
(voir knowledge_engine.py, qui sait lui QUOI indexer — cours, exercices,
erreurs fréquentes...) et renvoie les plus pertinents pour une requête. Seule
responsabilité : chercher vite, sans jamais renvoyer tout le corpus.
"""
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# scikit-learn ne fournit pas de liste de mots vides français prête à l'emploi
# (seulement 'english') : sans elle, des mots très fréquents ("de", "la",
# "un"...) peuvent dominer la similarité sur un corpus de quelques centaines
# de documents et fausser le classement au profit du document le plus long.
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

_TOKEN_RE = re.compile(r"(?u)\b\w\w+\b")


def _light_stem(token):
    """Normalisation légère (pas un vrai stemmer linguistique) : gomme les
    pluriels/accords en genre les plus courants ("valeurs" -> "valeur",
    "absolues" -> "absolu") pour que la comparaison de tokens exacts de
    TF-IDF ne rate pas une correspondance évidente à cause d'un simple "s"
    ou "e" final. Sans cette normalisation, la requête "valeurs absolues" ne
    matchait aucun mot de la notion "La valeur absolue" (accord singulier)
    et se faisait devancer par un chapitre sans rapport partageant juste le
    mot "valeurs" — bug confirmé en testant le pipeline directement."""
    if len(token) > 4 and token.endswith("s") and not token.endswith("ss"):
        token = token[:-1]
    if len(token) > 4 and token.endswith("x"):
        token = token[:-1]
    if len(token) > 4 and token.endswith("e"):
        token = token[:-1]
    return token


def _tokenize(text):
    return [_light_stem(t) for t in _TOKEN_RE.findall(text)]


# Les mots vides doivent subir la même normalisation que les tokens du corpus
# (sinon "toujours" -> "toujour" côté document ne serait plus reconnu comme
# mot vide et polluerait la comparaison).
_STEMMED_STOPWORDS = sorted({_light_stem(w) for w in FRENCH_STOPWORDS})


class Index:
    """Index immuable une fois construit (voir build_index). Un appelant
    (knowledge_engine.py) le garde en cache tant que les documents source
    n'ont pas changé — reconstruire l'index est la seule opération coûteuse."""

    __slots__ = ("vectorizer", "matrix", "documents")

    def __init__(self, vectorizer, matrix, documents):
        self.vectorizer = vectorizer
        self.matrix = matrix
        self.documents = documents


def build_index(documents):
    """documents : liste de dicts contenant au moins un champ "text" (le
    reste des champs est libre — métadonnées propres à l'appelant, renvoyées
    telles quelles par search()). Renvoie un Index vide si `documents` est vide."""
    if not documents:
        return Index(None, None, [])
    vectorizer = TfidfVectorizer(
        strip_accents="unicode", lowercase=True,
        tokenizer=_tokenize, token_pattern=None,
        stop_words=_STEMMED_STOPWORDS,
    )
    matrix = vectorizer.fit_transform([d["text"] for d in documents])
    return Index(vectorizer, matrix, documents)


def search(index, query, top_k=3, min_score=0.12):
    """Renvoie jusqu'à `top_k` documents pertinents (score décroissant, champ
    "score" ajouté), en excluant ceux sous `min_score` (évite de renvoyer du
    bruit si la requête ne correspond à rien de précis dans le corpus)."""
    if index.vectorizer is None or not (query or "").strip():
        return []
    query_vec = index.vectorizer.transform([query])
    scores = cosine_similarity(query_vec, index.matrix).ravel()
    ranked = sorted(range(len(index.documents)), key=lambda i: scores[i], reverse=True)
    results = []
    for i in ranked[:top_k]:
        if scores[i] < min_score:
            break
        results.append({**index.documents[i], "score": float(scores[i])})
    return results
