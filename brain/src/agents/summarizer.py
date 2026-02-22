from pydantic import BaseModel

from agents.base import WhatsAppDeps, make_agent


class ConversationSummary(BaseModel):
    """Structured summary of a WhatsApp conversation, optimized for voice output."""

    summary: str
    key_points: list[str]
    action_required: bool
    suggested_actions: list[str]


summarizer_agent = make_agent(
    output_type=ConversationSummary,
    deps_type=WhatsAppDeps,
    instructions="""
    Resuma a conversa de WhatsApp de forma clara e natural, como se fosse
    falar para alguém que vai ouvir via assistente de voz.
    Seja conciso. Priorize informação acionável.
    Idioma: pt-BR.
    """,
)
