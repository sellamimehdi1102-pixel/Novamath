"""
Anti-répétition — Phase 4, Mission 6.

Mesure (jamais ne génère de texte automatiquement — voir justification dans
le rapport de phase) la diversité RÉELLE des pools de formulations utilisés
par `knowledge_response_composer.py` (blocs de forme et leads de blocs) et
`template_library.py` (variantes de données Dashboard) :
- nombre de variantes disponibles par pool ;
- nombre RÉELLEMENT utilisées sur N tirages simulés (même mécanisme de choix
  aléatoire que le code réel, `random.choice`, jamais une nouvelle logique) ;
- pools sous un seuil de diversité (candidats à enrichir en priorité).

N'invente et n'ajoute aucune formulation : une variante pédagogique de
mauvaise qualité générée automatiquement serait pire qu'un pool restreint
mais correct — voir recommandations du rapport de phase.
"""
import random
from collections import Counter

from . import knowledge_response_composer, template_library

# Seuil sous lequel un pool est considéré comme insuffisamment varié —
# 3 variantes est le minimum déjà pratiqué ailleurs dans le projet (voir
# template_library.py, response_composer.py).
MIN_RECOMMENDED_VARIANTS = 3


def _all_pools():
    pools = dict(knowledge_response_composer.VARIANT_POOLS)
    for intent, variants in template_library.TEMPLATES.items():
        pools[f"template_{intent}"] = variants
    return pools


def audit_pool_size():
    """Mission 6, partie statique : nombre de variantes disponibles par pool,
    sans simulation — repère immédiatement les pools trop petits."""
    return {
        name: {
            "available": len(variants),
            "sous_le_minimum_recommande": len(variants) < MIN_RECOMMENDED_VARIANTS,
        }
        for name, variants in _all_pools().items()
    }


def simulate_usage(n=200, seed=None):
    """Tire `n` fois dans chaque pool (même mécanisme que le code réel,
    `random.choice`) et mesure la diversité réellement observée — un pool à 5
    variantes peut très bien n'en montrer que 2 sur un petit échantillon par
    pur hasard, ce que cette simulation permet de détecter concrètement
    plutôt que de le supposer."""
    rng = random.Random(seed)
    results = {}
    for name, variants in _all_pools().items():
        picks = [rng.choice(variants) for _ in range(n)]
        counts = Counter(picks)
        distinct_used = len(counts)
        available = len(variants)
        most_common_text, most_common_count = counts.most_common(1)[0]
        results[name] = {
            "available": available,
            "distinct_used": distinct_used,
            "diversity_ratio": round(distinct_used / available, 2) if available else 0.0,
            "repetition_rate_pct": round(100 * most_common_count / n, 1),
            "most_repeated": most_common_text,
        }
    return results


def low_diversity_pools(n=200, seed=None, ratio_threshold=0.5, repetition_threshold_pct=50.0):
    """Mission 6 : pools à enrichir en priorité — diversité réellement
    observée sous le seuil, OU une formulation qui revient trop souvent."""
    usage = simulate_usage(n=n, seed=seed)
    flagged = []
    for name, stats in usage.items():
        if stats["diversity_ratio"] < ratio_threshold or stats["repetition_rate_pct"] > repetition_threshold_pct:
            flagged.append({"pool": name, **stats})
    flagged.sort(key=lambda p: p["diversity_ratio"])
    return flagged


def format_report(n=200, seed=None):
    sizes = audit_pool_size()
    usage = simulate_usage(n=n, seed=seed)
    low = low_diversity_pools(n=n, seed=seed)
    lines = [f"Audit de diversité ({len(sizes)} pools, {n} tirages simulés) :", ""]
    for name in sorted(sizes):
        s, u = sizes[name], usage[name]
        alerte = " [SOUS LE MINIMUM RECOMMANDÉ]" if s["sous_le_minimum_recommande"] else ""
        lines.append(
            f"  {name:30s} : {s['available']} variante(s) disponible(s), "
            f"{u['distinct_used']} utilisée(s) sur {n} tirages "
            f"(ratio {u['diversity_ratio']}, répétition max {u['repetition_rate_pct']}%){alerte}"
        )
    lines.append("")
    lines.append(f"{len(low)} pool(s) à enrichir en priorité : {[p['pool'] for p in low]}")
    return "\n".join(lines)
