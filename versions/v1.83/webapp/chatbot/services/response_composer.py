"""
Assemble une réponse locale : choisit une variante de formulation
(template_library.py) pour l'intention, résout les variables réelles
(variable_resolver.py) dedans, puis habille le résultat selon le mode et la
longueur actifs (chatbot_settings) — même esprit que prompt_builder.py pour
le LLM, mais appliqué à un texte déjà généré plutôt qu'à une instruction.

`student_context` (optionnel, Student Context Resolver v2) : permet d'éviter
de répéter mot pour mot une formulation déjà utilisée dans la conversation en
cours, via phrasing_memory.py — même mécanisme que
knowledge_response_composer.py, mutualisé plutôt que dupliqué (audit ton/
personnalité : ce module en était jusqu'ici dépourvu)."""
import random

from . import phrasing_memory, template_library

_MODE_TIP = "N'hésite pas à me demander plus de détails sur un chapitre en particulier."
# Reformulations variées du même conseil pour la longueur "detaille" — un
# seul texte fixe auparavant, désormais tiré via phrasing_memory comme le
# reste des formulations de forme (cf. audit : "aucune répétition visible").
_DETAILLE_TIP_VARIANTS = [
    "N'hésite pas à me demander plus de détails sur un chapitre précis.",
    "Dis-moi si tu veux que j'aille plus loin sur un point en particulier.",
    "Je peux approfondir n'importe lequel de ces points si tu veux.",
]


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
        return f"{text}\n\n[{bar}] {pct}%", False
    if mode == "professeur":
        return f"{text}\n\n{_MODE_TIP}", True
    return text, False


def apply_length(text, response_length, rng=None, avoid_blob="", already_has_tip=False):
    """`rng`/`avoid_blob` (optionnels, Student Context Resolver v2) : évitent
    de répéter mot pour mot le même rappel d'une réponse à l'autre — sans eux
    (appelants existants type `local_knowledge_service._try_exercise_answer`),
    une variante est simplement tirée au hasard, comportement inchangé.
    `already_has_tip` : le mode "professeur" a déjà ajouté une invitation à
    creuser (_MODE_TIP) juste au-dessus dans compose() — ne pas en superposer
    une seconde, quasi identique (bug constaté à l'audit ton/personnalité sur
    la combinaison mode=professeur + longueur=detaille). Transmis
    explicitement par l'appelant plutôt que redéduit du texte : les seuls
    autres appelants (ex. local_knowledge_service) ne passent jamais par
    `_apply_mode`, donc `already_has_tip` reste `False` par défaut pour eux."""
    if response_length == "court":
        first = text.split(". ")[0].split("\n")[0]
        return first if first.endswith((".", "!", "?")) else f"{first}."
    if response_length == "detaille":
        if already_has_tip:
            return text
        rng = rng or random.Random()
        tip = phrasing_memory.pick_rendered(rng, _DETAILLE_TIP_VARIANTS, avoid_blob)
        return f"{text} {tip}"
    return text


def compose(intent, variables, chatbot_settings=None, student_context=None):
    """Renvoie une réponse locale prête à afficher, ou None si aucune
    variante n'existe pour cette intention (appelant doit alors basculer sur
    le fallback LLM)."""
    chatbot_settings = chatbot_settings or {}
    variants = template_library.TEMPLATES.get(intent)
    if not variants:
        return None
    rng = random.Random()
    avoid = phrasing_memory.recent_assistant_text(student_context)
    # pick_rendered rend CHAQUE variante avec les vraies données avant de
    # choisir — jamais de comparaison sur un template brut encore truffé de
    # {variables} (même mécanisme, sans exception, que knowledge_response_
    # composer.py — voir phrasing_memory.py pour la justification complète).
    text = phrasing_memory.pick_rendered(rng, variants, avoid, mapping=_SafeDict(variables))
    text, has_tip = _apply_mode(text, chatbot_settings.get("mode"), variables)
    text = apply_length(
        text, chatbot_settings.get("responseLength", "normal"), rng=rng, avoid_blob=avoid, already_has_tip=has_tip,
    )
    return text
