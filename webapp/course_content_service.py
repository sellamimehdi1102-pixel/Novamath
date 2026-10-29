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
                                  profil "normal", exemples de niveau "free",
                                  erreursFrequentes, astuce, figure,
                                  quizExerciseIds
    PREMIUM+ (Premium et Ultra) : exemples de niveau "premium", formules[1:],
                                  methode.etapesParNiveau.debutant/rapide,
                                  explicationSimple, intuition,
                                  exemplesConcrets, erreursFrequentesDetail,
                                  aRetenir
    ULTRA uniquement            : exemples de niveau "ultra", demonstration

Un champ absent ou vide dans le JSON source reste absent après filtrage —
jamais d'erreur, jamais de champ inventé (voir filter_notion() ci-dessous :
chaque bloc ne retire un champ que s'il avait réellement une valeur non
vide, jamais un pop() inconditionnel).

`champsLibresForces` (refonte pédagogique, 2026-10-23) : liste explicite,
par notion, des champs de `_PREMIUM_SCALAR_FIELDS` que l'auteur a jugés
indispensables à la compréhension autonome du contenu Free pour CETTE
notion précise (ex. l'explication intuitive d'une notion à plusieurs règles)
— exempte ces champs du verrou Premium, sans toucher au verrou des autres
notions. Absent : comportement inchangé (tous ces champs restent Premium+).
Ne jamais utiliser pour vider artificiellement le palier Premium d'une
notion entière — seulement pour les champs réellement essentiels.

