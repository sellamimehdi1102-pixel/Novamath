"""
Filtrage du contenu pédagogique des cours selon le plan effectif de
l'utilisateur (Chantier "Répartition du contenu des cours par plan",
2026-08-26).

Architecture stricte, identique à quota_service.py/plan_service.py :

    server.py  →  course_content_service.py  →  curriculum_registry.py

jamais l'inverse. Ce module ne décide JAMAIS lui-même du plan d'un
utilisateur (aucune comparaison `user["plan"] == ...` ici) — il délègue
entièrement à owner_test_plan_service.effective_plan(user), exactement comme
quota_service.get_limit() le fait déjà, pour que le mode test Owner
fonctionne identiquement ici sans code dédié.

Principe : TOUTES les notions restent accessibles à tous les plans (aucun
verrou sur l'accès lui-même, voir server.py::api_course_content) — seule la
RICHESSE du contenu affiché à l'intérieur d'une notion varie. Rien n'est
jamais inventé : ce module ne fait que retirer des clés déjà présentes dans
le JSON source avant de renvoyer la réponse, jamais en ajouter.

Matrice de classification (issue de l'audit + validation manuelle des 153
notions existantes, voir le chantier) :

    FREE (tous les plans)      : intro, objectif, definition/definitions,
                                  reglesImportantes, formules[0], méthode
                                  profil "normal", exemples[0], erreursFrequentes,
                                  astuce, figure, quizExerciseIds
    PREMIUM+ (Premium et Ultra) : exemples[1:], formules[1:],
                                  methode.etapesParNiveau.debutant/rapide,
                                  explicationSimple, intuition,
                                  exemplesConcrets, erreursFrequentesDetail,
                                  aRetenir
    ULTRA uniquement            : demonstration

Un champ absent ou vide dans le JSON source reste absent après filtrage —
jamais d'erreur, jamais de champ inventé (voir filter_notion() ci-dessous :
chaque bloc ne retire un champ que s'il avait réellement une valeur non
vide, jamais un pop() inconditionnel).
"""
import json

import curriculum_registry
import owner_test_plan_service
from plan_service import Plan

# Même technique que quota_service._PLAN_ORDER (module privé, non réutilisable
# tel quel) — un rang par palier, pour comparer "le plan de l'utilisateur
# couvre-t-il au moins ce palier ?" sans dupliquer de logique de plan : la
# seule source de vérité de CE QU'EST un plan reste plan_service.Plan.
_PLAN_RANK = {Plan.FREE: 0, Plan.PREMIUM: 1, Plan.ULTRA: 2}

# Champs Premium+ : liste simple (booléen "verrouillé si présent et non
# débloqué"), à l'exception de exemples/formules (comptage, traités à part
# car ce sont des listes tronquées, pas des champs binaires).
_PREMIUM_SCALAR_FIELDS = (
    "explicationSimple",
    "intuition",
    "exemplesConcrets",
    "erreursFrequentesDetail",
    "aRetenir",
)


def _effective_plan(user):
    return owner_test_plan_service.effective_plan(user)


def _meets(plan, required):
    return _PLAN_RANK[plan] >= _PLAN_RANK[required]


def filter_notion(notion, plan):
    """Renvoie une COPIE de `notion` avec les champs au-dessus de `plan`
    retirés, et une clé `locked_content` ajoutée décrivant ce qui a été
    retiré (uniquement les champs qui avaient RÉELLEMENT du contenu dans la
    source — jamais une fausse promesse "plus de contenu" sur une notion qui
    n'en a structurellement pas plus, voir §5 "contenu manquant" du
    chantier)."""
    filtered = dict(notion)
    locked = {"premium": False, "premium_extra_examples": 0, "premium_extra_formulas": 0, "ultra": False}

    has_premium = _meets(plan, Plan.PREMIUM)
    has_ultra = _meets(plan, Plan.ULTRA)

    # Exemples : index 0 = Free, le reste = Premium+ (tronqué, jamais réécrit).
    exemples = notion.get("exemples") or []
    if len(exemples) > 1 and not has_premium:
        filtered["exemples"] = exemples[:1]
        locked["premium_extra_examples"] = len(exemples) - 1
        locked["premium"] = True
    # amount==0 ou has_premium déjà vrai : `filtered["exemples"]` reste la
    # liste complète (copie déjà faite via dict(notion) ci-dessus).

    # Formules : premier élément = Free, le reste = Premium+.
    formules = notion.get("formules") or []
    if len(formules) > 1 and not has_premium:
        filtered["formules"] = formules[:1]
        locked["premium_extra_formulas"] = len(formules) - 1
        locked["premium"] = True

    # Méthode : profil "normal" = Free, "debutant"/"rapide" = Premium+.
    methode = notion.get("methode")
    if isinstance(methode, dict):
        etapes_par_niveau = methode.get("etapesParNiveau")
        if isinstance(etapes_par_niveau, dict):
            debutant = etapes_par_niveau.get("debutant") or []
            rapide = etapes_par_niveau.get("rapide") or []
            if (debutant or rapide) and not has_premium:
                filtered_methode = dict(methode)
                filtered_epn = dict(etapes_par_niveau)
                if debutant:
                    filtered_epn["debutant"] = []
                    locked["premium"] = True
                if rapide:
                    filtered_epn["rapide"] = []
                    locked["premium"] = True
                filtered_methode["etapesParNiveau"] = filtered_epn
                filtered["methode"] = filtered_methode

    # Champs Premium+ scalaires (texte/liste), retirés en bloc s'ils ont un
    # contenu réel et que le plan ne couvre pas Premium.
    for field in _PREMIUM_SCALAR_FIELDS:
        value = notion.get(field)
        if value and not has_premium:
            filtered.pop(field, None)
            locked["premium"] = True

    # Démonstration : réservée à Ultra.
    if notion.get("demonstration") and not has_ultra:
        filtered.pop("demonstration", None)
        locked["ultra"] = True

    filtered["locked_content"] = locked
    return filtered


def get_chapter_content(class_level, chapter_id, user):
    """Charge le chapitre `chapter_id` de `class_level` depuis
    curriculum_registry.CURRICULUM_REGISTRY, filtre chaque notion selon le
    plan effectif de `user`, et renvoie le chapitre complet (mêmes clés
    top-level que le JSON source : chapterId/title/icon/notions) ou None si
    la classe ou le chapitre sont inconnus.

    IMPORTANT sécurité : jamais aucun champ Premium/Ultra non autorisé n'est
    présent dans la valeur renvoyée (retiré avant construction de la
    réponse, jamais après) — voir filter_notion()."""
    registry = curriculum_registry.CURRICULUM_REGISTRY
    if class_level not in registry:
        return None
    profile = registry[class_level]
    if profile.courses_dir is None:
        return None
    # Même convention de nommage que cours.js::coursDirFor/loadChapterContent
    # ("Chapitre_7" -> chapitre_7.json) — jamais un chemin construit
    # directement à partir de `chapter_id` tel quel (casse différente, préfixe
    # différent du nom de fichier réel sur disque).
    num = chapter_id.removeprefix("Chapitre_")
    if not num.isdigit():
        return None
    path = profile.courses_dir / f"chapitre_{num}.json"
    if not path.exists():
        return None

    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("chapterId") != chapter_id:
        return None

    plan = _effective_plan(user)
    notions = [filter_notion(n, plan) for n in data.get("notions", [])]

    return {**data, "notions": notions}
