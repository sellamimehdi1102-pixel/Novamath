# 05_train_model.py
import pandas as pd, numpy as np, joblib, os, matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, confusion_matrix, ConfusionMatrixDisplay

os.makedirs("models", exist_ok=True)

df = pd.read_csv("data/simulated_students.csv")

FEATURE_COLS = (
    [f"q{i+1}_correct" for i in range(7)] +
    ["score_easy", "score_medium", "score_hard", "total_score", "weighted_score"]
)
TARGET = "true_level"

X = df[FEATURE_COLS].values
y = df[TARGET].values

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42
)

# ── Modèles à comparer ────────────────────────────────────────────────────────
models = {
    "Decision Tree (depth 4)": DecisionTreeClassifier(
        max_depth=4, min_samples_leaf=10, class_weight="balanced", random_state=42),
    "Decision Tree (depth 6)": DecisionTreeClassifier(
        max_depth=6, min_samples_leaf=6, class_weight="balanced", random_state=42),
    "KNN (k=7)": Pipeline([
        ("scaler", StandardScaler()),
        ("knn", KNeighborsClassifier(n_neighbors=7))
    ]),
    "KNN (k=11)": Pipeline([
        ("scaler", StandardScaler()),
        ("knn", KNeighborsClassifier(n_neighbors=11))
    ]),
}

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

print("=== Cross-Validation (5-fold) ===")
best_name, best_score, best_model = None, 0, None
for name, model in models.items():
    scores = cross_val_score(model, X, y, cv=cv, scoring="accuracy")
    print(f"  {name:<30} {scores.mean():.3f} ± {scores.std():.3f}")
    if scores.mean() > best_score:
        best_score, best_name, best_model = scores.mean(), name, model

print(f"\n→ Meilleur modèle : {best_name} ({best_score:.3f})")

# ── Entraînement final ────────────────────────────────────────────────────────
best_model.fit(X_train, y_train)
y_pred = best_model.predict(X_test)

print(f"\n=== Résultats sur le jeu de test ===")
print(classification_report(y_test, y_pred,
      target_names=[f"Niveau {i}" for i in range(1, 4)]))  # 3 niveaux

# ── Matrice de confusion ──────────────────────────────────────────────────────
cm = confusion_matrix(y_test, y_pred)
fig, ax = plt.subplots(figsize=(5, 4))
ConfusionMatrixDisplay(cm, display_labels=[f"N{i}" for i in range(1, 4)]).plot(
    ax=ax, colorbar=False, cmap="Blues")
ax.set_title(f"Matrice de Confusion — {best_name}")
plt.tight_layout()
plt.savefig("models/confusion_matrix.png", dpi=120)
print("Matrice de confusion → models/confusion_matrix.png")

# ── Règles de l'arbre (si Decision Tree) ─────────────────────────────────────
actual_model = (best_model.named_steps.get("knn", best_model)
                if hasattr(best_model, "named_steps") else best_model)
if isinstance(actual_model, DecisionTreeClassifier):
    print("\n=== Règles de l'arbre (3 premiers niveaux) ===")
    print(export_text(actual_model, feature_names=FEATURE_COLS, max_depth=3))

# ── Sauvegarde ────────────────────────────────────────────────────────────────
joblib.dump(best_model,           "models/level_predictor.pkl")
joblib.dump(FEATURE_COLS,         "models/feature_cols.pkl")
joblib.dump([1, 1, 2, 2, 2, 3, 3], "models/quiz_difficulties.pkl")  # 3 difficultés

print("\n✅ Modèle sauvegardé → models/level_predictor.pkl")