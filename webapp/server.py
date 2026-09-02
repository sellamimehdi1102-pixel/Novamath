"""
Backend Flask pour l'interface web NovaMath.
Remplace l'UI Gradio de 06_quiz_app.py par une API JSON consommée par
webapp/static/index.html + script.js, tout en gardant EXACTEMENT la même
logique de sélection d'exercices et de prédiction de niveau (même
exercises_bank.json, mêmes modèles models/*.pkl).
"""
import json
import logging
import math
import os
import re
import secrets
import tempfile
import time
import uuid
from datetime import date as _date
from pathlib import Path

import joblib
import stripe
from dotenv import load_dotenv
from flask import Flask, jsonify, request, session, redirect, Response, g, send_from_directory, send_file, abort

# Charge les variables du fichier .env (racine du projet) dans os.environ,
# sans jamais écraser une variable déjà définie au niveau du système
# d'exploitation — même source de vérité que _get_or_create_secret/
# os.environ.get utilisés partout ailleurs dans le projet, juste alimentée
# depuis .env en plus de l'environnement réel. Doit s'exécuter avant tout
# import qui lit os.environ au niveau module (stripe_service, auth, chatbot).
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import admin_dashboard_service
import admin_nav_service
import admin_users_service
import admin_user_profile_service
import admin_ai_log_service
import admin_ai_service
import admin_analytics_export_service
import admin_analytics_service
import admin_subscriptions_service
import ai_provider_service
import auth
import backup_service
import billing_service
import config
import consent_service
import course_content_service
import curriculum_registry
from exercise_generator import registry as exercise_generator_registry
import curriculum_stats
import db
import health_service
import logging_service
import owner_service
import owner_test_plan_service
import plan_service
import privacy_service
import quota_service
import rate_limit_service
import security_headers_service
import settings_service
import stripe_service
import stripe_webhook_service
import subscription_plan_service
import support_attachment_service
import support_service
import system_health_service
from plan_service import Plan, Feature, requires_feature
from quota_service import QuotaType, QuotaExceededError
from rate_limit_service import rate_limit
from role_service import Role, requires_role, get_role, sync_super_admin_bootstrap_for_configured_emails
from auth import (
    auth_bp, get_current_user, login_required, login_required_page, require_non_guest,
    read_user_stats, write_user_stats,
    csrf_protect, read_user_settings, write_user_settings, read_user_course_progress, write_user_course_progress,
)

from chatbot import conversation_manager, provider_manager
from chatbot.providers.ollama_provider import OllamaConnectionError
from chatbot.providers.anthropic_provider import AnthropicConnectionError

_PROVIDER_DOWN_ERRORS = (OllamaConnectionError, AnthropicConnectionError)

# Chantier 5 (anti-abus) : plafond de longueur d'UN message chatbot, distinct
# de config.MAX_CONTENT_LENGTH (20 Mo, plafond HTTP global du corps de
# requête, jamais modifié ici). ~4000 caractères ≈ 1000 tokens — largement
# suffisant pour une question pédagogique, y compris un énoncé d'exercice
# recopié en entier ; refusé explicitement (400), jamais tronqué en silence.
MAX_CHATBOT_MESSAGE_CHARS = 4000

logger = logging.getLogger("server")

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
REVIEWS_PATH = DATA_DIR / "reviews.json"

# Garde-fou démarré AVANT tout chargement de contenu (voir
# curriculum_registry.validate_registry) : un programme enregistré dans le
# registre sans son dossier de cours généré doit empêcher le serveur de
# démarrer, jamais laisser un utilisateur découvrir un 404 en cliquant sur
# "Ouvrir" un chapitre (incident réel : "troisieme" avait été ajouté au
# registre sans que webapp/static/data/cours_troisieme/ ait été généré).
# Exécuté au niveau module pour s'appliquer aussi bien à `python server.py`
# (dev) qu'à `gunicorn webapp.server:app` (prod, qui importe `app` sans
# jamais passer par `if __name__ == "__main__"` en bas de ce fichier).
curriculum_registry.validate_registry()

# Seconde reste le seul programme dont les endpoints ci-dessous chargent
# effectivement les données (Première n'a pas encore de modèle/programme
# branchés — voir curriculum_registry.py) : les chemins littéraux
# précédemment codés en dur ici sont désormais lus depuis le registre, seule
# source de vérité, sans aucun changement des fichiers réellement chargés.
_SECONDE = curriculum_registry.CURRICULUM_REGISTRY["seconde"]
NATURAL_BANK_PATH = _SECONDE.natural_bank

# ── Chargement et Attribution d'IDs Automatiques ──────────────────────────────
with open(_SECONDE.exercise_bank, "r", encoding="utf-8") as f:
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

# "seconde" ne fusionne normalement jamais generated_exercise_bank (voir
# _class_bank() plus bas) — les 198 exercices de exercises_generated_seconde.json
# (droites.py/Chapitre_6 + signes.py/Chapitre_9) étaient donc entièrement
# orphelins côté élève. Audit (2026-09-02) : fusionner les 198 pousse le
# ratio max/min de 1,51 à 2,3 (Chapitre_6 étant déjà le plus fourni de
# Seconde), au-delà du plafond verrouillé. Seul Chapitre_9 (72 exercices,
# signes.py) est donc intégré ici — ratio résultant ≈1,73, sous le plafond ;
# Chapitre_6/droites.py reste en attente d'un futur rééquilibrage. IDs
# (810000+) et énoncés vérifiés sans collision avec exercises_bank.json.
if _SECONDE.generated_exercise_bank is not None and _SECONDE.generated_exercise_bank.exists():
    with open(_SECONDE.generated_exercise_bank, "r", encoding="utf-8") as f:
        _seconde_generated_raw = json.load(f)
    for ex in _seconde_generated_raw:
        if ex.get("chapter_id") != "Chapitre_9":
            continue
        ex = dict(ex)
        for field in ["enonce", "answer", "hint"]:
            if isinstance(ex.get(field), str):
                val = ex[field]
                if "\\" in val and "$" not in val:
                    val = f"${val}$"
                ex[field] = val
        BANK.append(ex)

BANK_BY_ID = {e["id"]: e for e in BANK}

MODEL = joblib.load(_SECONDE.models_dir / "level_predictor.pkl")
QUIZ_DIFFS = joblib.load(_SECONDE.models_dir / "quiz_difficulties.pkl")
N_QUESTIONS = len(QUIZ_DIFFS)
LEVEL_LABELS = {1: ("sprout", "Débutant"), 2: ("zap", "Intermédiaire"), 3: ("trophy", "Avancé")}


def get_chapter_num(name):
    nums = re.findall(r"\d+", name)
    return int(nums[0]) if nums else 0


CHAPTERS = sorted(list(set(ex.get("chapter_id", "") for ex in BANK)), key=get_chapter_num)

# ── Métadonnées de chapitres (titres + notions de cours), additif ────────────
# Lues depuis "Programme AI.json" (déjà présent dans le dépôt), utilisées
# uniquement pour enrichir /api/chapters — n'affecte pas la sélection d'exercices.
try:
    with open(_SECONDE.program_file, "r", encoding="utf-8") as f:
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


# ── Ressources d'exercices/chapitres par classe (Cours/Exercices/Entraînement/
# Chatbot) ─────────────────────────────────────────────────────────────────
# "seconde" réutilise directement BANK/BANK_BY_ID/CHAPTERS/CHAPTER_META/
# NATURAL_BY_ID déjà chargés ci-dessus (aucun double chargement, comportement
# historique strictement inchangé). Toute autre classe est chargée à la
# demande depuis curriculum_registry.py, jamais depuis un chemin en dur, et
# dégrade proprement (listes/dicts vides) si une ressource déclarée n'existe
# pas encore sur disque — jamais de repli silencieux vers les données Seconde.
_class_bank_cache = {}


def _class_bank(class_level):
    if class_level == "seconde":
        return {
            "bank": BANK, "bank_by_id": BANK_BY_ID, "chapters": CHAPTERS,
            "chapter_meta": CHAPTER_META, "natural_by_id": NATURAL_BY_ID,
            "variants_count_by_index": VARIANTS_COUNT_BY_INDEX,
        }
    if class_level not in _class_bank_cache:
        profile = curriculum_registry.CURRICULUM_REGISTRY[class_level]
        bank = []
        if profile.exercise_bank is not None and profile.exercise_bank.exists():
            raw = json.loads(profile.exercise_bank.read_text(encoding="utf-8"))
            for i, ex in enumerate(raw):
                ex = dict(ex)
                ex["id"] = ex.get("id") if ex.get("id") is not None else i
                for field in ["enonce", "answer", "hint"]:
                    if isinstance(ex.get(field), str):
                        val = ex[field]
                        if "\\" in val and "$" not in val:
                            val = f"${val}$"
                        ex[field] = val
                bank.append(ex)
        bank_by_id = {e["id"]: e for e in bank}
        chapters = sorted(set(e.get("chapter_id", "") for e in bank), key=get_chapter_num)

        chapter_meta = {}
        if profile.program_file is not None and profile.program_file.exists():
            programme = json.loads(profile.program_file.read_text(encoding="utf-8"))
            chapter_meta = {c["id"]: c for c in programme.get("chapters", [])}
        elif profile.courses_dir is not None and profile.courses_dir.exists():
            # Sans "programme officiel" déclaré (program_file=None), le titre
            # affiché de chaque chapitre est lu directement dans le cours déjà
            # généré (courses_dir/chapitre_N.json, "title" au niveau racine) —
            # même source de vérité que knowledge_engine.py (chatbot) et que le
            # lecteur de cours (cours.js::content.title). Sans ce repli, les
            # cartes de chapitres/dashboard/recherche retombaient sur
            # `chapter_id.replace("_", " ")` ("Chapitre 1") plus bas.
            for course_path in profile.courses_dir.glob("chapitre_*.json"):
                try:
                    with open(course_path, "r", encoding="utf-8") as f:
                        course = json.load(f)
                except (json.JSONDecodeError, OSError):
                    continue
                chapter_id = course.get("chapterId")
                if chapter_id and course.get("title"):
                    chapter_meta[chapter_id] = {"title": course["title"]}

        # Alignement par "id" (pas par position) : une banque naturelle sans
        # ce champ, ou mal alignée, ne doit jamais planter — elle est
        # simplement ignorée et public_exercise() retombe sur l'énoncé brut.
        natural_by_id = {}
        if profile.natural_bank is not None and profile.natural_bank.exists():
            natural_raw = json.loads(profile.natural_bank.read_text(encoding="utf-8"))
            natural_by_id = {e["id"]: e for e in natural_raw if "id" in e}

        # Pool généré par un moteur symbolique (webapp/exercise_generator/),
        # ajouté APRÈS la banque curée : mêmes champs qu'un exercice
        # classique (voir derivatives.build_exercise), donc aucun endpoint
        # existant (public_exercise, api_exercise, api_answer, practice_choices)
        # n'a besoin d'être modifié pour les servir. Absent = comportement
        # strictement inchangé (voir generated_exercise_bank=None ailleurs
        # dans le registre).
        if profile.generated_exercise_bank is not None and profile.generated_exercise_bank.exists():
            generated_raw = json.loads(profile.generated_exercise_bank.read_text(encoding="utf-8"))
            for ex in generated_raw:
                ex = dict(ex)
                for field in ["enonce", "answer", "hint"]:
                    if isinstance(ex.get(field), str):
                        val = ex[field]
                        if "\\" in val and "$" not in val:
                            val = f"${val}$"
                        ex[field] = val
                bank.append(ex)
            chapters = sorted(set(e.get("chapter_id", "") for e in bank), key=get_chapter_num)
            bank_by_id = {e["id"]: e for e in bank}

        _class_bank_cache[class_level] = {
            "bank": bank, "bank_by_id": bank_by_id, "chapters": chapters,
            "chapter_meta": chapter_meta, "natural_by_id": natural_by_id,
            "variants_count_by_index": [],  # pas de reformulations Natural déclarées hors Seconde
        }
    return _class_bank_cache[class_level]


