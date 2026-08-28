"""
Génère les fichiers de cours (webapp/static/data/cours_<classe>/chapitre_*.json)
d'une classe déclarée dans curriculum_registry.py, à partir de sa seule
banque d'exercices (`enonce`/`answer`/`hint`/`solution_steps`/`chapter_id`/
`notion`/`difficulty`) — aucune autre source, aucun contenu inventé.

Générique par construction : aucune logique ne nomme une classe précise
("premiere", "seconde"...) — tout part de curriculum_registry.CURRICULUM_REGISTRY
et de la seule forme des données réellement présentes dans exercise_bank.
Fonctionne à l'identique pour toute classe qui y est déclarée.

Ce script ne crée AUCUN deuxième système d'affichage : le résultat a
exactement le schéma déjà lu par chatbot/knowledge_engine.py et
static/js/cours.js (mêmes champs que webapp/static/data/cours/chapitre_*.json).
Les champs KE v2 (proprietes, vocabulaire_associe, synonymes, prerequis,
notions_liees) exigeraient une curation humaine ou une source externe
(topic_crosswalk.json) que rien dans exercise_bank ne permet de déduire sans
risque d'invention — laissés vides, exactement comme
knowledge_engine.get_prerequis()/get_notions_liees() dégradent déjà pour
tout champ non curé. schemaVersion=2 est utilisé quand même (les listes
vides sont un schéma valide, voir validate_cours_schema.REQUIRED_V2_LIST_FIELDS)
pour que le chatbot bénéficie des accesseurs KE v2 sur les champs qui, eux,
sont réellement dérivables (objectifs_pedagogiques, tags, difficulte).

Chaque champ pédagogique est DÉRIVÉ, jamais halluciné — aucune règle
mathématique n'est écrite par ce script, seul du texte déjà rédigé dans la
banque (hint/solution_steps/answer) est sélectionné, recomposé ou dupliqué :

- `definition`/`definitions.lycee` <- le hint le plus représentatif de la
  notion (le plus long parmi les plus fréquents : fréquence = signal de
  canonicité, longueur = signal de complétude).
- `definitions.college`             <- le hint distinct le plus court, sert
  d'angle "explication intuitive" plus simple (chatbot uniquement,
  get_definition(level="college") — cours.js ne lit que `definition`,
  aucun changement d'affichage).
- `reglesImportantes`/`aRetenir`    <- les hints distincts restants, triés
  par fréquence (les plus répétés = les plus structurants pour la notion).
- `methode.etapes`/`etapesParNiveau.normal` <- les solution_steps de
  l'exercice le PLUS DÉTAILLÉ de la notion (le plus grand nombre d'étapes
  réelles), jamais recomposées.
- `exemples`       <- des exercices réels, sélectionnés pour couvrir des
  difficultés distinctes quand c'est possible (progression pédagogique),
  jamais un énoncé recomposé.
- `quizExerciseIds` <- des exercices réels de la notion, disjoints des
  exemples déjà montrés (jamais la même question qu'un exemple déjà résolu).
- `objectifs_pedagogiques` <- l'objectif (déjà templaté) mis sous forme de
  liste, tel que documenté par knowledge_engine.get_objectifs_pedagogiques().
- `tags`           <- mots significatifs du nom de la notion (aucun
  vocabulaire externe).
- `difficulte`      <- la difficulté majoritaire réelle des exercices de la
  notion (vote, jamais une valeur choisie arbitrairement).
- `erreursFrequentes`/`astuce` : seulement si un hint contient un marqueur
  textuel explicite ("attention", "ne pas confondre", "astuce"...) — sinon
  laissés vides plutôt que fabriqués. Extraction purement lexicale, jamais
  de règle générée.

Usage : python -m generate_cours_from_bank <class_level> (depuis webapp/).
Valide systématiquement sa propre sortie avec le validateur déjà existant
(chatbot.validate_cours_schema.validate_all) — jamais de duplication de la
logique de validation.
"""
import json
import re
import sys
import unicodedata
from collections import Counter

