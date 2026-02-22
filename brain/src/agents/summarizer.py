from pydantic import BaseModel
from pydantic_ai import Agent

from agents.base import SONNET, WhatsAppDeps


class ConversationSummary(BaseModel):
    """Structured summary of a WhatsApp conversation, optimized for voice output."""

    summary: str
    key_points: list[str]
    action_required: bool
    suggested_actions: list[str]


summarizer_agent = Agent(
    SONNET,
    output_type=ConversationSummary,
    deps_type=WhatsAppDeps,
    instructions="""
    Resuma a conversa de WhatsApp de forma clara e natural, como se fosse
    falar para alguém que vai ouvir via assistente de voz.
    Seja conciso. Priorize informação acionável.
    Idioma: pt-BR.
    """,
)