def _n_variants_for(chapter_exercises_indices, variants_count_by_index=VARIANTS_COUNT_BY_INDEX):
    """Somme des variantes Natural pour un sous-ensemble d'exercices, identifiés
    par leur index dans BANK (= position dans exercises_bank_reformulations.json,
    listes alignées par construction — voir 07_naturalize_exercises.py)."""
    return sum(
        variants_count_by_index[i] for i in chapter_exercises_indices if i < len(variants_count_by_index)
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
# fine (1 à 5). Sans cette correspondance, practice_choices() ne pourrait
# jamais sélectionner un exercice dont la difficulté dépasse
# len(LEVEL_LABELS) : ~40% de la banque (difficultés 4 et 5) resterait
# définitivement inatteignable en entraînement adaptatif.
# Formule proportionnelle, dynamique et rétrocompatible : si la banque a déjà
# exactement len(LEVEL_LABELS) niveaux (ancienne échelle 1-3), c'est l'identité.
_N_STUDENT_LEVELS = len(LEVEL_LABELS)
_MAX_BANK_DIFFICULTY = max(DIFFICULTY_LEVELS) if DIFFICULTY_LEVELS else _N_STUDENT_LEVELS


def difficulty_bucket(d):
    if not _MAX_BANK_DIFFICULTY:
        return d
    return min(_N_STUDENT_LEVELS, max(1, math.ceil(d * _N_STUDENT_LEVELS / _MAX_BANK_DIFFICULTY)))


def _model_predict_level(model, responses, difficulties, bucket):
    """Prédiction par modèle ML entraîné (contrat de features figé : 7
    réponses, 3 paliers de difficulté — voir models/level_predictor.pkl).
    Ne change jamais : un futur profil qui déclare son propre models_dir
    dans curriculum_registry.py doit fournir un modèle entraîné sur ce même
    contrat pour rester compatible avec ce prédicteur générique."""
    r = (responses + [0] * 7)[:7]
    d = ([bucket(x) for x in difficulties] + [2] * 7)[:7]
    total = sum(r)
    weighted = sum(r[i] * d[i] for i in range(7))
    features = r + [
        sum(r[i] for i, v in enumerate(d) if v == 1),
        sum(r[i] for i, v in enumerate(d) if v == 2),
        sum(r[i] for i, v in enumerate(d) if v == 3),
        total,
        weighted,
    ]
    return int(model.predict([features])[0])


def _heuristic_predict_level(responses, difficulties, bucket):
    """Moteur générique utilisé quand curriculum_registry.py ne déclare
    aucun modèle ML pour la classe active (`models_dir` absent) — jamais un
    modèle spécifique créé pour compenser (voir _level_engine). Combine
    uniquement le taux de réussite réel et la difficulté réelle (bucketée
    sur l'échelle de CETTE classe) des exercices déjà répondus : aucune
    donnée inventée, aucun entraînement préalable requis. Générique par
    construction — fonctionne pour n'importe quelle échelle de niveaux
    (_N_STUDENT_LEVELS) et n'importe quelle banque."""
    if not responses:
        return max(1, math.ceil(_N_STUDENT_LEVELS / 2))
    buckets = [bucket(d) for d in difficulties[:len(responses)]]
    buckets += [buckets[-1] if buckets else 1] * (len(responses) - len(buckets))
    accuracy = sum(responses) / len(responses)
    # Difficulté moyenne des exercices RÉUSSIS : à taux de réussite égal, un
    # élève qui réussit des exercices difficiles mérite un niveau plus haut
    # qu'un élève qui ne réussit que les plus faciles.
    correct_buckets = [buckets[i] for i, r in enumerate(responses) if r]
    avg_correct_difficulty = sum(correct_buckets) / len(correct_buckets) if correct_buckets else 1
    score = accuracy * avg_correct_difficulty
    return max(1, min(_N_STUDENT_LEVELS, round(score) or 1))


# ── Moteur de niveau par classe (évaluation initiale + entraînement adaptatif) ─
# "seconde" réutilise directement MODEL/QUIZ_DIFFS/difficulty_bucket déjà
# chargés ci-dessus (aucun double chargement, comportement historique
# strictement inchangé). Toute autre classe : si curriculum_registry.py y
# déclare un models_dir avec les deux fichiers attendus, le modèle ML de
# CETTE classe est utilisé (jamais celui de Seconde) ; sinon le moteur
# heuristique générique ci-dessus prend le relais — jamais de repli
# implicite vers les données Seconde.
_level_engine_cache = {}


def _level_engine(class_level):
    if class_level not in _level_engine_cache:
        if class_level == "seconde":
            _level_engine_cache[class_level] = {
                "predict": lambda r, d: _model_predict_level(MODEL, r, d, difficulty_bucket),
                "quiz_diffs": QUIZ_DIFFS,
                "n_questions": N_QUESTIONS,
                "bucket": difficulty_bucket,
            }
        else:
            profile = curriculum_registry.CURRICULUM_REGISTRY[class_level]
            bank = _class_bank(class_level)["bank"]
            diff_levels = sorted(set(e.get("difficulty") for e in bank if e.get("difficulty") is not None))
            max_bank_difficulty = max(diff_levels) if diff_levels else _N_STUDENT_LEVELS

            def bucket(d, _max=max_bank_difficulty):
                if not _max:
                    return d
                return min(_N_STUDENT_LEVELS, max(1, math.ceil(d * _N_STUDENT_LEVELS / _max)))

            model_path = profile.models_dir / "level_predictor.pkl" if profile.models_dir else None
            diffs_path = profile.models_dir / "quiz_difficulties.pkl" if profile.models_dir else None
            if model_path is not None and model_path.exists() and diffs_path.exists():
                model = joblib.load(model_path)
                quiz_diffs = joblib.load(diffs_path)
                _level_engine_cache[class_level] = {
                    "predict": lambda r, d, _m=model, _b=bucket: _model_predict_level(_m, r, d, _b),
                    "quiz_diffs": quiz_diffs,
                    "n_questions": len(quiz_diffs),
                    "bucket": bucket,
                }
            else:
                # Pas de quiz entraîné pour cette classe : programme de
                # montée en difficulté générique (1 -> _N_STUDENT_LEVELS,
                # répété), même nombre de questions que le parcours
                # historique — jamais les quiz_diffs de Seconde.
                generic_quiz_diffs = [(i % _N_STUDENT_LEVELS) + 1 for i in range(N_QUESTIONS)]
                _level_engine_cache[class_level] = {
                    "predict": lambda r, d, _b=bucket: _heuristic_predict_level(r, d, _b),
                    "quiz_diffs": generic_quiz_diffs,
                    "n_questions": N_QUESTIONS,
                    "bucket": bucket,
                }
    return _level_engine_cache[class_level]


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


def public_exercise(ex, natural_by_id=NATURAL_BY_ID):
    """Exercice envoyé au front (enonce + hint + answer inclus, le JS gère l'affichage/masquage).
    Préfère la version en français naturel (exercises_bank_natural.json) si disponible,
    champ par champ, en conservant l'id/chapter_id/notion/difficulty d'origine."""
    natural = natural_by_id.get(ex["id"], {})
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


def practice_choices(allowed, level, bank=BANK, bucket=None):
    bucket = bucket or difficulty_bucket
    pool = [e for e in bank if e.get("chapter_id") in allowed] if allowed else bank
    return [
        {"id": e["id"], "label": f"{e.get('chapter_id')} : {e.get('notion')}"}
        for e in pool
        if bucket(e["difficulty"]) == level
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
# Pipeline de build frontend (voir vite.config.js, DEPLOYMENT.md section
# "Frontend : build, cache busting") : `npm run build` régénère
# static-dist/ (HTML réécrit avec les noms de fichiers JS/CSS hashés,
# jamais de renommage manuel) à côté de static/ (sources, jamais modifiées
# par le build). Si static-dist/ existe, on le sert en priorité — sinon
# (aucun build lancé, ex: développement local sans Node) on retombe sur
# static/ tel quel, comportement historique inchangé.
_STATIC_DIST = Path(__file__).parent / "static-dist"
_STATIC_FOLDER = "static-dist" if _STATIC_DIST.is_dir() else "static"
app = Flask(__name__, static_folder=_STATIC_FOLDER, static_url_path="")
app.secret_key = _get_or_create_secret("NOVAMATH_SECRET_KEY", ".flask_secret_key")
# Audit pré-production (2026-08-28) : sans ceci, request.url_root/is_secure
# restent "http://" derrière un reverse proxy qui termine le TLS (Render,
# Railway, Fly.io...), même sur un domaine HTTPS réel — ça affectait
# directement les success_url/cancel_url Stripe (api_checkout_create_session
# ci-dessous) et les liens envoyés par email (APP_BASE_URL reste séparé et
# à positionner manuellement, voir .env.example). N'affecte jamais le
# développement local (TRUST_PROXY_HEADERS par défaut à False hors
# production, voir config.py) : aucun changement de comportement en dev.
if config.TRUST_PROXY_HEADERS:
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_for=1, x_host=1)
# Debug + cookie de session Flask (session["q"]... état du quiz) pilotés par
# FLASK_ENV (voir config.py) : comportement dev inchangé par défaut, cookies
# Secure/HttpOnly/SameSite forcés en production.
app.config.update(
    DEBUG=config.DEBUG,
    SESSION_COOKIE_SECURE=config.SESSION_COOKIE_SECURE,
    SESSION_COOKIE_HTTPONLY=config.SESSION_COOKIE_HTTPONLY,
    SESSION_COOKIE_SAMESITE=config.SESSION_COOKIE_SAMESITE,
    RATE_LIMIT_ENABLED=config.RATE_LIMIT_ENABLED,
    # Rejette tout corps de requête au-delà de cette taille AVANT lecture
    # complète en mémoire (voir config.py::MAX_CONTENT_LENGTH) — protection
    # contre un upload massif (mémoire/disque), indépendante des limites
    # métier par route (15 Mo PDF, 5 Mo pièce jointe support) qui restent
    # inchangées et s'appliquent en plus de celle-ci.
    MAX_CONTENT_LENGTH=config.MAX_CONTENT_LENGTH,
)


@app.errorhandler(413)
def _request_entity_too_large(_error):
    return jsonify({"error": "Fichier ou requête trop volumineux."}), 413
# Clé admin pour la modération des avis (masquer/épingler/modifier/supprimer
# n'importe quel avis) — jamais en dur dans le code (voir _get_or_create_secret).
ADMIN_KEY = _get_or_create_secret("NOVAMATH_ADMIN_KEY", ".admin_key")

db.init_db()
# Infrastructure de préparation (ai_providers/subscription_ai_mapping,
# webapp/ai_provider_service.py) — n'insère les fournisseurs par défaut que
# si la table est encore vide (idempotent), et n'est lue par aucun fichier de
# webapp/chatbot/ à ce jour : ne change strictement rien au comportement du
# chatbot, qui continue d'utiliser les constantes de provider_manager.py.
ai_provider_service.seed_default_providers()
# Catalogue administrable des abonnements (subscription_plans, voir
# subscription_plan_service.py) — n'insère les 3 plans par défaut que si la
# table est encore vide (idempotent). PAS branché à plan_service.py/
# quota_service.py : ne change strictement rien aux droits/quotas réellement
# appliqués au chatbot.
subscription_plan_service.seed_default_plans()
# Socle de sécurité de l'espace Administration (voir role_service.py) —
# promeut immédiatement en SUPER_ADMIN tout compte de NOVAMATH_SUPER_ADMIN_
# EMAILS déjà existant en base, sans attendre sa prochaine connexion. Sûr à
# répéter à chaque démarrage : no-op pour un email absent de `users` ou déjà
# au rôle SUPER_ADMIN. Le cas "compte créé après ce démarrage" reste couvert
# séparément par auth.py (register/_create_authenticated_session).
sync_super_admin_bootstrap_for_configured_emails()
# Purge les fenêtres de rate limiting expirées à chaque démarrage — aucune
# tâche planifiée n'existe dans ce projet (voir rate_limit_service.cleanup()),
# donc rate_limit_events ne grossirait sinon jamais qu'à la hausse.
rate_limit_service.cleanup()
# Journalisation structurée + middleware de supervision (durée de requête,
# métriques, capture des exceptions non gérées) — toute la logique vit dans
# logging_service.py, voir sa docstring.
logging_service.init_app(app)
# En-têtes de sécurité HTTP (CSP, HSTS, X-Frame-Options, etc.) — toute la
# logique vit dans security_headers_service.py, voir sa docstring.
security_headers_service.init_app(app)
# Fournisseur IA réellement actif, journalisé une fois au démarrage — pour ne
# plus jamais découvrir après coup qu'un CHATBOT_PROVIDER oublié dans .env a
# fait retomber le chatbot sur FakeProvider (voir provider_manager.py).
provider_manager.log_startup_banner()
app.register_blueprint(auth_bp)


# ── Supervision ──────────────────────────────────────────────────────────────
# Route infrastructure (sondée par un load balancer / uptime monitor) :
# jamais authentifiée, jamais rate-limitée (voir rate_limit_service.py,
# "Ne pas limiter : ... health"), aucune logique ici — entièrement déléguée à
# health_service.py.
@app.route("/api/health")
def api_health():
    result = health_service.snapshot()
    return jsonify(result), 200 if result["status"] == "ok" else 503

# Pages qui nécessitent désormais un compte connecté : servies via une route
# explicite (au lieu du handler statique automatique de Flask) pour pouvoir
# vérifier la session côté serveur avant d'envoyer le HTML — une redirection
# uniquement côté client (JS) laisserait la page protégée s'afficher un
# instant et serait contournable.
PROTECTED_PAGES = [
    "dashboard.html", "chapitres.html", "cours.html", "exercice.html", "profil.html",
    "chatbot.html", "abonnement.html",
]

# ── Feature Flags : pages entièrement réservées à un palier payant ──────────
# Point d'extension unique pour verrouiller une future page premium/ultra :
# ajouter "ma_page.html": Feature.X ici suffit, _serve_protected() ci-dessous
# se charge de la redirection — aucune autre page à toucher. Vide aujourd'hui
# car aucune des pages existantes n'affiche de contenu qui dépasse le plan
# Free (voir plan_service.FEATURE_MATRIX) : chaque page reste donc accessible
# à tout compte connecté, aujourd'hui comme demain si son contenu ne change
# pas de palier.
PAGE_FEATURE_REQUIREMENTS = {}


def _serve_protected(page):
    user = get_current_user()
    if user is None:
        return redirect(f"/?next={page}")
    required_feature = PAGE_FEATURE_REQUIREMENTS.get(page)
    if required_feature is not None and not plan_service.has_feature(user, required_feature):
        return redirect(f"/abonnement.html?required={required_feature.value}")
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
    # security_headers_service.build_csp(), qui lit g.csp_nonce pour construire
    # l'en-tête (middleware installé via security_headers_service.init_app()).
    nonce = secrets.token_urlsafe(16)
    g.csp_nonce = nonce
    injected = f'<script nonce="{nonce}">window.__NOVAMATH_USER_ID__ = {json.dumps(user["id"])};</script>'
    html = html.replace("<head>", f"<head>\n{injected}", 1)
    return Response(html, mimetype="text/html")


for _page in PROTECTED_PAGES:
    app.add_url_rule(f"/{_page}", endpoint=f"protected_{_page}", view_func=lambda p=_page: _serve_protected(p))


# ── Page de diagnostic temporaire (debug-runtime.html/.js) ──────────────────
# Aucune donnée serveur : uniquement de la lecture d'état côté navigateur
# (localStorage/sessionStorage/cookies/fetch bruts) pour comparer l'état d'un
# environnement qui bloque avec un environnement qui fonctionne. Gardée par
# config.DEBUG (jamais accessible en production, où DEBUG est toujours faux —
# voir config.py::DEBUG) : 404 sinon, comme si la route n'existait pas.
@app.route("/debug-runtime")
def _serve_debug_runtime():
    if not config.DEBUG:
        abort(404)
    return send_from_directory(app.static_folder, "debug-runtime.html")


# settings.html a été retiré : les Paramètres sont désormais un popup ouvert
# depuis n'importe quelle page (voir static/js/settingsPopup.js). Un ancien
# lien/favori vers /settings.html est redirigé plutôt que de renvoyer un 404.
@app.route("/settings.html")
def _redirect_legacy_settings_page():
    return redirect("/dashboard.html")


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
    "Commencer gratuitement" réutilisait (voir auth.js::currentAccount) au lieu
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
    #
    # `?class_level=` (optionnel, "seconde" par défaut) : sans paramètre,
    # comportement HISTORIQUE strictement inchangé (BANK/CHAPTERS/CHAPTER_META
    # déjà chargés en mémoire). Toute autre classe déclarée dans
    # curriculum_registry.py est résolue via _class_bank() — jamais de repli
    # silencieux vers les données Seconde ; une classe inconnue renvoie 404
    # (même convention que /api/site/stats).
    class_level = request.args.get("class_level") or "seconde"
    if class_level not in curriculum_registry.CURRICULUM_REGISTRY:
        return jsonify({"error": f"classe inconnue : {class_level!r}"}), 404
    res = _class_bank(class_level)
    bank, chapters, chapter_meta = res["bank"], res["chapters"], res["chapter_meta"]
    variants_count_by_index = res["variants_count_by_index"]
    difficulty_levels = sorted(set(e.get("difficulty") for e in bank if e.get("difficulty") is not None))

    default_difficulty = difficulty_levels[len(difficulty_levels) // 2] if difficulty_levels else 2
    chapters_meta = []
    for chapter_id in chapters:
        meta = chapter_meta.get(chapter_id, {})
        chapter_exercises = [(i, e) for i, e in enumerate(bank) if e.get("chapter_id") == chapter_id]
        notions = sorted(set(e.get("notion") for _, e in chapter_exercises if e.get("notion")))
        diff_counts = {d: 0 for d in difficulty_levels}
        for _, e in chapter_exercises:
            d = e.get("difficulty")
            if d in diff_counts:
                diff_counts[d] += 1
        dominant_difficulty = max(diff_counts, key=diff_counts.get) if chapter_exercises else default_difficulty

        notions_detail = []
        for n in notions:
            n_exs = [(i, e) for i, e in chapter_exercises if e.get("notion") == n]
            n_diff_counts = {d: 0 for d in difficulty_levels}
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
                "n_natural_variants": _n_variants_for([i for i, _ in n_exs], variants_count_by_index),
                # Additif : ids exposés pour permettre de lancer une série ciblée sur
                # une seule notion depuis chapitres.html (aucune logique de sélection modifiée).
                "exercise_ids": [e["id"] for _, e in n_exs],
            })
        chapters_meta.append({
            "id": chapter_id,
            # Repli identique à generate_cours_from_bank.py quand aucun
            # programme officiel n'est déclaré (program_file=None) — jamais
            # atteint pour Seconde (CHAPTER_META toujours complet).
            "title": meta.get("title", chapter_id.replace("_", " ")),
            "notions_cours": meta.get("notions_cours", notions),
            "notions_detail": notions_detail,
            "n_exercises": len(chapter_exercises),
            "n_notions": len(notions),
            "difficulty_dominant": dominant_difficulty,
            "difficulty_counts": diff_counts,
            "difficulties_available": sorted(d for d, c in diff_counts.items() if c > 0),
            "n_natural_variants": _n_variants_for([i for i, _ in chapter_exercises], variants_count_by_index),
        })
    return jsonify({
        "chapters": chapters,
        "n_questions": _level_engine(class_level)["n_questions"],
        "chapters_meta": chapters_meta,
        # Additif : totaux globaux calculés dynamiquement depuis la banque,
        # pour tout affichage global (accueil, dashboard) sans valeur en dur.
        "totals": {
            "n_exercises": len(bank),
            "n_chapters": len(chapters),
            "n_notions": len(set(e.get("notion") for e in bank if e.get("notion"))),
            "difficulty_levels": difficulty_levels,
            "difficulty_counts": {d: sum(1 for e in bank if e.get("difficulty") == d) for d in difficulty_levels},
            "n_natural_variants": sum(variants_count_by_index),
        },
    })


@app.route("/api/site/stats")
def api_site_stats():
    """Source unique de vérité pour les statistiques marketing affichées sur la
    landing page (et toute autre page) : calculées à la volée depuis BANK,
    jamais codées en dur côté frontend.

    `?class_level=` (optionnel, "seconde" par défaut) : pour Seconde, cette
    route continue d'utiliser EXACTEMENT le même calcul qu'avant (depuis BANK,
    déjà chargée en mémoire) — aucun changement de comportement pour l'appel
    historique sans paramètre. Toute autre classe (ex. "premiere") délègue à
    curriculum_stats.py, qui lit sa propre banque via curriculum_registry.py
    sans jamais toucher BANK/MODEL ni aucune structure utilisée par les
    routes d'exercices (api_practice_*).

    `class_level` vient directement d'un paramètre de requête HTTP, donc d'un
    client non fiable par nature (frontend avec une valeur périmée en cache,
    appel direct de l'API, faute de frappe) — il DOIT être validé ici avant
    d'atteindre curriculum_stats.compute_stats(), qui indexe le registre sans
    filet (KeyError volontaire pour un appelant interne de confiance, voir
    canonical_ids.py). Sans cette validation, toute valeur non reconnue fait
    remonter un KeyError non intercepté jusqu'à Flask (500)."""
    class_level = request.args.get("class_level") or "seconde"
    if class_level == "seconde":
        return jsonify({
            "totalExercises": len(BANK),
            "chapters": len(CHAPTERS),
            "notions": len(set(e.get("notion") for e in BANK if e.get("notion"))),
            "difficultyLevels": len(DIFFICULTY_LEVELS),
        })
    if class_level not in curriculum_registry.CURRICULUM_REGISTRY:
        return jsonify({"error": f"classe inconnue : {class_level!r}"}), 404
    return jsonify(curriculum_stats.compute_stats(class_level))


@app.route("/api/curricula")
def api_curricula():
    """Liste des programmes scolaires disponibles (Seconde, Première...),
    avec leurs statistiques calculées automatiquement — seule route que le
    sélecteur de classe interroge pour afficher ses cartes : ajouter une
    classe se fait uniquement dans curriculum_registry.py, jamais ici."""
    return jsonify(curriculum_stats.list_curricula())


@app.route("/api/exercise/<int:exercise_id>")
def api_exercise(exercise_id):
    """Route additive : consultation directe d'un exercice (mode entraînement enrichi),
    sans toucher aux routes /api/practice/* existantes.

    `?class_level=` (optionnel, "seconde" par défaut) : même convention que
    /api/chapters — la banque résolue via _class_bank() ne mélange jamais
    deux classes (un id peut exister dans les deux banques avec un contenu
    différent)."""
    class_level = request.args.get("class_level") or "seconde"
    if class_level not in curriculum_registry.CURRICULUM_REGISTRY:
        return jsonify({"error": f"classe inconnue : {class_level!r}"}), 404
    res = _class_bank(class_level)
    ex = res["bank_by_id"].get(exercise_id)
    if ex is None:
        return jsonify({"error": "exercice inconnu"}), 404
    return jsonify({"exercise": public_exercise(ex, natural_by_id=res["natural_by_id"])})


