from agents.base import WhatsAppDeps
from agents.reply_generator import reply_generator_agent
from alexa.session import AlexaResponse, SessionStore
from database.engine import async_session_factory
from database.repo import PreferencesRepo
from whatsapp.client import whatsapp_client


async def handle(body: dict) -> dict:
    """Generate three reply options for the specified contact and present them via Alexa."""
    session_id = body["session"]["sessionId"]
    slots = body.get("request", {}).get("intent", {}).get("slots", {})
    contact_name = slots.get("ContactName", {}).get("value")

    if not contact_name:
        return AlexaResponse.elicit_slot(
            "ContactName",
            "Para quem você quer responder?",
            "GenerateReplyIntent",
        )

    jid = await whatsapp_client.find_contact(contact_name)
    if not jid:
        return AlexaResponse.speak(f"Não encontrei o contato {contact_name}.")

    msgs = await whatsapp_client.get_messages(jid, limit=20)

    async with async_session_factory() as session:
        prefs = await PreferencesRepo.get(session)

    deps = WhatsAppDeps(
        chat_jid=jid,
        recent_messages=msgs,
        preferences=prefs,
        whatsapp_client=whatsapp_client,
    )
    result = await reply_generator_agent.run(
        f"Gere respostas para a conversa com {contact_name}",
        deps=deps,
    )
    options = result.output.options

    await SessionStore.set(
        session_id,
        "pending_replies",
        {
            "contact": contact_name,
            "jid": jid,
            "options": [o.text for o in options],
        },
    )

    speech = "Aqui estão 3 opções. "
    for i, opt in enumerate(options, 1):
        speech += f"Opção {i}: {opt.text}. "
    speech += "Qual você prefere?"

    return AlexaResponse.speak(speech, reprompt="Diga opção 1, 2 ou 3.", end_session=False)


async def handle_selection(body: dict) -> dict:
    """Send the reply option selected by the user and confirm via Alexa speech."""
    session_id = body["session"]["sessionId"]
    slots = body.get("request", {}).get("intent", {}).get("slots", {})
    option_num_str = slots.get("OptionNumber", {}).get("value", "0")

    try:
        option_num = int(option_num_str)
    except ValueError:
        option_num = 0

    pending = await SessionStore.get(session_id, "pending_replies")
    if not pending or option_num not in (1, 2, 3):
        return AlexaResponse.speak(
            "Não entendi. Diga opção 1, 2 ou 3.",
            reprompt="Diga opção 1, 2 ou 3.",
            end_session=False,
        )

    text = pending["options"][option_num - 1]
    contact = pending["contact"]
    jid = pending["jid"]

    await whatsapp_client.send_message(jid, text)
    await SessionStore.delete(session_id, "pending_replies")

    return AlexaResponse.speak(f"Mensagem enviada para {contact}.")
