from pydantic import BaseModel
from pydantic_ai import Agent

from agents.base import SONNET, WhatsAppDeps


class ReplyOption(BaseModel):
    text: str
    tone: str  # "formal" | "casual" | "rápido"
    reasoning: str


class ReplyOptions(BaseModel):
    options: list[ReplyOption]  # sempre 3 opções


reply_generator_agent = Agent(
    SONNET,
    output_type=ReplyOptions,
    deps_type=WhatsAppDeps,
    instructions="""
    Gere 3 opções de resposta para o WhatsApp, variando em tom:
    uma formal, uma casual e uma curta/direta.
    As respostas devem ser naturais, humanas, contextualizadas.
    Idioma: pt-BR.
    """,
)