def _stats_entry_key(entry):
    """Identité stable d'une entrée d'historique/série pour la fusion (voir
    _merge_stats_payload) : `ts`/`id` quand présent (toujours le cas pour les
    entrées produites par le code actuel de store.js — recordAnswer()/
    finalizeSeries()), sinon le contenu complet sérialisé (entrées historiques
    d'avant l'ajout de ce champ) — jamais `id(entry)` (l'identité mémoire de
    l'objet Python), qui dupliquerait une même entrée à chaque fusion
    successive puisqu'elle change à chaque désérialisation JSON."""
    ts_or_id = entry.get("ts", entry.get("id"))
    if ts_or_id is not None:
        return ts_or_id
    return json.dumps(entry, sort_keys=True, default=str)


def _merge_stats_payload(old, incoming):
    """Fusionne l'état de gamification déjà persisté (`old`) avec celui reçu
    du client (`incoming`) — jamais un simple remplacement (voir audit
    Release Candidate : deux onglets/appareils postant des états locaux
    divergents écrasaient silencieusement l'un l'autre, perte d'XP/historique/
    séries/badges). Union par identité stable de chaque entrée d'historique/
    série (jamais de doublon même fusionné plusieurs fois), union des badges
    (un badge débloqué ne peut jamais être "retiré" par une fusion), XP
    toujours RECALCULÉ à partir de l'historique fusionné (jamais celui envoyé
    tel quel par le client) — auto-cohérent par construction, ne peut jamais
    reculer puisqu'il ne dépend que d'un ensemble d'entrées qui ne fait que
    grossir. Compatible SQLite/PostgreSQL par construction : aucune requête
    SQL ici, uniquement une fusion de structures Python avant persistance."""
    old_history = old.get("history") or []
    incoming_history = incoming.get("history") or []
    merged_by_key = {}
    for entry in old_history + incoming_history:
        merged_by_key[_stats_entry_key(entry)] = entry
    merged_history = sorted(merged_by_key.values(), key=lambda h: h.get("ts") or 0)

    old_series = old.get("series") or []
    incoming_series = incoming.get("series") or []
    series_by_key = {}
    for entry in old_series + incoming_series:
        series_by_key[_stats_entry_key(entry)] = entry
    merged_series = sorted(series_by_key.values(), key=lambda s: s.get("startedAt") or 0)

    merged_badges = sorted(set(old.get("badges") or []) | set(incoming.get("badges") or []))
    merged_xp = sum(h.get("xp") or 0 for h in merged_history)

    return {"xp": merged_xp, "history": merged_history, "badges": merged_badges, "series": merged_series}


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


_STATS_SERIES_WINDOW = {
    plan_service.Plan.FREE: 20,
    plan_service.Plan.PREMIUM: 50,
    plan_service.Plan.ULTRA: None,
}

# Chantier "Différenciation des abonnements — suggestions du Dashboard"
# (2026-08-27) : nombre maximal de cartes de suggestion (renderSuggestions,
# voir static/js/dashboard.js) affichées à l'élève — le calcul lui-même
# (taux de réussite par notion à partir de history[], jamais tronqué) reste
# strictement inchangé, seul le nombre de cartes RETENUES varie. Même
# mécanisme que _STATS_SERIES_WINDOW ci-dessus (effective_plan, jamais une
# nouvelle notion de plan) — volontairement PAS dans QUOTA_MATRIX
# (quota_service.py) : il ne s'agit pas d'une consommation quotidienne
# remise à zéro, mais d'un plafond d'affichage statique, structurellement
# identique à _STATS_SERIES_WINDOW plutôt qu'à un QuotaType.
_SUGGESTIONS_LIMIT_BY_PLAN = {
    plan_service.Plan.FREE: 3,
    plan_service.Plan.PREMIUM: 5,
    plan_service.Plan.ULTRA: 8,
}


@app.route("/api/stats", methods=["GET", "POST"])
@login_required
@requires_feature(Feature.STATISTICS)
@csrf_protect
def api_stats():
    """Persistance de la gamification (XP, historique, badges, séries) — un
    fichier JSON par utilisateur (webapp/auth.py::read_user_stats/write_user_stats),
    sans lien avec la logique de sélection/prédiction. Nécessite une session
    active depuis l'introduction des comptes."""
    user_id = request.current_user["id"]

    if request.method == "GET":
        stats = read_user_stats(user_id)
        # Répartition dashboard par plan (chantier 2026-08-26) : seule la
        # fenêtre de `series[]` (graphique + table "dernières séries") est
        # réduite selon le plan effectif. `history[]` — dont dépendent seuls
        # streak/XP/mastery/badges/accuracy côté client (store.js) — reste
        # toujours complet : aucune de ces fonctions n'utilise `series`
        # (vérifié dans store.js::BADGE_DEFS/scopedStats). La troncature ne
        # porte que sur la réponse ; le fichier persisté sur disque n'est
        # jamais modifié (voir _merge_stats_payload, qui relit toujours
        # l'historique complet depuis read_user_stats() côté POST).
        plan = owner_test_plan_service.effective_plan(request.current_user)
        series = stats.get("series") or []
        window = _STATS_SERIES_WINDOW[plan]
        if window is not None and len(series) > window:
            stats = {**stats, "series": series[-window:]}
        # suggestions_limit : jamais persistée sur disque (ajoutée uniquement
        # à la réponse, même principe que la troncature de series[]
        # ci-dessus) — dashboard.js l'utilise pour plafonner l'affichage des
        # suggestions déjà calculées côté client à partir de history[],
        # jamais recalculées ici.
        stats = {**stats, "suggestions_limit": _SUGGESTIONS_LIMIT_BY_PLAN[plan]}
        # notion_breakdown_enabled (Chantier "Différenciateurs Premium/Ultra",
        # 2026-08-27) : réutilise Feature.ADVANCED_EXPLANATIONS (déjà
        # Premium+, déjà utilisée pour la richesse du contenu de cours —
        # même famille "contenu pédagogique enrichi") plutôt qu'une nouvelle
        # Feature. has_feature() résout déjà owner_test_plan_service.
        # effective_plan() en interne : le mode test Owner fonctionne donc
        # automatiquement, sans code spécifique ici. Jamais persisté sur
        # disque (même principe que suggestions_limit ci-dessus) — le calcul
        # du bilan lui-même reste côté client, à partir de history[] déjà
        # complet dans `stats` ; ce flag ne fait qu'autoriser son affichage.
        stats = {**stats, "notion_breakdown_enabled": plan_service.has_feature(request.current_user, Feature.ADVANCED_EXPLANATIONS)}
        return jsonify(stats)

    data = request.get_json(force=True) or {}
    incoming = {
        "xp": int(data.get("xp", 0)),
        "history": data.get("history", []),
        "badges": data.get("badges", []),
        "series": data.get("series", []),
    }
    # Fusion (jamais un remplacement) : voir _merge_stats_payload — empêche
    # qu'un état local périmé (autre onglet/appareil pas encore resynchronisé)
    # n'efface silencieusement de l'XP/historique/séries/badges plus récents
    # déjà persistés.
    payload = _merge_stats_payload(read_user_stats(user_id), incoming)
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
@requires_feature(Feature.COURSES)
@csrf_protect
def api_course_progress():
    """Progression de lecture du module Cours (section courante, notions
    terminées, score des mini-quiz) — même stratégie que /api/stats et
    /api/settings : un fichier JSON par utilisateur, purgé avec le reste du
    compte pour les invités (voir auth.py::_purge_account)."""
    user_id = request.current_user["id"]

    if request.method == "GET":
        class_level = request.args.get("class_level") or "seconde"
        if class_level not in curriculum_registry.CURRICULUM_REGISTRY:
            return jsonify({"error": f"classe inconnue : {class_level!r}"}), 404
        return jsonify(read_user_course_progress(user_id, class_level=class_level))

    data = request.get_json(force=True) or {}
    chapter_id = data.get("chapterId")
    notion_id = data.get("notionId")
    patch = data.get("patch") or {}
    class_level = data.get("class_level") or "seconde"
    if class_level not in curriculum_registry.CURRICULUM_REGISTRY:
        return jsonify({"error": f"classe inconnue : {class_level!r}"}), 404
    if not chapter_id or not notion_id or not isinstance(patch, dict):
        return jsonify({"error": "chapterId, notionId et patch sont requis"}), 400
    updated = write_user_course_progress(user_id, chapter_id, notion_id, patch, class_level=class_level)
    return jsonify(updated)


@app.route("/api/course-content/<class_level>/<chapter_id>")
@login_required
@requires_feature(Feature.COURSES)
def api_course_content(class_level, chapter_id):
    """Contenu pédagogique complet d'un chapitre, filtré selon le plan
    effectif de l'utilisateur (Chantier "Répartition du contenu des cours par
    plan") — remplace le fetch direct que faisait auparavant cours.js vers le
    JSON statique (webapp/static/data/cours*/), désormais déplacé hors de
    static/ (voir curriculum_registry.COURSE_CONTENT_DIR) et donc plus
    accessible par aucune URL directe. `Feature.COURSES` est en Free (aucune
    notion n'est verrouillée par cette route, voir course_content_service.py :
    seule la RICHESSE du contenu à l'intérieur varie selon le plan)."""
    content = course_content_service.get_chapter_content(class_level, chapter_id, request.current_user)
    if content is None:
        return jsonify({"error": "chapitre introuvable"}), 404
    return jsonify(content)


@app.route("/api/data/summary")
@login_required
@requires_feature(Feature.EXPORT)
def api_data_summary():
    """Chiffres bruts affichés dans l'onglet Données des paramètres, et
    source de données du rapport PDF (js/pdfExport.js::exportProgressPdf) —
    calculés à la volée depuis l'historique réel (aucune valeur mise en cache
    séparée). Feature.EXPORT (présente en Free) : ne restreint personne
    aujourd'hui, mais garde le panneau "Données" et l'export PDF alignés sur
    la même décision d'accès si ce plan devait un jour évoluer."""
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
    """« Exporter les statistiques » / « Télécharger mes données » — droit RGPD
    d'export/portabilité des données. Un seul fichier JSON regroupant profil,
    statistiques, préférences, progression Cours ET (SEC-04) historique complet
    des consentements/demandes de consentement parental/journal de sécurité —
    jamais de secret (pas de hash de mot de passe, pas de secret 2FA, pas de
    cookie/token, voir privacy_service._SENSITIVE_USER_FIELDS). Volontairement
    non gatée par @requires_feature : c'est un export brut à but de portabilité
    des données, pas le rapport PDF marketing (voir Feature.EXPORT sur
    /api/data/summary, qui alimente réellement js/pdfExport.js) — un accès à
    ses propres données ne doit jamais dépendre d'un palier d'abonnement.
    L'agrégation des données issues de la base est déléguée à privacy_service
    (qui journalise aussi l'événement `gdpr_export`) ; les données stockées en
    fichiers JSON par utilisateur restent lues ici, via auth.py."""
    user = request.current_user
    export = privacy_service.export_account_data(user, ip=request.headers.get("X-Forwarded-For", request.remote_addr))
    export["stats"] = read_user_stats(user["id"])
    export["settings"] = read_user_settings(user["id"])
    export["course_progress"] = read_user_course_progress(user["id"])
    export["exported_at"] = _date.today().isoformat()
    resp = jsonify(export)
    resp.headers["Content-Disposition"] = f'attachment; filename="novamath_export_{user["id"]}.json"'
    return resp


@app.route("/api/privacy/consent-history")
@login_required
def api_privacy_consent_history():
    """Historique complet des décisions de consentement (CGU, politique de
    confidentialité, consentement parental, cookies) du compte connecté —
    droit RGPD de traçabilité, affiché dans Paramètres → Confidentialité."""
    return jsonify({"consent_history": privacy_service.get_consent_history(request.current_user["id"])})


@app.route("/api/privacy/policy-status")
@login_required
def api_privacy_policy_status():
    """Indique si le compte connecté doit ré-accepter les CGU/politique de
    confidentialité (nouvelle version publiée depuis sa dernière acceptation,
    voir consent_service.TERMS_VERSION/PRIVACY_VERSION)."""
    return jsonify({
        "needs_reacceptance": consent_service.needs_policy_reacceptance(request.current_user),
        "terms_version": consent_service.TERMS_VERSION,
        "privacy_version": consent_service.PRIVACY_VERSION,
    })


@app.route("/api/privacy/policy-accept", methods=["POST"])
@login_required
@csrf_protect
def api_privacy_policy_accept():
    consent_service.record_policy_reacceptance(
        request.current_user["id"], ip=request.headers.get("X-Forwarded-For", request.remote_addr)
    )
    return jsonify({"ok": True})


@app.route("/api/privacy/cookie-consent", methods=["GET"])
@login_required
def api_privacy_get_cookie_consent():
    """Préférences cookies du compte connecté — la bannière (cookieConsent.js)
    lit d'abord localStorage (fonctionne aussi pour un visiteur anonyme) ; un
    compte connecté peut en plus les relire/modifier ici depuis Paramètres."""
    return jsonify(consent_service.get_cookie_consent(request.current_user["id"]))


@app.route("/api/privacy/cookie-consent", methods=["PUT"])
@login_required
@csrf_protect
def api_privacy_set_cookie_consent():
    data = request.get_json(force=True) or {}
    result = consent_service.set_cookie_consent(
        request.current_user["id"],
        statistics=bool(data.get("statistics")),
        marketing=bool(data.get("marketing")),
        ip=request.headers.get("X-Forwarded-For", request.remote_addr),
    )
    return jsonify(result)


@app.route("/parent/consent/<token>")
def parent_consent_page(token):
    """Page publique ouverte par le parent depuis le lien reçu par email —
    aucune logique métier ici (voir consent_service.get_public_consent_info,
    appelé côté client par static/js/parentConsent.js via /api/auth/
    parental-consent/<token>) : `token` n'est utilisé que pour le routing,
    jamais lu côté serveur dans cette vue."""
    return send_from_directory(app.static_folder, "parent-consent.html")


# ── Avis (section "Avis" de la landing page), additif ─────────────────────────
ALLOWED_AVATAR_PREFIXES = (
    "data:image/png;base64,",
    "data:image/jpeg;base64,",
    "data:image/jpg;base64,",
    "data:image/webp;base64,",
    "data:image/gif;base64,",
)
MAX_AVATAR_LEN = 300_000  # ~220 Ko décodé, largement suffisant pour un avatar de profil
CLASSE_CHOICES = {"Troisième", "Seconde", "Première", "Terminale", "Autre"}


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
    # compare_digest (déjà utilisé par auth.py::csrf_protect pour le même
    # type de comparaison) plutôt que `==` : une comparaison de chaînes
    # standard s'arrête au premier caractère différent, ce qui fuite un
    # signal temporel exploitable pour retrouver ADMIN_KEY caractère par
    # caractère (voir audit production). ADMIN_KEY vide (non configurée)
    # ne doit jamais matcher un header vide — compare_digest("", "") est
    # True, d'où le `bool(key)` conservé avant.
    return bool(key) and secrets.compare_digest(key, ADMIN_KEY)


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
# methods={"POST"} : seule la création d'un avis (potentiellement anonyme,
# donc rate-limitée par IP faute de compte, voir rate_limit_service) doit
# être limitée — la lecture (GET) est publique et consultée à chaque
# chargement de la page, jamais visée par cette protection anti-spam.
@rate_limit(requests=10, per_seconds=60, methods={"POST"})
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
@rate_limit(requests=10, per_seconds=60)
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


@app.route("/api/practice/load", methods=["POST"])
@login_required
@requires_feature(Feature.EXERCISES)
@csrf_protect
def api_practice_load():
    """`class_level` (optionnel dans le corps JSON, "seconde" par défaut) :
    même convention que /api/chapters — un id d'exercice peut exister dans
    les deux banques avec un contenu différent, jamais de mélange.

    QuotaType.EXERCISES_DAILY (Chantier "Limitation des exercices par
    abonnement") : consommé ICI, une fois l'exercice réellement trouvé et sa
    réponse déjà construite — jamais avant (classe inconnue / id inconnu ne
    doivent rien facturer), jamais après (aucune opération ne peut plus
    échouer entre consume() et le retour de la réponse ci-dessous)."""
    data = request.get_json(force=True) or {}
    ex_id = data.get("exercise_id")
    class_level = data.get("class_level") or "seconde"
    if class_level not in curriculum_registry.CURRICULUM_REGISTRY:
        return jsonify({"error": f"classe inconnue : {class_level!r}"}), 404
    res = _class_bank(class_level)
    ex = res["bank_by_id"].get(ex_id)
    if ex is None:
        return jsonify({"error": "exercice inconnu"}), 404

    payload = {"exercise": public_exercise(ex, natural_by_id=res["natural_by_id"])}

    try:
        quota_service.consume(request.current_user, QuotaType.EXERCISES_DAILY)
    except QuotaExceededError as e:
        return jsonify(quota_service.exceeded_error_payload(e)), 429

    return jsonify(payload)


@app.route("/api/practice/result", methods=["POST"])
@login_required
@requires_feature(Feature.EXERCISES)
@csrf_protect
def api_practice_result():
    data = request.get_json(force=True) or {}
    is_correct = bool(data.get("correct"))
    ex_id = data.get("exercise_id")
    class_level = data.get("class_level") or "seconde"
    if class_level not in curriculum_registry.CURRICULUM_REGISTRY:
        return jsonify({"error": f"classe inconnue : {class_level!r}"}), 404
    res = _class_bank(class_level)
    engine = _level_engine(class_level)
    current_ex = res["bank_by_id"].get(ex_id)
    if current_ex is None:
        return jsonify({"error": "exercice inconnu"}), 400

    p_resps = session.get("practice_resps", []) + [1 if is_correct else 0]
    p_diffs = session.get("practice_diffs", []) + [current_ex["difficulty"]]
    history = session.get("history", [])
    allowed = session.get("allowed", [])
    current_lvl = session.get("current_level", 1)

    result_word = "Réussi" if is_correct else "Échoué"
    history = history + [f"{result_word} — {current_ex.get('chapter_id')} : {current_ex.get('notion')}"]

    new_lvl = current_lvl
    level_updated = False
    if len(p_resps) >= 3:
        new_lvl = engine["predict"](p_resps, p_diffs)
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
        "practice_choices": practice_choices(allowed, new_lvl, bank=res["bank"], bucket=engine["bucket"]),
    })


