"""Réponse réelle de /api/chapters pour les cinq classes, telle que la reçoit
exercice.js : ids et difficultés des exercices servis par notion (client de test
Flask, lecture seule, sans compte ni quota).

Instantané versionné : static/js/__tests__/fixtures/served_chapters.json, lu par
exercice-adaptive-classes.test.js (le job frontend de la CI n'a pas Python).
test_served_chapters_fixture.py vérifie qu'il est identique à la réponse réelle.

    python tests/dump_served_chapters.py --write   # met à jour l'instantané
"""
import json
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FIXTURE = Path(__file__).resolve().parents[1] / "static" / "js" / "__tests__" / "fixtures" / "served_chapters.json"
CLASSES = ("quatrieme", "troisieme", "seconde", "premiere", "premiere_specifique")


def served_chapters() -> dict:
    import server

    client = server.app.test_client()
    out = {}
    for class_level in CLASSES:
        response = client.get(f"/api/chapters?class_level={class_level}")
        assert response.status_code == 200, (class_level, response.status_code)
        out[class_level] = [
            {"id": ch["id"], "notions_detail": [
                {"notion": n["notion"], "exercise_ids": n["exercise_ids"], "exercise_difficulties": n["exercise_difficulties"]}
                for n in ch["notions_detail"]
            ]}
            for ch in response.get_json()["chapters_meta"]
        ]
    return out


if __name__ == "__main__":
    logging.disable(logging.CRITICAL)
    data = served_chapters()
    if "--write" in sys.argv:
        FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        FIXTURE.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        print(f"Instantané écrit : {FIXTURE}")
    else:
        sys.stdout.write(json.dumps(data, ensure_ascii=False))
