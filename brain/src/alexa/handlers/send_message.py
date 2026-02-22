from alexa.session import AlexaResponse
from whatsapp.client import whatsapp_client


async def handle(body: dict) -> dict:
    slots = body.get("request", {}).get("intent", {}).get("slots", {})
    contact_name = slots.get("ContactName", {}).get("value")
    message_content = slots.get("MessageContent", {}).get("value")

    if not contact_name:
        return AlexaResponse.elicit_slot(
            "ContactName", "Para quem você quer enviar a mensagem?", "SendMessageIntent"
        )

    if not message_content:
        return AlexaResponse.elicit_slot(
            "MessageContent", "O que você quer dizer?", "SendMessageIntent"
        )

    jid = await whatsapp_client.find_contact(contact_name)
    if not jid:
        return AlexaResponse.speak(f"Não encontrei o contato {contact_name}.")

    await whatsapp_client.send_message(jid, message_content)
    return AlexaResponse.speak(f"Mensagem enviada para {contact_name}.")
