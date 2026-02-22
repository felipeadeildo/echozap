from collections.abc import Callable, Coroutine
from typing import Any

from alexa.handlers import (
    check_messages,
    generate_reply,
    play_audio,
    read_messages,
    send_message,
    summarize,
)
from alexa.session import AlexaResponse

AsyncHandler = Callable[[dict], Coroutine[Any, Any, dict]]


async def _help(_body: dict) -> dict:
    return AlexaResponse.speak(
        "Você pode me pedir para verificar mensagens, ler mensagens, "
        "resumir conversas, gerar respostas ou enviar mensagens.",
        end_session=False,
    )


async def _stop(_body: dict) -> dict:
    return AlexaResponse.speak("Até mais!")


def _end_session(_body: dict) -> dict:
    return {"version": "1.0", "response": {}}


async def _launch(_body: dict) -> dict:
    return AlexaResponse.speak(
        "Olá! Seu WhatsApp está pronto. O que você quer fazer?",
        reprompt="Diga 'verificar mensagens' ou 'resumir conversa'.",
        end_session=False,
    )


INTENT_MAP: dict[str, AsyncHandler] = {
    "CheckMessagesIntent": check_messages.handle,
    "ReadMessagesIntent": read_messages.handle,
    "SummarizeConversationIntent": summarize.handle,
    "GenerateReplyIntent": generate_reply.handle,
    "SelectReplyIntent": generate_reply.handle_selection,
    "SendMessageIntent": send_message.handle,
    "PlayAudioIntent": play_audio.handle,
    "AMAZON.HelpIntent": _help,
    "AMAZON.StopIntent": _stop,
    "AMAZON.CancelIntent": _stop,
}


async def dispatch(body: dict) -> dict:
    """Route an Alexa request body to the appropriate intent handler."""
    request_type = body.get("request", {}).get("type", "")

    if request_type == "LaunchRequest":
        return await _launch(body)

    if request_type == "SessionEndedRequest":
        return _end_session(body)

    if request_type == "IntentRequest":
        intent_name = body["request"]["intent"]["name"]
        handler = INTENT_MAP.get(intent_name)
        if handler:
            return await handler(body)

    return AlexaResponse.speak("Não entendi. Tente novamente.")