import curriculum_registry

EXERCISES_BANK_SCALE_TO_LABEL = {1: "facile", 2: "facile", 3: "moyen", 4: "difficile", 5: "difficile"}
DIFFICULTE_LEVELS = ("facile", "moyen", "difficile")
STEP_COLORS = ["blue", "purple", "green", "orange", "pink"]
STEP_ICONS = ["search", "sliders", "check", "compass", "penSquare"]
MAX_EXEMPLES_PAR_NOTION = 4
MAX_REGLES_PAR_NOTION = 5
MAX_ARETENIR_PAR_NOTION = 6
MAX_QUIZ_PAR_NOTION = 3
MAX_TAGS_PAR_NOTION = 4

# Marqueurs purement lexicaux (aucune règle mathématique associée) : un hint
# n'est retenu comme "erreur fréquente" ou "astuce" QUE s'il contient un de
# ces mots — sinon la section reste vide plutôt que d'inventer un contenu
# pédagogique. Générique : ne dépend d'aucun vocabulaire propre à une classe.
_ERREUR_MARKERS = re.compile(
    r"\battention\b|ne pas confondre|ne confondez|\bpi[eè]ge\b|\berreur\b|à ne pas|ne pas oublier",
    re.IGNORECASE,
)
_ASTUCE_MARKERS = re.compile(
    r"\bastuce\b|\bconseil\b|pense[sz]? à|n['’]oublie[sz]? pas|\bretenez\b|\bretiens\b|rappel[- ]toi|\btruc\b",
    re.IGNORECASE,
)

# Mots trop génériques pour servir de tag (articles, connecteurs français
# courants) — filtrage purement mécanique, pas un lexique métier.
_STOPWORDS = {
    "le", "la", "les", "un", "une", "des", "de", "du", "et", "en", "au", "aux",
    "sur", "dans", "avec", "pour", "par", "d", "l", "à", "ou", "que", "qui",
}


def _slug(text):
    """Même esprit que canonical_ids._normalize_label (aplatit accents/casse)
    + remplacement des espaces par des tirets, pour obtenir un id conforme à
    la convention déjà utilisée dans static/data/cours/chapitre_*.json
    (ex. "puissances-entieres-relatives")."""
    folded = "".join(c for c in unicodedata.normalize("NFKD", text or "") if not unicodedata.combining(c))
    folded = folded.lower().strip()
    return "-".join(part for part in folded.replace("'", " ").split() if part) or "notion"


def _flatten_solution_steps(steps):
    if isinstance(steps, list):
        return [s for s in steps if isinstance(s, str) and s.strip()]
    if isinstance(steps, dict):
        flat = []
        for value in steps.values():
            flat.extend(value) if isinstance(value, list) else flat.append(value)
        return [s for s in flat if isinstance(s, str) and s.strip()]
    return []


def _output_dir(class_level):
    return curriculum_registry.STATIC_DATA_DIR / f"cours_{class_level}"


def _ranked_distinct_hints(exercises):
    """Hints distincts triés par (fréquence décroissante, longueur
    décroissante) — le hint le plus répété/complet d'une notion en est
    généralement la reformulation la plus canonique, jamais un texte généré."""
    counts = Counter((ex.get("hint") or "").strip() for ex in exercises)
    counts.pop("", None)
    return [h for h, _ in sorted(counts.items(), key=lambda kv: (kv[1], len(kv[0])), reverse=True)]


def _build_etapes(steps):
    return [
        {"icone": STEP_ICONS[i % len(STEP_ICONS)], "couleur": STEP_COLORS[i % len(STEP_COLORS)], "texte": s}
        for i, s in enumerate(steps)
    ]


