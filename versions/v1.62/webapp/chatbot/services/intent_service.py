"""
Classification d'intention pédagogique — Intent Engine v2 (Response Engine v2).
Appelée AVANT tout appel LLM (conversation_manager.py) pour détecter ce que
demande l'élève, par mots-clés/regex (pas de ML) sur un ensemble de phrases
déclencheuses curées, complété par un REPLI FLOU (difflib, même approche que
canonical_ids.py) qui compare le message entier aux phrases déclencheuses
connues — c'est ce repli flou qui permet de couvrir "plusieurs centaines de
formulations" réelles sans écrire des centaines de regex à la main : une
formulation jamais vue mais proche d'une phrase connue est reconnue par
similarité, pas seulement par correspondance exacte.

Repère aussi le chapitre/la notion visée par recherche floue déjà éprouvée
(search_service — aucune logique de correspondance dupliquée ici), et une
éventuelle quantité demandée ("plusieurs exercices", "3 exemples").

Détecte aussi les demandes incompréhensibles ("aaaa", "......") pour
court-circuiter le LLM avec une réponse de clarification fixe plutôt que de
laisser le fournisseur IA halluciner une réponse hors-sujet.
"""
import difflib
import re
import unicodedata

from . import search_service


def _fold_accents(text):
    """Aplatit les accents (é -> e) avant comparaison difflib — sans ça,
    "résumé" vs "resume" (0.67) reste sous le seuil de tolérance par mot
    (0.75) à cause des seuls caractères accentués, alors que le mot est
    identique sans l'accent. Trouvé par test empirique (canonical_ids.py
    fait déjà ce repli pour les mêmes raisons, voir _normalize_label)."""
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))

EXERCICE = "exercice"
EXEMPLE = "exemple"
EXPLICATION = "explication"
QUIZ = "quiz"
FICHE = "fiche"
CORRECTION = "correction"
RESTART_BASICS = "restart_basics"
FORMULE = "formule"
PROGRESSION = "progression"
STATISTIQUE = "statistique"
DASHBOARD = "dashboard"
PROFIL = "profil"
PARAMETRES = "parametres"
SERIE = "serie"
# Nouvelles intentions (Intent Engine v2, Response Engine v2) :
DEFINITION = "definition"
COURS = "cours"
RESUME = "resume"
METHODE = "methode"
PROPRIETE = "propriete"
DEMONSTRATION = "demonstration"
INDICE = "indice"
RAPPEL = "rappel"
REVISION = "revision"
REFORMULATION = "reformulation"
NONE_INTENT = "none"
UNCLEAR = "unclear"

# Intents entièrement répondables localement (variable_resolver.py +
# response_composer.py, Phase O/P/Q) — aucune donnée nécessaire ne dépend
# d'un appel LLM, la variable existe toujours (même à zéro).
LOCAL_DATA_INTENTS = {PROGRESSION, STATISTIQUE, DASHBOARD, PROFIL, PARAMETRES, SERIE}

CLARIFICATION_MESSAGE = (
    "Je n'ai pas bien compris votre demande.\n\n"
    "Pouvez-vous reformuler votre question ?\n\n"
    "Vous pouvez par exemple me demander :\n"
    "- expliquer une notion ;\n"
    "- proposer un exercice ;\n"
    "- corriger un exercice ;\n"
    "- créer une série d'entraînement."
)

_GIBBERISH_PUNCT_RE = re.compile(r"^[^a-zàâäéèêëïîôöùûüç0-9]+$", re.IGNORECASE)
_REPEATED_CHAR_RE = re.compile(r"^(.)\1{3,}$")
_VOWEL_RE = re.compile(r"[aeiouyàâäéèêëïîôöùûü]", re.IGNORECASE)
_LETTERS_RE = re.compile(r"[^a-zàâäéèêëïîôöùûüç]", re.IGNORECASE)