# ── Génération d'exercices sur mesure (Ultra) — Chantier "Différenciateurs
# Premium/Ultra" (2026-08-27). Réutilise le moteur symbolique existant
# (exercise_generator/, voir registry.py pour la cartographie exacte des
# notions/familles réellement disponibles) : AUCUN appel LLM, correction
# garantie par sympy. Distinct de _class_bank()/api_practice_load : un
# exercice généré ici n'est jamais écrit dans la banque commune, jamais
# persisté, et ne peut donc pas être posté à /api/practice/result (qui
# exige un exercice présent dans res["bank_by_id"] pour son moteur adaptatif
# de session — contaminer cette banque avec du contenu éphémère aurait été
# plus risqué que de laisser le frontend afficher directement answer/
# solution_steps déjà fournis par le générateur, en auto-correction).
# QuotaType.CUSTOM_EXERCISES (quota_service.py) volontairement PAS consommé
# ici : Feature.CUSTOM_EXERCISES est déjà réservée à Ultra seul dans
# FEATURE_MATRIX (Free/Premium reçoivent 403 avant d'atteindre un quota), et
# QUOTA_MATRIX[ULTRA][CUSTOM_EXERCISES] est illimité — consommer n'aurait
# aucun effet pratique aujourd'hui (décision validée explicitement, pas
# supposée).
@app.route("/api/practice/generate/options")
@login_required
@requires_feature(Feature.CUSTOM_EXERCISES)
def api_practice_generate_options():
    """Notions/familles réellement générables à la demande, pour construire
    le sélecteur frontend — jamais une liste inventée, dérivée de
    exercise_generator.registry.available_notions() (FAMILIES réelles).
    Couvre les 3 classes qui ont un moteur symbolique (troisieme/seconde/
    premiere) — le frontend filtre par la classe actuellement sélectionnée
    (getStoredClassLevel), une classe sans générateur reçoit simplement une
    liste vide (jamais une fausse promesse)."""
    notions = [
        {"class_level": class_level, "chapter_id": chapter_id, "notion": notion, "families": families}
        for (class_level, chapter_id, notion), families in exercise_generator_registry.available_notions().items()
    ]
    return jsonify({"notions": notions})


@app.route("/api/practice/generate", methods=["POST"])
@login_required
@requires_feature(Feature.CUSTOM_EXERCISES)
@csrf_protect
def api_practice_generate():
    data = request.get_json(force=True) or {}
    # Les 4 champs sont exigés ensemble : family_id seul est AMBIGU (voir
    # exercise_generator/registry.py — plusieurs modules réutilisent le même
    # family_id pour des notions différentes). Le frontend les obtient tous
    # les 4 tels quels depuis GET /api/practice/generate/options, jamais
    # reconstruits à la main.
    class_level = data.get("class_level")
    chapter_id = data.get("chapter_id")
    notion = data.get("notion")
    family_id = data.get("family_id")
    if not (class_level and chapter_id and notion and family_id):
        return jsonify({"error": "class_level, chapter_id, notion et family_id sont requis"}), 400

    generated = exercise_generator_registry.generate(class_level, chapter_id, notion, family_id)
    if generated is None:
        return jsonify({"error": "famille d'exercice inconnue"}), 404

    exercise = {
        **generated,
        "id": f"generated:{family_id}:{uuid.uuid4().hex[:8]}",
        "class_level": class_level,
    }
    return jsonify({"exercise": exercise})


# ── Chatbot pédagogique (webapp/chatbot/) — ces routes forment le "ChatController"
# de l'architecture en couches (Frontend -> ChatController -> ConversationManager
# -> PromptBuilder -> ContextBuilder -> KnowledgeEngine/RuleEngine/MathEngine ->
# RetrievalEngine -> ProviderManager -> fournisseur actif). Elles ne connaissent
# jamais le fournisseur IA actif ni les moteurs internes : tout passe par
# conversation_manager.py. Résumé léger {id, title} des chapitres, calculé une
# seule fois depuis BANK déjà chargée ci-dessus — évite au context_builder de
# recharger exercises_bank.json pour un simple intitulé de chapitre.
_CHATBOT_CHAPTERS_SUMMARY = [
    {"id": cid, "title": CHAPTER_META.get(cid, {}).get("title", cid)} for cid in CHAPTERS
]


@app.route("/api/chatbot/conversations", methods=["GET", "POST"])
@login_required
@require_non_guest
@requires_feature(Feature.CHATBOT)
@csrf_protect
def api_chatbot_conversations():
    user_id = request.current_user["id"]
    if request.method == "GET":
        search = request.args.get("q")
        return jsonify({"conversations": conversation_manager.list_conversations(user_id, search)})
    conv = conversation_manager.create_conversation(user_id)
    return jsonify({"conversation": conv}), 201


@app.route("/api/chatbot/conversations/<int:conversation_id>", methods=["PATCH", "DELETE"])
@login_required
@require_non_guest
@requires_feature(Feature.CHATBOT)
@csrf_protect
def api_chatbot_conversation_detail(conversation_id):
    user_id = request.current_user["id"]
    if request.method == "DELETE":
        conversation_manager.delete_conversation(user_id, conversation_id)
        return jsonify({"ok": True})

    data = request.get_json(force=True) or {}
    conv = None
    if "title" in data:
        conv = conversation_manager.rename_conversation(user_id, conversation_id, data["title"])
    if "pinned" in data:
        conv = conversation_manager.pin_conversation(user_id, conversation_id, bool(data["pinned"]))
    if conv is None:
        return jsonify({"error": "Conversation introuvable."}), 404
    return jsonify({"conversation": conv})


@app.route("/api/chatbot/attachments/pdf", methods=["POST"])
@login_required
@require_non_guest
@requires_feature(Feature.ADVANCED_AI)
@rate_limit(requests=5, per_seconds=3600)
@csrf_protect
def api_chatbot_attachment_pdf():
    """Extrait le texte d'un PDF joint dans le chatbot (voir chatbot/attachments.py) ;
    le fichier n'est jamais écrit sur disque, uniquement traité en mémoire.
    Réservé à Ultra (Feature.ADVANCED_AI) : l'analyse de documents joints est
    une capacité IA avancée, au même titre que le mode "IA avancée" du chatbot
    — le seul palier de la matrice qui inclut cette Feature."""
    from chatbot.attachments import extract_pdf_text, AttachmentError

    file = request.files.get("file")
    if file is None or not file.filename:
        return jsonify({"error": "Aucun fichier reçu."}), 400
    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Seuls les fichiers PDF sont acceptés."}), 400

    # Taille lue via le flux (seek/tell) avant matérialisation en bytes Python
    # — même technique que support_attachment_service.save_attachment — pour
    # ne jamais garder une copie inutile en mémoire d'un fichier déjà refusé.
    file.stream.seek(0, 2)
    size_bytes = file.stream.tell()
    file.stream.seek(0)
    if size_bytes > 15 * 1024 * 1024:
        return jsonify({"error": "Fichier trop volumineux (15 Mo maximum)."}), 400

    file_bytes = file.read()

    try:
        text, truncated = extract_pdf_text(file_bytes)
    except AttachmentError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"text": text, "truncated": truncated, "filename": file.filename})


@app.route("/api/chatbot/conversations/<int:conversation_id>/messages", methods=["GET", "POST"])
@login_required
@require_non_guest
@requires_feature(Feature.CHATBOT)
# methods={"POST"} : seul l'envoi d'un message déclenche un vrai appel au
# moteur IA (flux SSE) — la lecture de l'historique (GET) n'a aucune raison
# d'être limitée à la même fréquence.
@rate_limit(requests=30, per_seconds=60, methods={"POST"})
@csrf_protect
def api_chatbot_messages(conversation_id):
    user = request.current_user
    if request.method == "GET":
        messages = conversation_manager.get_messages(user["id"], conversation_id)
        if messages is None:
            return jsonify({"error": "Conversation introuvable."}), 404
        return jsonify({"messages": messages})

    data = request.get_json(force=True) or {}
    text = (data.get("message") or "").strip()
    if not text:
        return jsonify({"error": "Message vide."}), 400
    if len(text) > MAX_CHATBOT_MESSAGE_CHARS:
        return jsonify({
            "error": f"Message trop long ({len(text)} caractères, maximum {MAX_CHATBOT_MESSAGE_CHARS}).",
        }), 400
    mentions = data.get("mentions") or None
    class_level = data.get("class_level") or "seconde"
    if class_level not in curriculum_registry.CURRICULUM_REGISTRY:
        return jsonify({"error": f"classe inconnue : {class_level!r}"}), 404

    # Contrôle préalable en lecture seule (quota_service.peek_exceeded) : un
    # flux SSE a déjà envoyé ses en-têtes (200) dès la première ligne — il est
    # donc trop tard pour répondre par un vrai 429 une fois `generate()`
    # démarré. La consommation réelle et autoritaire reste dans
    # conversation_manager.stream_reply (check_and_increment_quota, appelée
    # une seule fois par message) ; le except QuotaExceededError plus bas
    # reste en filet de sécurité pour la course concurrente résiduelle (deux
    # requêtes passant ce contrôle au même instant).
    quota_error = quota_service.peek_exceeded(user, QuotaType.CHAT_MESSAGES)
    if quota_error is not None:
        return jsonify(quota_service.exceeded_error_payload(quota_error)), 429

    # BLACK BOX RECORDER (observabilité permanente, aucune logique métier
    # modifiée) : request_id/t_start capturés ICI, en dehors du générateur,
    # car le contexte de requête Flask (g, request) est dépilé avant que
    # `generate()` ne commence réellement à s'exécuter (consommé par le
    # serveur WSGI après le retour de la vue) — même raison que `user`/
    # `conversation_id`/`text` déjà capturés par fermeture ci-dessous.
    request_id = getattr(g, "_novamath_request_id", "-")
    t_start = time.perf_counter()

    def generate():
        first_byte_at = None
        close_reason = "normal"
        logger.info(
            "[BLACKBOX] SSE demarre — request_id=%s route=/messages user=%s conversation_id=%s",
            request_id, user["id"], conversation_id,
        )
        try:
            try:
                for chunk in conversation_manager.stream_reply(
                    user, conversation_id, text, _CHATBOT_CHAPTERS_SUMMARY, mentions=mentions, class_level=class_level,
                    request_id=request_id,
                ):
                    if first_byte_at is None:
                        first_byte_at = time.perf_counter()
                        logger.info(
                            "[BLACKBOX] premier octet — request_id=%s delai_s=%.3f",
                            request_id, first_byte_at - t_start,
                        )
                    yield f"data: {json.dumps({'delta': chunk})}\n\n"
                cards = conversation_manager.attach_action_cards(
                    user, conversation_id, _CHATBOT_CHAPTERS_SUMMARY, class_level=class_level,
                )
                yield f"data: {json.dumps({'done': True, 'cards': cards})}\n\n"
            except QuotaExceededError as e:
                close_reason = "quota_exceeded"
                logger.info(
                    "[BLACKBOX] arret quota — request_id=%s type=%s message=%s",
                    request_id, type(e).__name__, str(e),
                )
                payload = quota_service.exceeded_error_payload(e)
                yield f"data: {json.dumps({**payload, 'quota_exceeded': True})}\n\n"
            except _PROVIDER_DOWN_ERRORS as e:
                close_reason = "provider_down"
                logger.warning(
                    "[BLACKBOX] provider indisponible — request_id=%s type=%s message=%s",
                    request_id, type(e).__name__, str(e),
                )
                yield f"data: {json.dumps({'error': str(e), 'provider_down': True})}\n\n"
            except ValueError as e:
                close_reason = "value_error"
                logger.warning(
                    "[BLACKBOX] value_error — request_id=%s message=%s", request_id, str(e),
                )
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
            except Exception:
                # Auparavant, ce branchement ne laissait AUCUNE trace côté
                # serveur — le SSE envoyé au client reste inchangé (yield
                # identique à avant), seul le logger.exception() est ajouté.
                close_reason = "exception"
                logger.exception(
                    "[BLACKBOX] exception non geree dans le generateur SSE — "
                    "request_id=%s user=%s conversation_id=%s",
                    request_id, user["id"], conversation_id,
                )
                yield f"data: {json.dumps({'error': 'Le service IA est momentanément indisponible.'})}\n\n"
        except GeneratorExit:
            # Le client a fermé la connexion (onglet fermé, navigation,
            # coupure réseau) avant la fin du flux — jusqu'ici invisible car
            # GeneratorExit n'est pas une Exception, donc jamais capturée par
            # les `except` ci-dessus. Doit être relevée telle quelle (contrat
            # standard des générateurs Python), seul le log est ajouté.
            close_reason = "client_disconnected"
            raise
        finally:
            logger.info(
                "[BLACKBOX] SSE termine — request_id=%s route=/messages fermeture=%s duree_s=%.3f premier_octet_s=%s",
                request_id, close_reason, time.perf_counter() - t_start,
                f"{(first_byte_at - t_start):.3f}" if first_byte_at is not None else "None",
            )

    return Response(generate(), mimetype="text/event-stream", headers={"X-Accel-Buffering": "no"})


@app.route("/api/chatbot/conversations/<int:conversation_id>/regenerate", methods=["POST"])
@login_required
@require_non_guest
@requires_feature(Feature.CHATBOT)
@rate_limit(requests=30, per_seconds=60)
@csrf_protect
def api_chatbot_regenerate(conversation_id):
    user = request.current_user
    data = request.get_json(silent=True) or {}
    class_level = data.get("class_level") or "seconde"
    if class_level not in curriculum_registry.CURRICULUM_REGISTRY:
        return jsonify({"error": f"classe inconnue : {class_level!r}"}), 404

    # Même contrôle préalable que /messages (voir son commentaire) :
    # regenerate_last consomme aussi un message IA (nouvelle génération réelle).
    quota_error = quota_service.peek_exceeded(user, QuotaType.CHAT_MESSAGES)
    if quota_error is not None:
        return jsonify(quota_service.exceeded_error_payload(quota_error)), 429

    # BLACK BOX RECORDER : voir commentaire identique sur /messages ci-dessus.
    request_id = getattr(g, "_novamath_request_id", "-")
    t_start = time.perf_counter()

    def generate():
        first_byte_at = None
        close_reason = "normal"
        logger.info(
            "[BLACKBOX] SSE demarre — request_id=%s route=/regenerate user=%s conversation_id=%s",
            request_id, user["id"], conversation_id,
        )
        try:
            try:
                for chunk in conversation_manager.regenerate_last(
                    user, conversation_id, _CHATBOT_CHAPTERS_SUMMARY, class_level=class_level,
                    request_id=request_id,
                ):
                    if first_byte_at is None:
                        first_byte_at = time.perf_counter()
                        logger.info(
                            "[BLACKBOX] premier octet — request_id=%s delai_s=%.3f",
                            request_id, first_byte_at - t_start,
                        )
                    yield f"data: {json.dumps({'delta': chunk})}\n\n"
                cards = conversation_manager.attach_action_cards(
                    user, conversation_id, _CHATBOT_CHAPTERS_SUMMARY, class_level=class_level,
                )
                yield f"data: {json.dumps({'done': True, 'cards': cards})}\n\n"
            except QuotaExceededError as e:
                close_reason = "quota_exceeded"
                logger.info(
                    "[BLACKBOX] arret quota — request_id=%s type=%s message=%s",
                    request_id, type(e).__name__, str(e),
                )
                payload = quota_service.exceeded_error_payload(e)
                yield f"data: {json.dumps({**payload, 'quota_exceeded': True})}\n\n"
            except _PROVIDER_DOWN_ERRORS as e:
                close_reason = "provider_down"
                logger.warning(
                    "[BLACKBOX] provider indisponible — request_id=%s type=%s message=%s",
                    request_id, type(e).__name__, str(e),
                )
                yield f"data: {json.dumps({'error': str(e), 'provider_down': True})}\n\n"
            except ValueError as e:
                close_reason = "value_error"
                logger.warning(
                    "[BLACKBOX] value_error — request_id=%s message=%s", request_id, str(e),
                )
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
            except Exception:
                close_reason = "exception"
                logger.exception(
                    "[BLACKBOX] exception non geree dans le generateur SSE — "
                    "request_id=%s user=%s conversation_id=%s",
                    request_id, user["id"], conversation_id,
                )
                yield f"data: {json.dumps({'error': 'Le service IA est momentanément indisponible.'})}\n\n"
        except GeneratorExit:
            close_reason = "client_disconnected"
            raise
        finally:
            logger.info(
                "[BLACKBOX] SSE termine — request_id=%s route=/regenerate fermeture=%s duree_s=%.3f premier_octet_s=%s",
                request_id, close_reason, time.perf_counter() - t_start,
                f"{(first_byte_at - t_start):.3f}" if first_byte_at is not None else "None",
            )

    return Response(generate(), mimetype="text/event-stream", headers={"X-Accel-Buffering": "no"})


