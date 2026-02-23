from alexa.session import AlexaResponse, SessionStore
from whatsapp.client import whatsapp_client


async def handle(body: dict) -> dict:
    """Send a WhatsApp message to the specified contact on behalf of the user."""
    session_id = body["session"]["sessionId"]
    slots = body.get("request", {}).get("intent", {}).get("slots", {})
    contact_name = slots.get("ContactName", {}).get("value")

    if not contact_name:
        return AlexaResponse.elicit_slot(
            "ContactName", "Para quem você quer enviar a mensagem?", "SendMessageIntent"
        )

    jid = await whatsapp_client.find_contact(contact_name)
    if not jid:
        return AlexaResponse.speak(f"Não encontrei o contato {contact_name}.")

    # Salva o destinatário na sessão e pede o conteúdo no próximo turno
    await SessionStore.set(session_id, "pending_send", {"contact": contact_name, "jid": jid})

    return AlexaResponse.speak(
        f"O que você quer dizer para {contact_name}?",
        reprompt="O que você quer dizer?",
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
