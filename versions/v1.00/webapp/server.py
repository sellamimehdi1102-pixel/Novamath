"""
Backend Flask pour l'interface web NovaMath.
Remplace l'UI Gradio de 06_quiz_app.py par une API JSON consommée par
webapp/static/index.html + script.js, tout en gardant EXACTEMENT la même
logique de sélection d'exercices et de prédiction de niveau (même
exercises_bank.json, mêmes modèles models/*.pkl).
"""
import json
import os
import re
import random
import tempfile
from pathlib import Path

import joblib
from flask import Flask, jsonify, request, session, send_from_directory

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
STATS_PATH = DATA_DIR / "stats_store.json"
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


# ── Logique de sélection (identique à 06_quiz_app.py) ─────────────────────────
def pick_exercise(difficulty, exclude_ids, allowed_chapters):
    pool = [e for e in BANK if e.get("chapter_id") in allowed_chapters] if allowed_chapters else BANK
    candidates = [e for e in pool if e["difficulty"] == difficulty and e["id"] not in exclude_ids]
    if not candidates:
        for d in [1, -1, 2, -2]:
            candidates = [e for e in pool if e["difficulty"] == difficulty + d and e["id"] not in exclude_ids]
            if candidates:
                break
    if not candidates:
        candidates = pool
    return random.choice(candidates)


def predict_level(responses, difficulties):
    r = (responses + [0] * 7)[:7]
    d = (difficulties + [2] * 7)[:7]
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
        if e["difficulty"] == level
    ]


# ── App Flask ───────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder="static", static_url_path="")
app.secret_key = "adaptivemath-local-dev"  # app locale mono-utilisateur


@app.after_request
def no_cache(response):
    """Projet en développement actif : on désactive tout cache navigateur pour
    être sûr que chaque rechargement récupère la dernière version du JS/CSS
    (sinon un fix déjà livré peut sembler "ne pas s'appliquer" côté client)."""
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
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


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/chapters")
def api_chapters():
    # "chapters" et "n_questions" restent inchangés (contrat existant).
    # "chapters_meta" est un ajout additif : titre + notions de cours + nb
    # d'exercices/notions par chapitre, pour les cartes de chapitres.html.
    chapters_meta = []
    for chapter_id in CHAPTERS:
        meta = CHAPTER_META.get(chapter_id, {})
        chapter_exercises = [e for e in BANK if e.get("chapter_id") == chapter_id]
        notions = sorted(set(e.get("notion") for e in chapter_exercises if e.get("notion")))
        diff_counts = {1: 0, 2: 0, 3: 0}
        for e in chapter_exercises:
            d = e.get("difficulty")
            if d in diff_counts:
                diff_counts[d] += 1
        dominant_difficulty = max(diff_counts, key=diff_counts.get) if chapter_exercises else 2

        notions_detail = []
        for n in notions:
            n_exs = [e for e in chapter_exercises if e.get("notion") == n]
            n_diff_counts = {1: 0, 2: 0, 3: 0}
            for e in n_exs:
                if e.get("difficulty") in n_diff_counts:
                    n_diff_counts[e["difficulty"]] += 1
            notions_detail.append({
                "notion": n,
                "n_exercises": len(n_exs),
                "difficulty_dominant": max(n_diff_counts, key=n_diff_counts.get) if n_exs else 2,
                # Additif : ids exposés pour permettre de lancer une série ciblée sur
                # une seule notion depuis chapitres.html (aucune logique de sélection modifiée).
                "exercise_ids": [e["id"] for e in n_exs],
            })
        chapters_meta.append({
            "id": chapter_id,
            "title": meta.get("title", chapter_id),
            "notions_cours": meta.get("notions_cours", notions),
            "notions_detail": notions_detail,
            "n_exercises": len(chapter_exercises),
            "n_notions": len(notions),
            "difficulty_dominant": dominant_difficulty,
        })
    return jsonify({"chapters": CHAPTERS, "n_questions": N_QUESTIONS, "chapters_meta": chapters_meta})


@app.route("/api/exercise/<int:exercise_id>")
def api_exercise(exercise_id):
    """Route additive : consultation directe d'un exercice (mode entraînement enrichi),
    sans toucher aux routes /api/practice/* existantes."""
    ex = BANK_BY_ID.get(exercise_id)
    if ex is None:
        return jsonify({"error": "exercice inconnu"}), 404
    return jsonify({"exercise": public_exercise(ex)})


def _read_stats():
    if not STATS_PATH.exists():
        return {"xp": 0, "history": [], "badges": [], "series": []}
    with open(STATS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("series", [])
    return data


def _write_stats(payload):
    """Écriture atomique (fichier temporaire + rename) pour éviter toute corruption
    si le serveur redémarre en pleine écriture."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=DATA_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        os.replace(tmp_path, STATS_PATH)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.route("/api/stats", methods=["GET", "POST"])
def api_stats():
    """Persistance additive de la gamification (XP, historique, badges) — fichier
    JSON local, mono-utilisateur, sans lien avec la logique de sélection/prédiction."""
    if request.method == "GET":
        return jsonify(_read_stats())

    data = request.get_json(force=True) or {}
    payload = {
        "xp": int(data.get("xp", 0)),
        "history": data.get("history", []),
        "badges": data.get("badges", []),
        "series": data.get("series", []),
    }
    _write_stats(payload)
    return jsonify({"ok": True})


@app.route("/api/start", methods=["POST"])
def api_start():
    data = request.get_json(force=True) or {}
    chapters = data.get("chapters", [])
    reset_session()
    session["allowed"] = chapters

    ex = pick_exercise(QUIZ_DIFFS[0], [], chapters)
    session["used_ids"] = [ex["id"]]

    return jsonify({
        "progress": {"current": 1, "total": N_QUESTIONS},
        "exercise": public_exercise(ex),
    })


@app.route("/api/answer", methods=["POST"])
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
def api_practice_load():
    data = request.get_json(force=True) or {}
    ex_id = data.get("exercise_id")
    ex = BANK_BY_ID.get(ex_id)
    if ex is None:
        return jsonify({"error": "exercice inconnu"}), 404
    return jsonify({"exercise": public_exercise(ex)})


@app.route("/api/practice/result", methods=["POST"])
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
def api_restart():
    reset_session()
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=True, port=5050)
