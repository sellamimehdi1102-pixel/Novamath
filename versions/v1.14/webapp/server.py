"""
Backend Flask pour l'interface web NovaMath.
Remplace l'UI Gradio de 06_quiz_app.py par une API JSON consommée par
webapp/static/index.html + script.js, tout en gardant EXACTEMENT la même
logique de sélection d'exercices et de prédiction de niveau (même
exercises_bank.json, mêmes modèles models/*.pkl).
"""
import json
import math
import os
import re
import random
import secrets
import tempfile
import uuid
from datetime import date as _date
from pathlib import Path

import joblib
from flask import Flask, jsonify, request, session, redirect, Response, g

import auth
import db
from auth import (
    auth_bp, get_current_user, login_required, read_user_stats, write_user_stats, csrf_protect,
    read_user_settings, write_user_settings, read_user_course_progress, write_user_course_progress,
)

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
REVIEWS_PATH = DATA_DIR / "reviews.json"
NATURAL_BANK_PATH = ROOT / "exercises_bank_natural.json"

# ── Chargement et Attribution d'IDs Automatiques ──────────────────────────────
with open(ROOT / "exercises_bank.json", "r", encoding="utf-8") as f:
    raw_bank = json.load(f)

BANK = []
for i, ex in enumerate(raw_bank):
    ex["id"] = ex.get("id") if ex.get("id") is not None else i
    for field in ["enonce", "answer", "hint"]:
        if isinstance(ex.get(field), str):
            val = ex[field]
            if "\\" in val and "$" not in val:
                val = f"${val}$"
            ex[field] = val
    BANK.append(ex)

BANK_BY_ID = {e["id"]: e for e in BANK}

MODEL = joblib.load(ROOT / "models" / "level_predictor.pkl")
QUIZ_DIFFS = joblib.load(ROOT / "models" / "quiz_difficulties.pkl")
N_QUESTIONS = len(QUIZ_DIFFS)
LEVEL_LABELS = {1: ("🌱", "Débutant"), 2: ("⚡", "Intermédiaire"), 3: ("🏆", "Avancé")}


def get_chapter_num(name):
    nums = re.findall(r"\d+", name)
    return int(nums[0]) if nums else 0


CHAPTERS = sorted(list(set(ex.get("chapter_id", "") for ex in BANK)), key=get_chapter_num)

# ── Métadonnées de chapitres (titres + notions de cours), additif ────────────
# Lues depuis "Programme AI.json" (déjà présent dans le dépôt), utilisées
# uniquement pour enrichir /api/chapters — n'affecte pas la sélection d'exercices.
try:
    with open(ROOT / "Programme AI.json", "r", encoding="utf-8") as f:
        _programme = json.load(f)
    CHAPTER_META = {c["id"]: c for c in _programme.get("chapters", [])}
except FileNotFoundError:
    CHAPTER_META = {}

# ── Banque en français naturel (optionnelle), additif ─────────────────────────
# Générée par 07_naturalize_exercises.py. Si absente, le contrat existant reste
# inchangé : on retombe sur les énoncés originaux de exercises_bank.json.
try:
    with open(NATURAL_BANK_PATH, "r", encoding="utf-8") as f:
        _natural = json.load(f)
    NATURAL_BY_ID = {e["id"]: e for e in _natural}
except FileNotFoundError:
    NATURAL_BY_ID = {}

# ── Banque de reformulations (optionnelle), additif ───────────────────────────
# Générée par 07_naturalize_exercises.py également : une liste de variantes
# ("natural_variants") par exercice, alignée par position avec exercises_bank.json.
# Utilisée uniquement pour la statistique "nombre de variantes Natural" par
# notion exposée dans /api/chapters — n'affecte ni la sélection ni l'affichage
# des exercices.
REFORMULATIONS_PATH = ROOT / "exercises_bank_reformulations.json"
try:
    with open(REFORMULATIONS_PATH, "r", encoding="utf-8") as f:
        _reformulations = json.load(f)
    VARIANTS_COUNT_BY_INDEX = [len(e.get("natural_variants") or []) for e in _reformulations]
except FileNotFoundError:
    VARIANTS_COUNT_BY_INDEX = []


def _n_variants_for(chapter_exercises_indices):
    """Somme des variantes Natural pour un sous-ensemble d'exercices, identifiés
    par leur index dans BANK (= position dans exercises_bank_reformulations.json,
    listes alignées par construction — voir 07_naturalize_exercises.py)."""
    return sum(
        VARIANTS_COUNT_BY_INDEX[i] for i in chapter_exercises_indices if i < len(VARIANTS_COUNT_BY_INDEX)
    )


# ── Niveaux de difficulté réellement présents dans la banque, additif ─────────
# Calculé dynamiquement (au lieu d'une échelle 1-3 supposée en dur) : la banque
# régénérée utilise désormais 5 niveaux. Toute logique d'agrégation par
# difficulté (répartition, dominante) doit couvrir l'échelle réelle, pas une
# échelle historique figée.
DIFFICULTY_LEVELS = sorted(set(e.get("difficulty") for e in BANK if e.get("difficulty") is not None))