def _pick_examples(exercises, limit):
    """Priorise la diversité de difficulté réelle (une progression facile ->
    difficile, comme les cours rédigés à la main) avant de compléter avec les
    exercices restants — jamais un énoncé recomposé, toujours un exercice
    réel tel quel."""
    by_difficulty = {}
    for ex in exercises:
        if _flatten_solution_steps(ex.get("solution_steps")):
            by_difficulty.setdefault(ex.get("difficulty"), ex)
    ordered_ids = set()
    picked = []
    for diff in sorted(by_difficulty):
        picked.append(by_difficulty[diff])
        ordered_ids.add(by_difficulty[diff]["id"])
        if len(picked) >= limit:
            return picked
    for ex in exercises:
        if ex["id"] in ordered_ids:
            continue
        if not _flatten_solution_steps(ex.get("solution_steps")):
            continue
        picked.append(ex)
        ordered_ids.add(ex["id"])
        if len(picked) >= limit:
            break
    return picked


def _tags_from_label(notion_label):
    folded = "".join(c for c in unicodedata.normalize("NFKD", notion_label or "") if not unicodedata.combining(c))
    words = re.findall(r"[a-zA-Z]+", folded.lower())
    seen = []
    for w in words:
        if w in _STOPWORDS or len(w) < 3 or w in seen:
            continue
        seen.append(w)
        if len(seen) >= MAX_TAGS_PAR_NOTION:
            break
    return seen


def _majority_difficulty_label(exercises):
    labels = [EXERCISES_BANK_SCALE_TO_LABEL.get(ex.get("difficulty")) for ex in exercises]
    labels = [l for l in labels if l in DIFFICULTE_LEVELS]
    if not labels:
        return ""
    return Counter(labels).most_common(1)[0][0]


def _build_notion(notion_label, exercises):
    hints_ranked = _ranked_distinct_hints(exercises)
    if hints_ranked:
        definition = hints_ranked[0]
        definition_college = min(hints_ranked, key=len) if len(hints_ranked) > 1 else ""
        remaining_hints = hints_ranked[1:]
    else:
        definition = (
            f"Cette notion est travaillée à travers des exercices d'application — "
            f"voir les exemples ci-dessous."
        )
        definition_college = ""
        remaining_hints = []
    if definition_college == definition:
        definition_college = ""

    regles = remaining_hints[:MAX_REGLES_PAR_NOTION]
    a_retenir = remaining_hints[:MAX_ARETENIR_PAR_NOTION] or regles

    erreurs = [h for h in hints_ranked if _ERREUR_MARKERS.search(h)]
    astuce_candidates = [h for h in hints_ranked if _ASTUCE_MARKERS.search(h)]
    astuce = astuce_candidates[0] if astuce_candidates else ""

    # Méthode : les étapes réelles de l'exercice le plus détaillé de la
    # notion (le plus d'étapes réelles), jamais recomposées.
    with_steps = [ex for ex in exercises if _flatten_solution_steps(ex.get("solution_steps"))]
    methode_source = max(with_steps, key=lambda ex: len(_flatten_solution_steps(ex["solution_steps"]))) if with_steps else None
    etapes = _build_etapes(_flatten_solution_steps(methode_source["solution_steps"])) if methode_source else []

    exemples = []
    exemple_ids = set()
    for ex in _pick_examples(exercises, MAX_EXEMPLES_PAR_NOTION):
        steps = _flatten_solution_steps(ex.get("solution_steps"))
        exemples.append({
            "id": f"exemple-{ex['id']}",
            "titre": f"Exemple {len(exemples) + 1}",
            "enonce": ex.get("enonce", ""),
            "calcul": [{"expr": "", "texte": s} for s in steps],
            "reponse": ex.get("answer", ""),
            "difficulte": EXERCISES_BANK_SCALE_TO_LABEL.get(ex.get("difficulty"), "moyen"),
        })
        exemple_ids.add(ex["id"])

    # Quiz : des exercices réels, jamais les mêmes questions que les exemples
    # déjà résolus juste au-dessus (sinon la notion=`quiz` recopierait une
    # réponse déjà donnée).
    quiz_ids = [ex["id"] for ex in exercises if ex["id"] not in exemple_ids][:MAX_QUIZ_PAR_NOTION]
    if not quiz_ids:
        quiz_ids = [ex["id"] for ex in exercises[:MAX_QUIZ_PAR_NOTION]]

    notion_id = _slug(notion_label)
    definitions = {"lycee": definition}
    if definition_college:
        definitions["college"] = definition_college

    objectif = f"À la fin de ce cours, tu sauras résoudre des exercices sur {notion_label}."

    return {
        "id": notion_id,
        "title": notion_label,
        "schemaVersion": 2,
        "intro": f"Dans cette leçon, tu vas apprendre à utiliser : {notion_label}.",
        "objectif": objectif,
        "definition": definition,
        "definitions": definitions,
        "reglesImportantes": regles,
        "formules": [],
        "methode": {"titre": f"Méthode — {notion_label}", "etapes": etapes} if etapes else {},
        "exemples": exemples,
        "erreursFrequentes": erreurs,
        "erreursFrequentesDetail": [],
        "astuce": astuce,
        "aRetenir": a_retenir,
        "figure": None,
        "quizExerciseIds": quiz_ids,
        "topic_id": notion_id,
        "proprietes": [],
        "vocabulaire_associe": [],
        "synonymes": [],
        # Documenté par knowledge_engine.get_objectifs_pedagogiques() : reprend
        # l'objectif singulier sous forme de liste, aucune donnée inventée.
        "objectifs_pedagogiques": [objectif],
        "prerequis": [],
        "notions_liees": [],
        "difficulte": _majority_difficulty_label(exercises),
        "tags": _tags_from_label(notion_label),
    }