@app.route("/api/chatbot/conversations/<int:conversation_id>/retry", methods=["POST"])
@login_required
@require_non_guest
@requires_feature(Feature.CHATBOT)
@rate_limit(requests=30, per_seconds=60)
@csrf_protect
def api_chatbot_retry(conversation_id):
    """Réessaie la génération pour le dernier message utilisateur, sans le
    dupliquer — pour une tentative précédente interrompue par une erreur
    réseau/fournisseur avant qu'aucune réponse assistant n'ait été persistée
    (voir conversation_manager.retry_last). Mêmes erreurs gérées que
    /regenerate, même contrat SSE côté client."""
    user = request.current_user
    data = request.get_json(silent=True) or {}
    class_level = data.get("class_level") or "seconde"
    if class_level not in curriculum_registry.CURRICULUM_REGISTRY:
        return jsonify({"error": f"classe inconnue : {class_level!r}"}), 404

    # BLACK BOX RECORDER : voir commentaire identique sur /messages ci-dessus.
    request_id = getattr(g, "_novamath_request_id", "-")
    t_start = time.perf_counter()

    def generate():
        first_byte_at = None
        close_reason = "normal"
        logger.info(
            "[BLACKBOX] SSE demarre — request_id=%s route=/retry user=%s conversation_id=%s",
            request_id, user["id"], conversation_id,
        )
        try:
            try:
                for chunk in conversation_manager.retry_last(
                    user, conversation_id, _CHATBOT_CHAPTERS_SUMMARY, class_level=class_level,
                    request_id=request_id,
                ):
                    if first_byte_at is None:
                        first_byte_at = time.perf_counter()
                        logger.info(
                            "[BLACKBOX] premier octet — request_id=%s delai_s=%.3f",
                            request_id, first_byte_at - t_start,
                        )
                    yield f"data: {json.dumps({'delta': chunk})}\n\n"
                cards = conversation_manager.attach_action_cards(
                    user, conversation_id, _CHATBOT_CHAPTERS_SUMMARY, class_level=class_level,
                )
                yield f"data: {json.dumps({'done': True, 'cards': cards})}\n\n"
            except QuotaExceededError as e:
                # retry_last ne consomme jamais de quota (voir sa docstring) —
                # ce branchement reste défensif, jamais atteint en pratique.
                close_reason = "quota_exceeded"
                logger.info(
                    "[BLACKBOX] arret quota — request_id=%s type=%s message=%s",
                    request_id, type(e).__name__, str(e),
                )
                payload = quota_service.exceeded_error_payload(e)
                yield f"data: {json.dumps({**payload, 'quota_exceeded': True})}\n\n"
            except _PROVIDER_DOWN_ERRORS as e:
                close_reason = "provider_down"
                logger.warning(
                    "[BLACKBOX] provider indisponible — request_id=%s type=%s message=%s",
                    request_id, type(e).__name__, str(e),
                )
                yield f"data: {json.dumps({'error': str(e), 'provider_down': True})}\n\n"
            except ValueError as e:
                close_reason = "value_error"
                logger.warning(
                    "[BLACKBOX] value_error — request_id=%s message=%s", request_id, str(e),
                )
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
            except Exception:
                close_reason = "exception"
                logger.exception(
                    "[BLACKBOX] exception non geree dans le generateur SSE — "
                    "request_id=%s user=%s conversation_id=%s",
                    request_id, user["id"], conversation_id,
                )
                yield f"data: {json.dumps({'error': 'Le service IA est momentanément indisponible.'})}\n\n"
        except GeneratorExit:
            close_reason = "client_disconnected"
            raise
        finally:
            logger.info(
                "[BLACKBOX] SSE termine — request_id=%s route=/retry fermeture=%s duree_s=%.3f premier_octet_s=%s",
                request_id, close_reason, time.perf_counter() - t_start,
                f"{(first_byte_at - t_start):.3f}" if first_byte_at is not None else "None",
            )

    return Response(generate(), mimetype="text/event-stream", headers={"X-Accel-Buffering": "no"})


@app.route("/api/chatbot/messages/<int:message_id>/feedback", methods=["POST"])
@login_required
@require_non_guest
@requires_feature(Feature.CHATBOT)
@csrf_protect
def api_chatbot_feedback(message_id):
    data = request.get_json(force=True) or {}
    liked = data.get("liked")
    try:
        conversation_manager.set_feedback(request.current_user["id"], message_id, liked)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    return jsonify({"ok": True})


@app.route("/api/chatbot/quota")
@login_required
@require_non_guest
@requires_feature(Feature.CHATBOT)
def api_chatbot_quota():
    """Format historique {"used", "limit"} — conservé pour compatibilité,
    voir GET /api/quota pour le format détaillé (remaining/unlimited, tous
    les QuotaType) utilisé par le nouvel indicateur du chatbot."""
    return jsonify(conversation_manager.quota_status(request.current_user))


@app.route("/api/quota")
@login_required
def api_quota():
    """Snapshot du jour pour tous les QuotaType (voir quota_service.py) —
    aucune logique ici, pure délégation. Accessible à tout plan connecté
    (consulter son propre usage n'est jamais une fonctionnalité payante)."""
    return jsonify(quota_service.usage_snapshot_all(request.current_user))


# ── Mode test Owner (owner_test_plan_service.py) ─────────────────────────────
# Réservé exclusivement au compte configuré via NOVAMATH_OWNER_USER_ID — voir
# owner_service.owner_only (404, jamais 403, pour ne même pas révéler
# l'existence de ces routes à un autre compte, y compris un autre
# super_admin). N'écrit jamais users.plan/Stripe : simulation locale
# uniquement (voir owner_test_plan_service.py pour l'architecture complète).
@app.route("/api/owner/test-plan")
@login_required
@owner_service.owner_only
def api_owner_test_plan_get():
    return jsonify(owner_test_plan_service.status(request.current_user))


@app.route("/api/owner/test-plan", methods=["PATCH"])
@login_required
@owner_service.owner_only
@csrf_protect
def api_owner_test_plan_patch():
    """Corps JSON : {"plan": "free"|"premium"|"ultra"|null} et/ou
    {"unlimited_quotas": bool} — chaque clé est optionnelle et traitée
    indépendamment. `plan: null` désactive le plan de test (retour au
    comportement owner par défaut, plan effectif = ULTRA). Ne fait jamais
    confiance à une valeur envoyée par le frontend : revalidée par
    owner_test_plan_service (Plan.parse strict)."""
    data = request.get_json(force=True) or {}
    actor = request.current_user
    if "plan" in data:
        ok, error = owner_test_plan_service.set_test_plan(actor, data["plan"])
        if not ok:
            return jsonify({"error": error}), 400
    if "unlimited_quotas" in data:
        if not isinstance(data["unlimited_quotas"], bool):
            return jsonify({"error": "unlimited_quotas doit être un booléen."}), 400
        ok, error = owner_test_plan_service.set_unlimited_quotas(actor, data["unlimited_quotas"])
        if not ok:
            return jsonify({"error": error}), 400
    return jsonify(owner_test_plan_service.status(actor))


@app.route("/api/chatbot/context-preview")
@login_required
@require_non_guest
@requires_feature(Feature.CHATBOT)
def api_chatbot_context_preview():
    """Alimente le panneau contextuel de chatbot.html (niveau, notions faibles,
    chapitres en cours) — le même résumé compact que celui injecté dans le
    prompt système (voir chatbot/context_builder.py), pour que l'élève voie
    exactement ce que le chatbot sait de sa progression."""
    from chatbot.context_builder import build_context_summary
    class_level = request.args.get("class_level") or "seconde"
    if class_level not in curriculum_registry.CURRICULUM_REGISTRY:
        return jsonify({"error": f"classe inconnue : {class_level!r}"}), 404
    summary = build_context_summary(request.current_user, _CHATBOT_CHAPTERS_SUMMARY, class_level=class_level)
    return jsonify(summary)


@app.route("/api/chatbot/greeting")
@login_required
@require_non_guest
@requires_feature(Feature.CHATBOT)
def api_chatbot_greeting():
    """Message d'accueil personnalisé affiché comme premier message assistant
    à l'ouverture d'une conversation vide — construit à partir du même résumé
    de contexte que /api/chatbot/context-preview, jamais un texte statique."""
    from chatbot.context_builder import build_context_summary
    from chatbot.services.greeting_service import build_greeting
    class_level = request.args.get("class_level") or "seconde"
    if class_level not in curriculum_registry.CURRICULUM_REGISTRY:
        return jsonify({"error": f"classe inconnue : {class_level!r}"}), 404
    summary = build_context_summary(request.current_user, _CHATBOT_CHAPTERS_SUMMARY, class_level=class_level)
    return jsonify({"greeting": build_greeting(summary)})


@app.route("/api/chatbot/health")
@login_required
@require_non_guest
@requires_feature(Feature.CHATBOT)
def api_chatbot_health():
    """Testé au chargement de chatbot.html : si le fournisseur actif (décidé
    en interne par provider_manager.py, jamais par l'utilisateur) ne répond
    pas — clé API absente/invalide, réseau coupé... — le frontend affiche un
    bandeau générique au lieu de laisser l'utilisateur envoyer un message qui
    échouera."""
    return jsonify(provider_manager.health_check())


@app.route("/api/chatbot/mentions")
@login_required
@require_non_guest
@requires_feature(Feature.CHATBOT)
def api_chatbot_mentions():
    """Sert le menu de la palette "@" du chatbot : catégories de page réelles
    + ressources trouvées (cours/exercices, avec repli flou pour les fautes
    de frappe) — voir chatbot/services/mentions_service.py."""
    from chatbot.services.mentions_service import search_mentions
    query = request.args.get("q", "")
    limit = min(max(int(request.args.get("limit", 8)), 1), 20)
    class_level = request.args.get("class_level")
    if class_level is not None and class_level not in curriculum_registry.CURRICULUM_REGISTRY:
        return jsonify({"error": f"classe inconnue : {class_level!r}"}), 404
    return jsonify(search_mentions(query, limit=limit, class_level=class_level))


# ── Recherche unifiée + objectifs quotidiens ──────────────────────────────────
# Fondations pour la personnalisation du chatbot (accueil, cartes intelligentes,
# palette @, Command Palette) : deux routes de lecture seule, aucune donnée
# fictive, chacune déléguée à un service dédié dans chatbot/services/.
@app.route("/api/search")
@login_required
@rate_limit(requests=60, per_seconds=60)
def api_search():
    from chatbot.services import search_service
    query = request.args.get("q", "")
    scope_param = request.args.get("scope")
    scope = [s.strip() for s in scope_param.split(",") if s.strip()] if scope_param else None
    limit = min(max(int(request.args.get("limit", 10)), 1), 50)
    class_level = request.args.get("class_level")
    if class_level is not None and class_level not in curriculum_registry.CURRICULUM_REGISTRY:
        return jsonify({"error": f"classe inconnue : {class_level!r}"}), 404
    return jsonify({"results": search_service.search(query, scope=scope, limit=limit, class_level=class_level)})


@app.route("/api/goals/daily")
@login_required
@requires_feature(Feature.GOALS)
def api_goals_daily():
    from chatbot.services import goals_service
    return jsonify(goals_service.get_daily_goals_summary(request.current_user))


# ── Espace Administration (socle de sécurité uniquement — voir role_service.py) ─
# Aucune fonctionnalité métier ici : cette page se contente d'afficher le
# compte connecté (nom/email/rôle), pour valider que la chaîne de protection
# (redirection si non connecté, 403 si rôle insuffisant) fonctionne
# réellement de bout en bout avant toute construction ultérieure (gestion des
# utilisateurs, fournisseurs IA, etc. — voir le document d'architecture,
# volontairement non implémentées à ce stade).
#
# `Role.SUPPORT` : rôle minimum pour voir le SOCLE /admin (tout rôle interne
# non-USER) — les futures pages internes plus sensibles (utilisateurs,
# fournisseurs IA, équipe...) exigeront individuellement un rôle plus élevé,
# sans jamais abaisser ce minimum de base.
ADMIN_MINIMUM_ROLE = Role.SUPPORT


@login_required_page
@requires_role(ADMIN_MINIMUM_ROLE)
def serve_admin_page():
    return send_from_directory(app.static_folder, "admin.html")


# Enregistrée explicitement sur LES DEUX routes — même raison exacte que
# _serve_landing plus haut (voir sa docstring) : `admin.html` vit dans
# app.static_folder avec static_url_path="", donc Flask le servirait AUSSI
# tel quel via son handler statique automatique à l'URL /admin.html, sans
# jamais passer par login_required_page/requires_role ci-dessus, si une route
# explicite n'existait pas pour /admin.html également (endpoints distincts,
# même vue, même principe que app.add_url_rule("/", ...)/("/index.html", ...)
# pour landing_root/landing_index_html).
app.add_url_rule("/admin", endpoint="admin_root", view_func=serve_admin_page)
app.add_url_rule("/admin.html", endpoint="admin_html", view_func=serve_admin_page)


# ── Shell SaaS (sidebar/header/navigation interne) — voir admin_nav_service.py
# pour la source unique de vérité des modules/rôles. Chaque module du menu
# (hors Dashboard, déjà enregistré ci-dessus) reçoit sa propre route Flask —
# TOUJOURS le même gabarit admin.html, JAMAIS un fichier statique par module
# (aucun risque de contournement du handler statique automatique, voir la
# docstring au-dessus de app.add_url_rule("/admin.html", ...) : il n'existe
# aucun fichier "users.html"/"ia.html"/... dans static/ qui pourrait entrer en
# collision). Protégée par le rôle minimum déclaré dans admin_nav_service.py —
# un seul endroit à modifier pour changer l'accès requis par un module,
# jamais une décision dupliquée entre le menu et sa route.
def _make_admin_module_view(module):
    @login_required_page
    @requires_role(module.minimum_role)
    def view():
        return send_from_directory(app.static_folder, "admin.html")
    return view


for _module in admin_nav_service.MODULES:
    if _module.path in ("/admin", "/admin.html"):
        continue
    app.add_url_rule(_module.path, endpoint=f"admin_module_{_module.id}", view_func=_make_admin_module_view(_module))


@app.route("/api/admin/me")
@login_required
@requires_role(ADMIN_MINIMUM_ROLE)
def api_admin_me():
    """Identité minimale du compte connecté pour le shell /admin (nom, email,
    avatar, rôle) — jamais de donnée supplémentaire (pas d'id interne, pas de
    champ de progression élève) : cette route n'a aucune vocation métier, elle
    ne fait que confirmer que la protection par rôle laisse passer un accès
    légitime."""
    user = request.current_user
    return jsonify({
        "name": user["pseudo"],
        "email": user["email"],
        "avatar": user["avatar"],
        "role": get_role(user).value,
    })


@app.route("/api/admin/nav")
@login_required
@requires_role(ADMIN_MINIMUM_ROLE)
def api_admin_nav():
    """Menu latéral réellement autorisé pour l'utilisateur connecté — filtré
    côté serveur (voir admin_nav_service.modules_for_user), jamais par le
    frontend : ce dernier ne reçoit ici que les entrées qu'il a le droit
    d'afficher, aucune règle de rôle ne vit dans le JS."""
    modules = admin_nav_service.modules_for_user(request.current_user)
    return jsonify({"modules": [admin_nav_service.serialize_module(m) for m in modules]})


@app.route("/api/admin/dashboard")
@login_required
@requires_role(ADMIN_MINIMUM_ROLE)
def api_admin_dashboard():
    """Snapshot du Dashboard Administrateur — cartes/graphiques/activité
    récente (voir admin_dashboard_service.py). Lecture seule stricte : aucune
    écriture, aucune action destructive, protégée exactement comme
    /api/admin/me (même rôle minimum, aucune nouvelle règle de permission)."""
    return jsonify(admin_dashboard_service.get_dashboard_snapshot())


# Route de détail (/admin/users/:id) — pas une entrée du menu latéral (elle
# n'apparaît pas dans admin_nav_service.MODULES), donc pas couverte par la
# boucle d'enregistrement ci-dessus : c'est une sous-page du module
# "Utilisateurs", protégée par EXACTEMENT le même rôle minimum que
# /admin/users (voir admin_nav_service.module_by_path), jamais un rôle
# recodé ici. Sert le même admin.html — le routeur JS (admin-shell.js)
# reconnaît ce chemin et affiche "Profil utilisateur bientôt disponible."
_USERS_MODULE_ROLE = admin_nav_service.module_by_path("/admin/users").minimum_role


@app.route("/admin/users/<int:user_id>")
@login_required_page
@requires_role(_USERS_MODULE_ROLE)
def serve_admin_user_profile(user_id):
    return send_from_directory(app.static_folder, "admin.html")


@app.route("/api/admin/users")
@login_required
@requires_role(ADMIN_MINIMUM_ROLE)
def api_admin_users():
    """CRM utilisateur en lecture seule (voir admin_users_service.py) —
    recherche/filtres/tri/pagination appliqués en SQL, jamais en mémoire.
    Aucune écriture : ni ce module ni admin_users_service.py n'exposent de
    verbe de modification (pas de suppression/suspension/changement de plan
    ou de rôle)."""
    args = request.args
    return jsonify(admin_users_service.list_users(
        search=args.get("search"),
        role=args.get("role"),
        plan=args.get("plan"),
        account_status=args.get("account_status"),
        payment_status=args.get("payment_status"),
        sort_by=args.get("sort_by", "created_at"),
        sort_dir=args.get("sort_dir", "desc"),
        page=args.get("page", 1),
        page_size=args.get("page_size", admin_users_service.PAGE_SIZE_DEFAULT),
    ))


