from agents.base import WhatsAppDeps
from agents.summarizer import summarizer_agent
from alexa.session import AlexaResponse
from database.engine import async_session_factory
from database.repo import PreferencesRepo
from whatsapp.client import whatsapp_client


async def handle(body: dict) -> dict:
    """Summarise a WhatsApp conversation using the AI summarizer agent and read it aloud."""
    slots = body.get("request", {}).get("intent", {}).get("slots", {})
    contact_name = slots.get("ContactName", {}).get("value")

    if not contact_name:
        return AlexaResponse.elicit_slot(
            "ContactName",
            "De qual conversa você quer o resumo?",
            "SummarizeConversationIntent",
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
    result = await summarizer_agent.run("Resuma esta conversa", deps=deps)
    summary = result.output

    speech = summary.summary
    if summary.action_required and summary.suggested_actions:
        speech += f" Ação sugerida: {summary.suggested_actions[0]}."

    return AlexaResponse.speak(speech)
