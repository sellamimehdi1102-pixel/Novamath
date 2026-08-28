"""
Construit le message d'accueil personnalisé du chatbot à partir du résumé de
contexte déjà calculé par context_builder.py::build_context_summary — aucune
requête réseau ici, fonction pure, testable indépendamment du reste du
pipeline (rule_engine/math_engine/knowledge_engine/provider_manager).
"""

_FALLBACK_PSEUDO = "Invité"


def _first_name(pseudo):
    if not pseudo or pseudo == _FALLBACK_PSEUDO:
        return None
    return pseudo.strip().split(" ")[0]


def build_greeting(context_summary):
    name = _first_name(context_summary.get("pseudo"))
    salutation = f"Salut {name} !" if name else "Salut !"

    if not context_summary.get("total_exercises"):
        return (
            f"{salutation} Je suis l'assistant NovaMath. Pose-moi une question sur un cours, "
            "un exercice qui bloque, ou dis-moi ce que tu veux réviser — je t'accompagne pas à pas."
        )

    lines = [salutation]

    goals = context_summary.get("daily_goals") or {}
    if goals.get("reached"):
        lines.append("Objectif du jour déjà atteint, bravo !")
    elif goals.get("remaining_exercises"):
        lines.append(
            f"Il te reste {goals['remaining_exercises']} exercice"
            f"{'s' if goals['remaining_exercises'] > 1 else ''} pour atteindre ton objectif du jour."
        )

    weak = context_summary.get("weak_notions") or []
    chapters = context_summary.get("chapters_in_progress") or []
    if weak:
        lines.append(f"Je vois que tu peux encore progresser sur : {', '.join(weak[:2])}.")
    elif chapters:
        lines.append(f"Tu es en train de travailler {chapters[0]} — dis-moi si tu veux qu'on continue dessus.")

    lines.append("Sur quoi veux-tu qu'on travaille aujourd'hui ?")
    return " ".join(lines)
