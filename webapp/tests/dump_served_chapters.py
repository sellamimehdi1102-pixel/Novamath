"""Imprime (JSON, sortie standard) la réponse réelle de /api/chapters pour les
cinq classes, telle que la reçoit exercice.js : ids et difficultés des
exercices servis par notion. Utilisé par
static/js/__tests__/exercice-adaptive-classes.test.js pour valider le moteur
adaptatif sur les vraies banques servies (aucun compte, aucun quota : client
de test Flask, lecture seule).
"""
import json
import logging
import os
import sys

logging.disable(logging.CRITICAL)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import server  # noqa: E402

CLASSES = ("quatrieme", "troisieme", "seconde", "premiere", "premiere_specifique")

if __name__ == "__main__":
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
    sys.stdout.write(json.dumps(out, ensure_ascii=False))
