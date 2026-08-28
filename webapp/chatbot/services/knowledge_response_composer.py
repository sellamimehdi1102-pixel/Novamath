"""
Knowledge Response Composer — Phase 3A bis (Response Engine v2).

Rôle UNIQUE de ce module : à partir d'une `ResponseStrategy` déjà décidée
(`response_strategy.py`, jamais recalculée ici) et d'un `StudentContext`
(`student_context_resolver.py`), ASSEMBLER une réponse pédagogique en blocs à
partir du Knowledge Engine (`chatbot/knowledge_engine.py`) — jamais prendre de
décision stratégique (quel moteur répondre, quel chapitre viser...), jamais
lire directement un fichier JSON de cours (toujours via les accesseurs
`knowledge_engine.get_*`, source unique de vérité).

Périmètre couvert : les intents "de cours" que ni Math/Rule Engine ni
Dashboard (`services/response_composer.py`, INCHANGÉ, responsable des seules
données PROGRESSION/STATISTIQUE/DASHBOARD/PROFIL/PARAMETRES/SERIE) ne
traitent — DEFINITION/COURS/RESUME/METHODE/PROPRIETE/DEMONSTRATION/INDICE/
RAPPEL/REVISION/REFORMULATION/EXEMPLE/EXPLICATION/FORMULE.

IMPORTANT (voir consigne explicite) : ce module n'est PAS câblé au pipeline
principal (`conversation_manager.py`). Entièrement testable en isolation
(voir webapp/tests/test_knowledge_response_composer.py).

── Séparation des responsabilités (architecture cible, voir rapport de phase)
    response_strategy.py             décide QUI répond (existant, Phase 3A)
    knowledge_response_composer.py   compose les réponses "de cours" (CE FICHIER)
    response_composer.py             compose les réponses de données (INCHANGÉ)
    exercise_response_composer.py    FUTUR (énoncé d'exercice)
    quiz_response_composer.py        FUTUR (aucune génération de quiz locale)
    recommendation_composer.py       FUTUR/à clarifier (chevauchement avec
                                      action_cards_service.py existant)

── Assemblage par blocs
Une réponse est une liste ordonnée de `ResponseBlock` (kind, text), assemblée
selon l'intent de la `ResponseStrategy` reçue — introduction/définition/
méthode/exemple/deuxième exemple/propriété/formule/erreur fréquente/astuce/
rappel/conseil/résumé/ouverture. Les blocs de contenu (définition, méthode,
exemple...) viennent du Knowledge Engine ; les blocs de forme (introduction,
ouverture, conseil) viennent d'une bibliothèque de formulations (ci-dessous).

── Variabilité
Chaque bloc de forme choisit une variante au hasard (`random.Random`, injecté
ou par défaut) PARMI CELLES NON UTILISÉES récemment dans la conversation
(`student_context["historique_conversation"]`, déjà fourni par le Student
Context Resolver v2 — jamais relu ici). Ceci répond à l'exigence "ne plus
jamais deux réponses identiques" sans reconstruire un mécanisme de mémoire
déjà présent ailleurs.

── Paramètres utilisateur (influence réelle, pas décorative)
    longueur ("court"/"normal"/"detaille")   : nombre de blocs inclus
    niveau_explication ("college"/"lycee"/"expert"/"auto") : quel texte de
        définition choisir (knowledge_engine.get_definition(level=...))
    mode ("rapide"/"pas_a_pas"/"professeur"/"visuel"/"examen") : quelles
        étapes de méthode (get_methode_etapes(niveau=...)), et présence du
        bloc "conseil"
    difficulty ("easy"/"hard", ResponseStrategy) : quel exemple choisir
        (get_exemple(difficulte=...))
    quantity (ResponseStrategy) : nombre d'exemples inclus
    simplify (ResponseStrategy) : redescend d'un niveau de définition
        (expert -> lycée -> collège) et l'annonce explicitement

── Fallback (jamais d'erreur)
Si un bloc de contenu n'a pas de données (ex. `proprietes` toujours vide
aujourd'hui dans les cours migrés, voir knowledge_engine.py), le compositeur
retombe intelligemment sur une autre donnée du Knowledge Engine (formule,
règle importante, "à retenir"...) plutôt que de produire un bloc vide ou une
exception. Si aucune notion n'est résolue du tout (`chapter_id`/`topic_id`
absents ou inconnus), une réponse de repli générique est renvoyée — jamais
une erreur, jamais un texte vide.
"""
import random
from dataclasses import dataclass
from typing import Optional, Tuple

from .. import knowledge_engine
from . import intent_service, phrasing_memory

ENGINE_NAME = "knowledge_response_composer"

# ── Identifiants de blocs ────────────────────────────────────────────────────
BLOCK_INTRODUCTION = "introduction"
BLOCK_DEFINITION = "definition"
BLOCK_METHODE = "methode"
BLOCK_EXEMPLE = "exemple"
BLOCK_EXEMPLE_2 = "exemple_2"
BLOCK_PROPRIETE = "propriete"
BLOCK_FORMULE = "formule"
BLOCK_ERREUR_FREQUENTE = "erreur_frequente"
BLOCK_ASTUCE = "astuce"
BLOCK_RAPPEL = "rappel"
BLOCK_CONSEIL = "conseil"
BLOCK_RESUME = "resume"
BLOCK_OUVERTURE = "ouverture"
BLOCK_INTROUVABLE = "introuvable"


