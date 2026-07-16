import json
import os
import requests

# --- CONFIGURATION ---
# Chemin vers le fichier JSON brut contenant les exercices générés par le script précédent.
RAW_FILE = "exercises_temp/raw_generated.json"
# Chemin vers le fichier JSON qui stockera les exercices validés.
BANK_FILE = "exercises_bank.json"
# URL du serveur Ollama local utilisé pour corriger automatiquement des exercices.
OLLAMA_URL = "http://localhost:11434/api/generate"

def call_ai_fix(exercise, instruction):
    """Demande à l'IA de corriger un exercice en suivant une instruction précise.

    Cette fonction transforme l'exercice JSON actuel en un prompt structuré,
    l'envoie au serveur Ollama, puis tente de relire la réponse JSON.
    Si la correction échoue, elle retourne None.
    """
    prompt = f"""Voici un exercice de mathématiques en JSON :
{json.dumps(exercise, ensure_ascii=False)}

Instruction de correction : {instruction}

Réponds UNIQUEMENT avec le JSON corrigé, sans texte autour."""

    payload = {
        "model": "mistral",
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=30)
        # On récupère la clé 'response' renvoyée par Ollama et on la parse en JSON.
        return json.loads(resp.json().get('response', '{}'))
    except Exception:
        # En cas d'erreur réseau ou de parsing, on ne casse pas la validation.
        return None

def main():
    # Si le fichier brut n'existe pas, il n'y a rien à valider.
    if not os.path.exists(RAW_FILE):
        return

    # Charge tous les exercices générés par le script précédent.
    with open(RAW_FILE, "r", encoding="utf-8") as f:
        raw_exercises = json.load(f)

    # Charge la banque d'exercices validés existante, si elle existe.
    bank = []
    if os.path.exists(BANK_FILE):
        with open(BANK_FILE, "r", encoding="utf-8") as f:
            bank = json.load(f)

    # Liste des énoncés déjà validés pour éviter les doublons.
    done_enonces = [ex.get('enonce') for ex in bank]

    # Chapitres à valider : 1 à 6 uniquement.
    allowed_chapters = {f"Chapitre_{n}" for n in range(1, 7)}

    # Sélectionne uniquement les exercices des chapitres 1 à 6 qui n'ont pas déjà été acceptés.
    to_validate = [
        ex for ex in raw_exercises
        if ex.get('enonce') not in done_enonces
        and ex.get('chapter_id') in allowed_chapters
    ]

    for i, ex in enumerate(to_validate):
        while True:
            # Nettoie l'écran pour afficher un nouveau bloc de validation propre.
            os.system('cls' if os.name == 'nt' else 'clear')
            print(f"--- EXERCICE {i+1}/{len(to_validate)} ---")
            print(f"NOTION : {ex.get('notion')} | Diff: {ex.get('difficulty')}")

            # Affiche les champs principaux de l'exercice.
            print(f"\n1. 📝 ÉNONCÉ : {ex.get('enonce')}")
            print(f"2. ✅ RÉPONSE : {ex.get('answer')}")
            print(f"3. 💡 INDICE  : {ex.get('hint')}")
            # On tronque les étapes pour ne pas surcharger l'écran.
            print(f"4. 📖 ÉTAPES  : {str(ex.get('solution_steps', ''))[:100]}...")
            print("\n[y] Accepter | [n] Jeter | [e] MODIFIER | [q] Quitter")

            choice = input("\nAction : ").lower().strip()

            if choice == 'y':
                # Acceptation : ajoute l'exercice à la banque et sauvegarde immédiatement.
                bank.append(ex)
                with open(BANK_FILE, "w", encoding="utf-8") as f:
                    json.dump(bank, f, ensure_ascii=False, indent=2)
                break
            elif choice == 'n':
                # Rejet : ne conserve pas l'exercice et passe au suivant.
                break
            elif choice == 'q':
                # Quitte le programme sans continuer la validation.
                return
            elif choice == 'e':
                # Mode édition manuelle ou automatique.
                print("\nQue veux-tu modifier ?")
                print("1: Énoncé | 2: Réponse | 3: Indice | 4: Étapes | 5: 🤖 IA FIX (Correction auto)")
                sub_choice = input("Choix : ")

                if sub_choice == '1':
                    ex['enonce'] = input("Nouvel énoncé : ") or ex['enonce']
                elif sub_choice == '2':
                    ex['answer'] = input("Nouvelle réponse : ") or ex['answer']
                elif sub_choice == '3':
                    ex['hint'] = input("Nouvel indice : ") or ex['hint']
                elif sub_choice == '4':
                    ex['solution_steps'] = input("Nouvelles étapes : ") or ex['solution_steps']
                elif sub_choice == '5':
                    # Demande une correction spécifique à l'IA et met à jour l'exercice.
                    inst = input("Dis à l'IA quoi corriger (ex: 'le calcul fait 144') : ")
                    new_ex = call_ai_fix(ex, inst)
                    if new_ex:
                        ex.update(new_ex)
                        print("✅ IA a corrigé l'exercice.")
                    else:
                        print("❌ Échec de l'IA.")
                # Après modification, on reste dans la boucle pour relire l'exercice.

if __name__ == "__main__":
    main()