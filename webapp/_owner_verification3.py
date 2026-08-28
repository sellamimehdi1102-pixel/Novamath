"""
Vérification du CHEMIN RÉEL d'appel LLM (llm_fallback_service.generate — le
point de sortie unique vers le fournisseur IA actif, appelé par
conversation_manager.py exactement à cet endroit une fois les moteurs locaux
épuisés). Contourne délibérément local_knowledge_service/search_service
(étapes AVANT ce point, qui répondent déjà localement à des questions de
cours — confirmé par _owner_verification.py) pour garantir un VRAI appel
réseau vers le provider réellement sélectionné selon le plan effectif de
test Owner, avec écriture réelle dans ai_request_logs/ai_provider_usage —
exactement le mécanisme réel de production, pas une simulation.
"""
import json
import time
from dotenv import load_dotenv
load_dotenv()

import ai_provider_service
import db
import owner_test_plan_service
from chatbot.services import llm_fallback_service

OWNER_ID = 1543


def run_real_call(user, plan_label):
    call_info = {}
    messages = [{"role": "user", "content": "Bonjour"}]
    system_prompt = "Tu es un tuteur de mathématiques bref et rigoureux."
    chatbot_settings = {}
    chunks = []
    t0 = time.perf_counter()
    for chunk in llm_fallback_service.generate(
        messages, system_prompt, chatbot_settings, user=user, call_info=call_info,
    ):
        chunks.append(chunk)
    elapsed = time.perf_counter() - t0
    text = "".join(chunks)

    # Écriture réelle dans ai_provider_usage/ai_request_logs — même appel
    # que conversation_manager._log_llm_call_details() en production.
    usage = call_info.get("usage") or {}
    ai_provider_service.record_llm_usage(
        call_info.get("provider"), call_info.get("model"), usage,
        success=call_info.get("success", True), response_time_ms=call_info.get("elapsed_ms"),
        error_type=call_info.get("error_type"), error_message=call_info.get("error_message"),
        is_fallback=bool(call_info.get("fallback_from")),
    )
    db.create_ai_request_log(
        user["id"], None, call_info.get("provider", "?"), call_info.get("model", "?"),
        input_tokens=usage.get("prompt_tokens", 0),
        output_tokens=usage.get("completion_tokens", 0),
        total_tokens=usage.get("total_tokens", 0),
        response_time_ms=int(call_info.get("elapsed_ms") or 0),
        success=call_info.get("success", True), fallback=bool(call_info.get("fallback_from")),
    )

    print("=" * 60)
    print("PLAN:", plan_label)
    print("call_info:", json.dumps({k: v for k, v in call_info.items() if k != "usage"}, ensure_ascii=False, default=str))
    print("usage:", call_info.get("usage"))
    print("temps mesuré (script) :", round(elapsed, 3), "s")
    print("réponse reçue (200 premiers caractères) :", text[:200].replace("\n", " "))


def main():
    for plan in ("free", "premium", "ultra"):
        ok, err = owner_test_plan_service.set_test_plan({"id": OWNER_ID}, plan)
        assert ok, err
        user = db.get_user_by_id(OWNER_ID)
        run_real_call(user, plan)

    ok, err = owner_test_plan_service.set_test_plan({"id": OWNER_ID}, None)
    assert ok, err
    print("=" * 60)
    print("Reset effectué — test_plan =", owner_test_plan_service.get_test_plan(db.get_user_by_id(OWNER_ID)))


if __name__ == "__main__":
    main()