@dataclass(frozen=True)
class ResponseBlock:
    kind: str
    text: str


@dataclass(frozen=True)
class ResponseDraft:
    """Brouillon de réponse structuré — PAS le texte final envoyé à l'élève
    en soi (conversation_manager.py, Phase 3B, décidera de la mise en forme
    finale) mais déjà un texte assemblé et cohérent (`text`), plus le détail
    des blocs (`blocks`) pour un futur post-traitement (cartes d'action,
    rendu par blocs côté frontend...)."""

    text: str
    blocks: Tuple[ResponseBlock, ...]
    engine: str
    intent: str
    chapter_id: Optional[str]
    topic_id: Optional[str]
    used_fallback: bool
    explanation: str
    # Chantier "fausse mémoire d'approche" (2026-08-22) : approche RÉELLEMENT
    # réalisée par cette composition (voir _primary_approach), jamais
    # supposée égale à `strategy.recommended_approach` — None si le premier
    # bloc de contenu ne correspond à aucune approche du vocabulaire
    # d'escalade (ex: RESUME/FORMULE/PROPRIETE).
    primary_approach: Optional[str] = None
    # Audit "le chatbot abandonne trop vite" (2026-07-26, épisode 2) : distinct
    # de `used_fallback` (qui couvre aussi un repli BÉNIN entre deux blocs de
    # contenu de LA MÊME notion résolue, ex. _block_propriete retombant sur une
    # formule — ce n'est PAS un échec). `notion_resolved=False` signale
    # UNIQUEMENT le cas où aucune notion n'a pu être résolue du tout : ce texte
    # n'est alors qu'un REPLI DE DERNIER RECOURS interne à ce module, jamais une
    # réponse à considérer comme valide par l'appelant (voir
    # local_response_engine.py::_execute_engine, qui doit continuer la
    # cascade plutôt que d'afficher ce texte à l'élève).
    notion_resolved: bool = True
    # Chantier "répétition des exemples" (2026-08-23) : ids des exemples
    # RÉELLEMENT choisis pendant CETTE composition (0, 1 ou 2 — BLOCK_EXEMPLE/
    # BLOCK_EXEMPLE_2), à ajouter par l'appelant à la mémoire persistée de la
    # conversation (voir conversation_manager._commit_used_exemple). Ne
    # contient PAS les ids hérités des tours précédents (déjà dans
    # `strategy.used_exemple_ids`, seulement lus ici pour les exclure du
    # tirage — jamais retournés en double).
    new_exemple_ids: tuple = ()


# ── Correspondances de paramètres (documentées, pas de valeur devinée) ──────
_NIVEAU_BRUT_TO_DEFINITION_LEVEL = {1: "college", 2: "lycee", 3: "expert"}
_SIMPLIFY_STEP_DOWN = {"expert": "lycee", "lycee": "college", "college": "college"}
_NIVEAU_EXPLICATION_VALUES = {"college", "lycee", "expert"}
_MODE_TO_METHODE_NIVEAU = {"rapide": "rapide", "pas_a_pas": "debutant"}

