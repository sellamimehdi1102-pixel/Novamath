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

from .. import retrieval_engine
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
# FOLLOWUP (chantier continuité conversationnelle, 2026-08-22) : messages de
# pure continuation ("continue", "pourquoi ?", "développe"...) qui ne portent
# ni mot-clé de sujet ni même une reformulation explicite (REFORMULATION vise
# "je n'ai pas compris"/"explique autrement" : une NOUVELLE explication de la
# même notion). FOLLOWUP vise la poursuite du raisonnement déjà entamé — la
# distinction compte pour pedagogy_templates.build_intent_instruction (ne pas
# répéter l'explication, la continuer).
FOLLOWUP = "followup"
NONE_INTENT = "none"
UNCLEAR = "unclear"

# Intents entièrement répondables localement (variable_resolver.py +
# response_composer.py, Phase O/P/Q) — aucune donnée nécessaire ne dépend
# d'un appel LLM, la variable existe toujours (même à zéro).
LOCAL_DATA_INTENTS = {PROGRESSION, STATISTIQUE, DASHBOARD, PROFIL, PARAMETRES, SERIE}

CLARIFICATION_MESSAGE = (
    "Je veux bien t'aider ! Peux-tu reformuler ta question ?\n\n"
    "Tu peux par exemple me demander :\n"
    "- d'expliquer une notion ;\n"
    "- de proposer un exercice ;\n"
    "- de corriger un exercice ;\n"
    "- de créer une série d'entraînement."
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
    r"exemples? (?:\w+\s+){0,3}sur|montre[- ]moi (?:un |des |plusieurs )?exemples?|"
    # Message NU ("un exemple", "encore un exemple", "un autre exemple"...) —
    # ancré sur TOUT le message (^...$), même principe que FOLLOWUP_RE/
    # REFORMULATION_RE("^encore$") : sans ce cas, "un exemple" seul (courant
    # après une explication) restait NONE_INTENT au lieu d'EXEMPLE (audit
    # global du routage pédagogique, 2026-08-22) — aucune instruction
    # "donne un exemple simple et résolu" (pedagogy_templates) n'était alors
    # injectée dans le prompt, alors même que le sujet restait correctement
    # conservé (Current Learning Context, indépendant de cette regex).
    r"^(?:un |des |plusieurs |encore un |encore |un autre |un second |autre )?exemples?\s*[.!?]*$)",
    re.IGNORECASE,
)
# REFORMULATION doit être vérifiée AVANT EXPLICATION : "explique autrement"
# matche aussi `^explique\b` (EXPLICATION_RE) — la reformulation est plus
# spécifique et doit l'emporter (voir _INTENT_PATTERNS, ordre de priorité).
#
# Couvre aussi les formulations d'incompréhension/de suivi ("réexplique",
# "je n'ai pas compris", "peux-tu détailler"...) — Current Learning Context
# (voir _detect_chapter/classify ci-dessous et conversation_manager.py) :
# ces messages ne portent plus aucun mot-clé de sujet, le chapitre/la notion
# doit alors venir du dernier sujet réellement discuté dans CETTE
# conversation, jamais d'une recherche floue sur "réexplique" qui pourrait
# accrocher n'importe quel autre chapitre au hasard (bug confirmé : la
# recherche TF-IDF sur des messages aussi courts/génériques peut dépasser le
# seuil de confiance tout en pointant vers une notion sans rapport).
# "encore" seul est volontairement ancré à TOUT le message (^...$) : le mot
# apparaît dans bien d'autres phrases ("encore un exercice") où il ne s'agit
# pas d'une demande de reformulation.
#
# "simplifie"/"plus simple" seuls (chantier "reformulations successives",
# 2026-08-22) : idem ancrés sur TOUT le message — "simple"/"simplifie"
# apparaissent aussi dans bien d'autres phrases ("un exercice plus simple")
# qui NE sont PAS une demande de reformulation et ne doivent pas matcher ici.
# Sans cet ancrage étroit, "simplifie" seul (mot pourtant très naturel après
# une explication) restait NONE_INTENT — ce qui cassait la chaîne de
# _detect_repeated_incomprehension (conversation_manager.py), qui exige que
# le tour PRÉCÉDENT soit déjà classé REFORMULATION/RESTART_BASICS pour
# déclencher l'instruction "change réellement d'approche" au tour suivant
# (bug confirmé : "simplifie" -> "explique plus simplement je n'ai rien
# compris" ne produisait jamais cette instruction, car "simplifie" seul
# était classé NONE_INTENT). SIMPLIFY_RE (`plus simplement`, `vulgarise`...)
# reste inchangée : ce n'est qu'un FLAG (simplify=True) sur l'intent déjà
# déterminé, pas un intent en soi, et ne suffit donc pas à réparer la chaîne.
REFORMULATION_RE = re.compile(
    r"(explique(?:[- ]moi)? autrement|reformule|dis[- ]le autrement|d'une autre fa[çc]on|"
    r"autrement dit|d'une mani[eè]re diff[ée]rente|"
    r"r[ée]explique(?:[- ]moi)?|explique(?:[- ]moi)? diff[ée]remment|"
    r"je n'ai pas (?:tout )?compris|j'ai pas (?:tout )?compris|"
    r"je ne comprends (?:pas|toujours pas)|je comprends pas|"
    r"peux[- ]tu (?:me )?recommencer|recommence(?:[- ]moi)?|"
    r"peux[- ]tu (?:me )?d[ée]tailler|d[ée]taille(?:[- ]moi)?|"
    r"^encore\s*[.!?]*$|^encore une fois\s*[.!?]*$|"
    r"^simplifie\s*[.!?]*$|^plus simple\s*[.!?]*$)",
    re.IGNORECASE,
)

