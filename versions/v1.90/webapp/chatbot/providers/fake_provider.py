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
from .base import ChatProvider

MODEL_ID = "moteur-novamath"

# Marqueur du bloc construit par mentions_service.build_grounding_block() —
# présent dans `system` dès qu'une mention "@" ou un exercice résolu par
# intent_service (Phase H) doit primer sur la recherche générique. Sans ce
# repérage, FakeProvider ignorait entièrement `system` et refaisait sa propre
# recherche sur le message brut, rendant invisible tout le mécanisme de
# grounding tant qu'aucun vrai fournisseur IA n'est configuré (cas par défaut).
GROUNDING_MARKER = "RESSOURCES MENTIONNÉES PAR L'ÉLÈVE"
RAG_MARKER = "\n\nEXTRAITS DE COURS NOVAMATH PERTINENTS"

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

    def _answer_from_grounding(self, system):
        """Si `system` contient un bloc de ressource déjà résolue (mention "@"
        ou exercice choisi par intent_service, Phase H), la réponse doit se
        baser dessus — jamais re-deviner via une recherche générique sur le
        message brut, qui pourrait retomber sur une autre notion."""
        if not system or GROUNDING_MARKER not in system:
            return None
        block = system.split(GROUNDING_MARKER, 1)[1]
        block = block.split(RAG_MARKER, 1)[0]
        if "###" not in block:
            return None
        content = "### " + block.split("###", 1)[1].strip()
        return "\n".join([
            "Voici la ressource que tu as demandée :",
            "",
            content,
            "",
            "_Réponse assemblée directement depuis cette ressource, sans intelligence artificielle. "
            "Pour une explication pas-à-pas adaptée à ta question exacte, active Claude ou Ollama "
            "dans Paramètres → Chatbot._",
        ])

    def _answer_from_rag(self, system):
        """Si `system` contient le bloc RAG (knowledge_engine.context_block,
        déjà scopé par class_level dans conversation_manager.py AVANT l'appel
        à ce fournisseur), la réponse doit se baser dessus — jamais relancer
        une recherche ici, qui n'a aucun moyen de connaître la classe active
        (ChatProvider ne reçoit que `messages`/`system`, voir audit multi-
        classe du chatbot). Une classe scopée sans aucun résultat produit un
        `rag_block` vide côté prompt_builder (RAG_MARKER absent) : ce cas
        retombe honnêtement sur NO_MATCH_ANSWER, jamais une seconde recherche
        non scopée qui recontaminerait la réponse avec une autre classe."""
        if not system or RAG_MARKER not in system:
            return None
        block = system.split(RAG_MARKER, 1)[1]
        if "###" not in block:
            return None
        content = "### " + block.split("###", 1)[1].strip()
        return "\n".join([
            "Voici ce que dit ton cours sur ce sujet :",
            "",
            content,
            "",
            "_Réponse assemblée directement depuis tes cours, sans intelligence artificielle. "
            "Pour une explication pas-à-pas adaptée à ta question exacte, active Claude ou Ollama "
            "dans Paramètres → Chatbot._",
        ])

    def _assemble_answer(self, user_message, system=None):
        grounded = self._answer_from_grounding(system)
        if grounded is not None:
            return grounded
        from_rag = self._answer_from_rag(system)
        if from_rag is not None:
            return from_rag
        return NO_MATCH_ANSWER

    def stream_chat(self, messages, system, temperature=0.7, max_tokens=1024):
        user_message = self._last_user_message(messages)
        yield self._assemble_answer(user_message, system)