# ── Bibliothèque de formulations (variabilité, jamais deux réponses identiques) ─
_INTRO_VARIANTS = {
    "default": [
        "D'accord, regardons ça ensemble.",
        "Bonne question ! Voici ce qu'il faut retenir.",
        "Reprenons ce point tranquillement.",
        "Allons-y étape par étape.",
        "Voici de quoi t'aider sur ce point.",
    ],
    "professeur": [
        "Très bien, prenons le temps de bien comprendre ce point.",
        "C'est une notion importante, détaillons-la correctement.",
        "Voyons cela en profondeur, comme on le ferait en classe.",
    ],
    "rapide": [
        "Voici l'essentiel :",
        "En bref :",
        "Droit au but :",
    ],
    # Neutre, académique, sans familiarité ni encouragement (mode examen,
    # Personality Engine) — jamais "on", jamais de ponctuation exclamative.
    "examen": [
        "Voici l'analyse de cette question.",
        "Examinons cet énoncé.",
        "Voici les éléments de réponse.",
    ],
    # Progression guidée, une étape après l'autre (mode pas-à-pas).
    "pas_a_pas": [
        "Nous allons procéder étape par étape.",
        "Avançons pas à pas, une étape après l'autre.",
        "Suivons la méthode dans l'ordre, sans rien sauter.",
    ],
}
_OUVERTURE_VARIANTS = {
    "default": [
        "N'hésite pas si tu veux un exemple ou une explication complémentaire.",
        "Dis-moi si tu veux qu'on aille plus loin sur ce point.",
        "Tu peux me demander un exercice sur cette notion si tu veux t'entraîner.",
        "Si un point reste flou, n'hésite pas à demander une reformulation.",
    ],
    "professeur": [
        "Prends le temps de relire ce point avant de continuer — n'hésite pas à revenir dessus.",
        "N'hésite pas à me poser d'autres questions, c'est normal de devoir y revenir plusieurs fois.",
    ],
    "rapide": [
        "Autre chose ?",
        "Besoin d'un exercice ?",
    ],
    # Chaque étape prépare la suivante (mode pas-à-pas) — jamais une clôture
    # généraliste, toujours un lien explicite vers la suite.
    "pas_a_pas": [
        "Une fois cette étape bien comprise, on pourra passer à la suivante.",
        "Prends le temps de valider cette étape avant de continuer.",
        "Dis-moi quand tu es prêt à passer à l'étape suivante.",
    ],
    # Pas d'entrée "examen" : voir _block_ouverture — aucune formule de
    # clôture/encouragement en mode examen, le bloc est omis entièrement.
}
_LEADIN_DEFINITION = [
    "Voici la définition de **{title}** :",
    "Pour rappel, **{title}** se définit ainsi :",
    "**{title}**, en quelques mots :",
    "Ce qu'il faut savoir sur **{title}** :",
]
# Utilisé quand `simplify=True` (repli d'un niveau de définition) — remplace
# l'ancien suffixe technique " (version simplifiée)" par une phrase intégrée
# naturellement, comme le ferait un professeur qui reformule à l'oral,
# plutôt qu'une étiquette entre parenthèses (mission Personality Engine).
_LEADIN_DEFINITION_SIMPLIFIEE = [
    "Pour le dire plus simplement, **{title}** :",
    "Si on reformule plus simplement, **{title}** c'est :",
    "En plus simple : **{title}**, c'est",
    "Reprenons ça plus simplement — **{title}** :",
]
_LEADIN_METHODE = {
    "default": [
        "Voici la méthode à suivre :",
        "Procède étape par étape :",
        "Voici comment faire :",
        "La marche à suivre :",
    ],
    # Insiste sur la progression graduelle (mode pas-à-pas) — jamais
    # "voici comment faire" (trop direct), toujours une notion
    # d'avancée mesurée, cohérente avec les nombreuses transitions
    # attendues de ce mode.
    "pas_a_pas": [
        "Décomposons ça étape par étape, sans rien sauter :",
        "On y va progressivement, une étape après l'autre :",
        "Avançons pas à pas sur cette méthode :",
    ],
}
_LEADIN_EXEMPLE = [
    "Voyons comment ça fonctionne avec un exemple :",
    "Regardons un exemple concret :",
    "Prenons un cas concret :",
    "Par exemple :",
]
_LEADIN_EXEMPLE_2 = [
    "Voici un second exemple pour bien fixer le principe :",
    "Un autre exemple, pour être sûr d'avoir compris :",
    "Et un deuxième cas :",
]
# Chantier "répétition des exemples" (2026-08-23) : utilisée UNIQUEMENT
# quand knowledge_engine.exemple_pool_exhausted() est vrai (aucun exemple
# inédit ne reste dans les données de cette notion) — le dit honnêtement
# plutôt que de présenter la répétition comme si elle était nouvelle.
_LEADIN_EXEMPLE_EPUISE = [
    "Je t'ai déjà montré tous les exemples que j'ai sur ce point — reprenons celui-ci, ça vaut le coup de bien le fixer :",
    "Je n'ai pas d'autre exemple différent sous la main pour cette notion précise — revoyons le même, en y prêtant bien attention :",
]
_LEADIN_FORMULE = [
    "Voici la formule à connaître :",
    "La formule utile ici :",
    "Retiens cette formule :",
]
_LEADIN_PROPRIETE = [
    "Voici la propriété à retenir :",
    "Ce qu'il faut retenir ici :",
    "Une règle importante :",
]
_LEADIN_ERREUR = [
    "Attention à une erreur fréquente :",
    "Un piège classique à éviter :",
    "Erreur courante à ne pas commettre :",
]
_LEADIN_ASTUCE = [
    "Astuce :",
    "Petit conseil :",
    "Un truc utile :",
]
_LEADIN_RAPPEL = [
    "Petit rappel :",
    "Pour mémoire :",
    "Rappel rapide :",
]
_LEADIN_RESUME = [
    "En résumé, ce qu'il faut retenir :",
    "Pour résumer :",
    "L'essentiel à retenir :",
]
_CONSEIL_VARIANTS = [
    "Essaie de refaire cet exemple sans regarder la méthode, puis vérifie ta réponse.",
    "Un bon réflexe : reformule cette règle avec tes propres mots pour vérifier que tu l'as comprise.",
    "N'hésite pas à t'entraîner avec un exercice sur cette notion pour bien l'ancrer.",
]
# Audit «le chatbot ne doit jamais donner l'impression d'abandonner»
# (2026-07-26, épisode 2) : ce texte n'est plus qu'un filet de sécurité
# interne à ce module (voir ResponseDraft.notion_resolved=False plus haut) —
# local_response_engine.py ne l'affiche JAMAIS à l'élève, il relance la
# cascade vers un autre moteur. Reformulé quand même en dialogue naturel
# (jamais «je n'ai pas trouvé»/ton froid), en défense en profondeur.
_INTROUVABLE_VARIANTS = [
    "Bien sûr. Peux-tu me dire de quel chapitre ou de quelle notion tu parles ?",
    "Je veux bien t'aider. Dis-moi simplement le nom du chapitre, ou colle ton exercice.",
    "Je ne suis pas certain du sujet dont tu parles. Peux-tu me donner un peu plus de contexte ?",
]


