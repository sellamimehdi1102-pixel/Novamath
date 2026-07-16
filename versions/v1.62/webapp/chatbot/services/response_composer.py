"""
Assemble une réponse locale : choisit une variante de formulation
(template_library.py) pour l'intention, résout les variables réelles
(variable_resolver.py) dedans, puis habille le résultat selon le mode et la
longueur actifs (chatbot_settings) — même esprit que prompt_builder.py pour
le LLM, mais appliqué à un texte déjà généré plutôt qu'à une instruction.
"""
import random

from . import template_library

_MODE_TIP = "N'hésite pas à me demander plus de détails sur un chapitre en particulier."


class _SafeDict(dict):
    """Une variable manquante reste visible (`{nom}`) plutôt que de faire
    planter tout le message — ne devrait jamais arriver en pratique
    (variable_resolver.py couvre toutes les clés utilisées par les
    templates), mais reste sans risque si un template est étendu plus tard
    sans mettre à jour le resolver du même coup."""

    def __missing__(self, key):
        return f"{{{key}}}"


def _apply_mode(text, mode, variables):
    if mode == "visuel" and "progression" in variables:
        try:
            pct = int(variables.get("progression") or 0)
        except (TypeError, ValueError):
            pct = 0
        filled = max(0, min(10, pct // 10))
        bar = "█" * filled + "░" * (10 - filled)
        return f"{text}\n\n[{bar}] {pct}%"
    if mode == "professeur":
        return f"{text}\n\n{_MODE_TIP}"
    return text


def apply_length(text, response_length):
    if response_length == "court":
        first = text.split(". ")[0].split("\n")[0]
        return first if first.endswith((".", "!", "?")) else f"{first}."
    if response_length == "detaille":
        return f"{text} N'hésite pas à me demander plus de détails sur un chapitre précis."
    return text


def compose(intent, variables, chatbot_settings=None):
    """Renvoie une réponse locale prête à afficher, ou None si aucune
    variante n'existe pour cette intention (appelant doit alors basculer sur
    le fallback LLM)."""
    chatbot_settings = chatbot_settings or {}
    variants = template_library.TEMPLATES.get(intent)
    if not variants:
        return None
    template = random.choice(variants)
    text = template.format_map(_SafeDict(variables))
    text = _apply_mode(text, chatbot_settings.get("mode"), variables)
    text = apply_length(text, chatbot_settings.get("responseLength", "normal"))
    return text
