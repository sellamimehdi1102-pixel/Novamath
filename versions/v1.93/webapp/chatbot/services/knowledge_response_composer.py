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
_INTROUVABLE_VARIANTS = [
    "Je n'ai pas trouvé de notion de cours correspondant précisément à ta demande. Peux-tu reformuler, ou préciser le chapitre concerné ?",
    "Je ne retrouve pas exactement cette notion dans le programme actuel. Essaie de reformuler ou de préciser le chapitre.",
    "Cette notion ne correspond à rien de précis dans les cours disponibles pour l'instant. Peux-tu préciser ta demande ?",
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
    exemple = knowledge_engine.get_exemple(notion, difficulte=difficulte_label)
    if exemple and exemple.get("id") in exclude_ids:
        alternatives = [e for e in (notion.get("exemples") or []) if e.get("id") not in exclude_ids]
        exemple = rng.choice(alternatives) if alternatives else None
    if not exemple:
        return None, None
    lead = _pick(rng, leadins or _LEADIN_EXEMPLE, avoid)
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
def _content_plan(intent, longueur, quantity):
    """Renvoie la liste ordonnée des blocs de CONTENU (hors introduction/
    ouverture, ajoutés systématiquement sauf en longueur "court") pour un
    intent donné. `quantity`/`longueur` ajustent le nombre d'exemples."""
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
        intent_service.REFORMULATION: [BLOCK_DEFINITION],
        intent_service.EXPLICATION: [BLOCK_DEFINITION, BLOCK_METHODE, BLOCK_EXEMPLE],
    }
    plan = list(plans.get(intent, [BLOCK_DEFINITION]))

    if longueur == "court":
        plan = plan[:1]
    elif longueur == "detaille":
        if BLOCK_ERREUR_FREQUENTE not in plan and intent in (
            intent_service.METHODE, intent_service.EXPLICATION, intent_service.COURS, intent_service.EXEMPLE,
        ):
            plan.append(BLOCK_ERREUR_FREQUENTE)
        if BLOCK_ASTUCE not in plan:
            plan.append(BLOCK_ASTUCE)

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
        )

    level = _resolve_definition_level(student_context, strategy.simplify)
    niveau_methode = _MODE_TO_METHODE_NIVEAU.get(mode, "normal")
    difficulte_label = knowledge_engine.INTENT_DIFFICULTY_TO_LABEL.get(strategy.difficulty)

    plan = _content_plan(strategy.intent, longueur, strategy.quantity)

    blocks = []
    used_fallback = False
    used_exemple_ids = set()
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
        elif kind == BLOCK_EXEMPLE_2:
            block, ex_id = _block_exemple(
                rng, avoid, notion, difficulte_label, used_exemple_ids,
                kind=BLOCK_EXEMPLE_2, leadins=_LEADIN_EXEMPLE_2,
            )
            if ex_id:
                used_exemple_ids.add(ex_id)
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

    if not blocks:
        # Garde-fou ultime : la notion existe mais n'a produit aucun bloc de
        # contenu exploitable (cas limite, jamais observé dans les cours
        # migrés à ce jour) — jamais de réponse vide.
        blocks = [_block_introuvable(rng, avoid)]
        used_fallback = True
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
        explanation=explanation,
    )