# Export public additif (Phase 4, Mission 6 -- diversity_audit.py) : liste
# tous les pools de formulations de ce module pour un audit de diversite
# externe, sans dupliquer leur contenu ni changer leur usage interne. Généré
# à partir des dicts `{mode: variants}` sources (préfixés par pool) plutôt
# que réénuméré à la main : toute entrée de mode ajoutée à `_INTRO_VARIANTS`/
# `_OUVERTURE_VARIANTS`/`_LEADIN_METHODE` apparaît ici automatiquement.
def _prefixed(prefix, variants_by_mode):
    return {f"{prefix}_{mode}": variants for mode, variants in variants_by_mode.items()}


VARIANT_POOLS = {
    **_prefixed("introduction", _INTRO_VARIANTS),
    **_prefixed("ouverture", _OUVERTURE_VARIANTS),  # pas d'entrée "examen" : bloc omis entièrement dans ce mode
    "leadin_definition": _LEADIN_DEFINITION,
    "leadin_definition_simplifiee": _LEADIN_DEFINITION_SIMPLIFIEE,
    **{f"leadin_methode_{mode}": variants for mode, variants in _LEADIN_METHODE.items()},
    "leadin_exemple": _LEADIN_EXEMPLE,
    "leadin_exemple_2": _LEADIN_EXEMPLE_2,
    "leadin_formule": _LEADIN_FORMULE,
    "leadin_propriete": _LEADIN_PROPRIETE,
    "leadin_erreur": _LEADIN_ERREUR,
    "leadin_astuce": _LEADIN_ASTUCE,
    "leadin_rappel": _LEADIN_RAPPEL,
    "leadin_resume": _LEADIN_RESUME,
    "conseil": _CONSEIL_VARIANTS,
    "introuvable": _INTROUVABLE_VARIANTS,
}


# Mémoire de style mutualisée (phrasing_memory.py, extraite d'ici). `_pick`
# pointe désormais sur `pick_rendered` (render d'abord, pick ensuite) — le
# seul appel avec placeholder (_block_definition, {title}) est mis à jour en
# conséquence ci-dessous ; tous les autres (pools sans placeholder) restent
# textuellement inchangés, le rendu y étant un no-op.
_recent_assistant_texts = phrasing_memory.recent_assistant_text
_pick = phrasing_memory.pick_rendered


def _fmt_steps(etapes):
    lignes = [e.get("texte", "").strip() for e in etapes if e.get("texte")]
    return "\n".join(f"{i + 1}. {texte}" for i, texte in enumerate(lignes))


def _resolve_definition_level(student_context, simplify):
    parametres = (student_context or {}).get("parametres") or {}
    niveau_explication = parametres.get("niveau_explication") or "auto"
    if niveau_explication in _NIVEAU_EXPLICATION_VALUES:
        level = niveau_explication
    else:
        level = _NIVEAU_BRUT_TO_DEFINITION_LEVEL.get((student_context or {}).get("niveau_brut"), "lycee")
    if simplify:
        level = _SIMPLIFY_STEP_DOWN.get(level, level)
    return level


# ── Blocs de contenu (Knowledge Engine, jamais de lecture directe des JSON) ──
def _block_definition(rng, avoid, notion, level, simplify):
    text = knowledge_engine.get_definition(notion, level=level)
    if not text:
        return None
    pool = _LEADIN_DEFINITION_SIMPLIFIEE if simplify else _LEADIN_DEFINITION
    lead = _pick(rng, pool, avoid, mapping={"title": notion.get("title") or "cette notion"})
    return ResponseBlock(BLOCK_DEFINITION, f"{lead}\n\n{text}")


def _block_methode(rng, avoid, notion, niveau_methode, mode):
    etapes = knowledge_engine.get_methode_etapes(notion, niveau=niveau_methode)
    if not etapes:
        return None
    pool = _LEADIN_METHODE.get(mode, _LEADIN_METHODE["default"])
    lead = _pick(rng, pool, avoid)
    return ResponseBlock(BLOCK_METHODE, f"{lead}\n\n{_fmt_steps(etapes)}")


def _block_exemple(rng, avoid, notion, difficulte_label, exclude_ids, kind=BLOCK_EXEMPLE, leadins=None, hint_only=False):
    # Chantier "répétition des exemples" (2026-08-23) : `exclude_ids` porte
    # désormais À LA FOIS les ids déjà utilisés DANS CETTE MÊME réponse
    # (BLOCK_EXEMPLE avant BLOCK_EXEMPLE_2, voir compose()) ET ceux déjà
    # montrés lors des tours PRÉCÉDENTS de la conversation (voir
    # conversation_manager._commit_used_exemple) — le tirage exclut les deux
    # à la fois en un seul appel, jamais deux logiques séparées.
    exhausted = knowledge_engine.exemple_pool_exhausted(notion, exclude_ids)
    exemple = knowledge_engine.get_exemple(notion, difficulte=difficulte_label, exclude_ids=exclude_ids)
    if not exemple:
        return None, None
    # Stock réellement épuisé (aucune alternative inédite) : le dit
    # honnêtement plutôt que de présenter la répétition comme un exemple
    # neuf — jamais de fausse variante fabriquée, quel que soit le bloc
    # (premier ou second exemple de la réponse).
    lead = _pick(rng, _LEADIN_EXEMPLE_EPUISE, avoid) if exhausted else _pick(rng, leadins or _LEADIN_EXEMPLE, avoid)
    if hint_only:
        premiere_etape = (exemple.get("calcul") or [{}])[0].get("texte", "")
        body = "\n\n".join(part for part in (exemple.get("enonce", ""), premiere_etape) if part)
    else:
        calcul = "\n".join(f"- {c.get('expr', '')} — {c.get('texte', '')}" for c in (exemple.get("calcul") or []))
        body = "\n\n".join(part for part in (
            exemple.get("enonce", ""), calcul, f"**Résultat :** {exemple.get('reponse', '')}" if exemple.get("reponse") else "",
        ) if part)
    return ResponseBlock(kind, f"{lead}\n\n{body}"), exemple.get("id")