`apercus` (refonte pédagogique, 2026-10-23) : métadonnées PUBLIQUES
décrivant un contenu Premium/Ultra verrouillé (titre, niveau requis,
description de l'intérêt pédagogique) — jamais le contenu protégé
lui-même, voir _filter_apercus() ci-dessous. Toujours rédigées à la main
par l'auteur du cours, jamais déduites automatiquement du contenu cachée
(qui pourrait changer sans que la description reste exacte) : à l'auteur de
garantir qu'un aperçu annonce un contenu qui existe réellement.

Classification des exemples (refonte pédagogique des cours, 2026-10-23) :
auparavant purement positionnelle (exemples[0] toujours Free, exemples[1:]
toujours Premium+), ce qui ne garantissait aucun exemple gratuit pour chaque
règle/méthode essentielle d'une notion qui en a plusieurs (voir le cours
pilote "Composition de fonctions et dérivation", qui a 3 règles essentielles
— puissance/racine/inverse — mais un seul exemple gratuit avec l'ancien
système). Chaque exemple PEUT désormais porter un champ `niveauAcces`
explicite ("free"/"premium"/"ultra", voir _example_access_level ci-dessous).
Quand ce champ est absent (cas des notions non encore auditées), le repli
positionnel historique s'applique EXACTEMENT comme avant (index 0 = free, le
reste = premium) — aucune des 153 notions existantes ne change de
comportement tant qu'elle n'a pas été explicitement classée exemple par
exemple. Ne jamais ajouter ce champ à une notion sans avoir réellement
examiné le rôle pédagogique de chaque exemple (voir la consigne du chantier :
ne pas rendre gratuits tous les exemples existants par défaut).
"""
import json

import curriculum_registry
import owner_test_plan_service
from plan_service import Plan, pedagogy_plan

# Même technique que quota_service._PLAN_ORDER (module privé, non réutilisable
# tel quel) — un rang par palier, pour comparer "le plan de l'utilisateur
# couvre-t-il au moins ce palier ?" sans dupliquer de logique de plan : la
# seule source de vérité de CE QU'EST un plan reste plan_service.Plan.
_PLAN_RANK = {Plan.FREE: 0, Plan.PREMIUM: 1, Plan.ULTRA: 2}

# Valeurs valides de `exemple["niveauAcces"]` — toute autre valeur (y compris
# absente) retombe sur le repli positionnel historique, voir
# _example_access_level() ci-dessous. Jamais une valeur par défaut "free" en
# cas de typo : une faute de frappe dans ce champ doit se comporter comme une
# absence (repli sûr), jamais exposer accidentellement du contenu Premium.
_VALID_ACCESS_LEVELS = ("free", "premium", "ultra")

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
    # Cours complets (exemples, démonstrations) pour tous quand la gratuité
    # pédagogique est active (voir plan_service.pedagogy_plan).
    return pedagogy_plan(owner_test_plan_service.effective_plan(user))


def _meets(plan, required):
    return _PLAN_RANK[plan] >= _PLAN_RANK[required]


def _filter_apercus(apercus, plan):
    """Un aperçu n'a de sens que pour un palier que l'utilisateur n'a PAS
    encore : jamais annoncer à un Premium un contenu Premium qu'il a déjà
    (bruit inutile), mais toujours lui montrer ce qu'Ultra ajouterait.
    `niveau` invalide (faute de frappe) : aperçu ignoré, jamais affiché par
    défaut — même philosophie de repli sûr que _example_access_level()."""
    kept = []
    for a in apercus or []:
        niveau = a.get("niveau")
        if niveau not in ("premium", "ultra"):
            continue
        required = Plan.PREMIUM if niveau == "premium" else Plan.ULTRA
        if not _meets(plan, required):
            kept.append({"id": a.get("id"), "section": a.get("section"), "niveau": niveau, "titre": a.get("titre"), "description": a.get("description")})
    return kept


def _example_access_level(exemple, index):
    """Niveau d'accès d'un exemple : `exemple["niveauAcces"]` s'il vaut
    explicitement "free"/"premium"/"ultra", sinon repli positionnel
    historique (index 0 = "free", tout le reste = "premium") — voir la
    docstring du module pour la justification de ce repli."""
    level = exemple.get("niveauAcces")
    if level in _VALID_ACCESS_LEVELS:
        return level
    return "free" if index == 0 else "premium"


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

    # Exemples : niveau d'accès explicite par exemple (niveauAcces), avec
    # repli positionnel historique pour les notions non encore classées —
    # voir _example_access_level() et la docstring du module. Jamais de
    # réécriture du contenu gardé, uniquement une troncature de liste.
    exemples = notion.get("exemples") or []
    kept_exemples = []
    hidden_premium = 0
    hidden_ultra = False
    for i, exemple in enumerate(exemples):
        level = _example_access_level(exemple, i)
        if level == "ultra":
            if has_ultra:
                kept_exemples.append(exemple)
            else:
                hidden_ultra = True
        elif level == "premium":
            if has_premium:
                kept_exemples.append(exemple)
            else:
                hidden_premium += 1
        else:
            kept_exemples.append(exemple)
    filtered["exemples"] = kept_exemples
    if hidden_premium:
        locked["premium"] = True
        locked["premium_extra_examples"] = hidden_premium
    if hidden_ultra:
        locked["ultra"] = True

    # Questions éclair (notion.questionsEclair, voir cours.js::
    # questionsEclairHtml) : jamais filtrées par champ (aucun verrou
    # Premium/Ultra dédié, contrairement à erreursFrequentesDetail/aRetenir),
    # MAIS une question ancrée sur un exemple précis ("apres": "exemple:<id>")
    # doit disparaître si CET exemple vient d'être retiré ci-dessus — sinon
    # son id et son énoncé (qui peut indirectement décrire le contenu de
    # l'exemple verrouillé, ex. "pourquoi ce résultat contient-il un facteur
    # -2 ?") restent visibles dans la réponse Free alors que l'exemple
    # correspondant, lui, ne l'est plus : une fuite d'information sur un
    # contenu payant, même sans en recopier le texte intégral. Les autres
    # ancres (pourquoi/intuition/methode/figure) ne sont jamais concernées,
    # elles ne référencent aucun exemple.
    questions_eclair = notion.get("questionsEclair") or []
    if questions_eclair:
        kept_exemple_ids = {ex.get("id") for ex in kept_exemples if ex.get("id")}
        filtered["questionsEclair"] = [
            q
            for q in questions_eclair
            if not (isinstance(q.get("apres"), str) and q["apres"].startswith("exemple:"))
            or q["apres"].removeprefix("exemple:") in kept_exemple_ids
        ]

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
    # contenu réel et que le plan ne couvre pas Premium — sauf ceux que
    # l'auteur a explicitement classés indispensables pour CETTE notion
    # (champsLibresForces, voir docstring du module).
    champs_libres = set(notion.get("champsLibresForces") or ())
    for field in _PREMIUM_SCALAR_FIELDS:
        if field in champs_libres:
            continue
        value = notion.get(field)
        if value and not has_premium:
            filtered.pop(field, None)
            locked["premium"] = True

    # Démonstration : réservée à Ultra.
    if notion.get("demonstration") and not has_ultra:
        filtered.pop("demonstration", None)
        locked["ultra"] = True

    # Aperçus publics des contenus verrouillés (apercus, voir docstring du
    # module) — jamais le contenu lui-même, uniquement des métadonnées
    # décoratives. Absent de la réponse si la notion n'en déclare aucun, ou
    # si plus rien n'est à débloquer pour ce plan (Ultra ne reçoit jamais
    # d'aperçu).
    apercus = _filter_apercus(notion.get("apercus"), plan)
    if apercus:
        filtered["apercus"] = apercus
    else:
        filtered.pop("apercus", None)

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