# Fiche utilisateur complète (/admin/users/:id) — une API INDÉPENDANTE par
# onglet (jamais un agrégat géant), pour que le frontend ne charge que
# l'onglet réellement ouvert (lazy loading, voir static/js/admin-user-profile.js).
# Toutes protégées par le même rôle minimum que la page /admin/users/:id
# (voir _USERS_MODULE_ROLE ci-dessus) — aucune nouvelle règle de permission.
# Un user_id inconnu renvoie 404 (comportement REST standard, distinct de la
# règle "jamais 404" qui ne concerne que les modules du menu latéral).
_ADMIN_USER_PROFILE_TABS = {
    "profile": admin_user_profile_service.get_profile,
    "activity": admin_user_profile_service.get_activity,
    "courses": admin_user_profile_service.get_courses,
    "exercises": admin_user_profile_service.get_exercises,
    "chatbot": admin_user_profile_service.get_chatbot,
    "learning": admin_user_profile_service.get_learning,
    "subscription": admin_user_profile_service.get_subscription,
    "support": admin_user_profile_service.get_support,
}


def _make_admin_user_profile_view(loader):
    @login_required
    @requires_role(_USERS_MODULE_ROLE)
    def view(user_id):
        data = loader(user_id)
        if data is None:
            return jsonify({"error": "utilisateur introuvable"}), 404
        return jsonify(data)
    return view


for _tab_name, _loader in _ADMIN_USER_PROFILE_TABS.items():
    app.add_url_rule(
        f"/api/admin/users/<int:user_id>/{_tab_name}",
        endpoint=f"api_admin_user_profile_{_tab_name}",
        view_func=_make_admin_user_profile_view(_loader),
    )


# ── Gestion des fournisseurs IA (/admin/ia) — lecture ET écriture ───────────
# Panneau d'administration complet des tables ai_providers/
# subscription_ai_mapping/ai_provider_health (voir admin_ai_service.py, qui
# valide et écrit exclusivement via ai_provider_service.py — jamais un accès
# direct à db.py ici). N'importe et ne modifie JAMAIS conversation_manager.py
# ni llm_fallback_service.py : les tables restent la SEULE interface entre
# cette administration et le chatbot réel (lu par
# provider_manager.select_llm_for_user(), voir la phase de migration
# précédente) — aucune route ci-dessous n'appelle jamais directement le
# pipeline de génération. Même rôle minimum que le module "ai" dans
# admin_nav_service.py (ADMIN), jamais recodé ici.
_AI_MODULE_ROLE = admin_nav_service.module_by_path("/admin/ia").minimum_role


def _admin_actor():
    """Identité résolue de l'administrateur courant, pour le Journal
    d'activité IA (voir admin_ai_log_service.py) — mêmes valeurs que
    /api/admin/me (get_role) et la même adresse IP que le reste du projet
    (request.headers.get("X-Forwarded-For", request.remote_addr), voir
    privacy_service.py/consent_service.py). Un seul endroit pour résoudre cet
    "acteur", jamais reconstruit différemment d'une route à l'autre."""
    user = request.current_user
    return {
        "id": user["id"], "name": user["pseudo"], "role": get_role(user).value,
        "ip": request.headers.get("X-Forwarded-For", request.remote_addr),
    }


@app.route("/admin/ia/<int:provider_id>")
@login_required_page
@requires_role(_AI_MODULE_ROLE)
def serve_admin_ai_provider_detail(provider_id):
    return send_from_directory(app.static_folder, "admin.html")


@app.route("/api/admin/ai/providers")
@login_required
@requires_role(_AI_MODULE_ROLE)
def api_admin_ai_providers():
    """Carte "Fournisseurs IA" — tous les fournisseurs de ai_providers."""
    return jsonify(admin_ai_service.list_providers())


@app.route("/api/admin/ai/subscriptions")
@login_required
@requires_role(_AI_MODULE_ROLE)
def api_admin_ai_subscriptions():
    """Carte "Abonnements" — mapping FREE/PREMIUM/ULTRA → fournisseur(s),
    lecture seule (subscription_ai_mapping)."""
    return jsonify(admin_ai_service.list_subscriptions())


@app.route("/api/admin/ai/health")
@login_required
@requires_role(_AI_MODULE_ROLE)
def api_admin_ai_health():
    """Carte "État des fournisseurs" — ai_provider_health."""
    return jsonify(admin_ai_service.list_health())


@app.route("/api/admin/ai/usage")
@login_required
@requires_role(_AI_MODULE_ROLE)
def api_admin_ai_usage():
    """Carte "Consommation IA" — ai_provider_usage, agrégée par fournisseur +
    graphique journalier global."""
    return jsonify(admin_ai_service.list_usage())


# ── Écriture : fournisseurs (créer/modifier/activer/désactiver/supprimer/
# réordonner) — chaque route traduit le (ok/id, errors) d'admin_ai_service.py
# en réponse HTTP, jamais de logique de validation ici (voir sa docstring).
@app.route("/api/admin/ai/providers", methods=["POST"])
@login_required
@requires_role(_AI_MODULE_ROLE)
@csrf_protect
def api_admin_ai_provider_create():
    data = request.get_json(force=True) or {}
    provider_id, errors = admin_ai_service.create_provider_logged(_admin_actor(), data)
    if errors:
        return jsonify({"error": "Configuration invalide.", "fields": errors}), 400
    return jsonify({"id": provider_id}), 201


@app.route("/api/admin/ai/providers/<int:provider_id>", methods=["PUT"])
@login_required
@requires_role(_AI_MODULE_ROLE)
@csrf_protect
def api_admin_ai_provider_update(provider_id):
    data = request.get_json(force=True) or {}
    ok, errors = admin_ai_service.update_provider_logged(_admin_actor(), provider_id, data)
    if not ok:
        status = 404 if errors.get("_") == "Fournisseur introuvable." else 400
        return jsonify({"error": errors.get("_", "Configuration invalide."), "fields": errors}), status
    return jsonify({"ok": True})


@app.route("/api/admin/ai/providers/<int:provider_id>", methods=["DELETE"])
@login_required
@requires_role(_AI_MODULE_ROLE)
@csrf_protect
def api_admin_ai_provider_delete(provider_id):
    ok, errors = admin_ai_service.delete_provider_logged(_admin_actor(), provider_id)
    if not ok:
        status = 404 if errors.get("_") == "Fournisseur introuvable." else 409
        return jsonify({"error": errors.get("_", "Suppression impossible.")}), status
    return jsonify({"ok": True})


@app.route("/api/admin/ai/providers/<int:provider_id>/enabled", methods=["PATCH"])
@login_required
@requires_role(_AI_MODULE_ROLE)
@csrf_protect
def api_admin_ai_provider_set_enabled(provider_id):
    data = request.get_json(force=True) or {}
    ok, errors = admin_ai_service.set_provider_enabled_logged(_admin_actor(), provider_id, bool(data.get("enabled")))
    if not ok:
        return jsonify({"error": errors.get("_", "Action impossible.")}), 404
    return jsonify({"ok": True})


@app.route("/api/admin/ai/providers/<int:provider_id>/move-up", methods=["POST"])
@login_required
@requires_role(_AI_MODULE_ROLE)
@csrf_protect
def api_admin_ai_provider_move_up(provider_id):
    ok, errors = admin_ai_service.move_provider_priority_logged(_admin_actor(), provider_id, "up")
    if not ok:
        status = 404 if errors.get("_") == "Fournisseur introuvable." else 409
        return jsonify({"error": errors.get("_", "Action impossible.")}), status
    return jsonify({"ok": True})


@app.route("/api/admin/ai/providers/<int:provider_id>/move-down", methods=["POST"])
@login_required
@requires_role(_AI_MODULE_ROLE)
@csrf_protect
def api_admin_ai_provider_move_down(provider_id):
    ok, errors = admin_ai_service.move_provider_priority_logged(_admin_actor(), provider_id, "down")
    if not ok:
        status = 404 if errors.get("_") == "Fournisseur introuvable." else 409
        return jsonify({"error": errors.get("_", "Action impossible.")}), status
    return jsonify({"ok": True})


# Health-check réel, écrit ai_provider_health (voir admin_ai_service.run_health_check)
# — ne touche jamais aux conversations. Même protection anti-abus que /test.
@app.route("/api/admin/ai/providers/<int:provider_id>/health-check", methods=["POST"])
@login_required
@requires_role(_AI_MODULE_ROLE)
@rate_limit(requests=10, per_seconds=60)
@csrf_protect
def api_admin_ai_provider_health_check(provider_id):
    result = admin_ai_service.run_health_check_logged(_admin_actor(), provider_id)
    if result is None:
        return jsonify({"error": "fournisseur introuvable"}), 404
    return jsonify(result)


# "Tester la connexion" : VRAI prompt (tokens réels via provider.last_usage)
# + écriture ai_provider_health en une seule action (voir
# admin_ai_service.test_connection) — même protection anti-abus que
# /test et /health-check ci-dessus (appel réseau réel vers un fournisseur externe).
@app.route("/api/admin/ai/providers/<int:provider_id>/test-connection", methods=["POST"])
@login_required
@requires_role(_AI_MODULE_ROLE)
@rate_limit(requests=10, per_seconds=60)
@csrf_protect
def api_admin_ai_provider_test_connection(provider_id):
    result = admin_ai_service.test_connection_logged(_admin_actor(), provider_id)
    if result is None:
        return jsonify({"error": "fournisseur introuvable"}), 404
    return jsonify(result)


# ── Haute disponibilité IA : clés API multiples par fournisseur, rotation
# automatique en cas d'échec (voir ai_provider_key_service.py). Une clé n'est
# JAMAIS renvoyée en clair par ces routes (voir admin_ai_service._serialize_api_key) —
# seuls label/statistiques/état sont exposés au frontend.
@app.route("/api/admin/ai/keys", methods=["GET"])
@login_required
@requires_role(_AI_MODULE_ROLE)
def api_admin_ai_keys_list():
    provider_key = request.args.get("provider_key")
    return jsonify(admin_ai_service.list_api_keys(provider_key))


@app.route("/api/admin/ai/keys", methods=["POST"])
@login_required
@requires_role(_AI_MODULE_ROLE)
@csrf_protect
def api_admin_ai_keys_create():
    data = request.get_json(force=True) or {}
    key_id, errors = admin_ai_service.create_api_key_logged(_admin_actor(), data)
    if errors:
        return jsonify({"error": errors.get("_", "Configuration invalide."), "fields": errors}), 400
    return jsonify({"id": key_id}), 201


@app.route("/api/admin/ai/keys/<int:key_id>", methods=["PATCH"])
@login_required
@requires_role(_AI_MODULE_ROLE)
@csrf_protect
def api_admin_ai_keys_update(key_id):
    data = request.get_json(force=True) or {}
    ok, errors = admin_ai_service.update_api_key_logged(_admin_actor(), key_id, data)
    if not ok:
        status = 404 if errors.get("_") == "Clé introuvable." else 400
        return jsonify({"error": errors.get("_", "Configuration invalide."), "fields": errors}), status
    return jsonify({"ok": True})


@app.route("/api/admin/ai/keys/<int:key_id>", methods=["DELETE"])
@login_required
@requires_role(_AI_MODULE_ROLE)
@csrf_protect
def api_admin_ai_keys_delete(key_id):
    ok, errors = admin_ai_service.delete_api_key_logged(_admin_actor(), key_id)
    if not ok:
        return jsonify({"error": errors.get("_", "Clé introuvable.")}), 404
    return jsonify({"ok": True})


@app.route("/api/admin/ai/keys/<int:key_id>/test", methods=["POST"])
@login_required
@requires_role(_AI_MODULE_ROLE)
@rate_limit(requests=10, per_seconds=60)
@csrf_protect
def api_admin_ai_keys_test(key_id):
    result = admin_ai_service.test_api_key_logged(_admin_actor(), key_id)
    if result is None:
        return jsonify({"error": "clé introuvable"}), 404
    return jsonify(result)


# ── Écriture : abonnements (quels fournisseurs sont utilisés par ce plan) ──
@app.route("/api/admin/ai/subscriptions/<subscription>", methods=["PUT"])
@login_required
@requires_role(_AI_MODULE_ROLE)
@csrf_protect
def api_admin_ai_subscription_update(subscription):
    data = request.get_json(force=True) or {}
    ok, errors = admin_ai_service.set_subscription_providers_logged(_admin_actor(), subscription, data.get("provider_ids"))
    if not ok:
        return jsonify({"error": errors.get("_", "Configuration invalide.")}), 400
    return jsonify({"ok": True})


# Fiche détaillée d'un fournisseur (/admin/ia/:id) — une API INDÉPENDANTE par
# onglet (jamais un agrégat géant), même contrat que
# _ADMIN_USER_PROFILE_TABS ci-dessus (lazy loading, cache par onglet côté
# frontend). Un provider_id inconnu renvoie 404.
_ADMIN_AI_PROVIDER_TABS = {
    "info": admin_ai_service.get_provider_info,
    "health": admin_ai_service.get_provider_health,
    "usage": admin_ai_service.get_provider_usage,
    "config": admin_ai_service.get_provider_config,
}


def _make_admin_ai_provider_view(loader):
    @login_required
    @requires_role(_AI_MODULE_ROLE)
    def view(provider_id):
        data = loader(provider_id)
        if data is None:
            return jsonify({"error": "fournisseur introuvable"}), 404
        return jsonify(data)
    return view


for _tab_name, _loader in _ADMIN_AI_PROVIDER_TABS.items():
    app.add_url_rule(
        f"/api/admin/ai/providers/<int:provider_id>/{_tab_name}",
        endpoint=f"api_admin_ai_provider_{_tab_name}",
        view_func=_make_admin_ai_provider_view(_loader),
    )


# ── Journal d'activité IA (/admin/journal) — lecture seule stricte ─────────
# Historique de toutes les actions effectuées depuis le panneau
# d'administration IA (voir admin_ai_log_service.py) — aucune route
# d'écriture ici : chaque entrée est déjà créée par les fonctions
# "*_logged" de admin_ai_service.py, jamais directement depuis une route.
# Totalement indépendant du chatbot (voir docstring de
# admin_ai_log_service.py). Même rôle minimum que le module "journal" dans
# admin_nav_service.py (ADMIN), jamais recodé ici.
_JOURNAL_MODULE_ROLE = admin_nav_service.module_by_path("/admin/journal").minimum_role


def _journal_filters_from_request():
    args = request.args
    return dict(
        search=args.get("search"),
        admin_user_id=args.get("admin_user_id"),
        provider_id=args.get("provider_id"),
        action=args.get("action"),
        result=args.get("result"),
        date_from=args.get("date_from"),
        date_to=args.get("date_to"),
    )


@app.route("/api/admin/journal")
@login_required
@requires_role(_JOURNAL_MODULE_ROLE)
def api_admin_journal():
    filters = _journal_filters_from_request()
    return jsonify(admin_ai_log_service.list_log(
        **filters,
        page=request.args.get("page", 1),
        page_size=request.args.get("page_size", admin_ai_log_service.PAGE_SIZE_DEFAULT),
    ))


@app.route("/api/admin/journal/filters")
@login_required
@requires_role(_JOURNAL_MODULE_ROLE)
def api_admin_journal_filters():
    """Options réellement présentes dans le journal (administrateurs/
    fournisseurs/actions), pour peupler les filtres du frontend."""
    return jsonify(admin_ai_log_service.list_filters())


@app.route("/api/admin/journal/export.csv")
@login_required
@requires_role(_JOURNAL_MODULE_ROLE)
def api_admin_journal_export_csv():
    filters = _journal_filters_from_request()
    csv_text = admin_ai_log_service.export_csv(**filters)
    return Response(
        csv_text, mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=journal-ia.csv"},
    )


@app.route("/api/admin/journal/export.json")
@login_required
@requires_role(_JOURNAL_MODULE_ROLE)
def api_admin_journal_export_json():
    filters = _journal_filters_from_request()
    return jsonify(admin_ai_log_service.export_json(**filters))


# ── Support (/admin/support) — gestion des tickets, lecture ET écriture ────
# Panneau d'administration complet de support_service.py : liste (recherche/
# filtres/tri/pagination), fiche ticket (conversation/pièces jointes/notes
# internes/historique/statut/assignation), statistiques. Même rôle minimum
# que le module "support" dans admin_nav_service.py (SUPPORT, le rôle interne
# le plus bas — accessible dès qu'un compte a un rôle d'équipe).
_SUPPORT_MODULE_ROLE = admin_nav_service.module_by_path("/admin/support").minimum_role


# Route de détail (/admin/support/:id) — pas une entrée du menu latéral,
# même principe que /admin/users/:id (voir _USERS_MODULE_ROLE plus haut) :
# sert le même admin.html, le routeur JS (admin-shell.js) reconnaît ce
# chemin et affiche la fiche ticket.
@app.route("/admin/support/<int:ticket_id>")
@login_required_page
@requires_role(_SUPPORT_MODULE_ROLE)
def serve_admin_support_ticket(ticket_id):
    return send_from_directory(app.static_folder, "admin.html")


@app.route("/api/admin/support/tickets")
@login_required
@requires_role(_SUPPORT_MODULE_ROLE)
def api_admin_support_tickets():
    args = request.args
    return jsonify(support_service.list_tickets(
        search=args.get("search"), status=args.get("status"), category=args.get("category"),
        priority=args.get("priority"), assigned_admin_id=args.get("assigned_admin_id"),
        sort_by=args.get("sort_by", "created_at"), sort_dir=args.get("sort_dir", "desc"),
        page=args.get("page", 1), page_size=args.get("page_size", support_service.PAGE_SIZE_DEFAULT),
    ))


@app.route("/api/admin/support/tickets/<int:ticket_id>")
@login_required
@requires_role(_SUPPORT_MODULE_ROLE)
def api_admin_support_ticket_detail(ticket_id):
    detail = support_service.get_ticket_detail(ticket_id)
    if detail is None:
        return jsonify({"error": "ticket introuvable"}), 404
    return jsonify(detail)


