import logging
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
from alexa.session import AlexaResponse, SessionStore

logger = logging.getLogger(__name__)

AsyncHandler = Callable[[dict], Coroutine[Any, Any, dict]]

_NEGATIVE = {"não", "nao", "negativo", "errado", "errada", "cancelar", "cancel", "nope"}
_POSITIVE = {
    "sim",
    "yes",
    "ok",
    "confirmar",
    "confirmo",
    "certo",
    "certa",
    "isso",
    "esse",
    "esta",
    "este",
}


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
    "CaptureMessageIntent": send_message.handle_capture,
    "AMAZON.YesIntent": send_message.handle_yes,
    "AMAZON.NoIntent": send_message.handle_no,
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

        # When a contact confirmation is pending, intercept any intent and check
        # whether the user said something affirmative or negative before routing
        # normally — the NLU often misfires on conversational yes/no phrases.
        if intent_name not in ("AMAZON.StopIntent", "AMAZON.CancelIntent"):
            session_id = body.get("session", {}).get("sessionId", "")
            if session_id:
                pending_confirm = await SessionStore.get(session_id, "pending_confirm")
                if pending_confirm:
                    # Collect all words the user said (intent name + slot values)
                    spoken_words: set[str] = set()
                    for slot in body["request"]["intent"].get("slots", {}).values():
                        for w in (slot.get("value") or "").lower().split():
                            spoken_words.add(w)
                    for w in intent_name.lower().replace(".", " ").split():
                        spoken_words.add(w)

                    if spoken_words & _POSITIVE:
                        return await send_message.handle_yes(body)
                    if spoken_words & _NEGATIVE:
                        return await send_message.handle_no(body)

                    # Could not determine — re-ask
                    contact = pending_confirm.get("contact", "")
                    return AlexaResponse.speak(
                        f"Não entendi. Encontrei {contact}. Diga sim para confirmar ou não para cancelar.",  # noqa: E501
                        reprompt="Diga sim ou não.",
                        end_session=False,
                    )

        handler = INTENT_MAP.get(intent_name)
        if handler:
            try:
                return await handler(body)
            except Exception:
                logger.exception("Error handling intent %s", intent_name)
                return AlexaResponse.speak("Ocorreu um erro interno. Tente novamente em instantes.")

    return AlexaResponse.speak("Não entendi. Tente novamente.")
