import json, joblib, gradio as gr, random, time, re

# ── Chargement et Attribution d'IDs Automatiques ──────────────────────────────
with open("exercises_bank.json", "r", encoding="utf-8") as f:
    raw_bank = json.load(f)

def clean_text(text):
    if not isinstance(text, str):
        return text
    
    # 1. RÉPARATION DU BUG \f (Form Feed) : remplace l'espace+rac par \frac
    # On cherche les caractères de contrôle invisibles ou les erreurs de lecture
    text = text.replace('\x0c', '\\f') # Répare le caractère invisible \f
    
    # 2. Nettoyage des retours à la ligne
    text = text.replace("\r", "").replace("\n", " ")
    
    # 3. Normalisation des espaces
    text = re.sub(r'\s+', ' ', text)
    
    # 4. ENTOURER LES FORMULES PAR DES $ (pour le LaTeX dans Gradio)
    # On cherche les motifs typiques comme \frac, \sqrt, les puissances ^, etc.
    # Cette regex simplifiée essaie de détecter où commencent et finissent les maths
    if "\\" in text or "^" in text or "_" in text:
        # Si le texte contient des commandes LaTeX mais pas de $, on en ajoute
        # Note: Cette partie dépend de la structure de vos phrases. 
        # Le mieux est d'avoir les $ directement dans le JSON.
        pass 

    return text.strip()

BANK = []
for i, ex in enumerate(raw_bank):
    ex["id"] = ex.get("id") if ex.get("id") is not None else i
    for field in ["enonce", "answer", "hint"]:
        if isinstance(ex.get(field), str):
            val = ex[field]
            # Si la chaîne contient des maths sans délimiteurs, on sécurise
            if "\\" in val and "$" not in val:
                val = f"${val}$"
            ex[field] = val 
        
    BANK.append(ex)

MODEL = joblib.load("models/level_predictor.pkl")
QUIZ_DIFFS = joblib.load("models/quiz_difficulties.pkl")
N_QUESTIONS = len(QUIZ_DIFFS)
LEVEL_LABELS = {1: ("🌱", "Débutant"), 2: ("⚡", "Intermédiaire"), 3: ("🏆", "Avancé")}

def get_chapter_num(name):
    nums = re.findall(r'\d+', name)
    return int(nums[0]) if nums else 0

CHAPTERS = sorted(list(set(ex.get("chapter_id", "") for ex in BANK)), key=get_chapter_num)

# ── Logique de sélection ──────────────────────────────────────────────────────
def pick_exercise(difficulty, exclude_ids, allowed_chapters):
    pool = [e for e in BANK if e.get("chapter_id") in allowed_chapters] if allowed_chapters else BANK
    candidates = [e for e in pool if e["difficulty"] == difficulty and e["id"] not in exclude_ids]
    if not candidates:
        for d in [1, -1, 2, -2]:
            candidates = [e for e in pool if e["difficulty"] == difficulty + d and e["id"] not in exclude_ids]
            if candidates: break
    if not candidates: candidates = pool
    return random.choice(candidates)

def predict_level(responses, difficulties):
    r = (responses + [0] * 7)[:7]
    d = (difficulties + [2] * 7)[:7]
    total = sum(r)
    weighted = sum(r[i] * d[i] for i in range(7))
    features = r + [sum(r[i] for i, v in enumerate(d) if v==1), 
                    sum(r[i] for i, v in enumerate(d) if v==2),
                    sum(r[i] for i, v in enumerate(d) if v==3), total, weighted]
    return int(MODEL.predict([features])[0])