def _block_formule(rng, avoid, notion):
    formules = knowledge_engine.get_formules(notion)
    if not formules:
        return None
    f = formules[0]
    lead = _pick(rng, _LEADIN_FORMULE, avoid)
    body = f"**{f.get('nom', '')}** : {f.get('expression', '')}\n\n{f.get('quand_utiliser', '')}".strip()
    return ResponseBlock(BLOCK_FORMULE, f"{lead}\n\n{body}")


def _block_propriete(rng, avoid, notion):
    """Repli intelligent (voir docstring module) : `proprietes` est vide sur
    toutes les notions migrées à ce jour (curation humaine non encore faite,
    voir knowledge_engine.get_proprietes) — on retombe sur une formule, puis
    une règle importante historique, jamais sur un bloc vide."""
    proprietes = knowledge_engine.get_proprietes(notion)
    if proprietes:
        p = proprietes[0]
        lead = _pick(rng, _LEADIN_PROPRIETE, avoid)
        return ResponseBlock(BLOCK_PROPRIETE, f"{lead}\n\n**{p.get('nom', '')}** : {p.get('explication', '')}"), False
    formules = knowledge_engine.get_formules(notion)
    if formules:
        f = formules[0]
        lead = _pick(rng, _LEADIN_PROPRIETE, avoid)
        return ResponseBlock(BLOCK_PROPRIETE, f"{lead}\n\n**{f.get('nom', '')}** : {f.get('expression', '')}"), True
    regles = knowledge_engine.get_regles(notion)
    if regles:
        lead = _pick(rng, _LEADIN_PROPRIETE, avoid)
        return ResponseBlock(BLOCK_PROPRIETE, f"{lead}\n\n{regles[0]}"), True
    return None, True


def _block_erreur_frequente(rng, avoid, notion):
    detail = knowledge_engine.get_erreurs_detail(notion)
    if detail:
        e = detail[0]
        lead = _pick(rng, _LEADIN_ERREUR, avoid)
        texte = " ".join(part for part in (e.get("description"), e.get("comment_eviter")) if part)
        return ResponseBlock(BLOCK_ERREUR_FREQUENTE, f"{lead}\n\n{texte}")
    erreurs = notion.get("erreurs") or []
    if erreurs:
        lead = _pick(rng, _LEADIN_ERREUR, avoid)
        return ResponseBlock(BLOCK_ERREUR_FREQUENTE, f"{lead}\n\n{erreurs[0]}")
    return None


def _block_astuce(rng, avoid, notion):
    """`astuce` (notion entière) n'est pas conservée comme champ propre par
    knowledge_engine._load_notions (seulement indexée pour la recherche) —
    repli sur l'astuce d'une formule, puis sur le premier point "à retenir"."""
    tip = None
    for f in knowledge_engine.get_formules(notion):
        if f.get("astuce"):
            tip = f["astuce"]
            break
    if not tip:
        a_retenir = knowledge_engine.get_a_retenir(notion)
        tip = a_retenir[0] if a_retenir else None
    if not tip:
        return None
    lead = _pick(rng, _LEADIN_ASTUCE, avoid)
    return ResponseBlock(BLOCK_ASTUCE, f"{lead} {tip}")


def _block_rappel(rng, avoid, notion):
    source = knowledge_engine.get_regles(notion) or knowledge_engine.get_a_retenir(notion)
    if not source:
        return None
    lead = _pick(rng, _LEADIN_RAPPEL, avoid)
    return ResponseBlock(BLOCK_RAPPEL, f"{lead} {source[0]}")


def _block_resume(rng, avoid, notion):
    a_retenir = knowledge_engine.get_a_retenir(notion)
    if not a_retenir:
        return None
    lead = _pick(rng, _LEADIN_RESUME, avoid)
    bullets = "\n".join(f"- {item}" for item in a_retenir[:4])
    return ResponseBlock(BLOCK_RESUME, f"{lead}\n\n{bullets}")


def _block_conseil(rng, avoid):
    return ResponseBlock(BLOCK_CONSEIL, _pick(rng, _CONSEIL_VARIANTS, avoid))