@app.route("/api/admin/support/tickets/<int:ticket_id>/messages", methods=["POST"])
@login_required
@requires_role(_SUPPORT_MODULE_ROLE)
@csrf_protect
def api_admin_support_ticket_add_message(ticket_id):
    """multipart/form-data (champ "body" + fichiers "attachments", 0 à N) ou
    JSON simple {"body": "..."} sans pièce jointe — les deux formats sont
    acceptés, comme /api/chatbot/attachments/pdf pour le multipart."""
    body = request.form.get("body") if request.form else (request.get_json(silent=True) or {}).get("body")
    message_id, error = support_service.add_message(ticket_id, "admin", request.current_user["id"], body)
    if error:
        status = 404 if error == "Ticket introuvable." else 400
        return jsonify({"error": error}), status
    for file in request.files.getlist("attachments"):
        if not file or not file.filename:
            continue
        try:
            support_attachment_service.save_attachment(message_id, ticket_id, file)
        except support_attachment_service.AttachmentRejected as exc:
            return jsonify({"error": str(exc)}), 400
    return jsonify({"id": message_id}), 201


@app.route("/api/admin/support/tickets/<int:ticket_id>/notes", methods=["POST"])
@login_required
@requires_role(_SUPPORT_MODULE_ROLE)
@csrf_protect
def api_admin_support_ticket_add_note(ticket_id):
    data = request.get_json(force=True) or {}
    note_id, error = support_service.add_note(ticket_id, request.current_user["id"], data.get("body"))
    if error:
        status = 404 if error == "Ticket introuvable." else 400
        return jsonify({"error": error}), status
    return jsonify({"id": note_id}), 201


@app.route("/api/admin/support/tickets/<int:ticket_id>/status", methods=["PATCH"])
@login_required
@requires_role(_SUPPORT_MODULE_ROLE)
@csrf_protect
def api_admin_support_ticket_status(ticket_id):
    data = request.get_json(force=True) or {}
    ok, error = support_service.change_status(ticket_id, data.get("status"), request.current_user["id"])
    if not ok:
        status = 404 if error == "Ticket introuvable." else 400
        return jsonify({"error": error}), status
    return jsonify({"ok": True})


@app.route("/api/admin/support/tickets/<int:ticket_id>/assign", methods=["PATCH"])
@login_required
@requires_role(_SUPPORT_MODULE_ROLE)
@csrf_protect
def api_admin_support_ticket_assign(ticket_id):
    data = request.get_json(force=True) or {}
    admin_id = data.get("admin_id")
    admin_id = int(admin_id) if admin_id else None
    ok, error = support_service.assign_admin(ticket_id, admin_id, request.current_user["id"])
    if not ok:
        return jsonify({"error": error}), 404
    return jsonify({"ok": True})


@app.route("/api/admin/support/attachments/<int:attachment_id>")
@login_required
@requires_role(_SUPPORT_MODULE_ROLE)
def api_admin_support_attachment_download(attachment_id):
    resolved = support_attachment_service.resolve_attachment_path(attachment_id)
    if resolved is None:
        return jsonify({"error": "pièce jointe introuvable"}), 404
    absolute_path, original_filename, content_type = resolved
    return send_file(absolute_path, mimetype=content_type, as_attachment=True, download_name=original_filename)


# ── Support côté utilisateur (créer/consulter ses propres tickets) — hors
# module Administration, accessible à tout compte connecté (login_required
# seul, aucun rôle d'équipe requis) : c'est la SEULE façon de créer un ticket,
# jamais depuis l'administration elle-même (voir support_service.py). ───────
@app.route("/api/support/tickets", methods=["GET", "POST"])
@login_required
@csrf_protect
def api_support_tickets():
    if request.method == "GET":
        return jsonify(support_service.list_tickets_for_user(request.current_user["id"]))
    data = request.get_json(force=True) or {}
    ticket_id, error = support_service.create_ticket(
        request.current_user["id"], data.get("subject"), data.get("category"), data.get("body"),
        priority=data.get("priority", "normale"),
    )
    if error:
        return jsonify({"error": error}), 400
    return jsonify({"id": ticket_id}), 201


def _user_owns_ticket_or_404(ticket_id):
    detail = support_service.get_ticket_detail(ticket_id)
    if detail is None or detail["user_id"] != request.current_user["id"]:
        return None
    return detail


@app.route("/api/support/tickets/<int:ticket_id>")
@login_required
def api_support_ticket_detail(ticket_id):
    detail = _user_owns_ticket_or_404(ticket_id)
    if detail is None:
        return jsonify({"error": "ticket introuvable"}), 404
    # Les notes internes ne sont jamais visibles par l'utilisateur — retirées
    # ici, jamais filtrées côté frontend (une donnée sensible ne doit jamais
    # transiter jusqu'au navigateur de l'élève).
    detail = {k: v for k, v in detail.items() if k != "notes"}
    return jsonify(detail)


@app.route("/api/support/tickets/<int:ticket_id>/messages", methods=["POST"])
@login_required
@csrf_protect
def api_support_ticket_add_message(ticket_id):
    if _user_owns_ticket_or_404(ticket_id) is None:
        return jsonify({"error": "ticket introuvable"}), 404
    body = request.form.get("body") if request.form else (request.get_json(silent=True) or {}).get("body")
    message_id, error = support_service.add_message(ticket_id, "user", request.current_user["id"], body)
    if error:
        return jsonify({"error": error}), 400
    for file in request.files.getlist("attachments"):
        if not file or not file.filename:
            continue
        try:
            support_attachment_service.save_attachment(message_id, ticket_id, file)
        except support_attachment_service.AttachmentRejected as exc:
            return jsonify({"error": str(exc)}), 400
    return jsonify({"id": message_id}), 201


@app.route("/api/support/tickets/<int:ticket_id>/satisfaction", methods=["POST"])
@login_required
@csrf_protect
def api_support_ticket_satisfaction(ticket_id):
    data = request.get_json(force=True) or {}
    ok, error = support_service.set_satisfaction_rating(ticket_id, request.current_user["id"], data.get("rating"))
    if not ok:
        return jsonify({"error": error}), 400
    return jsonify({"ok": True})


@app.route("/api/support/attachments/<int:attachment_id>")
@login_required
def api_support_attachment_download(attachment_id):
    row = db.get_support_ticket_attachment(attachment_id)
    if row is None:
        return jsonify({"error": "pièce jointe introuvable"}), 404
    message = db.get_support_ticket_message(row["message_id"])
    ticket = db.get_support_ticket(message["ticket_id"]) if message else None
    if ticket is None or ticket["user_id"] != request.current_user["id"]:
        return jsonify({"error": "pièce jointe introuvable"}), 404
    resolved = support_attachment_service.resolve_attachment_path(attachment_id)
    if resolved is None:
        return jsonify({"error": "pièce jointe introuvable"}), 404
    absolute_path, original_filename, content_type = resolved
    return send_file(absolute_path, mimetype=content_type, as_attachment=True, download_name=original_filename)


# ── Santé du système (/admin/health) — centre de supervision, lecture seule ─
# Aucune écriture ici : le seul bouton d'action ("Tester la connexion") réutilise
# TEL QUEL /api/admin/ai/providers/<id>/health-check (voir plus haut), jamais
# dupliqué. Même rôle minimum que le module "ai"/"subscriptions"/"journal"
# (ADMIN, données techniques sensibles).
_HEALTH_MODULE_ROLE = admin_nav_service.module_by_path("/admin/health").minimum_role


@app.route("/api/admin/system-health/overview")
@login_required
@requires_role(_HEALTH_MODULE_ROLE)
def api_admin_system_health_overview():
    return jsonify(system_health_service.full_snapshot())


@app.route("/api/admin/system-health/incidents")
@login_required
@requires_role(_HEALTH_MODULE_ROLE)
def api_admin_system_health_incidents():
    window = request.args.get("window", "7j")
    if window not in system_health_service.WINDOWS:
        window = "7j"
    return jsonify({"window": window, "items": system_health_service.list_incidents(window)})




# ── Paramètres (/admin/settings) — centre de configuration ─────────────────
# Ne modifie JAMAIS le routage IA (provider_manager.py), Stripe, les quotas ni
# le système d'abonnements — voir settings_service.py pour le détail exact de
# ce qui est réellement persisté/appliqué vs affiché en lecture seule. Clés
# API IA : réutilise TEL QUEL /api/admin/ai/keys/* (voir plus haut), jamais
# dupliqué ici. Même rôle minimum que déclaré dans admin_nav_service.py
# (SUPER_ADMIN — impact le plus large de tout le panneau).
_SETTINGS_MODULE_ROLE = admin_nav_service.module_by_path("/admin/settings").minimum_role


@app.route("/api/admin/settings/overview")
@login_required
@requires_role(_SETTINGS_MODULE_ROLE)
def api_admin_settings_overview():
    return jsonify(settings_service.full_snapshot())


# Réglages IA réellement lus par le pipeline chatbot à chaque appel LLM (voir
# chatbot/services/llm_fallback_service.py::_ai_default_temperature/
# _ai_default_max_tokens/_ai_fallback_enabled) — ne modifie jamais
# provider_manager.py (choix du fournisseur/modèle reste inchangé).
@app.route("/api/admin/settings/ai", methods=["PATCH"])
@login_required
@requires_role(_SETTINGS_MODULE_ROLE)
@csrf_protect
def api_admin_settings_ai():
    data = request.get_json(force=True) or {}
    ok, errors = settings_service.update_ai_settings(_admin_actor(), data)
    if not ok:
        return jsonify({"error": "Valeur(s) invalide(s).", "fields": errors}), 400
    return jsonify(settings_service.ai_settings())


# Envoie un VRAI email de test — appel réseau réel vers le serveur SMTP
# configuré, protégé contre les abus (voir /api/admin/ai/providers/*/test
# pour la même politique de rate-limit sur un appel réseau externe réel).
@app.route("/api/admin/settings/smtp/test", methods=["POST"])
@login_required
@requires_role(_SETTINGS_MODULE_ROLE)
@rate_limit(requests=5, per_seconds=60)
@csrf_protect
def api_admin_settings_smtp_test():
    data = request.get_json(force=True) or {}
    to_address = (data.get("to_address") or request.current_user["email"] or "").strip()
    if not to_address:
        return jsonify({"error": "Adresse email de destination manquante."}), 400
    sent, error = settings_service.test_smtp(_admin_actor(), to_address)
    return jsonify({"sent": sent, "error": error})


@app.route("/api/admin/settings/backups", methods=["POST"])
@login_required
@requires_role(_SETTINGS_MODULE_ROLE)
@csrf_protect
def api_admin_settings_backup_create():
    filename, error = settings_service.create_backup(_admin_actor())
    if error:
        return jsonify({"error": error}), 500
    return jsonify({"filename": filename}), 201


@app.route("/api/admin/settings/backups/<path:filename>/download")
@login_required
@requires_role(_SETTINGS_MODULE_ROLE)
def api_admin_settings_backup_download(filename):
    match = next((b for b in backup_service.list_backups() if b["filename"] == filename), None)
    if match is None:
        return jsonify({"error": "sauvegarde introuvable"}), 404
    return send_file(match["path"], as_attachment=True, download_name=filename)


@app.route("/api/admin/settings/backups/<path:filename>/restore", methods=["POST"])
@login_required
@requires_role(_SETTINGS_MODULE_ROLE)
@csrf_protect
def api_admin_settings_backup_restore(filename):
    ok, error = settings_service.restore_backup(_admin_actor(), filename)
    if not ok:
        return jsonify({"error": error}), 404
    return jsonify({"ok": True})


@app.route("/api/admin/settings/backups/<path:filename>", methods=["DELETE"])
@login_required
@requires_role(_SETTINGS_MODULE_ROLE)
@csrf_protect
def api_admin_settings_backup_delete(filename):
    ok, error, not_found = settings_service.delete_backup(_admin_actor(), filename)
    if not ok:
        return jsonify({"error": error}), 404 if not_found else 500
    return jsonify({"ok": True})


# ── Analytics (/admin/analytics) — FONDATIONS uniquement, lecture seule ─────
# Graphiques/exports/tableaux avancés/classements : chantier ultérieur,
# volontairement absents ici. Ne modifie JAMAIS le chatbot/Stripe/les
# abonnements/les quotas/le routage IA — uniquement des agrégats de lecture,
# voir admin_analytics_service.py. Même rôle minimum que déclaré dans
# admin_nav_service.py (SUPPORT).
_ANALYTICS_MODULE_ROLE = admin_nav_service.module_by_path("/admin/analytics").minimum_role


@app.route("/api/admin/analytics/filters")
@login_required
@requires_role(_ANALYTICS_MODULE_ROLE)
def api_admin_analytics_filters():
    return jsonify(admin_analytics_service.list_filters())


@app.route("/api/admin/analytics/overview")
@login_required
@requires_role(_ANALYTICS_MODULE_ROLE)
def api_admin_analytics_overview():
    window = request.args.get("window", "30j")
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    # `groups` (optionnel) : voir la docstring de admin_analytics_service.overview()
    # — absent => tout calculer (comportement historique), présent (même vide)
    # => restreindre aux groupes réellement demandés par le frontend.
    groups_param = request.args.get("groups")
    groups = [g for g in groups_param.split(",") if g] if groups_param is not None else None
    payload, error = admin_analytics_service.overview(window, date_from, date_to, groups=groups)
    if error:
        return jsonify({"error": error}), 400
    return jsonify(payload)


@app.route("/api/admin/analytics/charts")
@login_required
@requires_role(_ANALYTICS_MODULE_ROLE)
def api_admin_analytics_charts():
    window = request.args.get("window", "30j")
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    payload, error = admin_analytics_service.charts(window, date_from, date_to)
    if error:
        return jsonify({"error": error}), 400
    return jsonify(payload)


@app.route("/api/admin/analytics/rankings")
@login_required
@requires_role(_ANALYTICS_MODULE_ROLE)
def api_admin_analytics_rankings():
    window = request.args.get("window", "30j")
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    limit = request.args.get("limit", "10")
    limit = min(max(int(limit), 1), 50) if limit.isdigit() else 10
    payload, error = admin_analytics_service.rankings(window, date_from, date_to, limit)
    if error:
        return jsonify({"error": error}), 400
    return jsonify(payload)


@app.route("/api/admin/analytics/search")
@login_required
@requires_role(_ANALYTICS_MODULE_ROLE)
def api_admin_analytics_search():
    query = request.args.get("q", "")
    return jsonify(admin_analytics_service.global_search(query))


# ── Analytics : exports ponctuels (CSV/Excel/PDF) — jamais écrits sur disque,
# streamés directement, toujours journalisés (Partie 12) via export_logged().
_ANALYTICS_EXPORT_MIME = {
    "csv": "text/csv",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
}


def _analytics_export_route(export_format):
    window = request.args.get("window", "30j")
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    content, filename, error = admin_analytics_export_service.export_logged(
        _admin_actor(), export_format, window, date_from, date_to,
    )
    if error:
        return jsonify({"error": error}), 400
    return Response(content, mimetype=_ANALYTICS_EXPORT_MIME[export_format], headers={
        "Content-Disposition": f'attachment; filename="{filename}"',
    })


@app.route("/api/admin/analytics/export/csv")
@login_required
@requires_role(_ANALYTICS_MODULE_ROLE)
def api_admin_analytics_export_csv():
    return _analytics_export_route("csv")


@app.route("/api/admin/analytics/export/excel")
@login_required
@requires_role(_ANALYTICS_MODULE_ROLE)
def api_admin_analytics_export_excel():
    return _analytics_export_route("xlsx")


@app.route("/api/admin/analytics/export/pdf")
@login_required
@requires_role(_ANALYTICS_MODULE_ROLE)
def api_admin_analytics_export_pdf():
    return _analytics_export_route("pdf")


# ── Analytics : rapports enregistrés (section Rapports) ─────────────────────
@app.route("/api/admin/analytics/reports", methods=["GET"])
@login_required
@requires_role(_ANALYTICS_MODULE_ROLE)
def api_admin_analytics_reports_list():
    return jsonify({"items": admin_analytics_export_service.list_export_history(limit=50)})


@app.route("/api/admin/analytics/reports", methods=["POST"])
@login_required
@requires_role(_ANALYTICS_MODULE_ROLE)
@rate_limit(requests=10, per_seconds=60)
@csrf_protect
def api_admin_analytics_reports_create():
    data = request.get_json(force=True) or {}
    filename, error = admin_analytics_export_service.generate_report_logged(
        _admin_actor(), data.get("report_type"), data.get("format"),
        data.get("date_from"), data.get("date_to"),
    )
    if error:
        return jsonify({"error": error}), 400
    return jsonify({"filename": filename}), 201


@app.route("/api/admin/analytics/reports/<path:filename>/download")
@login_required
@requires_role(_ANALYTICS_MODULE_ROLE)
def api_admin_analytics_reports_download(filename):
    path = admin_analytics_export_service.resolve_report_path(filename)
    if path is None:
        return jsonify({"error": "rapport introuvable"}), 404
    return send_file(path, as_attachment=True, download_name=filename)


# ── Analytics : favoris (vues sauvegardées) ─────────────────────────────────
@app.route("/api/admin/analytics/views", methods=["GET"])
@login_required
@requires_role(_ANALYTICS_MODULE_ROLE)
def api_admin_analytics_views_list():
    return jsonify({"items": admin_analytics_service.list_saved_views(request.current_user["id"])})