# ── Correspondance difficulté d'exercice → niveau élève (additif) ─────────────
# Le modèle de prédiction (models/level_predictor.pkl) et QUIZ_DIFFS ont été
# entraînés sur une échelle à len(LEVEL_LABELS) niveaux (Débutant/Intermédiaire/
# Avancé). La banque régénérée utilise désormais une échelle de difficulté plus
# fine (1 à 5). Sans cette correspondance, pick_exercise()/practice_choices()
# ne pourraient jamais sélectionner un exercice dont la difficulté dépasse
# len(LEVEL_LABELS) : ~40% de la banque (difficultés 4 et 5) resterait
# définitivement inatteignable en évaluation/entraînement adaptatif.
# Formule proportionnelle, dynamique et rétrocompatible : si la banque a déjà
# exactement len(LEVEL_LABELS) niveaux (ancienne échelle 1-3), c'est l'identité.
_N_STUDENT_LEVELS = len(LEVEL_LABELS)
_MAX_BANK_DIFFICULTY = max(DIFFICULTY_LEVELS) if DIFFICULTY_LEVELS else _N_STUDENT_LEVELS


def difficulty_bucket(d):
    if not _MAX_BANK_DIFFICULTY:
        return d
    return min(_N_STUDENT_LEVELS, max(1, math.ceil(d * _N_STUDENT_LEVELS / _MAX_BANK_DIFFICULTY)))


# ── Logique de sélection (identique à 06_quiz_app.py, adaptée à difficulty_bucket) ─
def pick_exercise(difficulty, exclude_ids, allowed_chapters):
    pool = [e for e in BANK if e.get("chapter_id") in allowed_chapters] if allowed_chapters else BANK
    candidates = [e for e in pool if difficulty_bucket(e["difficulty"]) == difficulty and e["id"] not in exclude_ids]
    if not candidates:
        for d in [1, -1, 2, -2]:
            candidates = [
                e for e in pool if difficulty_bucket(e["difficulty"]) == difficulty + d and e["id"] not in exclude_ids
            ]
            if candidates:
                break
    if not candidates:
        candidates = pool
    return random.choice(candidates)


def predict_level(responses, difficulties):
    r = (responses + [0] * 7)[:7]
    # Les difficultés passées ici sont celles, réelles, des exercices tirés
    # (echelle de la banque) : on les ramène sur l'échelle 1..len(LEVEL_LABELS)
    # attendue par le modèle avant de construire les features (voir
    # difficulty_bucket ci-dessus).
    d = ([difficulty_bucket(x) for x in difficulties] + [2] * 7)[:7]
    total = sum(r)
    weighted = sum(r[i] * d[i] for i in range(7))
    features = r + [
        sum(r[i] for i, v in enumerate(d) if v == 1),
        sum(r[i] for i, v in enumerate(d) if v == 2),
        sum(r[i] for i, v in enumerate(d) if v == 3),
        total,
        weighted,
    ]
    return int(MODEL.predict([features])[0])


def _flatten_solution_steps(steps):
    """Certains exercices ont solution_steps sous forme de dict plutôt que de
    liste (ex: {"produit": "...", "quotient": "..."}) — on aplatit en liste
    ordonnée pour que le frontend puisse toujours itérer dessus."""
    if isinstance(steps, list):
        return steps
    if isinstance(steps, dict):
        flat = []
        for value in steps.values():
            flat.extend(value) if isinstance(value, list) else flat.append(value)
        return flat
    return []


def public_exercise(ex):
    """Exercice envoyé au front (enonce + hint + answer inclus, le JS gère l'affichage/masquage).
    Préfère la version en français naturel (exercises_bank_natural.json) si disponible,
    champ par champ, en conservant l'id/chapter_id/notion/difficulty d'origine."""
    natural = NATURAL_BY_ID.get(ex["id"], {})
    steps = natural.get("solution_steps") if "solution_steps" in natural else ex.get("solution_steps")
    return {
        "id": ex["id"],
        "chapter_id": ex.get("chapter_id"),
        "notion": ex.get("notion"),
        "difficulty": ex.get("difficulty"),
        "enonce": natural.get("enonce", ex.get("enonce")),
        "hint": natural.get("hint", ex.get("hint")),
        "answer": natural.get("answer", ex.get("answer")),
        "solution_steps": _flatten_solution_steps(steps),
    }


def practice_choices(allowed, level):
    pool = [e for e in BANK if e.get("chapter_id") in allowed] if allowed else BANK
    return [
        {"id": e["id"], "label": f"{e.get('chapter_id')} : {e.get('notion')}"}
        for e in pool
        if difficulty_bucket(e["difficulty"]) == level
    ]


# ── Secrets ───────────────────────────────────────────────────────────────────
# Toujours lus depuis une variable d'environnement en priorité (déploiement réel :
# NOVAMATH_SECRET_KEY / NOVAMATH_ADMIN_KEY). En local sans configuration, un secret
# aléatoire est généré une seule fois puis persisté dans un fichier hors du dossier
# static/ (jamais servi publiquement) — pour ne jamais écrire un secret en dur dans
# le code, tout en gardant les sessions stables entre deux redémarrages du serveur.
def _get_or_create_secret(env_name, file_name):
    value = os.environ.get(env_name)
    if value:
        return value
    path = DATA_DIR / file_name
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    value = secrets.token_urlsafe(32)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")
    return value