# ── Blocs de forme (bibliothèque de formulations, pas de Knowledge Engine) ──
def _block_introduction(rng, avoid, mode):
    pool = _INTRO_VARIANTS.get(mode, _INTRO_VARIANTS["default"])
    return ResponseBlock(BLOCK_INTRODUCTION, _pick(rng, pool, avoid))


def _block_ouverture(rng, avoid, mode):
    # Mode examen : aucune formule de clôture/encouragement (cf. mission
    # Personality Engine — "aucune familiarité, aucun encouragement inutile")
    # — le bloc est omis entièrement plutôt que d'en forcer une version
    # neutre qui sonnerait quand même comme une politesse déplacée.
    if mode == "examen":
        return None
    pool = _OUVERTURE_VARIANTS.get(mode, _OUVERTURE_VARIANTS["default"])
    return ResponseBlock(BLOCK_OUVERTURE, _pick(rng, pool, avoid))


def _block_introuvable(rng, avoid):
    return ResponseBlock(BLOCK_INTROUVABLE, _pick(rng, _INTROUVABLE_VARIANTS, avoid))


# ── Plan de blocs par intent ─────────────────────────────────────────────────
# Vocabulaire d'approche (chantier "escalade pédagogique", 2026-08-22) —
# EXACTEMENT le même que conversation_manager._LOCAL_APPROACHES : seules
# "definition"/"methode"/"exemple" correspondent à un bloc composable
# localement à partir de données réelles. "analogie"/"question_guidee"
# (vocabulaire LLM uniquement, voir conversation_manager._LLM_APPROACHES)
# n'ont ICI aucune traduction — le plan par défaut de l'intent s'applique
# alors sans réordonnancement (jamais de contenu inventé pour les simuler).
_APPROACH_TO_BLOCK = {
    "definition": BLOCK_DEFINITION,
    "methode": BLOCK_METHODE,
    "exemple": BLOCK_EXEMPLE,
}
_BLOCK_TO_APPROACH = {block: approach for approach, block in _APPROACH_TO_BLOCK.items()}


def _primary_approach(blocks):
    """Chantier "fausse mémoire d'approche" (2026-08-22) : approche
    RÉELLEMENT réalisée par cette composition — le premier bloc de CONTENU
    (jamais introduction/ouverture, purement cosmétiques) dont le type
    correspond au vocabulaire d'escalade (definition/methode/exemple, voir
    _APPROACH_TO_BLOCK). Renvoie None si le premier bloc de contenu ne
    correspond à aucune de ces trois catégories (ex: RESUME/FORMULE/
    PROPRIETE) — dans ce cas l'appelant (conversation_manager) ne doit rien
    ajouter à approaches_used, jamais deviner."""
    for block in blocks:
        if block.kind in (BLOCK_INTRODUCTION, BLOCK_OUVERTURE):
            continue
        return _BLOCK_TO_APPROACH.get(block.kind)
    return None


