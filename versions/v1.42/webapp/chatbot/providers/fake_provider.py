"""
Fournisseur par défaut de NovaMath aujourd'hui : ne contacte AUCUNE API. Il
respecte exactement le même contrat que les futurs fournisseurs IA
(ChatProvider — stream_chat/health/available_models/current_model), si bien
que basculer demain vers Anthropic/OpenAI/Gemini/Ollama ne change que le
réglage "provider" (Paramètres → Chatbot ou ProviderManager), jamais le reste
de la chaîne.

Le Rule Engine et le Math Engine ont déjà répondu en amont (voir
conversation_manager.py) pour tout ce qu'ils savent traiter sans IA. Si on
arrive jusqu'ici, c'est qu'aucun des deux n'a pu répondre seul : ce
fournisseur assemble alors la meilleure réponse possible à partir du
Knowledge Engine (extraits de cours pertinents), sans jamais inventer une
explication qu'il ne peut pas réellement produire — il est honnête sur ses
limites plutôt que de simuler une compréhension qu'il n'a pas.
"""
from .. import knowledge_engine
from .base import ChatProvider

MODEL_ID = "moteur-novamath"

NO_MATCH_ANSWER = (
    "Je n'ai pas trouvé d'information assez précise dans tes cours NovaMath pour répondre "
    "directement à cette question.\n\n"
    "Tu peux : reformuler ta question de façon plus précise (le nom d'une notion, d'un chapitre, "
    "ou coller l'énoncé d'un exercice), consulter l'onglet **Cours**, ou activer un fournisseur IA "
    "(Claude, Ollama) dans **Paramètres → Chatbot** pour une explication plus poussée."
)


class FakeProvider(ChatProvider):
    def __init__(self, model=None):
        self._model = model or MODEL_ID

    def health(self):
        return {"ok": True, "detail": ""}

    def available_models(self):
        return {MODEL_ID: "Moteur NovaMath (sans IA)"}

    def current_model(self):
        return self._model

    def _last_user_message(self, messages):
        for message in reversed(messages):
            if message.get("role") == "user":
                return message.get("content", "")
        return ""

    def _assemble_answer(self, user_message):
        # Seuil calé sur celui de knowledge_engine.try_answer_definition : en
        # dessous, le score TF-IDF ne distingue plus un vrai match d'un bruit
        # de mots communs (vérifié empiriquement — une question totalement
        # hors-sujet peut atteindre ~0.12, un vrai match dépasse largement 0.2).
        # Mieux vaut admettre ne pas savoir que citer un cours sans rapport.
        matches = knowledge_engine.search(user_message, top_k=2, min_score=0.20)
        if not matches:
            return NO_MATCH_ANSWER
        best = matches[0]
        lines = [
            f"Voici ce que dit ton cours sur **{best['title']}** *({best['chapter_title']})* :",
            "",
            best["definition"],
        ]
        if best["regles"]:
            lines.append("")
            lines.append("**Règles importantes :**")
            lines.extend(f"- {r}" for r in best["regles"])
        if best["erreurs"]:
            lines.append("")
            lines.append("**Erreurs fréquentes à éviter :**")
            lines.extend(f"- {r}" for r in best["erreurs"])
        lines.append("")
        lines.append(
            "_Réponse assemblée directement depuis tes cours, sans intelligence artificielle. "
            "Pour une explication pas-à-pas adaptée à ta question exacte, active Claude ou Ollama "
            "dans Paramètres → Chatbot._"
        )
        return "\n".join(lines)

    def stream_chat(self, messages, system, temperature=0.7, max_tokens=1024):
        user_message = self._last_user_message(messages)
        yield self._assemble_answer(user_message)