# ── App Flask ───────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder="static", static_url_path="")
app.secret_key = _get_or_create_secret("NOVAMATH_SECRET_KEY", ".flask_secret_key")
# Clé admin pour la modération des avis (masquer/épingler/modifier/supprimer
# n'importe quel avis) — jamais en dur dans le code (voir _get_or_create_secret).
ADMIN_KEY = _get_or_create_secret("NOVAMATH_ADMIN_KEY", ".admin_key")

db.init_db()
app.register_blueprint(auth_bp)

# Pages qui nécessitent désormais un compte connecté : servies via une route
# explicite (au lieu du handler statique automatique de Flask) pour pouvoir
# vérifier la session côté serveur avant d'envoyer le HTML — une redirection
# uniquement côté client (JS) laisserait la page protégée s'afficher un
# instant et serait contournable.
PROTECTED_PAGES = ["dashboard.html", "chapitres.html", "cours.html", "exercice.html", "evaluation.html", "profil.html"]


def _serve_protected(page):
    user = get_current_user()
    if user is None:
        return redirect(f"/?next={page}")
    # Injecte l'id du compte connecté dans la page, avant tout script applicatif :
    # store.js s'en sert pour purger de façon synchrone tout cache localStorage
    # laissé par un compte précédent utilisé sur le même navigateur (voir
    # store.js::syncAccountScope) — sans cette info, deux comptes partageant le
    # même navigateur affichaient la progression/l'avatar l'un de l'autre tant
    # que /api/auth/me n'avait pas répondu (fenêtre de course avec les scripts
    # qui lisent localStorage dès leur chargement).
    html = (Path(app.static_folder) / page).read_text(encoding="utf-8")
    # Nonce dédié à cet unique script inline : permet une CSP script-src stricte
    # (pas de 'unsafe-inline') tout en autorisant ce script précis — voir
    # security_headers() ci-dessous, qui lit g.csp_nonce pour construire l'en-tête.
    nonce = secrets.token_urlsafe(16)
    g.csp_nonce = nonce
    injected = f'<script nonce="{nonce}">window.__NOVAMATH_USER_ID__ = {json.dumps(user["id"])};</script>'
    html = html.replace("<head>", f"<head>\n{injected}", 1)
    return Response(html, mimetype="text/html")


for _page in PROTECTED_PAGES:
    app.add_url_rule(f"/{_page}", endpoint=f"protected_{_page}", view_func=lambda p=_page: _serve_protected(p))


# settings.html a été retiré : les Paramètres sont désormais un popup ouvert
# depuis n'importe quelle page (voir static/js/settingsPopup.js). Un ancien
# lien/favori vers /settings.html est redirigé plutôt que de renvoyer un 404.
@app.route("/settings.html")
def _redirect_legacy_settings_page():
    return redirect("/dashboard.html")


