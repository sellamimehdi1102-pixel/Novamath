# Pipeline de génération — archivé (2026-07-13)

Ces scripts formaient l'ancien pipeline de génération du contenu de NovaMath
(extraction PDF → génération LLM → validation → simulation de données →
entraînement du modèle → naturalisation). Depuis le 2026-07-13, les banques
d'exercices (`exercises_bank*.json`) et les modèles (`models/*.pkl`) sont des
données définitives, générées sur une autre machine puis simplement copiées
dans le projet — ce pipeline ne fait donc plus partie du processus de
développement de NovaMath.

Ils sont conservés ici pour l'historique et au cas où le pipeline devrait être
relancé un jour, mais **aucun n'est appelé par `webapp/`** (vérifié : aucun
n'est jamais importé, seules leurs sorties passées — `exercises_bank.json`,
`models/*.pkl` — sont chargées par `webapp/server.py`).

| Script | Rôle |
|---|---|
| `01_extract_pdfs.py` | Extraction PDF → texte (remplacé pour le module Cours par `tools/regenerate_course_content.py`) |
| `02_generate_exercises_v1.py` | Génération d'exercices bruts via LLM local (Ollama/Mistral) |
| `03_validate_exercises.py` | Validation interactive des exercices générés |
| `04_simulate_data.py` | Simulation de données d'élèves fictifs |
| `05_train_model.py` | Entraînement du modèle de prédiction de niveau |
| `06_quiz_app.py` | Prototype Gradio, ancêtre de `webapp/` |
| `07_naturalize_exercises.py` | Conversion LaTeX → français naturel |

**Si relancé un jour** : `01`, `02`, `04`, `06` et `audit_script.py`/`clean_json.py`
(dans `tools/`) utilisent des chemins relatifs au répertoire courant — à lancer
depuis la racine du projet (`python tools/legacy-pipeline/01_extract_pdfs.py`
depuis `c:\Users\sella\Desktop\Programation AI`). `03` dépend de la sortie de
`02` (`exercises_temp/raw_generated.json`). `07` a été ajusté pour continuer à
cibler la racine du projet après son déplacement ici.