def _content_plan(intent, longueur, quantity, recommended_approach=None, escalation_level=0):
    """Renvoie la liste ordonnée des blocs de CONTENU (hors introduction/
    ouverture, ajoutés systématiquement sauf en longueur "court") pour un
    intent donné. `quantity`/`longueur` ajustent le nombre d'exemples.

    `recommended_approach` (chantier "escalade pédagogique", 2026-08-22) :
    si l'approche recommandée par l'état d'escalade (voir
    conversation_manager._select_approach) correspond à un bloc DÉJÀ PRÉSENT
    dans le plan de cet intent, ce bloc est simplement déplacé en tête —
    aucun bloc ajouté, aucun contenu inventé, le plan par défaut de chaque
    intent reste la seule source de vérité sur CE QUI peut être montré.

    `escalation_level` (chantier "escalade réellement exécutée", 2026-08-22) :
    audit LIVE confirmé — un intent NON mappé ici (ex. "none", produit par
    "encore une autre façon"/"je comprends toujours pas") retombait
    TOUJOURS sur le repli `[BLOCK_DEFINITION]` seul, quel que soit le niveau
    d'escalade déjà atteint — un élève ayant déjà exprimé 3 incompréhensions
    recevait alors une réponse quasi identique à sa toute première question
    (similarité textuelle mesurée : 0,685). Correctif : si l'intent est
    absent de `plans` (repli) ET `escalation_level >= 2`, réutilise le MÊME
    plan enrichi que REFORMULATION — jamais un nouveau bloc, jamais une
    invention, seulement le même repli déjà appliqué à un intent voisin."""
    deuxieme_exemple = (quantity or 1) >= 2 or longueur == "detaille"

    plans = {
        intent_service.DEFINITION: [BLOCK_DEFINITION],
        intent_service.COURS: [BLOCK_DEFINITION, BLOCK_METHODE, BLOCK_EXEMPLE, BLOCK_PROPRIETE, BLOCK_RESUME],
        intent_service.RESUME: [BLOCK_RESUME],
        intent_service.METHODE: [BLOCK_METHODE, BLOCK_EXEMPLE],
        intent_service.PROPRIETE: [BLOCK_PROPRIETE, BLOCK_EXEMPLE],
        intent_service.FORMULE: [BLOCK_FORMULE, BLOCK_EXEMPLE],
        intent_service.DEMONSTRATION: [BLOCK_PROPRIETE, BLOCK_DEFINITION],
        intent_service.EXEMPLE: [BLOCK_EXEMPLE] + ([BLOCK_EXEMPLE_2] if deuxieme_exemple else []),
        intent_service.INDICE: [BLOCK_EXEMPLE],  # hint_only=True géré par compose()
        intent_service.RAPPEL: [BLOCK_RAPPEL],
        intent_service.REVISION: [BLOCK_RESUME, BLOCK_METHODE],
        # REFORMULATION (chantier "réponses répétitives", 2026-08-22) :
        # utilisait auparavant [BLOCK_DEFINITION] — EXACTEMENT le même bloc,
        # tiré du même champ `notion["definition"]` (texte fixe, jamais
        # randomisé contrairement à `_block_exemple`), que le plan DEFINITION
        # ci-dessus. Une reformulation ("explique autrement", "je n'ai pas
        # compris"...) obtenait donc un texte quasi identique à la toute
        # première explication — bug réel confirmé (audit "valeur absolue").
        # Correctif : mène avec la MÉTHODE (étapes) et un EXEMPLE (tiré au
        # sort parmi ceux de la notion, voir _block_exemple) — deux angles
        # pédagogiques réellement différents, RÉUTILISANT des mécanismes déjà
        # existants (aucun nouveau contenu, aucun appel LLM supplémentaire).
        # BLOCK_DEFINITION reste en dernier recours : si la notion n'a ni
        # méthode ni exemple, la définition continue d'être montrée (jamais
        # une réponse vide) — comportement inchangé pour ce cas limite.
        intent_service.REFORMULATION: [BLOCK_METHODE, BLOCK_EXEMPLE, BLOCK_DEFINITION],
        # RESTART_BASICS (chantier "reformulations successives", 2026-08-22) :
        # absent d'ici, il retombait sur le plan par défaut [BLOCK_DEFINITION]
        # — identique au plan DEFINITION — malgré son intent typiquement plus
        # marqué ("j'ai rien compris"/"reprends depuis le début") qu'une
        # simple demande de définition. Alignée sur REFORMULATION pour la
        # même raison (angle méthode+exemple plutôt que redite de la
        # définition) — même mécanisme, même garde-fou (BLOCK_DEFINITION en
        # dernier recours si la notion n'a ni méthode ni exemple).
        intent_service.RESTART_BASICS: [BLOCK_METHODE, BLOCK_EXEMPLE, BLOCK_DEFINITION],
        intent_service.EXPLICATION: [BLOCK_DEFINITION, BLOCK_METHODE, BLOCK_EXEMPLE],
    }
    if intent in plans:
        plan = list(plans[intent])
    elif (escalation_level or 0) >= 2:
        plan = list(plans[intent_service.REFORMULATION])
    else:
        plan = [BLOCK_DEFINITION]

    if longueur == "court":
        plan = plan[:1]
    elif longueur == "detaille":
        if BLOCK_ERREUR_FREQUENTE not in plan and intent in (
            intent_service.METHODE, intent_service.EXPLICATION, intent_service.COURS, intent_service.EXEMPLE,
        ):
            plan.append(BLOCK_ERREUR_FREQUENTE)
        if BLOCK_ASTUCE not in plan:
            plan.append(BLOCK_ASTUCE)

    preferred_block = _APPROACH_TO_BLOCK.get(recommended_approach)
    if preferred_block and preferred_block in plan and plan[0] != preferred_block:
        plan.remove(preferred_block)
        plan.insert(0, preferred_block)

    return plan


