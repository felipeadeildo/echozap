"""Context analyzer agent — stub para fase futura."""

from pydantic import BaseModel
from pydantic_ai import Agent

from agents.base import SONNET, WhatsAppDeps


class ConversationContext(BaseModel):
    topic: str
    sentiment: str  # positive | neutral | negative
    participants: list[str]
    is_ongoing: bool


context_analyzer_agent = Agent(
    SONNET,
    output_type=ConversationContext,
    deps_type=WhatsAppDeps,
    instructions="""
    Analise o contexto geral da conversa de WhatsApp.
    Identifique o tópico principal, sentimento e se a conversa está em andamento.
    Idioma: pt-BR.
    """,
)
