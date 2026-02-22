from dataclasses import dataclass

from pydantic_ai.models.anthropic import AnthropicModel

SONNET = AnthropicModel("claude-sonnet-4-6")


@dataclass
class WhatsAppDeps:
    """Shared dependencies injected into pydantic-ai agent tools."""

    chat_jid: str
    recent_messages: list[dict]
    preferences: object  # UserPreferences (evita import circular)
    whatsapp_client: object  # WhatsAppClient
