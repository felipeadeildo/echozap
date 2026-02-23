from alexa.session import AlexaResponse, SessionStore
from whatsapp.client import whatsapp_client


async def handle(body: dict) -> dict:
    """Resolve the contact and ask the user to confirm before proceeding."""
    session_id = body["session"]["sessionId"]
    slots = body.get("request", {}).get("intent", {}).get("slots", {})
    contact_name = slots.get("ContactName", {}).get("value")

    if not contact_name:
        return AlexaResponse.elicit_slot(
            "ContactName", "Para quem você quer enviar a mensagem?", "SendMessageIntent"
        )

    result = await whatsapp_client.find_contact(contact_name)
    if not result:
        return AlexaResponse.speak(f"Não encontrei o contato {contact_name}.")

    matched_name, jid = result

    # Save to session and ask for confirmation
    await SessionStore.set(session_id, "pending_confirm", {"contact": matched_name, "jid": jid})

    return AlexaResponse.speak(
        f"Encontrei {matched_name}. É esse contato?",
        reprompt="Diga sim para confirmar ou não para cancelar.",
        end_session=False,
    )


async def handle_yes(body: dict) -> dict:
    """User confirmed the contact — now ask for the message content."""
    session_id = body["session"]["sessionId"]

    pending = await SessionStore.get(session_id, "pending_confirm")
    if not pending:
        return AlexaResponse.speak(
            "Não há nenhum envio pendente. Diga 'enviar mensagem para' seguido do nome."
        )

    await SessionStore.delete(session_id, "pending_confirm")
    await SessionStore.set(session_id, "pending_send", pending)

    return AlexaResponse.speak(
        f"O que você quer dizer para {pending['contact']}?",
        reprompt="O que você quer dizer?",
        end_session=False,
    )


async def handle_no(body: dict) -> dict:
    """User rejected the contact — cancel and let them retry."""
    session_id = body["session"]["sessionId"]
    await SessionStore.delete(session_id, "pending_confirm")
    return AlexaResponse.speak(
        "Tudo bem, envio cancelado. Diga 'enviar mensagem para' com o nome correto.",
        end_session=False,
    )


async def handle_capture(body: dict) -> dict:
    """Receive the message content and send it to the contact saved in session."""
    session_id = body["session"]["sessionId"]
    slots = body.get("request", {}).get("intent", {}).get("slots", {})
    content = slots.get("MessageContent", {}).get("value")

    if not content:
        return AlexaResponse.speak("Não entendi o que você quer dizer. Tente novamente.")

    pending = await SessionStore.get(session_id, "pending_send")
    if not pending:
        return AlexaResponse.speak(
            "Não sei para quem enviar. Diga 'enviar mensagem para' seguido do nome."
        )

    await whatsapp_client.send_message(pending["jid"], content)
    await SessionStore.delete(session_id, "pending_send")

    return AlexaResponse.speak(f"Mensagem enviada para {pending['contact']}.")