# ── Interface Gradio ──────────────────────────────────────────────────────────
# latex_delimiters permet d'afficher les formules mathématiques correctement
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    state_q = gr.State(0)
    state_resps = gr.State([])
    state_diffs = gr.State([])
    state_used_ids = gr.State([])
    state_ex = gr.State(None)
    state_allowed = gr.State([])
    state_current_level = gr.State(1)
    state_history = gr.State([])
    state_practice_resps = gr.State([])
    state_practice_diffs = gr.State([])

    with gr.Column(visible=True) as screen_start:
        gr.Markdown("# 🧮 NovaMath — Seconde")
        chapter_sel = gr.CheckboxGroup(choices=CHAPTERS, label="Sélectionnez vos chapitres", value=[])
        btn_start = gr.Button("🚀 Démarrer l'évaluation initiale", variant="primary")

    with gr.Column(visible=False) as screen_quiz:
        md_progress = gr.Markdown()
        md_question = gr.Markdown()
        with gr.Row():
            btn_hint = gr.Button("💡 Indice", size="sm")
            btn_ans = gr.Button("👁 Réponse", size="sm")
        md_hint, md_answer = gr.Markdown(visible=False), gr.Markdown(visible=False)
        gr.Markdown("---")
        gr.Markdown("### As-tu réussi cet exercice ?")
        with gr.Row():
            btn_yes = gr.Button("✅ Réussi", variant="primary")
            btn_no = gr.Button("❌ Échoué", variant="secondary")

    with gr.Column(visible=False) as screen_result:
        md_lvl_display = gr.Markdown()
        with gr.Row():
            with gr.Column(scale=2):
                gr.Markdown("### 📚 Entraînement")
                exercise_list = gr.Dropdown(label="Choisir : Chapitre | Notion", choices=[])
                btn_load_ex = gr.Button("📝 Charger l'exercice")
            with gr.Column(scale=1):
                gr.Markdown("### 📈 Suivi & Progression")
                md_history = gr.Markdown("*Aucun exercice fait*")

        with gr.Group(visible=False) as practice_area:
            md_p_enonce = gr.Markdown()
            with gr.Row():
                btn_p_hint = gr.Button("💡 Indice", size="sm")
                btn_p_sol = gr.Button("👁 Réponse", size="sm")
            md_p_hint, md_p_sol = gr.Markdown(visible=False), gr.Markdown(visible=False)
            gr.Markdown("#### Auto-évaluation :")
            with gr.Row():
                btn_p_yes = gr.Button("✅ Réussi", variant="primary")
                btn_p_no = gr.Button("❌ Échoué", variant="secondary")
        
        btn_restart = gr.Button("🔄 Recommencer à zéro", variant="stop", size="sm")

    # ── Fonctions de logique ──

    def start_quiz(chapters):
        ex = pick_exercise(QUIZ_DIFFS[0], [], chapters)
        return {
            screen_start: gr.update(visible=False),
            screen_quiz: gr.update(visible=True),
            md_progress: f"### Question 1 / {N_QUESTIONS}",
            md_question: f"**{ex.get('chapter_id')}**\n\n{ex['enonce']}",
            state_ex: ex, state_allowed: chapters, state_used_ids: [ex["id"]],
            state_q: 0, state_resps: [], state_diffs: [],
            state_history: [], state_practice_resps: [], state_practice_diffs: []
        }

    def handle_quiz_answer(is_correct, q_idx, resps, diffs, used, current_ex, allowed):
        new_resps = resps + [1 if is_correct else 0]
        new_diffs = diffs + [current_ex["difficulty"]]
        new_q = q_idx + 1

        if new_q >= N_QUESTIONS:
            level = predict_level(new_resps, new_diffs)
            icon, label = LEVEL_LABELS[level]
            pool = [e for e in BANK if e.get("chapter_id") in allowed] if allowed else BANK
            choices = [(f"{e.get('chapter_id')} : {e.get('notion')}", str(e['id'])) for e in pool if e['difficulty'] == level]
            return {
                screen_quiz: gr.update(visible=False),
                screen_result: gr.update(visible=True),
                md_lvl_display: f"# {icon} Votre Niveau : {label}",
                exercise_list: gr.update(choices=choices, value=None),
                state_current_level: level,
                state_q: new_q, state_resps: new_resps, state_diffs: new_diffs
            }

        next_ex = pick_exercise(QUIZ_DIFFS[new_q], used, allowed)
        return {
            md_progress: f"### Question {new_q+1} / {N_QUESTIONS}",
            md_question: f"**{next_ex.get('chapter_id')}**\n\n{next_ex['enonce']}",
            state_q: new_q, state_resps: new_resps, state_diffs: new_diffs,
            state_used_ids: used + [next_ex["id"]], state_ex: next_ex,
            md_hint: gr.update(visible=False, value=""), md_answer: gr.update(visible=False, value="")
        }

    def load_practice_ex(ex_id):
        if not ex_id: return {practice_area: gr.update(visible=False)}
        ex = next((e for e in BANK if str(e["id"]) == ex_id), None)
        return {
            practice_area: gr.update(visible=True),
            md_p_enonce: f"### Enoncé :\n{ex['enonce']}",
            state_ex: ex,
            md_p_hint: gr.update(visible=False, value=""),
            md_p_sol: gr.update(visible=False, value="")
        }

    def handle_practice_result(is_correct, p_resps, p_diffs, history, current_ex, allowed, current_lvl):
        new_p_resps = p_resps + [1 if is_correct else 0]
        new_p_diffs = p_diffs + [current_ex["difficulty"]]
        icon_res = "✅" if is_correct else "❌"
        new_history = history + [f"{icon_res} {current_ex.get('chapter_id')} : {current_ex.get('notion')}"]
        
        new_lvl = current_lvl
        msg_eval = ""
        
        if len(new_p_resps) >= 3:
            new_lvl = predict_level(new_p_resps, new_p_diffs)
            if new_lvl != current_lvl:
                msg_eval = f"### 💡 Niveau mis à jour : {LEVEL_LABELS[new_lvl][1]} !\n"
            new_p_resps, new_p_diffs = [], []

        icon_l, label_l = LEVEL_LABELS[new_lvl]
        pool = [e for e in BANK if e.get("chapter_id") in allowed] if allowed else BANK
        choices = [(f"{e.get('chapter_id')} : {e.get('notion')}", str(e['id'])) for e in pool if e['difficulty'] == new_lvl]
        history_md = "**Derniers exercices :**\n\n" + "\n".join([f"- {e}" for e in new_history[-5:]])

        return {
            state_practice_resps: new_p_resps,
            state_practice_diffs: new_p_diffs,
            state_history: new_history,
            state_current_level: new_lvl,
            md_lvl_display: f"{msg_eval}# {icon_l} Votre Niveau : {label_l}",
            md_history: history_md,
            exercise_list: gr.update(choices=choices, value=None),
            practice_area: gr.update(visible=False)
        }

    # ── Câblage ──
    start_outs = [screen_start, screen_quiz, md_progress, md_question, state_ex, state_allowed, state_used_ids, state_q, state_resps, state_diffs, state_history, state_practice_resps, state_practice_diffs]
    btn_start.click(start_quiz, [chapter_sel], start_outs)

    quiz_outs = [screen_quiz, screen_result, md_progress, md_question, md_hint, md_answer, md_lvl_display, exercise_list, state_current_level, state_q, state_resps, state_diffs, state_used_ids, state_ex]
    btn_yes.click(lambda *a: handle_quiz_answer(True, *a), [state_q, state_resps, state_diffs, state_used_ids, state_ex, state_allowed], quiz_outs)
    btn_no.click(lambda *a: handle_quiz_answer(False, *a), [state_q, state_resps, state_diffs, state_used_ids, state_ex, state_allowed], quiz_outs)

    btn_load_ex.click(load_practice_ex, [exercise_list], [practice_area, md_p_enonce, state_ex, md_p_hint, md_p_sol])
    
    p_params = [state_practice_resps, state_practice_diffs, state_history, state_ex, state_allowed, state_current_level]
    p_outs = [state_practice_resps, state_practice_diffs, state_history, state_current_level, md_lvl_display, md_history, exercise_list, practice_area]
    btn_p_yes.click(lambda *a: handle_practice_result(True, *a), p_params, p_outs)
    btn_p_no.click(lambda *a: handle_practice_result(False, *a), p_params, p_outs)

    btn_hint.click(lambda ex: gr.update(visible=True, value=f"💡 {ex['hint']}"), [state_ex], md_hint)
    btn_ans.click(lambda ex: gr.update(visible=True, value=f"✅ {ex['answer']}"), [state_ex], md_answer)
    btn_p_hint.click(lambda ex: gr.update(visible=True, value=f"💡 {ex['hint']}"), [state_ex], md_p_hint)
    btn_p_sol.click(lambda ex: gr.update(visible=True, value=f"✅ {ex['answer']}"), [state_ex], md_p_sol)
    
    btn_restart.click(lambda: (gr.update(visible=True), gr.update(visible=False)), None, [screen_start, screen_result])

if __name__ == "__main__":
    demo.launch()