def generate(class_level):
    profile = curriculum_registry.CURRICULUM_REGISTRY[class_level]
    if profile.exercise_bank is None or not profile.exercise_bank.exists():
        raise SystemExit(f"Aucune banque d'exercices déclarée/trouvée pour {class_level!r} — rien à générer.")

    bank = json.loads(profile.exercise_bank.read_text(encoding="utf-8"))
    for i, ex in enumerate(bank):
        if ex.get("id") is None:
            ex["id"] = i

    by_chapter = {}
    for ex in bank:
        chapter_id = ex.get("chapter_id")
        notion = ex.get("notion")
        if not chapter_id or not notion:
            continue
        by_chapter.setdefault(chapter_id, {}).setdefault(notion, []).append(ex)

    out_dir = _output_dir(class_level)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for chapter_id, notions_by_label in sorted(by_chapter.items()):
        chapter = {
            "chapterId": chapter_id,
            # Aucun programme officiel déclaré pour cette classe (program_file
            # absent du registre) : titre dérivé de l'identifiant, comme le
            # fait déjà /api/chapters (server.py::api_chapters) quand
            # CHAPTER_META ne connaît pas ce chapitre.
            "title": chapter_id.replace("_", " "),
            "icon": "layers",
            "notions": [
                _build_notion(notion_label, exs)
                for notion_label, exs in sorted(notions_by_label.items())
            ],
        }
        path = out_dir / f"{chapter_id.lower()}.json"
        path.write_text(json.dumps(chapter, ensure_ascii=False, indent=2), encoding="utf-8")
        written.append(path)
    return out_dir, written


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage : python -m generate_cours_from_bank <class_level>")
    target_class_level = sys.argv[1]
    if target_class_level not in curriculum_registry.CURRICULUM_REGISTRY:
        raise SystemExit(f"Classe inconnue du registre : {target_class_level!r}")
    out_dir, written = generate(target_class_level)
    print(f"{len(written)} chapitre(s) écrit(s) dans {out_dir}")

    from chatbot.validate_cours_schema import validate_all
    errors, stats = validate_all(cours_dir=out_dir)
    print(f"{stats['chapters']} chapitres, {stats['notions']} notions validés ({stats['schema_v2_notions']} en schemaVersion 2)")
    if errors:
        print(f"\n{len(errors)} erreur(s) :")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print("Aucune erreur de schéma.")
