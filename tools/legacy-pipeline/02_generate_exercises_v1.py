import json
import requests
import os
import re
from tqdm import tqdm

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "mistral" 
PROGRAMME_FILE = "Programme AI.json"
OUTPUT_FILE = "exercises_temp/raw_generated.json"
os.makedirs("exercises_temp", exist_ok=True)

def robust_json_parse(text):
    """Extrait le JSON même avec des balises ou des accents différents."""
    try:
        # 1. Nettoyer les balises Markdown
        text = re.sub(r'```json', '', text)
        text = re.sub(r'```', '', text)
        
        # 2. Chercher le premier { et le dernier }
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if not match:
            return None
        
        obj = json.loads(match.group())
        
        # 3. Normaliser les clés (transformer 'énoncé' ou 'statement' en 'enonce')
        normalized = {}
        # On définit les correspondances possibles
        mapping = {
            'énoncé': 'enonce', 'enoncé': 'enonce', 'statement': 'enonce',
            'réponse': 'answer', 'reponse': 'answer', 'solution': 'answer',
            'indice': 'hint', 'clue': 'hint',
            'solution_steps': 'solution_steps', 'étapes': 'solution_steps'
        }
        
        for k, v in obj.items():
            new_key = mapping.get(k.lower(), k.lower())
            normalized[new_key] = v
            
        return normalized
    except:
        return None

def call_ollama(prompt):
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.3}
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        raw_text = response.json().get('response', '')
        return robust_json_parse(raw_text)
    except:
        return None

# --- CHARGEMENT ---
with open(PROGRAMME_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

chapters = data.get("chapters", [])
all_exercises = []

print(f"🚀 Lancement de la génération (Mode Sauvetage)")

for chapter in chapters:
    ch_id = chapter.get('id')
    notions = chapter.get('notions_cours', [])
    
    print(f"\n📖 Chapitre : {ch_id}")
    for notion in tqdm(notions, desc="Notions"):
        for diff in [1, 3, 5]:
            prompt = f"Génère un exercice de mathématiques (niveau Seconde France) sur : {notion}. Difficulté : {diff}/5. Réponds en JSON avec les clés : enonce, answer, hint, solution_steps."
            
            exercise = call_ollama(prompt)
            
            if exercise and ("enonce" in exercise or "enoncé" in exercise):
                # On s'assure que les métadonnées sont là
                exercise['chapter_id'] = ch_id
                exercise['notion'] = notion
                exercise['difficulty'] = diff
                
                all_exercises.append(exercise)
                
                # SAUVEGARDE CRITIQUE : on écrit physiquement le fichier à chaque réussite
                with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                    json.dump(all_exercises, f, ensure_ascii=False, indent=2)
            else:
                # Log d'erreur pour savoir pourquoi ça rate
                with open("error_log.txt", "a", encoding="utf-8") as err_file:
                    err_file.write(f"Echec pour {notion} Lvl {diff}\n")

print(f"\n✅ Terminé ! {len(all_exercises)} exercices créés.")