RESTART_RE = re.compile(
    r"(j'ai rien compris|je n'ai rien compris|j'y comprends rien|je ne comprends rien|"
    r"reprend(?:re|s)?.{0,15}(d[ée]but|base)|repartir.{0,10}(z[ée]ro|base))",
    re.IGNORECASE,
)
QUIZ_RE = re.compile(
    r"(interroge[- ]moi|pose[- ]moi des questions|fais[- ]moi (un )?quiz|teste[- ]moi|questionne[- ]moi)",
    re.IGNORECASE,
)
CORRECTION_RE = re.compile(
    r"(corrige (mon|cet|ce)|correction de|est[- ]ce que c'est juste|v[ée]rifie ma r[ée]ponse)",
    re.IGNORECASE,
)
FICHE_RE = re.compile(
    r"(fais[- ]moi (une )?fiche|fiche de synth[eè]se|fiche r[ée]cap)",
    re.IGNORECASE,
)
EXERCICE_RE = re.compile(
    r"(donne(?:-moi)? (?:un |des |plusieurs |plusieurs?\s*\d+\s*|\d+\s*)?exercices?|"
    r"exercices? (?:\w+\s+){0,3}sur|propose[- ]moi (?:un |des |plusieurs )?exercices?|"
    r"entra[iî]ne[- ]moi|exercice[s]? d'entra[iî]nement)",
    re.IGNORECASE,
)
EXEMPLE_RE = re.compile(
    r"(donne(?:-moi)? (?:un |des |plusieurs |\d+\s*)?exemples?|"
    r"exemples? (?:\w+\s+){0,3}sur|montre[- ]moi (?:un |des |plusieurs )?exemples?)",
    re.IGNORECASE,
)
# REFORMULATION doit être vérifiée AVANT EXPLICATION : "explique autrement"
# matche aussi `^explique\b` (EXPLICATION_RE) — la reformulation est plus
# spécifique et doit l'emporter (voir _INTENT_PATTERNS, ordre de priorité).
REFORMULATION_RE = re.compile(
    r"(explique(?:[- ]moi)? autrement|reformule|dis[- ]le autrement|d'une autre fa[çc]on|"
    r"autrement dit|d'une mani[eè]re diff[ée]rente)",
    re.IGNORECASE,
)
EXPLICATION_RE = re.compile(r"(explique[- ]moi|^explique\b|comment (fonctionne|marche))", re.IGNORECASE)
FORMULE_RE = re.compile(r"(quelle est la formule|donne(?:-moi)? la formule|formule de)", re.IGNORECASE)
DEFINITION_RE = re.compile(
    # "qu[e']" : tolère l'élision grammaticale devant une voyelle
    # ("qu'est-ce qu'une puissance", pas "qu'est-ce que une puissance").
    r"(c'est quoi|qu'est[- ]ce qu[e']|d[ée]finition de|d[ée]fini[st]|que veut dire)",
    re.IGNORECASE,
)
COURS_RE = re.compile(
    r"(donne(?:-moi)? le cours|montre[- ]moi le cours|(?:je veux voir|voir) le cours|cours (?:complet |entier )?sur)",
    re.IGNORECASE,
)
RESUME_RE = re.compile(
    r"(r[ée]sume[- ]moi|fais[- ]moi (?:un )?r[ée]sum[ée]|r[ée]sum[ée] de|en r[ée]sum[ée])",
    re.IGNORECASE,
)
METHODE_RE = re.compile(
    r"(quelle (?:est la )?m[ée]thode|comment (?:faire pour )?r[ée]sou(?:s|dre)|comment on fait|"
    r"quelle est la d[ée]marche|quelles sont les [ée]tapes|comment proc[ée]der)",
    re.IGNORECASE,
)
PROPRIETE_RE = re.compile(r"(quelle est la propri[ée]t[ée]|propri[ée]t[ée]s? de)", re.IGNORECASE)
DEMONSTRATION_RE = re.compile(r"(d[ée]montre(?:r|-moi)?|d[ée]monstration de|prouve(?:r|-moi)? que|preuve de)", re.IGNORECASE)
INDICE_RE = re.compile(
    r"(donne(?:-moi)? un indice|un (?:petit )?indice|aide[- ]moi un peu|"
    r"sans (?:me )?donner la r[ée]ponse)",
    re.IGNORECASE,
)
RAPPEL_RE = re.compile(r"(rappelle[- ]moi|petit rappel sur|rappel de cours)", re.IGNORECASE)
REVISION_RE = re.compile(
    r"(je veux r[ée]viser|r[ée]vision de|aide[- ]moi [aà] r[ée]viser|"
    r"pr[ée]pare[- ]moi (?:pour|au) (?:le |un )?(?:contr[ôo]le|examen|brevet|bac))",
    re.IGNORECASE,
)