# FOLLOWUP (chantier continuité conversationnelle, 2026-08-22) : messages de
# PURE continuation, sans reformulation ni mot-clé de sujet — ancrés sur TOUT
# le message (^...$) comme "encore" ci-dessus, pour la même raison : ces mots
# apparaissent aussi dans bien d'autres phrases ("continue ton exercice sur
# les fractions" NE doit PAS matcher ici, le sujet "les fractions" doit être
# traité normalement). Volontairement une liste FERMÉE de formulations très
# courtes (pas de repli flou dessus : "pourquoi" ou "continue" isolé sont trop
# courts pour une comparaison difflib fiable, voir _phrase_coverage).
FOLLOWUP_RE = re.compile(
    r"^(continue\s*\.?|d[ée]veloppe(?:\s+[çc]a)?(?:\s+davantage)?\s*\.?|"
    r"pourquoi(?:\s+[çc]a)?\s*\??|comment(?:\s+[çc]a)?(?:\s+se fait)?\s*\??)\s*$",
    re.IGNORECASE,
)

# Confirmation/refus nu, sans aucun autre mot — l'ambiguïté ("oui"/"non" seuls
# peuvent aussi bien confirmer une proposition du chatbot que ne rien vouloir
# dire hors contexte) est résolue par classify() à partir du DERNIER MESSAGE
# DE L'ASSISTANT (voir `last_assistant_message`), jamais par une recherche
# TF-IDF sur ce seul mot. Un "non" suivi d'autre texte ("non, je parle de...")
# NE matche PAS ici : c'est alors un message normal, dont le sujet est détecté
# comme d'habitude (changement de sujet explicite légitime).
_BARE_YES_RE = re.compile(r"^(oui|ouais|ok|d'accord)\s*[.!]*$", re.IGNORECASE)
_BARE_NO_RE = re.compile(r"^non\s*[.!]*$", re.IGNORECASE)