@app.route("/api/admin/analytics/views", methods=["POST"])
@login_required
@requires_role(_ANALYTICS_MODULE_ROLE)
@csrf_protect
def api_admin_analytics_views_create():
    data = request.get_json(force=True) or {}
    view_id, error = admin_analytics_service.create_saved_view(
        request.current_user["id"], data.get("name"), data.get("window", "30j"),
        data.get("date_from"), data.get("date_to"),
    )
    if error:
        return jsonify({"error": error}), 400
    return jsonify({"id": view_id}), 201


@app.route("/api/admin/analytics/views/<int:view_id>", methods=["DELETE"])
@login_required
@requires_role(_ANALYTICS_MODULE_ROLE)
@csrf_protect
def api_admin_analytics_views_delete(view_id):
    ok = admin_analytics_service.delete_saved_view(request.current_user["id"], view_id)
    if not ok:
        return jsonify({"error": "vue introuvable"}), 404
    return jsonify({"ok": True})


# ── Analytics : tableau de bord personnalisé (cartes KPI épinglées) ─────────
@app.route("/api/admin/analytics/pinned-kpis", methods=["GET"])
@login_required
@requires_role(_ANALYTICS_MODULE_ROLE)
def api_admin_analytics_pinned_kpis_list():
    return jsonify({
        "pinned": admin_analytics_service.list_pinned_kpis(request.current_user["id"]),
        "pinnable": list(admin_analytics_service.PINNABLE_KPIS),
    })


@app.route("/api/admin/analytics/pinned-kpis", methods=["PATCH"])
@login_required
@requires_role(_ANALYTICS_MODULE_ROLE)
@csrf_protect
def api_admin_analytics_pinned_kpis_toggle():
    data = request.get_json(force=True) or {}
    ok, error = admin_analytics_service.toggle_pinned_kpi(
        request.current_user["id"], data.get("kpi_key"), bool(data.get("pinned")),
    )
    if not ok:
        return jsonify({"error": error}), 400
    return jsonify({"ok": True})


# ── Gestion des abonnements (/admin/subscriptions) — lecture ET écriture ───
# Panneau d'administration du catalogue subscription_plans (voir
# admin_subscriptions_service.py) : NE modifie JAMAIS plan_service.py/
# quota_service.py (droits/quotas réellement appliqués au chatbot) ni
# stripe_service.py/stripe_webhook_service.py/billing_service.py (facturation
# réelle) — voir la docstring d'admin_subscriptions_service.py. Même rôle
# minimum que le module "subscriptions" dans admin_nav_service.py (ADMIN),
# jamais recodé ici. Toutes les écritures journalisées via
# admin_ai_log_service.py (le journal d'administration déjà créé).
_SUBSCRIPTIONS_MODULE_ROLE = admin_nav_service.module_by_path("/admin/subscriptions").minimum_role


@app.route("/admin/subscriptions/<plan>")
@login_required_page
@requires_role(_SUBSCRIPTIONS_MODULE_ROLE)
def serve_admin_subscription_detail(plan):
    return send_from_directory(app.static_folder, "admin.html")


@app.route("/api/admin/subscriptions")
@login_required
@requires_role(_SUBSCRIPTIONS_MODULE_ROLE)
def api_admin_subscriptions():
    """Carte principale — les 3 plans catalogués + statistiques globales
    réelles (voir admin_subscriptions_service.get_overview)."""
    return jsonify(admin_subscriptions_service.get_overview())


_ADMIN_SUBSCRIPTION_SIMPLE_TABS = {
    "info": admin_subscriptions_service.get_plan_info,
    "pricing": admin_subscriptions_service.get_plan_pricing,
    "features": admin_subscriptions_service.get_plan_features,
}


def _make_admin_subscription_tab_view(loader):
    @login_required
    @requires_role(_SUBSCRIPTIONS_MODULE_ROLE)
    def view(plan):
        data = loader(plan)
        if data is None:
            return jsonify({"error": "abonnement introuvable"}), 404
        return jsonify(data)
    return view


for _tab_name, _loader in _ADMIN_SUBSCRIPTION_SIMPLE_TABS.items():
    app.add_url_rule(
        f"/api/admin/subscriptions/<plan>/{_tab_name}",
        endpoint=f"api_admin_subscription_{_tab_name}",
        view_func=_make_admin_subscription_tab_view(_loader),
    )


# Onglets "Utilisateurs"/"Historique" — paramètres de pagination/recherche en
# plus du simple provider_id, jamais un agrégat géant (même lazy loading par
# onglet que les autres fiches détaillées de l'espace Administration).
@app.route("/api/admin/subscriptions/<plan>/users")
@login_required
@requires_role(_SUBSCRIPTIONS_MODULE_ROLE)
def api_admin_subscription_users(plan):
    data = admin_subscriptions_service.get_plan_users(
        plan, search=request.args.get("search"),
        page=request.args.get("page", 1), page_size=request.args.get("page_size"),
    )
    if data is None:
        return jsonify({"error": "abonnement introuvable"}), 404
    return jsonify(data)


@app.route("/api/admin/subscriptions/<plan>/history")
@login_required
@requires_role(_SUBSCRIPTIONS_MODULE_ROLE)
def api_admin_subscription_history(plan):
    data = admin_subscriptions_service.get_plan_history(
        plan, page=request.args.get("page", 1), page_size=request.args.get("page_size"),
    )
    if data is None:
        return jsonify({"error": "abonnement introuvable"}), 404
    return jsonify(data)


# ── Écriture (journalisée, voir admin_subscriptions_service.py) ────────────
@app.route("/api/admin/subscriptions/<plan>", methods=["PUT"])
@login_required
@requires_role(_SUBSCRIPTIONS_MODULE_ROLE)
@csrf_protect
def api_admin_subscription_update(plan):
    data = request.get_json(force=True) or {}
    ok, errors = admin_subscriptions_service.update_plan_logged(_admin_actor(), plan, data)
    if not ok:
        status = 404 if errors.get("_") == "Abonnement introuvable." else 400
        return jsonify({"error": errors.get("_", "Configuration invalide."), "fields": errors}), status
    return jsonify({"ok": True})


@app.route("/api/admin/subscriptions/<plan>/active", methods=["PATCH"])
@login_required
@requires_role(_SUBSCRIPTIONS_MODULE_ROLE)
@csrf_protect
def api_admin_subscription_set_active(plan):
    data = request.get_json(force=True) or {}
    ok, errors = admin_subscriptions_service.set_plan_active_logged(_admin_actor(), plan, bool(data.get("active")))
    if not ok:
        return jsonify({"error": errors.get("_", "Action impossible.")}), 404
    return jsonify({"ok": True})


# Tableau de bord développeur (Phase 4, Mission 8) — lecture seule, aucune
# écriture, aucune donnée personnelle d'un élève autre que l'utilisateur
# connecté (les métriques agrégées sont globales au process, pas par élève).
# ENABLE_DEV_DASHBOARD : coupe-circuit instantané (Mission 9).
# SEC-05 : réservée aux comptes ADMIN/SUPER_ADMIN (voir role_service.py) —
# toute nouvelle route développeur/admin future se protège de la même façon,
# en ajoutant @requires_role(...) juste après @login_required.
ENABLE_DEV_DASHBOARD = True


@app.route("/api/dev/dashboard")
@login_required
@requires_role(Role.ADMIN)
def api_dev_dashboard():
    if not ENABLE_DEV_DASHBOARD:
        return jsonify({"error": "Tableau de bord développeur désactivé."}), 404
    from chatbot.services import dev_dashboard
    return jsonify(dev_dashboard.snapshot())


# ── Stripe Billing (abonnements Premium/Ultra) ────────────────────────────────
# Séparation Controller / Service : la logique d'appel Stripe vit entièrement
# dans stripe_service.py (aucun appel au SDK ici) ; ces routes se contentent
# d'associer le user NovaMath courant au customer/abonnement Stripe et de
# traduire les erreurs du service en réponses HTTP, sur le même modèle que les
# autres routes API (jsonify({"error": ...}), codes 4xx/5xx explicites).
@app.route("/api/checkout/create-session", methods=["POST"])
@login_required
@rate_limit(requests=10, per_seconds=3600)
@csrf_protect
def api_checkout_create_session():
    """Crée une Stripe Checkout Session pour le plan demandé (Premium ou
    Ultra) et renvoie son URL. Le client Stripe est créé au premier appel
    puis réutilisé (stripe_customer_id stocké sur l'utilisateur). Le plan
    n'est comparé qu'une seule fois, ici, au moment de désérialiser l'entrée
    JSON non fiable du client — Plan.parse() est strict (None si inconnu),
    contrairement à Plan.from_value() utilisé pour lire des données internes
    déjà fiables (voir plan_service.py)."""
    data = request.get_json(force=True) or {}
    plan = Plan.parse(data.get("plan"))
    if plan not in (Plan.PREMIUM, Plan.ULTRA):
        return jsonify({"error": "Plan inconnu.", "field": "plan"}), 400

    user = request.current_user
    try:
        customer_id = user.get("stripe_customer_id")
        if not customer_id:
            # Clé stable par utilisateur (jamais par requête) : un utilisateur
            # ne doit avoir qu'un seul Customer Stripe pour toute sa vie sur
            # NovaMath. Deux requêtes concurrentes (double onglet, retry
            # réseau) sur ce même appel envoient donc la MÊME idempotency_key
            # à Stripe, qui sérialise et renvoie le même Customer aux deux —
            # ça élimine la race condition "customer orphelin" identifiée en
            # audit production, sans verrou applicatif ni SELECT ... FOR
            # UPDATE (SQLite n'offre pas ce mécanisme).
            customer = stripe_service.create_customer(
                user["email"], name=user.get("pseudo"),
                idempotency_key=f"novamath-customer-{user['id']}",
            )
            customer_id = customer["id"]
            db.set_stripe_customer_id(user["id"], customer_id)

        # Fenêtre de 30s (pas une clé stable comme ci-dessus) : un double-clic
        # ou un onglet dupliqué dans les 30s reçoit la même Checkout Session
        # au lieu d'en créer une seconde, mais un nouvel essai légitime plus
        # tard (ex: session expirée, changement d'avis) n'est jamais bloqué.
        checkout_idempotency_key = f"novamath-checkout-{user['id']}-{plan.value}-{int(time.time() // 30)}"
        checkout_session = stripe_service.create_checkout_session(
            customer_id=customer_id,
            plan=plan,
            success_url=f"{request.url_root}checkout/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{request.url_root}checkout/cancel",
            idempotency_key=checkout_idempotency_key,
        )
    except stripe_service.StripeNotConfigured as e:
        logger.error("Stripe non configuré : %s", e)
        return jsonify({"error": "Le paiement n'est pas encore configuré sur ce serveur."}), 501
    except stripe.error.StripeError as e:
        logger.error("Erreur Stripe lors de la création de la Checkout Session : %s", e)
        return jsonify({"error": "Impossible de créer la session de paiement."}), 502

    return jsonify({"checkout_url": checkout_session["url"]})


@app.route("/checkout/success")
@login_required
def checkout_success():
    """Page de retour après un paiement réussi. La mise à jour fiable du plan
    se fait via le webhook (voir api_checkout_webhook) car Stripe garantit sa
    livraison même si l'utilisateur ferme l'onglet avant la redirection ; ici
    on tente une synchronisation immédiate best-effort pour l'UX seulement."""
    session_id = request.args.get("session_id")
    if session_id:
        try:
            checkout = stripe_service.get_checkout_session(session_id)
            subscription_id = checkout.get("subscription")
            customer_id = checkout.get("customer")
            if subscription_id and customer_id and request.current_user.get("stripe_customer_id") == customer_id:
                subscription = stripe_service.get_subscription(subscription_id)
                stripe_webhook_service.sync_subscription(request.current_user, subscription)
        except stripe.error.StripeError as e:
            # Best-effort seulement : le webhook (api_checkout_webhook) reste la
            # source de vérité fiable si cette synchronisation immédiate échoue.
            logger.warning("Synchronisation immédiate post-checkout impossible : %s", e)
    return redirect("/abonnement.html?checkout=success")


@app.route("/checkout/cancel")
@login_required
def checkout_cancel():
    return redirect("/abonnement.html?checkout=cancel")


@app.route("/api/checkout/webhook", methods=["POST"])
def api_checkout_webhook():
    """Endpoint appelé par Stripe (jamais par le navigateur) : signature
    vérifiée via STRIPE_WEBHOOK_SECRET, donc pas de login_required/csrf_protect
    (qui supposent une session utilisateur NovaMath, absente ici). Une requête
    sans en-tête Stripe-Signature (ou avec une signature invalide) est
    systématiquement rejetée avant tout traitement — voir
    stripe_service.construct_webhook_event. Toute la logique métier (quel
    événement met à jour quoi, idempotence) vit dans stripe_webhook_service ;
    cette route ne fait que vérifier la signature et traduire le résultat en
    réponse HTTP."""
    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature", "")
    try:
        event = stripe_service.construct_webhook_event(payload, sig_header)
    except stripe_service.StripeNotConfigured as e:
        logger.error("Webhook Stripe reçu mais non configuré : %s", e)
        return jsonify({"error": "Webhook non configuré."}), 501
    except stripe.error.SignatureVerificationError:
        logger.warning("Webhook Stripe reçu avec une signature invalide ou absente, ignoré.")
        return jsonify({"error": "Signature invalide."}), 400

    try:
        result = stripe_webhook_service.handle_event(event)
    except stripe.error.StripeError as e:
        # Erreur d'appel Stripe pendant le traitement (ex: get_subscription) :
        # l'événement n'est pas marqué comme traité (voir handle_event), donc
        # Stripe le redélivrera plus tard sur ce 502 — jamais de perte d'événement.
        logger.error("Erreur Stripe lors du traitement du webhook %s : %s", event.get("id"), e)
        return jsonify({"error": "Erreur lors du traitement de l'événement."}), 502
    except Exception:
        logger.exception("Erreur inattendue lors du traitement du webhook Stripe %s.", event.get("id"))
        return jsonify({"error": "Erreur interne."}), 500

    return jsonify(result), 200


# ── Stripe Billing : cycle de vie de l'abonnement (portail client, statut,
# changement de plan) ──────────────────────────────────────────────────────
# Même séparation Controller / Service que les routes /api/checkout/* ci-
# dessus : toute la logique (agrégation Stripe, choix upgrade/downgrade) vit
# dans billing_service.py, ces routes ne font que traduire requête <-> appel
# de service <-> réponse HTTP.
@app.route("/api/billing/status", methods=["GET"])
@login_required
@rate_limit(requests=20, per_seconds=3600)
def api_billing_status():
    """État d'abonnement complet (plan, statut, dates, moyen de paiement,
    factures), entièrement dérivé de Stripe — consommé par les pages
    Abonnement et Profil."""
    try:
        status = billing_service.get_billing_status(request.current_user)
    except stripe_service.StripeNotConfigured as e:
        logger.error("Stripe non configuré : %s", e)
        return jsonify({"error": "La facturation n'est pas encore configurée sur ce serveur."}), 501
    return jsonify(status)


@app.route("/api/billing/customer-portal", methods=["POST"])
@login_required
@rate_limit(requests=20, per_seconds=3600)
@csrf_protect
def api_billing_customer_portal():
    """Crée une Billing Portal Session pour le customer Stripe existant de
    l'utilisateur courant et renvoie son URL ; ne crée jamais de nouveau
    Customer (voir billing_service.create_portal_session)."""
    try:
        portal_url = billing_service.create_portal_session(
            request.current_user, return_url=f"{request.url_root}abonnement.html",
        )
    except billing_service.NoStripeCustomer:
        return jsonify({"error": "Aucun abonnement à gérer pour le moment."}), 400
    except stripe_service.StripeNotConfigured as e:
        logger.error("Stripe non configuré : %s", e)
        return jsonify({"error": "La gestion d'abonnement n'est pas encore configurée sur ce serveur."}), 501
    except stripe.error.StripeError as e:
        logger.error("Erreur Stripe lors de la création de la session du portail client : %s", e)
        return jsonify({"error": "Impossible d'ouvrir le portail client."}), 502

    return jsonify({"portal_url": portal_url})


@app.route("/api/billing/change-plan", methods=["POST"])
@login_required
@rate_limit(requests=20, per_seconds=3600)
@csrf_protect
def api_billing_change_plan():
    """Change le plan de l'abonnement actif : upgrade immédiat ou downgrade
    programmé à la prochaine période de facturation selon le sens du
    changement (voir billing_service.change_plan). N'écrit jamais en base :
    le webhook reste l'unique source de vérité pour users.plan."""
    data = request.get_json(force=True) or {}
    plan = Plan.parse(data.get("plan"))
    if plan not in (Plan.PREMIUM, Plan.ULTRA):
        return jsonify({"error": "Plan inconnu.", "field": "plan"}), 400

    try:
        billing_service.change_plan(request.current_user, plan)
    except billing_service.NoActiveSubscription:
        return jsonify({"error": "Aucun abonnement actif à modifier."}), 400
    except billing_service.SamePlan:
        return jsonify({"error": "Ce plan est déjà actif."}), 400
    except stripe_service.StripeNotConfigured as e:
        logger.error("Stripe non configuré : %s", e)
        return jsonify({"error": "Le paiement n'est pas encore configuré sur ce serveur."}), 501
    except stripe.error.StripeError as e:
        logger.error("Erreur Stripe lors du changement de plan : %s", e)
        return jsonify({"error": "Impossible de changer de plan."}), 502

    return jsonify({"status": "ok"})


if __name__ == "__main__":
    # Serveur de dev uniquement (reloader/debugger Werkzeug). En production,
    # ce bloc n'est jamais exécuté : lancer via `gunicorn webapp.server:app`
    # (voir README / .env.example), qui importe `app` directement ci-dessus.
    app.run(debug=config.DEBUG, port=int(os.environ.get("PORT", 5050)), threaded=True)
