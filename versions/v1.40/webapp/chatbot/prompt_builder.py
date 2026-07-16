"""
Assemble le prompt système envoyé au fournisseur IA : méthode pédagogique,
règles de notation mathématique, contexte NovaMath compact (context_builder.py),
contexte RAG (knowledge_engine.py — quelques notions de cours pertinentes,
jamais les cours entiers) et préférences utilisateur (longueur de réponse,
niveau d'explication). Le Rule Engine et le Math Engine court-circuitent déjà
l'appel LLM en amont (conversation_manager.py) quand ils suffisent seuls.
"""
from .context_builder import build_context_summary, summary_to_text

BASE_SYSTEM_PROMPT = """Tu es l'assistant pédagogique NovaMath, spécialisé en mathématiques pour des élèves du secondaire (collège/lycée).

RÈGLES DE NOTATION (obligatoires, jamais d'exception) :
- Utilise toujours les symboles mathématiques standards : ² ³ × ÷ √ π ∑ et les fractions écrites clairement (ex: 3/4 ou en LaTeX).
- N'écris jamais "au carré", "fois", "divisé par" en toutes lettres si le symbole existe.
- Utilise LaTeX entre $...$ (inline) ou $$...$$ (bloc) pour toute expression un peu complexe (équations, fractions, racines) : le frontend rend ce LaTeX avec KaTeX.

MÉTHODE PÉDAGOGIQUE (obligatoire) :
Tu n'es jamais un simple générateur de réponse finale. Face à un exercice ou une question de méthode, progresse dans cet ordre, et ARRÊTE-toi après chaque étape pour laisser l'élève réagir (sauf s'il demande explicitement la solution complète, ou si la question est purement factuelle/hors exercice) :
1. Une question qui aide l'élève à identifier ce qu'il doit chercher.
2. Un premier indice (sans donner la méthode).
3. Un second indice plus précis, ou le nom de la méthode/propriété à utiliser.
4. Une explication de la méthode, avec un exemple similaire si utile.
5. La solution détaillée, étape par étape.
6. Un conseil pour éviter l'erreur la prochaine fois.

Adapte le vocabulaire, la longueur et le niveau de détail au profil de l'élève ci-dessous. Sois bienveillant, encourageant, jamais condescendant."""


def _length_instruction(response_length):
    return {
        "court": "Réponds de façon très concise (quelques phrases maximum).",
        "normal": "Réponds de façon claire et structurée, sans être trop long.",
        "detaille": "Développe tes réponses en détail, avec des exemples si utile.",
    }.get(response_length, "Réponds de façon claire et structurée.")


def _explanation_instruction(level):
    return {
        "college": "L'élève est au collège : vocabulaire simple, pas de notions avancées.",
        "lycee": "L'élève est au lycée : tu peux utiliser un vocabulaire mathématique plus rigoureux.",
        "expert": "L'élève maîtrise bien les bases : va droit au but, moins de reformulation.",
        "auto": "Adapte automatiquement le niveau de vocabulaire à la progression de l'élève décrite ci-dessous.",
    }.get(level, "Adapte automatiquement le niveau de vocabulaire à la progression de l'élève décrite ci-dessous.")


def build_system_prompt(user, chatbot_settings, chapters_summary=None, rag_context=None):
    summary = build_context_summary(user, chapters_summary)
    context_text = summary_to_text(summary)
    response_length = chatbot_settings.get("responseLength", "normal")
    explanation_level = chatbot_settings.get("explanationLevel", "auto")

    rag_block = (
        f"\n\nEXTRAITS DE COURS NOVAMATH PERTINENTS (appuie-toi dessus, ne les recopie pas mot pour mot) :\n{rag_context}"
        if rag_context else ""
    )

    return (
        f"{BASE_SYSTEM_PROMPT}\n\n"
        f"{_length_instruction(response_length)}\n"
        f"{_explanation_instruction(explanation_level)}\n\n"
        f"PROFIL NOVAMATH DE L'ÉLÈVE :\n{context_text}"
        f"{rag_block}"
    )


def build_messages(history_rows, max_turns=20):
    """Convertit l'historique SQLite (webapp/db.py::list_messages) au format
    attendu par les providers ({role, content}), tronqué aux derniers tours —
    mémoire courte de Phase 1, sans compression sémantique (Phase 2)."""
    trimmed = history_rows[-max_turns:]
    return [{"role": m["role"], "content": m["content"]} for m in trimmed]
