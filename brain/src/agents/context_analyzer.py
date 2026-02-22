"""Context analyzer agent — stub para fase futura."""

from pydantic import BaseModel

from agents.base import WhatsAppDeps, make_agent


class ConversationContext(BaseModel):
    """Structured analysis of a WhatsApp conversation's context."""

    topic: str
    sentiment: str  # positive | neutral | negative
    participants: list[str]
    is_ongoing: bool


context_analyzer_agent = make_agent(
    output_type=ConversationContext,
    deps_type=WhatsAppDeps,
    instructions="""
    Analise o contexto geral da conversa de WhatsApp.
    Identifique o tópico principal, sentimento e se a conversa está em andamento.
    Idioma: pt-BR.
    """,
)