@app.after_request
def security_headers(response):
    """Projet en développement actif : on désactive tout cache navigateur pour
    être sûr que chaque rechargement récupère la dernière version du JS/CSS
    (sinon un fix déjà livré peut sembler "ne pas s'appliquer" côté client)."""
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    # ── En-têtes de sécurité ───────────────────────────────────────────────
    # script-src : 'self' + le CDN KaTeX (rendu des énoncés mathématiques,
    # chargé sur exercice.html/evaluation.html/dashboard.html/profil.html),
    # plus le nonce du script injecté par _serve_protected() sur les pages
    # protégées (aucun autre script inline n'existe dans le projet — vérifié).
    # style-src garde 'unsafe-inline' car de nombreux styles inline sont
    # générés par le JS existant (dashboard.js, profil.js, reviews.js...) ;
    # les retirer nécessiterait de les migrer vers des classes CSS, hors
    # périmètre de cette passe (voir TODO.md). Il inclut aussi le CDN KaTeX
    # pour sa feuille de style (katex.min.css).
    KATEX_CDN = "https://cdn.jsdelivr.net"
    nonce = getattr(g, "csp_nonce", None)
    script_src = f"'self' {KATEX_CDN} 'nonce-{nonce}'" if nonce else f"'self' {KATEX_CDN}"
    response.headers["Content-Security-Policy"] = (
        f"default-src 'self'; script-src {script_src}; style-src 'self' 'unsafe-inline' {KATEX_CDN}; "
        f"img-src 'self' data:; font-src 'self' {KATEX_CDN}; connect-src 'self'; "
        "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    # Défense en profondeur pré-CSP (navigateurs anciens sans frame-ancestors) :
    response.headers["X-Frame-Options"] = "DENY"
    return response


def reset_session():
    session["q"] = 0
    session["resps"] = []
    session["diffs"] = []
    session["used_ids"] = []
    session["allowed"] = []
    session["current_level"] = 1
    session["history"] = []
    session["practice_resps"] = []
    session["practice_diffs"] = []


def _serve_landing():
    """Point d'entrée UNIQUE de la landing page — pour `/` ET `/index.html`.

    Cause racine du bug "le mode invité ne se réinitialise pas" : `index.html`
    vit dans `app.static_folder` avec `static_url_path=""`, donc Flask le
    servait AUSSI tel quel via son handler statique automatique à l'URL
    `/index.html`, sans jamais passer par cette vue ni par la moindre
    vérification de session — exactement comme les pages de PROTECTED_PAGES
    auraient été vulnérables sans `_serve_protected()`. Un invité revenant sur
    la page d'accueil par ce chemin (bouton retour, lien direct, etc.)
    conservait donc une session invité toujours valide, que le clic sur
    "Démarrer l'évaluation" réutilisait (voir auth.js::currentAccount) au lieu
    d'en recréer une neuve — d'où les anciennes données qui réapparaissaient.

    En enregistrant explicitement cette même vue sur les deux routes (une
    règle explicite est toujours prioritaire sur la règle générique du
    handler statique dans le routage Werkzeug), la landing page devient un
    unique point de passage obligé, et donc l'endroit fiable où appliquer la
    règle métier : atteindre la landing page met TOUJOURS fin à une session
    invité en cours, sans exception ni contournement possible. Un compte réel
    n'est jamais concerné (redirection directe vers le dashboard, comportement
    inchangé)."""
    user = get_current_user()
    if user is not None and user["auth_provider"] != "guest":
        return redirect("/dashboard.html")

    html = (Path(app.static_folder) / "index.html").read_text(encoding="utf-8")
    resp = Response(html, mimetype="text/html")

    if user is not None:  # invité : fin de session immédiate et définitive
        auth._log_security_event("guest_session_ended", user_id=user["id"])
        auth._purge_account(user["id"])
        session.clear()
        resp.delete_cookie(auth.SESSION_COOKIE)
        resp.delete_cookie(auth.CSRF_COOKIE)

    return resp


app.add_url_rule("/", endpoint="landing_root", view_func=_serve_landing)
app.add_url_rule("/index.html", endpoint="landing_index_html", view_func=_serve_landing)


@app.route("/api/chapters")
def api_chapters():
    # "chapters" et "n_questions" restent inchangés (contrat existant).
    # "chapters_meta" est un ajout additif : titre + notions de cours + nb
    # d'exercices/notions par chapitre, pour les cartes de chapitres.html.
    default_difficulty = DIFFICULTY_LEVELS[len(DIFFICULTY_LEVELS) // 2] if DIFFICULTY_LEVELS else 2
    chapters_meta = []
    for chapter_id in CHAPTERS:
        meta = CHAPTER_META.get(chapter_id, {})
        chapter_exercises = [(i, e) for i, e in enumerate(BANK) if e.get("chapter_id") == chapter_id]
        notions = sorted(set(e.get("notion") for _, e in chapter_exercises if e.get("notion")))
        diff_counts = {d: 0 for d in DIFFICULTY_LEVELS}
        for _, e in chapter_exercises:
            d = e.get("difficulty")
            if d in diff_counts:
                diff_counts[d] += 1
        dominant_difficulty = max(diff_counts, key=diff_counts.get) if chapter_exercises else default_difficulty

        notions_detail = []
        for n in notions:
            n_exs = [(i, e) for i, e in chapter_exercises if e.get("notion") == n]
            n_diff_counts = {d: 0 for d in DIFFICULTY_LEVELS}
            for _, e in n_exs:
                if e.get("difficulty") in n_diff_counts:
                    n_diff_counts[e["difficulty"]] += 1
            notions_detail.append({
                "notion": n,
                "n_exercises": len(n_exs),
                "difficulty_dominant": max(n_diff_counts, key=n_diff_counts.get) if n_exs else default_difficulty,
                # Répartition complète (et non plus seulement la dominante) + liste
                # des niveaux effectivement disponibles pour cette notion.
                "difficulty_counts": n_diff_counts,
                "difficulties_available": sorted(d for d, c in n_diff_counts.items() if c > 0),
                # Nombre de reformulations "français naturel" disponibles pour les
                # exercices de cette notion (exercises_bank_reformulations.json).
                "n_natural_variants": _n_variants_for([i for i, _ in n_exs]),
                # Additif : ids exposés pour permettre de lancer une série ciblée sur
                # une seule notion depuis chapitres.html (aucune logique de sélection modifiée).
                "exercise_ids": [e["id"] for _, e in n_exs],
            })
        chapters_meta.append({
            "id": chapter_id,
            "title": meta.get("title", chapter_id),
            "notions_cours": meta.get("notions_cours", notions),
            "notions_detail": notions_detail,
            "n_exercises": len(chapter_exercises),
            "n_notions": len(notions),
            "difficulty_dominant": dominant_difficulty,
            "difficulty_counts": diff_counts,
            "difficulties_available": sorted(d for d, c in diff_counts.items() if c > 0),
            "n_natural_variants": _n_variants_for([i for i, _ in chapter_exercises]),
        })
    return jsonify({
        "chapters": CHAPTERS,
        "n_questions": N_QUESTIONS,
        "chapters_meta": chapters_meta,
        # Additif : totaux globaux calculés dynamiquement depuis la banque,
        # pour tout affichage global (accueil, dashboard) sans valeur en dur.
        "totals": {
            "n_exercises": len(BANK),
            "n_chapters": len(CHAPTERS),
            "n_notions": len(set(e.get("notion") for e in BANK if e.get("notion"))),
            "difficulty_levels": DIFFICULTY_LEVELS,
            "difficulty_counts": {d: sum(1 for e in BANK if e.get("difficulty") == d) for d in DIFFICULTY_LEVELS},
            "n_natural_variants": sum(VARIANTS_COUNT_BY_INDEX),
        },
    })


@app.route("/api/site/stats")
def api_site_stats():
    """Source unique de vérité pour les statistiques marketing affichées sur la
    landing page (et toute autre page) : calculées à la volée depuis BANK,
    jamais codées en dur côté frontend."""
    return jsonify({
        "totalExercises": len(BANK),
        "chapters": len(CHAPTERS),
        "notions": len(set(e.get("notion") for e in BANK if e.get("notion"))),
        "difficultyLevels": len(DIFFICULTY_LEVELS),
    })


@app.route("/api/exercise/<int:exercise_id>")
def api_exercise(exercise_id):
    """Route additive : consultation directe d'un exercice (mode entraînement enrichi),
    sans toucher aux routes /api/practice/* existantes."""
    ex = BANK_BY_ID.get(exercise_id)
    if ex is None:
        return jsonify({"error": "exercice inconnu"}), 404
    return jsonify({"exercise": public_exercise(ex)})


def _compute_stats_cache(history, xp, client_level):
    total = len(history)
    correct = sum(1 for h in history if h.get("correct"))
    accuracy = round((correct / total) * 100, 1) if total else 0.0
    total_time_s = sum(h.get("duration_s") or 0 for h in history)

    attempted = {}
    for h in history:
        if h.get("id") is None:
            continue
        attempted.setdefault(h.get("chapter"), set()).add(h["id"])
    chapter_exercise_counts = {c: sum(1 for e in BANK if e.get("chapter_id") == c) for c in CHAPTERS}
    ratios = [
        min(1.0, len(attempted.get(c, ())) / n) for c, n in chapter_exercise_counts.items() if n
    ]
    progression = round((sum(ratios) / len(ratios)) * 100, 1) if ratios else 0.0

    level = int(client_level) if isinstance(client_level, int) else 1
    return level, accuracy, progression, total_time_s


@app.route("/api/stats", methods=["GET", "POST"])
@login_required
@csrf_protect
def api_stats():
    """Persistance de la gamification (XP, historique, badges, séries) — un
    fichier JSON par utilisateur (webapp/auth.py::read_user_stats/write_user_stats),
    sans lien avec la logique de sélection/prédiction. Nécessite une session
    active depuis l'introduction des comptes."""
    user_id = request.current_user["id"]

    if request.method == "GET":
        return jsonify(read_user_stats(user_id))

    data = request.get_json(force=True) or {}
    payload = {
        "xp": int(data.get("xp", 0)),
        "history": data.get("history", []),
        "badges": data.get("badges", []),
        "series": data.get("series", []),
    }
    write_user_stats(user_id, payload)

    level, accuracy, progression, total_time_s = _compute_stats_cache(payload["history"], payload["xp"], data.get("level"))
    db.update_stats_cache(user_id, payload["xp"], level, accuracy, progression, total_time_s)

    return jsonify({"ok": True})


@app.route("/api/settings", methods=["GET", "POST"])
@login_required
@csrf_protect
def api_settings():
    """Préférences de personnalisation (apparence, entraînement, apprentissage,
    langue) — un fichier JSON par utilisateur, même stratégie
    que /api/stats (webapp/auth.py::read_user_settings/write_user_settings).
    Un invité a ses propres préférences, supprimées avec le reste de son compte
    à la fin de sa session (voir auth.py::_purge_account)."""
    user_id = request.current_user["id"]

    if request.method == "GET":
        return jsonify(read_user_settings(user_id))

    data = request.get_json(force=True) or {}
    merged = write_user_settings(user_id, data)
    return jsonify(merged)


@app.route("/api/course-progress", methods=["GET", "POST"])
@login_required
@csrf_protect
def api_course_progress():
    """Progression de lecture du module Cours (section courante, notions
    terminées, score des mini-quiz) — même stratégie que /api/stats et
    /api/settings : un fichier JSON par utilisateur, purgé avec le reste du
    compte pour les invités (voir auth.py::_purge_account)."""
    user_id = request.current_user["id"]

    if request.method == "GET":
        return jsonify(read_user_course_progress(user_id))

    data = request.get_json(force=True) or {}
    chapter_id = data.get("chapterId")
    notion_id = data.get("notionId")
    patch = data.get("patch") or {}
    if not chapter_id or not notion_id or not isinstance(patch, dict):
        return jsonify({"error": "chapterId, notionId et patch sont requis"}), 400
    updated = write_user_course_progress(user_id, chapter_id, notion_id, patch)
    return jsonify(updated)


@app.route("/api/data/summary")
@login_required
def api_data_summary():
    """Chiffres bruts affichés dans l'onglet Données des paramètres — calculés
    à la volée depuis l'historique réel (aucune valeur mise en cache séparée)."""
    user = request.current_user
    stats = read_user_stats(user["id"])
    history = stats.get("history", [])
    total = len(history)
    correct = sum(1 for h in history if h.get("correct"))
    accuracy = round((correct / total) * 100, 1) if total else 0.0
    total_time_s = sum(h.get("duration_s") or 0 for h in history)
    return jsonify({
        "totalExercises": total,
        "accuracy": accuracy,
        "totalTimeS": total_time_s,
        "seriesCount": len(stats.get("series", [])),
        "memberSince": user["created_at"],
    })


@app.route("/api/data/export")
@login_required
def api_data_export():
    """« Exporter les statistiques » / « Télécharger mes données » — un seul
    fichier JSON regroupant profil public, statistiques et préférences, jamais
    de secret (pas de hash de mot de passe, pas de cookie/token)."""
    user = request.current_user
    export = {
        "account": {
            "id": user["id"],
            "email": user["email"],
            "username": user["username"],
            "pseudo": user["pseudo"],
            "created_at": user["created_at"],
        },
        "stats": read_user_stats(user["id"]),
        "settings": read_user_settings(user["id"]),
        "exported_at": _date.today().isoformat(),
    }
    resp = jsonify(export)
    resp.headers["Content-Disposition"] = f'attachment; filename="novamath_export_{user["id"]}.json"'
    return resp


@app.route("/api/data/reset", methods=["POST"])
@login_required
@csrf_protect
def api_data_reset():
    """« Réinitialiser mes statistiques » / « Réinitialiser entièrement ma
    progression » : dans ce modèle de données, les deux actions portent sur la
    même source de vérité (XP, historique, séries, badges) — il n'existe pas de
    notion de "progression" distincte des statistiques, donc les deux boutons
    déclenchent la même remise à zéro complète et honnête plutôt qu'une
    distinction artificielle. Confirmation exigée côté client avant l'appel."""
    user_id = request.current_user["id"]
    empty = {"xp": 0, "history": [], "badges": [], "series": []}
    write_user_stats(user_id, empty)
    db.update_stats_cache(user_id, 0, 1, 0.0, 0.0, 0)
    return jsonify({"ok": True})


# ── Avis (section "Avis" de la landing page), additif ─────────────────────────
ALLOWED_AVATAR_PREFIXES = (
    "data:image/png;base64,",
    "data:image/jpeg;base64,",
    "data:image/jpg;base64,",
    "data:image/webp;base64,",
    "data:image/gif;base64,",
)
MAX_AVATAR_LEN = 300_000  # ~220 Ko décodé, largement suffisant pour un avatar de profil
CLASSE_CHOICES = {"Seconde", "Première", "Terminale", "Autre"}


def _read_reviews():
    if not REVIEWS_PATH.exists():
        return []
    with open(REVIEWS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_reviews(reviews):
    """Écriture atomique (fichier temporaire + rename), même stratégie que _write_stats."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=DATA_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(reviews, f, ensure_ascii=False)
        os.replace(tmp_path, REVIEWS_PATH)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def _is_admin(req):
    key = req.headers.get("X-Admin-Key", "")
    return bool(key) and key == ADMIN_KEY


def _public_review(r):
    """Version envoyée au client : jamais owner_token (secret de modification) ni
    user_id (identifiant interne, seulement utilisé pour vérifier la propriété)."""
    return {k: v for k, v in r.items() if k not in ("owner_token", "user_id")}


def _review_stats(reviews):
    visible = [r for r in reviews if not r.get("hidden")]
    total = len(visible)
    if total == 0:
        return {"total": 0, "average": 0, "distribution": {str(n): 0 for n in range(1, 6)}}
    counts = {n: 0 for n in range(1, 6)}
    for r in visible:
        counts[r["rating"]] = counts.get(r["rating"], 0) + 1
    average = round(sum(r["rating"] for r in visible) / total, 1)
    distribution = {str(n): round(counts[n] * 100 / total) for n in range(1, 6)}
    return {"total": total, "average": average, "distribution": distribution}


def _clean_text(value, max_len):
    return re.sub(r"\s+", " ", str(value or "")).strip()[:max_len]


def _validate_review_payload(data, existing_reviews, editing_id=None, account=None):
    """Valide et nettoie un payload d'avis. Lève ValueError(message) si invalide.
    Si `account` est fourni (utilisateur connecté), le nom/pseudo/photo affichés
    sont ceux du compte — un avis publié en étant connecté doit être attribué
    fidèlement au compte, pas à un nom saisi librement dans le formulaire."""
    if account:
        name = account["pseudo"]
        pseudo = account["username"]
    else:
        name = _clean_text(data.get("name"), 100)
        if not name:
            raise ValueError("Le nom est obligatoire.")
        pseudo = _clean_text(data.get("pseudo"), 50)

    classe = _clean_text(data.get("classe"), 50) or "Autre"
    if classe not in CLASSE_CHOICES:
        classe = "Autre"

    try:
        rating = int(data.get("rating"))
    except (TypeError, ValueError):
        raise ValueError("La note est obligatoire.")
    if rating < 1 or rating > 5:
        raise ValueError("La note doit être comprise entre 1 et 5 étoiles.")

    comment = _clean_text(data.get("comment"), 500)
    if not comment:
        raise ValueError("Le commentaire ne peut pas être vide.")

    if account:
        avatar = account["avatar"]
    else:
        avatar = data.get("avatar") or None
        if avatar:
            if not isinstance(avatar, str) or not avatar.startswith(ALLOWED_AVATAR_PREFIXES):
                raise ValueError("Format de photo de profil non supporté.")
            if len(avatar) > MAX_AVATAR_LEN:
                raise ValueError("La photo de profil est trop volumineuse.")
            if auth.sniff_image_type(avatar) is None:
                raise ValueError("Le contenu du fichier ne correspond pas à une image valide.")

    dup_key = (name.lower(), comment.lower())
    for r in existing_reviews:
        if r["id"] == editing_id or r.get("hidden"):
            continue
        if (r["name"].lower(), r["comment"].lower()) == dup_key:
            raise ValueError("Cet avis (même nom, même commentaire) a déjà été publié.")

    return {"name": name, "pseudo": pseudo, "classe": classe, "rating": rating, "comment": comment, "avatar": avatar}


@app.route("/api/reviews", methods=["GET", "POST"])
@csrf_protect
def api_reviews():
    reviews = _read_reviews()

    if request.method == "GET":
        admin = _is_admin(request)
        visible = reviews if admin else [r for r in reviews if not r.get("hidden")]
        visible = sorted(visible, key=lambda r: (not r.get("pinned"), ))
        return jsonify({"reviews": [_public_review(r) for r in visible], "stats": _review_stats(reviews)})

    account = get_current_user()
    if account and account["auth_provider"] == "guest":
        return jsonify({
            "error": "Publier un avis nécessite un compte.",
            "guest_restricted": True,
        }), 403

    data = request.get_json(force=True) or {}
    try:
        cleaned = _validate_review_payload(data, reviews, account=account)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    owner_token = uuid.uuid4().hex
    review = {
        "id": uuid.uuid4().hex,
        **cleaned,
        "date": _date.today().strftime("%d/%m/%Y"),
        "pinned": False,
        "hidden": False,
        "owner_token": owner_token,
        # Attribution fiable au compte (indépendante du navigateur/localStorage,
        # contrairement à owner_token) : permet à l'auteur de retrouver/modifier
        # son avis depuis n'importe quel appareil une fois connecté.
        "user_id": account["id"] if account else None,
    }
    reviews.append(review)
    _write_reviews(reviews)

    public = _public_review(review)
    public["owner_token"] = owner_token  # une seule fois, à la création : le client le conserve localement
    return jsonify({"review": public, "stats": _review_stats(reviews)}), 201


def _release_reviews_ownership(user_id):
    """Hook appelé par auth.py::delete_me() à la suppression d'un compte : les
    avis restent publics (comportement voulu depuis NovaMath V4) mais ne
    doivent plus être rattachés à un compte qui n'existe plus."""
    reviews = _read_reviews()
    changed = False
    for r in reviews:
        if r.get("user_id") == user_id:
            r["user_id"] = None
            changed = True
    if changed:
        _write_reviews(reviews)


auth.ACCOUNT_DELETION_HOOKS.append(_release_reviews_ownership)


@app.route("/api/reviews/<review_id>", methods=["PUT", "DELETE"])
@csrf_protect
def api_review_detail(review_id):
    reviews = _read_reviews()
    idx = next((i for i, r in enumerate(reviews) if r["id"] == review_id), None)
    if idx is None:
        return jsonify({"error": "Avis introuvable."}), 404

    data = request.get_json(force=True) or {}
    account = get_current_user()
    admin = _is_admin(request)
    is_owner_by_token = bool(data.get("owner_token")) and data.get("owner_token") == reviews[idx].get("owner_token")
    is_owner_by_account = bool(account) and account["id"] == reviews[idx].get("user_id")
    if not (admin or is_owner_by_token or is_owner_by_account):
        return jsonify({"error": "Tu ne peux modifier ou supprimer que ton propre avis."}), 403

    if request.method == "DELETE":
        del reviews[idx]
        _write_reviews(reviews)
        return jsonify({"ok": True, "stats": _review_stats(reviews)})

    # Un avis publié par un compte reste attribué à ce compte : on ne repasse
    # `account` que s'il correspond bien au propriétaire enregistré (sinon
    # l'admin qui édite l'avis de quelqu'un d'autre en étant lui-même connecté
    # écraserait le nom/pseudo/photo affichés par les siens).
    owning_account = account if is_owner_by_account else None
    try:
        cleaned = _validate_review_payload(data, reviews, editing_id=review_id, account=owning_account)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    reviews[idx].update(cleaned)
    _write_reviews(reviews)
    return jsonify({"review": _public_review(reviews[idx]), "stats": _review_stats(reviews)})


@app.route("/api/reviews/<review_id>/pin", methods=["POST"])
def api_review_pin(review_id):
    if not _is_admin(request):
        return jsonify({"error": "Réservé à l'administrateur."}), 403
    reviews = _read_reviews()
    review = next((r for r in reviews if r["id"] == review_id), None)
    if review is None:
        return jsonify({"error": "Avis introuvable."}), 404
    review["pinned"] = not review.get("pinned", False)
    _write_reviews(reviews)
    return jsonify({"review": _public_review(review)})


@app.route("/api/reviews/<review_id>/hide", methods=["POST"])
def api_review_hide(review_id):
    if not _is_admin(request):
        return jsonify({"error": "Réservé à l'administrateur."}), 403
    reviews = _read_reviews()
    review = next((r for r in reviews if r["id"] == review_id), None)
    if review is None:
        return jsonify({"error": "Avis introuvable."}), 404
    review["hidden"] = not review.get("hidden", False)
    _write_reviews(reviews)
    return jsonify({"review": _public_review(review), "stats": _review_stats(reviews)})


GUEST_MAX_CHAPTERS = 2


@app.route("/api/start", methods=["POST"])
@login_required
@csrf_protect
def api_start():
    data = request.get_json(force=True) or {}
    chapters = data.get("chapters", [])
    # Filet de sécurité serveur : la limite est déjà appliquée côté client
    # (chapitres.js empêche la sélection d'un 3e chapitre en mode invité), mais
    # un appel direct à l'API ne doit pas pouvoir la contourner.
    if request.current_user["auth_provider"] == "guest" and len(chapters) > GUEST_MAX_CHAPTERS:
        return jsonify({
            "error": f"Le mode invité est limité à {GUEST_MAX_CHAPTERS} chapitres.",
            "guest_restricted": True,
        }), 403
    reset_session()
    session["allowed"] = chapters

    ex = pick_exercise(QUIZ_DIFFS[0], [], chapters)
    session["used_ids"] = [ex["id"]]

    return jsonify({
        "progress": {"current": 1, "total": N_QUESTIONS},
        "exercise": public_exercise(ex),
    })


@app.route("/api/answer", methods=["POST"])
@login_required
@csrf_protect
def api_answer():
    data = request.get_json(force=True) or {}
    is_correct = bool(data.get("correct"))
    ex_id = data.get("exercise_id")
    current_ex = BANK_BY_ID.get(ex_id)
    if current_ex is None:
        return jsonify({"error": "exercice inconnu"}), 400

    resps = session.get("resps", []) + [1 if is_correct else 0]
    diffs = session.get("diffs", []) + [current_ex["difficulty"]]
    q = session.get("q", 0) + 1
    used = session.get("used_ids", [])
    allowed = session.get("allowed", [])

    session["resps"] = resps
    session["diffs"] = diffs
    session["q"] = q

    if q >= N_QUESTIONS:
        level = predict_level(resps, diffs)
        session["current_level"] = level
        icon, label = LEVEL_LABELS[level]
        return jsonify({
            "finished": True,
            "level": level,
            "level_icon": icon,
            "level_label": label,
            "practice_choices": practice_choices(allowed, level),
        })

    next_ex = pick_exercise(QUIZ_DIFFS[q], used, allowed)
    session["used_ids"] = used + [next_ex["id"]]

    return jsonify({
        "finished": False,
        "progress": {"current": q + 1, "total": N_QUESTIONS},
        "exercise": public_exercise(next_ex),
    })


@app.route("/api/practice/load", methods=["POST"])
@login_required
@csrf_protect
def api_practice_load():
    data = request.get_json(force=True) or {}
    ex_id = data.get("exercise_id")
    ex = BANK_BY_ID.get(ex_id)
    if ex is None:
        return jsonify({"error": "exercice inconnu"}), 404
    return jsonify({"exercise": public_exercise(ex)})


@app.route("/api/practice/result", methods=["POST"])
@login_required
@csrf_protect
def api_practice_result():
    data = request.get_json(force=True) or {}
    is_correct = bool(data.get("correct"))
    ex_id = data.get("exercise_id")
    current_ex = BANK_BY_ID.get(ex_id)
    if current_ex is None:
        return jsonify({"error": "exercice inconnu"}), 400

    p_resps = session.get("practice_resps", []) + [1 if is_correct else 0]
    p_diffs = session.get("practice_diffs", []) + [current_ex["difficulty"]]
    history = session.get("history", [])
    allowed = session.get("allowed", [])
    current_lvl = session.get("current_level", 1)

    icon_res = "✅" if is_correct else "❌"
    history = history + [f"{icon_res} {current_ex.get('chapter_id')} : {current_ex.get('notion')}"]

    new_lvl = current_lvl
    level_updated = False
    if len(p_resps) >= 3:
        new_lvl = predict_level(p_resps, p_diffs)
        level_updated = new_lvl != current_lvl
        p_resps, p_diffs = [], []

    session["practice_resps"] = p_resps
    session["practice_diffs"] = p_diffs
    session["history"] = history
    session["current_level"] = new_lvl

    icon_l, label_l = LEVEL_LABELS[new_lvl]

    return jsonify({
        "level": new_lvl,
        "level_icon": icon_l,
        "level_label": label_l,
        "level_updated": level_updated,
        "history": history[-5:],
        "practice_choices": practice_choices(allowed, new_lvl),
    })


@app.route("/api/restart", methods=["POST"])
@login_required
@csrf_protect
def api_restart():
    reset_session()
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=True, port=5050)
