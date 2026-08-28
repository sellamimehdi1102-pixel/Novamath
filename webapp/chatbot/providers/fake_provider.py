"""
Filet de sécurité de TOUT dernier recours de NovaMath : ne contacte AUCUNE
API, n'est utilisé QUE si le fournisseur IA réellement actif (voir
provider_manager.select_llm_for_user) a échoué à l'usage pour ce message
précis — jamais un choix visible ou compris par l'élève. Respecte exactement
le même contrat que les vrais fournisseurs IA (ChatProvider —
stream_chat/health/available_models/current_model).

IMPORTANT (voir audit "le chatbot abandonne trop vite" du 2026-07-26) :
l'élève ne doit JAMAIS savoir qu'il existe plusieurs fournisseurs IA, lequel
est actif, ni qu'un filet de sécurité local existe — aucun texte ci-dessous ne
doit jamais nommer un fournisseur (Gemini/Claude/Ollama/...), une API, ou
mentionner "intelligence artificielle"/"sans IA". Toute formulation reste
naturelle et pédagogique, comme si NovaMath répondait lui-même.

Audit du mode dégradé (2026-07-26) : CE fournisseur n'est plus responsable de
construire une réponse pédagogique à partir du Current Learning Context/de
l'historique/de la banque d'exercices — c'est désormais le rôle de
degraded_mode_service.py (accès aux VRAIS objets notion, pas seulement au
texte déjà figé de `system`), appelé par llm_fallback_service.generate()
AVANT de retomber ici. Si ce module est atteint, c'est qu'absolument aucun
sujet n'a pu être déterminé (aucun chapitre, aucune notion, aucun historique
exploitable, aucune recherche floue, aucun exercice) — seule exception :
une mention "@" explicite (ressource déjà résolue avec certitude, jamais une
supposition) reste affichée ici, cas différent d'"essayer de deviner le
sujet"."""
import random

from .base import ChatProvider

MODEL_ID = "moteur-novamath"

# Marqueur du bloc construit par mentions_service.build_grounding_block() —
# présent dans `system` dès qu'une mention "@" ou un exercice résolu par
# intent_service (Phase H) doit primer sur la recherche générique. Sans ce
# repérage, FakeProvider ignorait entièrement `system` et refaisait sa propre
# recherche sur le message brut, rendant invisible tout le mécanisme de
# grounding tant qu'aucun vrai fournisseur IA n'est configuré (cas par défaut).
GROUNDING_MARKER = "RESSOURCES MENTIONNÉES PAR L'ÉLÈVE"
# Encore utilisé pour délimiter la FIN du bloc de grounding ci-dessus (le
# bloc RAG générique, qui peut suivre dans `system`, ne doit jamais être
# inclus dans la ressource explicitement mentionnée) — la construction d'une
# réponse à PARTIR de ce bloc RAG est retirée, voir degraded_mode_service.py.
RAG_MARKER = "\n\nEXTRAITS DE COURS NOVAMATH PERTINENTS"

# Plusieurs formulations pour ne jamais répéter exactement le même message
# (même philosophie que get_exemple()/response_composer.py : jamais deux
# fois la même réponse). Jamais de référence technique — voir docstring.
# Audit "le chatbot ne doit jamais donner l'impression d'abandonner"
# (2026-07-26, épisode 2) : dialogue naturel et chaleureux, jamais un ton
# froid de type "je n'ai pas trouvé" — ce message ne doit apparaître qu'en
# tout dernier recours, quand degraded_mode_service.py n'a lui-même rien pu
# déterminer (aucun chapitre/notion/historique/RAG/exercice exploitable).
NO_MATCH_ANSWERS = (
    "Bien sûr. Peux-tu me dire de quel chapitre ou de quelle notion tu parles ?",
    "Je veux bien t'aider. Dis-moi simplement le nom du chapitre, ou colle ton exercice.",
    "Je ne suis pas certain du sujet dont tu parles. Peux-tu me donner un peu plus de contexte ?",
)


class FakeProvider(ChatProvider):
    def __init__(self, model=None, api_key=None):
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
        ])

    def _assemble_answer(self, user_message, system=None):
        # Le mode dégradé (degraded_mode_service.py, appelé par
        # llm_fallback_service.generate() avant ce provider) a déjà tenté
        # Current Learning Context/historique/RAG/banque d'exercices — s'il
        # n'a rien trouvé, aucune reconstruction supplémentaire n'est
        # possible à partir du seul texte de `system` (voir docstring du
        # module). Seule la ressource "@" déjà résolue avec certitude
        # (jamais une supposition) reste affichée ici.
        grounded = self._answer_from_grounding(system)
        if grounded is not None:
            return grounded
        return random.choice(NO_MATCH_ANSWERS)

    def stream_chat(self, messages, system, temperature=0.7, max_tokens=1024):
        user_message = self._last_user_message(messages)
        yield self._assemble_answer(user_message, system)
