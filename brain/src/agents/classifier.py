from typing import Literal

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext

from agents.base import SONNET, WhatsAppDeps


class NotificationDecision(BaseModel):
    should_notify: bool
    urgency: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    summary: str
    reason: str
    suggested_response: str | None = None


classifier_agent = Agent(
    SONNET,
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
    return ctx.deps.preferences.vip_contacts_list()


@classifier_agent.tool
async def get_urgent_keywords(ctx: RunContext[WhatsAppDeps]) -> list[str]:
    return ctx.deps.preferences.urgent_keywords_list()


@classifier_agent.tool
async def is_quiet_hours(ctx: RunContext[WhatsAppDeps]) -> bool:
    return ctx.deps.preferences.is_quiet_hours_now()