QUANTITE_MOTS = {"deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "plusieurs": 3, "quelques": 3}
QUANTITE_RE = re.compile(
    r"\b(\d+|deux|trois|quatre|cinq|plusieurs|quelques)\b(?:\s+\w+){0,2}\s+(exercices?|exemples?)",
    re.IGNORECASE,
)

# Phrases déclencheuses canoniques par intention — utilisées pour le REPLI
# FLOU (voir _fuzzy_intent) quand aucune regex de _INTENT_PATTERNS ne
# correspond. Reprend les triggers déjà couverts par les regex ci-dessus :
# le repli flou généralise autour de ces phrases (fautes de frappe,
# reformulations proches), il n'ajoute pas de nouveaux déclencheurs.
_FUZZY_TRIGGER_PHRASES = {
    DEFINITION: ["c'est quoi", "qu'est-ce que", "définition de", "que veut dire"],
    COURS: ["donne-moi le cours", "montre-moi le cours", "je veux voir le cours sur"],
    RESUME: ["résume-moi", "fais-moi un résumé", "en résumé", "faire un résumé"],
    METHODE: ["quelle est la méthode", "comment résoudre", "quelles sont les étapes"],
    PROPRIETE: ["quelle est la propriété", "propriété de"],
    DEMONSTRATION: ["démontre que", "démonstration de", "prouve que"],
    EXEMPLE: ["donne-moi un exemple", "montre-moi un exemple", "montrer un exemple"],
    EXERCICE: ["donne-moi un exercice", "propose-moi un exercice", "entraîne-moi", "exercice d'entraînement"],
    CORRECTION: ["corrige mon exercice", "vérifie ma réponse"],
    INDICE: ["donne-moi un indice", "aide-moi un peu"],
    QUIZ: ["interroge-moi", "pose-moi des questions", "teste-moi"],
    RAPPEL: ["rappelle-moi", "petit rappel sur"],
    REVISION: ["je veux réviser", "aide-moi à réviser"],
    REFORMULATION: ["explique autrement", "reformule", "dis-le autrement"],
    FICHE: ["fais-moi une fiche", "fiche de synthèse"],
    FORMULE: ["quelle est la formule", "formule de"],
    EXPLICATION: ["explique-moi", "comment ça marche"],
}
FUZZY_CUTOFF = 0.7
_WORD_MATCH_CUTOFF = 0.75  # tolérance par mot (singulier/pluriel, petite faute de frappe)

# Mots vides à ignorer dans la couverture de phrase (_phrase_coverage) : des
# mots aussi courts/fréquents que "que"/"ce"/"un" apparaissent dans presque
# toute phrase française et faussaient la mesure (ex: "qu'est-ce que" était
# détecté à 100% de couverture dans n'importe quelle phrase contenant "que",
# même sans rapport avec une définition — trouvé par test empirique).
_FUZZY_STOPWORDS = {
    "que", "qu'", "ce", "un", "une", "de", "la", "le", "les", "des", "sur",
    "moi", "tu", "toi", "je", "à", "et", "du", "en",
}

# Intents "données locales" (Phase O) — répondus depuis le vrai profil de
# l'élève (variable_resolver.py), jamais par le LLM. Les phrases ci-dessous
# reprennent explicitement les exemples du cahier des charges.
PROGRESSION_RE = re.compile(
    r"(quels? chapitres?.*(revoir|maitris)|quelle? est ma progression|ma progression|"
    r"meilleur chapitre|pire chapitre|chapitre le plus faible)",
    re.IGNORECASE,
)
STATISTIQUE_RE = re.compile(
    r"(mes? statistiques?|mon accuracy|ma pr[ée]cision|depuis combien de temps|"
    r"combien de temps (ai-je |j'ai )?travaill|exercices? (ai-je )?rat[ée]s?|exercices? (a |[àa] )?refaire)",
    re.IGNORECASE,
)
DASHBOARD_RE = re.compile(r"(tableau de bord|dashboard|derniers? chapitres?)", re.IGNORECASE)
PROFIL_RE = re.compile(r"(mon profil|mes favoris|niveau actuel|qui suis-je)", re.IGNORECASE)
PARAMETRES_RE = re.compile(r"(mes param[eè]tres|r[ée]glages actifs)", re.IGNORECASE)
SERIE_RE = re.compile(r"(mes s[ée]ries|s[ée]rie en cours|s[ée]rie actuelle)", re.IGNORECASE)

SIMPLIFY_RE = re.compile(
    r"(comme [aà] un [ée]l[eè]ve en difficult[ée]|explique(?:-moi)? simplement|plus simplement|vulgarise)",
    re.IGNORECASE,
)
DIFFICULT_RE = re.compile(r"\b(difficile|dur|cors[ée]|compliqu[ée])\b", re.IGNORECASE)
EASY_RE = re.compile(r"\b(facile|simple|basique)\b", re.IGNORECASE)

# Ordre de priorité : le premier motif qui correspond l'emporte (une demande
# de reprise des bases prime sur une simple demande d'explication, etc.)
_INTENT_PATTERNS = [
    (RESTART_BASICS, RESTART_RE),
    (PROGRESSION, PROGRESSION_RE),
    (STATISTIQUE, STATISTIQUE_RE),
    (DASHBOARD, DASHBOARD_RE),
    (PROFIL, PROFIL_RE),
    (PARAMETRES, PARAMETRES_RE),
    (SERIE, SERIE_RE),
    (QUIZ, QUIZ_RE),
    (INDICE, INDICE_RE),
    (CORRECTION, CORRECTION_RE),
    (DEMONSTRATION, DEMONSTRATION_RE),
    (PROPRIETE, PROPRIETE_RE),
    (REFORMULATION, REFORMULATION_RE),
    (RESUME, RESUME_RE),
    (FICHE, FICHE_RE),
    (COURS, COURS_RE),
    (METHODE, METHODE_RE),
    (EXERCICE, EXERCICE_RE),
    (EXEMPLE, EXEMPLE_RE),
    (FORMULE, FORMULE_RE),
    (DEFINITION, DEFINITION_RE),
    (RAPPEL, RAPPEL_RE),
    (REVISION, REVISION_RE),
    (EXPLICATION, EXPLICATION_RE),
]


def _is_gibberish(text):
    t = text.strip()
    if len(t) < 2:
        return True
    if _GIBBERISH_PUNCT_RE.match(t):
        return True
    if _REPEATED_CHAR_RE.match(t.lower()):
        return True
    letters = _LETTERS_RE.sub("", t.lower())
    if len(letters) >= 4 and not _VOWEL_RE.search(letters):
        return True
    return False


def _detect_difficulty(text):
    if DIFFICULT_RE.search(text):
        return "hard"
    if EASY_RE.search(text):
        return "easy"
    return None


def _detect_quantity(text):
    """Quantité demandée ("3 exercices", "plusieurs exemples", "quelques
    exercices") — None si aucune quantité explicite (comportement par défaut :
    un seul, inchangé). Distinct de l'intention elle-même : EXERCICE_RE/
    EXEMPLE_RE reconnaissent déjà "plusieurs"/un nombre comme déclencheur,
    mais ne disaient jusqu'ici jamais COMBIEN."""
    m = QUANTITE_RE.search(text)
    if not m:
        return None
    token = m.group(1).lower()
    if token.isdigit():
        return min(int(token), 10)  # borne raisonnable, évite une demande absurde ("500 exercices")
    return QUANTITE_MOTS.get(token)


def _phrase_coverage(text_words, phrase_lower):
    """Proportion des mots SIGNIFICATIFS de `phrase_lower` (hors
    _FUZZY_STOPWORDS) retrouvés (exactement ou à une petite faute de frappe
    près) N'IMPORTE OÙ dans `text_words` — contrairement à une comparaison de
    chaînes complètes (difflib.SequenceMatcher.ratio sur tout le message),
    cette mesure ne s'effondre pas quand le message est bien plus long que la
    phrase déclencheuse (ex: une phrase polie de 20 mots contenant "expliquer
    autrement" au milieu). Exclure les mots vides est nécessaire : sans ça,
    une phrase courte comme "qu'est-ce que" était mesurée à 100% de
    couverture dans N'IMPORTE QUELLE phrase contenant juste "que" (mot
    grammatical omniprésent) — trouvé par test empirique, pas théorique."""
    phrase_words = [_fold_accents(w) for w in phrase_lower.split() if w not in _FUZZY_STOPWORDS]
    if len(phrase_words) < 2:
        return 0.0  # phrase trop courte/générique une fois les mots vides ôtés : pas fiable en flou
    matched = 0
    for pw in phrase_words:
        best = max((difflib.SequenceMatcher(None, pw, tw).ratio() for tw in text_words), default=0.0)
        if best >= _WORD_MATCH_CUTOFF:
            matched += 1
    return matched / len(phrase_words)


def _fuzzy_intent(text):
    """Repli flou : mesure la couverture de chaque phrase déclencheuse connue
    (_FUZZY_TRIGGER_PHRASES) dans le message — reconnaît une formulation
    jamais vue mais proche d'un déclencheur connu (paraphrase, politesse
    autour, faute de frappe), là où les regex de _INTENT_PATTERNS exigent une
    correspondance exacte. Même esprit que canonical_ids._fuzzy_topic_id
    (difflib, pas de ML), adapté à des phrases entières plutôt qu'à un seul
    nom de notion."""
    text_words = [_fold_accents(w) for w in text.lower().split()]
    best_intent, best_score = None, 0.0
    for intent, phrases in _FUZZY_TRIGGER_PHRASES.items():
        for phrase in phrases:
            score = _phrase_coverage(text_words, phrase.lower())
            if score > best_score:
                best_intent, best_score = intent, score
    return best_intent if best_score >= FUZZY_CUTOFF else None


def _detect_chapter(text, context_summary):
    """Chapitre/notion visé par la demande — réutilise la recherche déjà
    éprouvée de search_service (TF-IDF + repli flou), jamais de logique de
    correspondance dupliquée ici. Repli sur le chapitre en cours de l'élève
    si rien n'est trouvé dans le texte, plutôt que de deviner au hasard."""
    matches = search_service.search(text, scope=[search_service.SCOPE_COURS], limit=1)
    if matches and matches[0]["score"] >= search_service.TFIDF_WEAK_THRESHOLD:
        return matches[0]["chapter_id"], matches[0]["notion_id"]
    if context_summary and context_summary.get("chapters_in_progress"):
        return context_summary["chapters_in_progress"][0], None
    return None, None


def classify(user_message, context_summary=None):
    """Retourne {intent, chapter_id, notion_id, difficulty, simplify, quantity}.
    `intent` vaut NONE_INTENT si aucun mot-clé pédagogique n'est reconnu (la
    question reste ouverte, traitée normalement par le LLM) — à ne pas
    confondre avec UNCLEAR (demande incompréhensible, court-circuitée avant
    tout appel IA). `quantity` : nombre d'exercices/exemples demandés
    explicitement ("3 exercices", "plusieurs exemples"), None sinon (un seul,
    comportement par défaut inchangé)."""
    text = (user_message or "").strip()
    if _is_gibberish(text):
        return {
            "intent": UNCLEAR, "chapter_id": None, "notion_id": None,
            "difficulty": None, "simplify": False, "quantity": None,
        }

    intent = NONE_INTENT
    matched = None
    for key, pattern in _INTENT_PATTERNS:
        m = pattern.search(text)
        if m:
            intent = key
            matched = m
            break

    # Repli flou (Intent Engine v2) : aucune regex n'a matché -> cherche une
    # formulation proche d'un déclencheur connu avant d'abandonner sur
    # NONE_INTENT (question ouverte, traitée par le LLM).
    if intent == NONE_INTENT:
        fuzzy = _fuzzy_intent(text)
        if fuzzy:
            intent = fuzzy

    # Cherche le chapitre seulement sur ce qui reste une fois la formule
    # déclencheuse retirée ("donne-moi un exercice" -> "") : sinon une
    # requête sans sujet réel se fait attribuer un chapitre au hasard par le
    # repli flou (comparaison de lettres sur des mots génériques).
    topic_text = text
    if matched:
        topic_text = (text[:matched.start()] + " " + text[matched.end():]).strip()

    chapter_id, notion_id = _detect_chapter(topic_text, context_summary)
    return {
        "intent": intent,
        "chapter_id": chapter_id,
        "notion_id": notion_id,
        "difficulty": _detect_difficulty(text),
        "simplify": bool(SIMPLIFY_RE.search(text)),
        "quantity": _detect_quantity(text),
    }
