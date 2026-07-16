# 04_simulate_data.py
import json, numpy as np, pandas as pd, os

with open("exercises_bank.json", "r", encoding="utf-8") as f:
    bank = json.load(f)

os.makedirs("data", exist_ok=True)

from collections import Counter
diff_dist = Counter(ex["difficulty"] for ex in bank)
print("Distribution des difficultés dans le bank :", dict(sorted(diff_dist.items())))

N_STUDENTS = 600
LEVELS     = [1, 2, 3]   # 3 niveaux étudiants

# Quiz : 7 questions avec les 3 difficultés disponibles
# On met plus de questions au milieu pour mieux discriminer
QUIZ_DIFF_SLOTS = [1, 1, 2, 2, 2, 3, 3]

def p_correct(student_level, exercise_difficulty):
    """Sigmoid : niveau > difficulté → facile → haute proba."""
    delta = student_level - exercise_difficulty
    return 1 / (1 + np.exp(-2.0 * delta))  # pente plus forte pour 3 niveaux

def sample_quiz_exercises(bank, difficulty_slots):
    selected = []
    for d in difficulty_slots:
        candidates = [ex for ex in bank if ex["difficulty"] == d]
        if not candidates:
            candidates = sorted(bank, key=lambda x: abs(x["difficulty"] - d))
        selected.append(np.random.choice(candidates))
    return selected

rows = []
np.random.seed(42)

for sid in range(N_STUDENTS):
    # Répartition réaliste : plus d'étudiants au niveau intermédiaire
    true_level = np.random.choice(LEVELS, p=[0.30, 0.40, 0.30])
    quiz_exs   = sample_quiz_exercises(bank, QUIZ_DIFF_SLOTS)

    responses = [
        int(np.random.random() < p_correct(true_level, ex["difficulty"]))
        for ex in quiz_exs
    ]

    row = {"student_id": sid, "true_level": true_level}
    for i, (r, ex) in enumerate(zip(responses, quiz_exs)):
        row[f"q{i+1}_correct"]    = r
        row[f"q{i+1}_difficulty"] = ex["difficulty"]

    # Features agrégées
    row["score_easy"]   = sum(responses[i] for i, d in enumerate(QUIZ_DIFF_SLOTS) if d == 1)
    row["score_medium"] = sum(responses[i] for i, d in enumerate(QUIZ_DIFF_SLOTS) if d == 2)
    row["score_hard"]   = sum(responses[i] for i, d in enumerate(QUIZ_DIFF_SLOTS) if d == 3)
    row["total_score"]  = sum(responses)
    row["weighted_score"] = sum(r * d for r, d in zip(responses, QUIZ_DIFF_SLOTS))

    rows.append(row)

df = pd.DataFrame(rows)
df.to_csv("data/simulated_students.csv", index=False)

print(f"\n✅ {N_STUDENTS} étudiants simulés → data/simulated_students.csv")
print("\nScore total moyen par niveau :")
print(df.groupby("true_level")["total_score"].mean().round(2).to_string())
print("\nScore pondéré moyen par niveau :")
print(df.groupby("true_level")["weighted_score"].mean().round(2).to_string())