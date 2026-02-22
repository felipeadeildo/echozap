from typing import Literal

from pydantic import BaseModel
from pydantic_ai import RunContext

from agents.base import WhatsAppDeps, make_agent


class NotificationDecision(BaseModel):
    """Result of the notification classifier agent."""

    should_notify: bool
    urgency: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    summary: str
    reason: str
    suggested_response: str | None = None


classifier_agent = make_agent(
    output_type=NotificationDecision,
    deps_type=WhatsAppDeps,
    instructions="""
    Você é um filtro inteligente de notificações de WhatsApp.
    Analise a mensagem e o contexto da conversa.
    Decida se o usuário precisa ser notificado agora via Alexa.
    Seja conservador: prefira não notificar a interromper desnecessariamente.
    Responda sempre em pt-BR.
    """,
)


@classifier_agent.tool
async def get_vip_contacts(ctx: RunContext[WhatsAppDeps]) -> list[str]:
    """Return the list of VIP contact JIDs from user preferences."""
    return ctx.deps.preferences.vip_contacts_list()


@classifier_agent.tool
async def get_urgent_keywords(ctx: RunContext[WhatsAppDeps]) -> list[str]:
    """Return the list of urgent keywords from user preferences."""
    return ctx.deps.preferences.urgent_keywords_list()


@classifier_agent.tool
async def is_quiet_hours(ctx: RunContext[WhatsAppDeps]) -> bool:
    """Check whether the current time falls within the user's quiet hours."""
    return ctx.deps.preferences.is_quiet_hours_now()
