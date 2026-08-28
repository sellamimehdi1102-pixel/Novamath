"""
Contrat unique que tout fournisseur IA doit respecter. Le reste du code
(conversation_manager.py notamment) ne dépasse jamais cette interface : changer
de fournisseur (OpenAI, Gemini, DeepSeek, un serveur local...) revient à
écrire une nouvelle classe ici et à l'enregistrer dans provider_manager.py,
sans toucher à quoi que ce soit d'autre.
"""
from abc import ABC, abstractmethod


class ProviderUnavailableError(RuntimeError):
    """Erreur commune levée par un ChatProvider quand un appel échoue —
    chaque fournisseur (Gemini/Anthropic/Ollama) définit sa propre sous-classe
    (GeminiConnectionError, etc.) mais hérite toujours de celle-ci, pour que
    provider_manager.py puisse traiter l'indisponibilité de façon générique
    quel que soit le fournisseur.

    `durable` distingue deux familles bien différentes :
    - True  : panne qui ne se résoudra pas toute seule à court terme (quota
      Free Tier à 0, clé invalide, accès refusé, crédit épuisé) — voir
      provider_manager.mark_unavailable(), qui met alors ce couple
      (provider, modèle) en cache d'indisponibilité pour ne plus le
      retenter à chaque message tant que le cache est actif.
    - False (défaut) : panne transitoire (réseau, 5xx, timeout, rafale de
      requêtes qui se résorbe d'elle-même) — jamais mise en cache, retentée
      normalement dès le message suivant.

    `ttl_seconds` (optionnel) : durée de vie du cache d'indisponibilité à
    utiliser pour CETTE panne précise, si `durable=True` — remplace le TTL
    fixe par défaut de provider_manager.UNAVAILABILITY_TTL_SECONDS (15 min).
    Un fournisseur qui distingue plusieurs familles de pannes durables (ex :
    GeminiProvider — quota RPM/TPM vs quota journalier vs clé invalide, voir
    gemini_provider.py::_classify_error) fixe ici la durée adaptée à chacune ;
    `None` (défaut) laisse provider_manager appliquer son TTL générique."""

    def __init__(self, message, durable=False, ttl_seconds=None):
        super().__init__(message)
        self.durable = durable
        self.ttl_seconds = ttl_seconds


class ChatProvider(ABC):
    # Rempli par stream_chat(), quand le fournisseur expose un décompte réel
    # de tokens consommés (voir gemini_provider.py/anthropic_provider.py/
    # ollama_provider.py) : {"prompt_tokens", "completion_tokens", "total_tokens"}.
    # None si le fournisseur ne l'expose pas (FakeProvider : aucun appel réel).
    last_usage = None

    # Rempli par stream_chat() quand le fournisseur expose la raison d'arrêt
    # du modèle (voir gemini_provider.py/anthropic_provider.py) : "STOP"/
    # "end_turn" (fin normale), "MAX_TOKENS"/"max_tokens" (réponse tronquée
    # par max_output_tokens/max_tokens — voir llm_fallback_service qui
    # journalise ce cas). None si non exposé ou fournisseur sans appel réel.
    last_finish_reason = None

    @abstractmethod
    def stream_chat(self, messages, system, temperature=0.7, max_tokens=1024):
        """Doit retourner un générateur de fragments de texte (str), au fil de
        l'arrivée de la réponse du modèle (streaming)."""
        raise NotImplementedError

    def health(self):
        """Renvoie {"ok": bool, "detail": str}. Implémentation par défaut
        optimiste (providers cloud sans endpoint de santé dédié) — les
        providers locaux (Ollama) la redéfinissent avec un vrai test réseau."""
        return {"ok": True, "detail": ""}

    def available_models(self):
        """Dict {id_modele: libellé affichable}. Par défaut vide (le
        provider_manager retombe alors sur son propre catalogue statique)."""
        return {}

    def current_model(self):
        return getattr(self, "_model", None)

    def has_credentials(self):
        """True si le provider dispose de ce qu'il faut pour émettre un appel
        réel (clé API...). Par défaut True (providers locaux comme Ollama, ou
        FakeProvider, n'ont rien à configurer) — les providers cloud à clé
        (AnthropicProvider, GeminiProvider) la redéfinissent."""
        return True

    def switch_model(self, model):
        """Change le modèle utilisé par cette instance sans recréer le
        provider. Par défaut, modifie simplement l'attribut interne."""
        self._model = model
