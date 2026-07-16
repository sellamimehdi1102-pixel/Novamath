import json
import os
from collections import defaultdict

def audit_avancement():
    # 1. Chargement des fichiers
    if not os.path.exists("Programme AI.json") or not os.path.exists("exercises_bank.json"):
        print("❌ Erreur : L'un des fichiers JSON est introuvable.")
        return

    with open("Programme AI.json", "r", encoding="utf-8") as f:
        programme = json.load(f).get("chapters", [])

    with open("exercises_bank.json", "r", encoding="utf-8") as f:
        bank = json.load(f)

    # 2. Analyse de la banque d'exercices (Pratique)
    # Structure : bank_stats[chapitre_id][notion_nom] = {difficulte: count}
    bank_stats = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    for ex in bank:
        ch_id = ex.get('chapter_id')
        notion = ex.get('notion')
        diff = ex.get('difficulty')
        bank_stats[ch_id][notion][diff] += 1

    # 3. Affichage du Rapport
    print("="*90)
    print(f"{'RAPPORT DU GÉNÉRATEUR ADAPTATIF':^90}")
    print("="*90)

    total_notions_prog = 0
    total_notions_couvertes = 0

    for ch in programme:
        ch_id = ch.get('id')
        ch_title = ch.get('title')
        notions_officielles = ch.get('notions_cours', [])
        
        # Calcul des stats pour ce chapitre
        nb_notions_total = len(notions_officielles)
        notions_dans_la_banque = bank_stats.get(ch_id, {})
        nb_notions_couvertes = len([n for n in notions_officielles if n in notions_dans_la_banque])
        
        # Mise à jour des globaux
        total_notions_prog += nb_notions_total
        total_notions_couvertes += nb_notions_couvertes

        # Affichage du header du chapitre
        pourcentage = (nb_notions_couvertes / nb_notions_total * 100) if nb_notions_total > 0 else 0
        print(f"\n📂 {ch_id} : {ch_title}")
        print(f"📊 Couverture : {nb_notions_couvertes}/{nb_notions_total} notions ({pourcentage:.1f}%)")
        print("-" * 90)

        # Affichage du détail par notion
        for notion in notions_officielles:
            if notion in notions_dans_la_banque:
                diffs = notions_dans_la_banque[notion]
                # Formatage des difficultés : L1: 2, L3: 1...
                detail_str = ", ".join([f"L{d}:{c}" for d, c in sorted(diffs.items())])
                total_exos = sum(diffs.values())
                status = "✅"
                print(f"  {status} {notion[:40]:<40} | {total_exos:>2} exos ({detail_str})")
            else:
                status = "❌"
                print(f"  {status} {notion[:40]:<40} | MANQUANT")

    # 4. Résumé Global
    print("\n" + "="*90)
    final_pct = (total_notions_couvertes / total_notions_prog * 100) if total_notions_prog > 0 else 0
    print(f"RÉSUMÉ GÉNÉRAL :")
    print(f"- Notions totales prévues : {total_notions_prog}")
    print(f"- Notions couvertes par l'IA : {total_notions_couvertes}")
    print(f"- Taux de complétion global : {final_pct:.1f}%")
    print(f"- Nombre total d'exercices validés : {len(bank)}")
    print("="*90)

if __name__ == "__main__":
    audit_avancement()