def compose(strategy, student_context=None, chatbot_settings=None, rng=None):
    """Assemble un `ResponseDraft` à partir d'une `ResponseStrategy` déjà
    décidée (jamais recalculée ici) et d'un `StudentContext`. Ne prend AUCUNE
    décision stratégique — exécute uniquement ce que `strategy` indique.
    `rng` (optionnel) : injecter un `random.Random(seed)` pour un test
    reproductible ; en usage réel, laisser `None` (non-déterminisme voulu,
    voir docstring module)."""
    rng = rng or random.Random()
    student_context = student_context or {}
    chatbot_settings = chatbot_settings or {}
    parametres = student_context.get("parametres") or {}
    longueur = parametres.get("longueur") or chatbot_settings.get("responseLength") or "normal"
    mode = strategy.mode or parametres.get("mode") or chatbot_settings.get("mode")
    avoid = _recent_assistant_texts(student_context)

    notion = None
    if strategy.chapter_id and strategy.topic_id:
        notion = knowledge_engine.get_notion(
            strategy.chapter_id, strategy.topic_id, class_level=student_context.get("class_level"),
        )

    if notion is None:
        block = _block_introuvable(rng, avoid)
        return ResponseDraft(
            text=block.text, blocks=(block,), engine=ENGINE_NAME, intent=strategy.intent,
            chapter_id=strategy.chapter_id, topic_id=strategy.topic_id, used_fallback=True,
            explanation="Aucune notion résolue (chapter_id/topic_id manquant ou inconnu du Knowledge "
                        "Engine) — réponse de repli générique renvoyée, jamais d'erreur.",
            notion_resolved=False,
        )

    level = _resolve_definition_level(student_context, strategy.simplify)
    niveau_methode = _MODE_TO_METHODE_NIVEAU.get(mode, "normal")
    difficulte_label = knowledge_engine.INTENT_DIFFICULTY_TO_LABEL.get(strategy.difficulty)

    plan = _content_plan(
        strategy.intent, longueur, strategy.quantity,
        recommended_approach=getattr(strategy, "recommended_approach", None),
        escalation_level=getattr(strategy, "escalation_level", 0),
    )

    blocks = []
    used_fallback = False
    # Amorcé avec les ids déjà montrés lors des tours PRÉCÉDENTS de la
    # conversation (chantier "répétition des exemples", 2026-08-23) — le même
    # set sert aussi à éviter qu'un BLOCK_EXEMPLE et un BLOCK_EXEMPLE_2 de
    # CETTE réponse ne choisissent le même exemple (comportement préexistant,
    # inchangé). `new_exemple_ids` isole ce qui est ajouté CE tour, pour ne
    # persister que la nouveauté (jamais les ids déjà connus de l'appelant).
    inherited_exemple_ids = set(getattr(strategy, "used_exemple_ids", ()) or ())
    used_exemple_ids = set(inherited_exemple_ids)
    new_exemple_ids = []
    trace = []

    for kind in plan:
        block = None
        if kind == BLOCK_DEFINITION:
            block = _block_definition(rng, avoid, notion, level, strategy.simplify)
        elif kind == BLOCK_METHODE:
            block = _block_methode(rng, avoid, notion, niveau_methode, mode)
        elif kind == BLOCK_EXEMPLE:
            hint_only = strategy.intent == intent_service.INDICE
            block, ex_id = _block_exemple(
                rng, avoid, notion, difficulte_label, used_exemple_ids,
                kind=BLOCK_EXEMPLE, hint_only=hint_only,
            )
            if ex_id:
                used_exemple_ids.add(ex_id)
                if ex_id not in inherited_exemple_ids:
                    new_exemple_ids.append(ex_id)
        elif kind == BLOCK_EXEMPLE_2:
            block, ex_id = _block_exemple(
                rng, avoid, notion, difficulte_label, used_exemple_ids,
                kind=BLOCK_EXEMPLE_2, leadins=_LEADIN_EXEMPLE_2,
            )
            if ex_id:
                used_exemple_ids.add(ex_id)
                if ex_id not in inherited_exemple_ids:
                    new_exemple_ids.append(ex_id)
        elif kind == BLOCK_PROPRIETE:
            block, fell_back = _block_propriete(rng, avoid, notion)
            used_fallback = used_fallback or fell_back
        elif kind == BLOCK_FORMULE:
            block = _block_formule(rng, avoid, notion)
        elif kind == BLOCK_ERREUR_FREQUENTE:
            block = _block_erreur_frequente(rng, avoid, notion)
        elif kind == BLOCK_ASTUCE:
            block = _block_astuce(rng, avoid, notion)
        elif kind == BLOCK_RAPPEL:
            block = _block_rappel(rng, avoid, notion)
        elif kind == BLOCK_RESUME:
            block = _block_resume(rng, avoid, notion)

        if block is not None:
            blocks.append(block)
            trace.append(f"+ {kind}")
        else:
            used_fallback = True
            trace.append(f"- {kind} (indisponible pour cette notion, omis)")

    if longueur == "detaille" and mode == "professeur" and not any(b.kind == BLOCK_CONSEIL for b in blocks):
        blocks.append(_block_conseil(rng, avoid))
        trace.append("+ conseil (mode professeur, longueur détaillée)")

    if longueur != "court":
        blocks.insert(0, _block_introduction(rng, avoid, mode))
        trace = ["+ introduction"] + trace
        ouverture = _block_ouverture(rng, avoid, mode)
        if ouverture is not None:
            blocks.append(ouverture)
            trace.append("+ ouverture")
        else:
            trace.append("- ouverture (mode examen, omise délibérément)")

    notion_resolved = True
    if not blocks:
        # Garde-fou ultime : la notion existe mais n'a produit aucun bloc de
        # contenu exploitable (cas limite, jamais observé dans les cours
        # migrés à ce jour) — jamais de réponse vide. Comme pour le cas
        # `notion is None` ci-dessus, ce n'est PAS une réponse valide :
        # `notion_resolved=False` pour que l'appelant continue la cascade.
        blocks = [_block_introuvable(rng, avoid)]
        used_fallback = True
        notion_resolved = False
        trace.append("(garde-fou) aucun bloc produit -> repli générique")

    text = "\n\n".join(b.text for b in blocks)
    explanation = (
        f"Notion : {notion.get('title')} ({strategy.chapter_id}/{strategy.topic_id})\n"
        f"Niveau de définition : {level} | Mode méthode : {niveau_methode} | Longueur : {longueur}\n"
        + "\n".join(trace)
    )
    return ResponseDraft(
        text=text, blocks=tuple(blocks), engine=ENGINE_NAME, intent=strategy.intent,
        chapter_id=strategy.chapter_id, topic_id=strategy.topic_id, used_fallback=used_fallback,
        explanation=explanation, notion_resolved=notion_resolved,
        primary_approach=_primary_approach(blocks),
        new_exemple_ids=tuple(new_exemple_ids),
    )