# Marqueurs explicites de changement de sujet volontaire — un élève qui les
# emploie sait qu'il change de notion ; combinés à une correspondance ne
# serait-ce que faible (TFIDF_WEAK_THRESHOLD), ce changement doit l'emporter
# sur le Current Learning Context sans exiger le score "fort" habituel (voir
# _detect_chapter : le score fort n'est là que pour départager une dérive
# accidentelle, jamais pour freiner une demande de changement assumée).
EXPLICIT_TOPIC_CHANGE_RE = re.compile(
    r"(maintenant,? (?:on|je|passons|explique)|passons? [aà]|"
    r"changeons? de (?:sujet|notion|chapitre)|change(?:ons)? de (?:sujet|notion|chapitre)|"
    r"je veux (?:plut[oô]t )?parler de|parlons plut[oô]t de|plut[oô]t (?:parler|discuter) de|"
    r"^non,)",
    re.IGNORECASE,
)
EXPLICATION_RE = re.compile(r"(explique[- ]moi|^explique\b|comment (fonctionne|marche))", re.IGNORECASE)
FORMULE_RE = re.compile(r"(quelle est la formule|donne(?:-moi)? la formule|formule de)", re.IGNORECASE)
DEFINITION_RE = re.compile(
    # "qu[e']" : tolère l'élision grammaticale devant une voyelle
    # ("qu'est-ce qu'une puissance", pas "qu'est-ce que une puissance"). Même
    # tolérance pour "d[e'’]" ("la définition d'une fonction", pas seulement
    # "la définition de la fonction") — sans cette variante, on ne pouvait
    # capturer l'élision qu'en s'appuyant accidentellement sur l'alternative
    # verbale ci-dessous, ce qui causait le bug documenté juste en dessous.
    #
    # "d[ée]fini[st]\b" (verbe : "il définit"/"tu définis") est ancré par un
    # \b final — SANS lui, ce fragment matche aussi au MILIEU d'un mot plus
    # long comme "définitions" (nom, pluriel) : une notion dont le TITRE
    # contient "définitions" (ex. "Autres définitions et propriétés",
    # Première) déclenchait alors à tort l'intent DEFINITION, ce qui ampute
    # la requête AVANT même la recherche du chapitre (voir classify() : le
    # fragment matché est retiré de topic_text) — bug confirmé par l'audit
    # global du routage pédagogique du 2026-08-22, indépendant du reranking
    # de titre. "défini[st]" reste volontairement SANS \b initial (on veut
    # toujours matcher "il/elle définit" même précédé d'un mot).
    r"(c'est quoi|qu'est[- ]ce qu[e']|d[ée]finition d[e'’]|d[ée]fini[st]\b|que veut dire)",
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
    REFORMULATION: [
        "explique autrement", "reformule", "dis-le autrement", "réexplique",
        "je n'ai pas compris", "peux-tu recommencer", "peux-tu détailler",
    ],
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

# Autres formulations de suivi (Current Learning Context) qui ne relèvent pas
# de REFORMULATION_RE : "donne un autre exemple" reste une demande EXEMPLE
# (déjà instruite "jamais une autre notion" par pedagogy_templates), "plus
# simplement" reste le simple flag SIMPLIFY_RE — mais dans les deux cas le
# message ne porte plus aucun mot-clé de SUJET, le chapitre/la notion doit
# donc aussi venir du Current Learning Context, jamais d'une recherche floue
# sur ces quelques mots (voir classify() : force_context).
FOLLOWUP_TOPIC_RE = re.compile(
    r"(un autre exemple|un second exemple|encore un exemple|autre exemple)",
    re.IGNORECASE,
)

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
    (FOLLOWUP, FOLLOWUP_RE),
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


# ── Reranking "boost de titre" pour le ROUTAGE chapitre/notion uniquement ───
# (audit global du routage pédagogique, 2026-08-22) : le TF-IDF brut de
# retrieval_engine donne parfois un score plus élevé au chapitre qui contient
# le PLUS de vocabulaire générique partagé qu'à celui dont le TITRE correspond
# réellement à la question (ex. "explique-moi la racine carrée" scorait plus
# haut sur "Fonctions de référence", qui parle beaucoup de "la fonction
# carrée", que sur la notion "La racine carrée" elle-même — mesuré : 0.285 vs
# 0.166). Mesuré sur les 153 notions/3 niveaux du corpus réel (audit dédié,
# 1071 formulations) : ce n'est PAS un cas isolé, 168/1071 tests (15,7 %)
# suivaient ce même schéma. Baisser le seuil ne change rien : le problème est
# le CLASSEMENT (quel document gagne), pas la confiance qu'on lui accorde.
#
# Portée volontairement LIMITÉE au routage du chatbot (cette fonction n'est
# appelée que par _detect_chapter, jamais par knowledge_engine.search/
# context_block, search_service.search, ni retrieval_engine — donc aucun
# impact sur le RAG générique, la recherche utilisateur (/api/search), les
# mentions "@" ou les cartes d'action, qui gardent le classement TF-IDF brut
# inchangé) : voir audit "autres consommateurs" avant cette correction.
#
# Réutilise EXACTEMENT le même tokenizer/stemmer/stopwords que
# retrieval_engine (pas de nouvelle normalisation inventée) pour rester
# cohérent avec l'index déjà construit.
# Passé de 5 à 10 (audit du 2026-08-22, phase de validation finale) : sur les
# 1071 tests de référence, un pool de 5 laissait 6 notions ("Additionner des
# vecteurs", rang réel #8 en TF-IDF brut) hors d'atteinte du reranking — un
# pool de 5 ne peut évidemment pas repêcher un candidat qu'il ne voit jamais,
# quels que soient alpha/beta. Mesuré : 5 -> 97,9% (22 collisions), 8 -> 98,9%
# (12), 10 -> 99,1% (10), 15 -> 99,1% (10, aucun gain supplémentaire au-delà
# de 10) — 0 régression à chaque palier testé. alpha/beta restent inchangés.
_TITLE_RERANK_CANDIDATES = 10  # top-K sur lequel reclasser, pas tout le corpus
# alpha/beta calibrés empiriquement sur le jeu de référence (153 notions ×
# 7 formulations = 1071 tests) : alpha=0.6/beta=0.4 est le point où le taux
# global (77,5/84,6/91,6 % -> 94,2/99,8/100 % par niveau) progresse fortement
# SANS introduire une seule régression sur les cas déjà corrects (0/1071),
# tout en conservant une majorité de poids (60%) au contenu réel du cours —
# une valeur plus extrême (ex. 0.3/0.7) gagne encore un peu de terrain sur ce
# jeu de test mais ferait dépendre le classement presque uniquement du titre,
# fragile pour une vraie reformulation qui n'emploierait aucun mot du titre.
TITLE_BOOST_ALPHA = 0.6
TITLE_BOOST_BETA = 0.4
# Un titre quasi intégralement présent dans la requête (>= 0.75, ex: "les
# ensembles de nombres" pour la notion "Les ensembles de nombres") vaut à lui
# seul un signal "explicit" même si le score TF-IDF brut est faible (document
# source court) — évite qu'une notion correctement identifiée par son titre
# retombe en "none"/"global" faute d'un score brut suffisant. Un recouvrement
# partiel (>= 0.5) vaut "weak", même logique que le seuil TF-IDF faible.
_TITLE_STRONG_MATCH = 0.75
_TITLE_WEAK_MATCH = 0.5


def _rerank_tokens(text):
    folded = _fold_accents(text).lower()
    return set(retrieval_engine._tokenize(folded)) - set(retrieval_engine._STEMMED_STOPWORDS)


def _title_match_score(query_tokens, title):
    """Fraction des mots du TITRE de la notion retrouvés dans la requête —
    volontairement rapportée à la taille du titre (pas de la requête) : un
    titre count de 1 à 2 mots (fréquent dans ce corpus) doit être quasi
    entièrement couvert pour compter comme un vrai match, tandis qu'un titre
    long ne doit pas exiger une couverture à 100% pour être reconnu."""
    title_tokens = _rerank_tokens(title)
    if not title_tokens:
        return 0.0
    return len(title_tokens & query_tokens) / len(title_tokens)


def _rerank_by_title(text, matches):
    """`matches` : résultats search_service.search (déjà triés par score
    TF-IDF brut), scope cours, plusieurs candidats (voir
    _TITLE_RERANK_CANDIDATES). Renvoie le meilleur candidat selon
    TITLE_BOOST_ALPHA*score_brut + TITLE_BOOST_BETA*correspondance_titre —
    le score TF-IDF brut du candidat RETENU (pas le score combiné) reste
    utilisé ensuite pour la confiance explicit/weak (voir _detect_chapter),
    afin de ne jamais changer la sémantique des seuils déjà calibrés."""
    if not matches:
        return None
    query_tokens = _rerank_tokens(text)
    best, best_final = None, -1.0
    for m in matches:
        final = TITLE_BOOST_ALPHA * m["score"] + TITLE_BOOST_BETA * _title_match_score(query_tokens, m["title"])
        if final > best_final:
            best_final, best = final, m
    return best


def _learning_context_class_matches(learning_context, class_level):
    """Chantier "dérive de classe" (2026-08-23) : True si `learning_context`
    n'a AUCUNE étiquette de classe mémorisée (créé avant ce chantier, ou
    classe inconnue au moment du tour où il a été écrit) OU si elle
    correspond exactement à `class_level`. False UNIQUEMENT en cas de
    désaccord avéré — c'est le seul cas où chapter_id/notion_id hérités ne
    doivent PAS être réutilisés : les identifiants de chapitre (ex.
    "Chapitre_3") sont réutilisés d'une classe à l'autre pour désigner des
    sujets totalement différents (audit confirmé : "Chapitre_3" = calcul
    littéral en Seconde, fractions en Troisième) — les réutiliser sans
    revalidation pourrait faire répondre le chatbot avec le contenu d'un
    autre niveau que celui réellement actif."""
    if not learning_context:
        return True
    stored_class = learning_context.get("class_level")
    return stored_class is None or stored_class == class_level


def _detect_chapter(text, context_summary, class_level=None, learning_context=None, force_context=False, explicit_change=False):
    """Chapitre/notion visé par la demande — réutilise la recherche déjà
    éprouvée de search_service (TF-IDF + repli flou), jamais de logique de
    correspondance dupliquée ici.

    Renvoie (chapter_id, notion_id, confidence). `confidence` distingue à
    quel point ce résultat doit être digne de confiance :
    - "explicit"  : sujet nettement identifié dans CE message (score fort, ou
                    score faible mais accompagné d'un marqueur de changement
                    de sujet assumé — voir EXPLICIT_TOPIC_CHANGE_RE) : peut
                    écraser sans hésiter le Current Learning Context.
    - "inherited" : vient du Current Learning Context (message ambigu forcé,
                    ou repli faute de mieux).
    - "weak"      : correspondance faible dans CE message, mais AUCUN Current
                    Learning Context à préférer (première question de la
                    conversation, faute de mieux).
    - "global"    : repli ultime sur une statistique globale de l'élève
                    (context_summary["chapters_in_progress"]), sans aucun
                    rapport garanti avec ce qui vient d'être discuté.

    `learning_context` (Current Learning Context, voir classify() et
    conversation_manager.py) : dernier {chapter_id, notion_id} réellement
    discuté dans CETTE conversation. `force_context=True` (message ambigu
    reconnu, voir REFORMULATION_RE/FOLLOWUP_RE) saute directement dessus SANS
    lancer la recherche — une recherche TF-IDF sur un message comme
    "réexplique" ou "encore" n'a plus aucun mot-clé de sujet à exploiter, la
    relancer ne peut que remonter un score faible mais réel sur une notion
    sans rapport (bug confirmé empiriquement), jamais un signal fiable à
    préférer au sujet déjà établi.

    Sans `force_context`, priorité corrigée (chantier continuité
    conversationnelle, 2026-08-22) : un Current Learning Context déjà établi
    ne doit plus être écrasé par une correspondance simplement AU-DESSUS du
    seuil faible — seul un score FORT (TFIDF_STRONG_THRESHOLD), ou un score
    faible accompagné d'un marqueur de changement de sujet explicite
    (`explicit_change`), gagne le droit de le remplacer. Sans Current
    Learning Context du tout, le score faible reste utilisé (faute de mieux),
    avant le repli ultime sur la statistique globale de l'élève."""
    if (
        force_context and learning_context and learning_context.get("chapter_id")
        and _learning_context_class_matches(learning_context, class_level)
    ):
        return learning_context["chapter_id"], learning_context.get("notion_id"), "inherited"

    matches = search_service.search(text, scope=[search_service.SCOPE_COURS], limit=_TITLE_RERANK_CANDIDATES, class_level=class_level)
    best = _rerank_by_title(text, matches)
    # La confiance (explicit/weak) est calculée sur le score TF-IDF BRUT du
    # candidat retenu après reranking — les seuils TFIDF_STRONG_THRESHOLD/
    # TFIDF_WEAK_THRESHOLD gardent leur sens d'origine (voir _rerank_by_title)
    # — SAUF si un titre de notion est retrouvé quasi intégralement dans la
    # requête (`_TITLE_STRONG_MATCH`) : un score TF-IDF brut peut être
    # mécaniquement faible pour une notion dont le document source est court
    # (peu de mots -> peu de poids), sans que le SUJET demandé soit le moins
    # du monde ambigu pour autant (audit du 2026-08-22 : "les ensembles de
    # nombres" citée quasi mot pour mot ne doit jamais être traitée comme
    # "aucun sujet identifié" simplement parce que son propre score TF-IDF
    # brut, dilué par la brièveté du document, retombe sous 0.12).
    score = best["score"] if best else 0.0
    title_score = _title_match_score(_rerank_tokens(text), best["title"]) if best else 0.0
    has_context = bool(
        learning_context and learning_context.get("chapter_id")
        and _learning_context_class_matches(learning_context, class_level)
    )

    if best and (
        score >= search_service.TFIDF_STRONG_THRESHOLD
        or title_score >= _TITLE_STRONG_MATCH
        or (explicit_change and score >= search_service.TFIDF_WEAK_THRESHOLD)
    ):
        return best["chapter_id"], best["notion_id"], "explicit"

    if has_context:
        # Un score faible ne suffit plus à écraser un sujet déjà établi — il
        # peut aussi bien venir d'une collision lexicale fortuite (voir
        # audit "équation cartésienne" -> "proportionnalité") que d'un vrai
        # changement de sujet timide ; dans le doute, on garde le contexte.
        return learning_context["chapter_id"], learning_context.get("notion_id"), "inherited"

    if best and (score >= search_service.TFIDF_WEAK_THRESHOLD or title_score >= _TITLE_WEAK_MATCH):
        return best["chapter_id"], best["notion_id"], "weak"

    if context_summary and context_summary.get("chapters_in_progress"):
        return context_summary["chapters_in_progress"][0], None, "global"

    return None, None, "none"


def classify(user_message, context_summary=None, class_level=None, learning_context=None, last_assistant_message=None):
    """Retourne {intent, chapter_id, notion_id, topic_inherited,
    topic_confidence, difficulty, simplify, quantity}. `intent` vaut
    NONE_INTENT si aucun mot-clé pédagogique n'est reconnu (la question reste
    ouverte, traitée normalement par le LLM) — à ne pas confondre avec
    UNCLEAR (demande incompréhensible, court-circuitée avant tout appel IA).
    `quantity` : nombre d'exercices/exemples demandés explicitement ("3
    exercices", "plusieurs exemples"), None sinon (un seul, comportement par
    défaut inchangé).

    `learning_context` (Current Learning Context, voir conversation_manager.py
    et db.get_conversation_learning_context) : dernier sujet réellement
    discuté dans cette conversation. `topic_inherited=True` dans le résultat
    signifie que chapter_id/notion_id viennent de ce contexte mémorisé
    (message ambigu, voir REFORMULATION_RE/FOLLOWUP_RE) plutôt que d'une
    mention explicite du message courant — utilisé par conversation_manager.py
    pour injecter une instruction système explicite ("ne change pas de
    sujet") et pour construire le contexte RAG par lookup exact plutôt que
    par recherche floue (voir knowledge_engine.notion_context_block).
    `topic_confidence` : voir _detect_chapter — "explicit"/"inherited"/
    "weak"/"global"/"none", utilisé par conversation_manager._update_learning_
    context pour décider si ce tour a le droit d'écraser le Current Learning
    Context déjà mémorisé.

    `last_assistant_message` (optionnel) : texte du dernier message de
    l'ASSISTANT (pas de l'élève) — sert uniquement à résoudre l'ambiguïté
    d'un "oui"/"non" nu (voir _BARE_YES_RE/_BARE_NO_RE) : un "oui"/"non" seul
    est traité comme une confirmation/un refus de la dernière proposition du
    chatbot (donc une continuation du sujet en cours) seulement si ce dernier
    message se terminait par une question ("?"). Sans cette information (ou
    si le dernier message n'était pas une question), "oui"/"non" nu reste une
    intention NONE_INTENT ordinaire, résolue comme n'importe quel autre
    message sans mot-clé de sujet (repli sur le contexte mémorisé s'il existe
    — voir _detect_chapter — jamais une recherche TF-IDF sur "oui" ou "non"
    eux-mêmes, qui ne veut rien dire)."""
    text = (user_message or "").strip()
    if _is_gibberish(text):
        return {
            "intent": UNCLEAR, "chapter_id": None, "notion_id": None, "topic_inherited": False,
            "topic_confidence": "none", "difficulty": None, "simplify": False, "quantity": None,
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

    # "oui"/"non" nu : une confirmation/un refus de la DERNIÈRE PROPOSITION du
    # chatbot est une continuation (FOLLOWUP), jamais une intention à part —
    # seulement si le dernier message assistant posait effectivement une
    # question. Un "non, ..." suivi d'autre texte ne matche pas _BARE_NO_RE
    # (voir sa définition) : il reste un message normal, dont le sujet est
    # détecté comme d'habitude plus bas (changement de sujet explicite).
    last_was_question = bool((last_assistant_message or "").rstrip().endswith("?"))
    is_bare_confirmation = last_was_question and (bool(_BARE_YES_RE.match(text)) or bool(_BARE_NO_RE.match(text)))
    if intent == NONE_INTENT and is_bare_confirmation:
        intent = FOLLOWUP

    # Cherche le chapitre seulement sur ce qui reste une fois la formule
    # déclencheuse retirée ("donne-moi un exercice" -> "") : sinon une
    # requête sans sujet réel se fait attribuer un chapitre au hasard par le
    # repli flou (comparaison de lettres sur des mots génériques).
    topic_text = text
    if matched:
        topic_text = (text[:matched.start()] + " " + text[matched.end():]).strip()

    has_learning_context = bool(learning_context and learning_context.get("chapter_id"))
    force_context = has_learning_context and (
        intent in (REFORMULATION, FOLLOWUP) or bool(SIMPLIFY_RE.search(text)) or bool(FOLLOWUP_TOPIC_RE.search(text))
    )
    explicit_change = bool(EXPLICIT_TOPIC_CHANGE_RE.search(text))
    chapter_id, notion_id, topic_confidence = _detect_chapter(
        topic_text, context_summary, class_level=class_level,
        learning_context=learning_context, force_context=force_context, explicit_change=explicit_change,
    )
    topic_inherited = topic_confidence == "inherited"
    return {
        "intent": intent,
        "chapter_id": chapter_id,
        "notion_id": notion_id,
        "topic_inherited": topic_inherited,
        "topic_confidence": topic_confidence,
        "difficulty": _detect_difficulty(text),
        "simplify": bool(SIMPLIFY_RE.search(text)),
        "quantity": _detect_quantity(text),
    }
