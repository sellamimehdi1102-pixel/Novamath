import json
import secrets
import time
from dotenv import load_dotenv
load_dotenv()

import db
import server

OWNER_ID = 1543


def make_client_for(user_id):
    client = server.app.test_client()
    token = db.create_session(user_id, days=1, user_agent="owner-verification-script-2")
    csrf = secrets.token_urlsafe(24)
    client.set_cookie("nm_session", token)
    client.set_cookie("nm_csrf", csrf)
    return client, {"X-CSRF-Token": csrf}


def try_prompt(client, headers, prompt):
    conv = client.post("/api/chatbot/conversations", headers=headers).get_json()["conversation"]
    conv_id = conv["id"]
    resp = client.post(
        f"/api/chatbot/conversations/{conv_id}/messages",
        json={"message": prompt, "class_level": "seconde"},
        headers=headers,
    )
    msgs = db.list_messages(conv_id)
    assistant = [m for m in msgs if m["role"] == "assistant"]
    engine = assistant[-1]["engine"] if assistant else None
    text = assistant[-1]["content"] if assistant else None
    return conv_id, resp.status_code, engine, text


def main():
    client, headers = make_client_for(OWNER_ID)
    prompts = [
        "Écris-moi un petit haïku totalement original sur la pluie qui tombe sur Paris un dimanche.",
        "Peux-tu inventer une courte blague absurde sur un chat qui apprend à faire du vélo ?",
        "Résume-moi en 3 phrases originales pourquoi tu aimes bien discuter de maths, avec ton propre style.",
    ]
    for p in prompts:
        conv_id, status, engine, text = try_prompt(client, headers, p)
        print("=" * 60)
        print("PROMPT:", p)
        print("HTTP:", status, "| conv:", conv_id, "| engine:", engine)
        print("REPONSE (200 premiers car.):", (text or "")[:200])


if __name__ == "__main__":
    main()
