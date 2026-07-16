import json
import shutil
import re

def fix_math_string(text):
    if not isinstance(text, str):
        return text
    
    # 1. RÉPARATION DU BUG \f (Form Feed) -> \frac
    # C'est ici que le "rac" est corrigé
    text = text.replace('\x0c', '\\frac')
    
    # 2. Nettoyage des retours à la ligne et espaces
    text = text.replace('\r', '').replace('\n', ' ')
    text = re.sub(r'\s+', ' ', text)
    
    # 3. PROTECTION DU LATEX
    # Liste des commandes qui DOIVENT être en mode mathématique
    commands = [r'\\frac', r'\\sqrt', r'\\times', r'\\le', r'\\ge', r'\\in', r'\\vec', r'\\mathbb']
    
    needs_math = False
    for cmd in commands:
        if cmd.replace('\\\\', '\\') in text or cmd in text:
            needs_math = True
            break
    
    # Si on détecte des maths mais qu'il n'y a pas de $, on entoure TOUTE la chaîne
    if (needs_math or '^' in text or '_' in text) and '$' not in text:
        text = f"${text}$"
        
    # 4. Nettoyage des doubles $ accidentels (ex: $$phrase$$)
    text = text.replace('$$', '$')
    if text.count('$') == 1: # Si un seul $, on le retire pour éviter de casser le rendu
        text = text.replace('$', '')

    return text.strip()

def process():
    file_path = "exercises_bank.json"
    backup_path = "exercises_bank_backup.json"
    shutil.copy(file_path, backup_path)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    for ex in data:
        ex["enonce"] = fix_math_string(ex.get("enonce", ""))
        ex["answer"] = fix_math_string(ex.get("answer", ""))
        ex["hint"] = fix_math_string(ex.get("hint", ""))
        if "solution_steps" in ex and isinstance(ex["solution_steps"], list):
            ex["solution_steps"] = [fix_math_string(s) for s in ex["solution_steps"]]
            
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print("--- Fichier JSON réparé et sauvegardé ! ---")

if __name__ == "__main__":
    process()