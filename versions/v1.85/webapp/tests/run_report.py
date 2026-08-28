"""
Exécute toute la suite fonctionnelle (test_canonical_ids, test_chatbot_routing,
test_non_regression), mesure la performance du résolveur, et imprime un
rapport structuré : nombre total de tests, taux de réussite, anomalies,
performance. Sort avec un code non nul si le taux de réussite n'est pas 100%.

Usage : python -m tests.run_report (depuis webapp/).
"""
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import canonical_ids


def _run_suite():
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=str(Path(__file__).resolve().parent), pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result


def _measure_performance():
    """Temps moyen de resolve_topic_id sur le chemin exact (lookup direct) et
    sur le chemin flou (repli difflib, plus coûteux)."""
    n = 500

    t0 = time.perf_counter()
    for _ in range(n):
        canonical_ids.resolve_topic_id("Puissances entières relatives", chapter_id="Chapitre_1")
    exact_ms = (time.perf_counter() - t0) * 1000 / n

    t0 = time.perf_counter()
    for _ in range(n):
        canonical_ids.resolve_topic_id("puissance entiere relatve", chapter_id="Chapitre_1")
    fuzzy_ms = (time.perf_counter() - t0) * 1000 / n

    t0 = time.perf_counter()
    for _ in range(n):
        canonical_ids.resolve_chapter_id("chapitre 1")
    chapter_ms = (time.perf_counter() - t0) * 1000 / n

    return {"exact_ms": exact_ms, "fuzzy_ms": fuzzy_ms, "chapter_ms": chapter_ms, "n": n}


def main():
    print("=" * 70)
    print("SUITE FONCTIONNELLE — Knowledge Engine v2 / Canonical IDs")
    print("=" * 70)
    result = _run_suite()

    total = result.testsRun
    failed = len(result.failures)
    errored = len(result.errors)
    passed = total - failed - errored
    rate = (passed / total * 100) if total else 0.0

    perf = _measure_performance()

    print()
    print("=" * 70)
    print("RAPPORT FINAL")
    print("=" * 70)
    print(f"Tests exécutés     : {total}")
    print(f"Réussis            : {passed}")
    print(f"Échoués            : {failed}")
    print(f"Erreurs            : {errored}")
    print(f"Taux de réussite   : {rate:.1f}%")
    print()
    print("Performance du résolveur (canonical_ids.py, moyenne sur {} appels) :".format(perf["n"]))
    print(f"  - resolve_topic_id (lookup exact)  : {perf['exact_ms']:.4f} ms/appel")
    print(f"  - resolve_topic_id (repli flou)    : {perf['fuzzy_ms']:.4f} ms/appel")
    print(f"  - resolve_chapter_id               : {perf['chapter_ms']:.4f} ms/appel")
    print()
    if failed or errored:
        print(f"{failed + errored} ANOMALIE(S) RESTANTE(S) :")
        for test, trace in result.failures + result.errors:
            print(f"  - {test}")
        sys.exit(1)
    print("Aucune anomalie. Taux de réussite 100%.")


if __name__ == "__main__":
    main()
