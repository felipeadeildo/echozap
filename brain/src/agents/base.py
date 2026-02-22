from dataclasses import dataclass

from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings

from config import settings
from database.models import UserPreferences


def make_agent[OutputT, DepsT](
    *,
    output_type: type[OutputT],
    deps_type: type[DepsT],
    instructions: str,
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> Agent[DepsT, OutputT]:
    """Factory para criar agents com model e settings vindos da config."""
    return Agent(  # type: ignore[return-value]
        settings.ai_model,
        output_type=output_type,
        deps_type=deps_type,
        instructions=instructions,
        model_settings=ModelSettings(temperature=temperature, max_tokens=max_tokens),
        defer_model_check=True,
    )


@dataclass
class WhatsAppDeps:
    """Shared dependencies injected into pydantic-ai agent tools."""

    chat_jid: str
    recent_messages: list[dict]
    preferences: UserPreferences
    whatsapp_client: object  # WhatsAppClient
