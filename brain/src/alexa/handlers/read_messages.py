from difflib import get_close_matches

from sqlalchemy import select

from alexa.session import AlexaResponse
from database.engine import async_session_factory
from database.models import ProcessedMessage


async def handle(body: dict) -> dict:
    """Read the five most recent unread messages aloud via Alexa."""
    slots = body.get("request", {}).get("intent", {}).get("slots", {})
    contact_name = slots.get("ContactName", {}).get("value")

    async with async_session_factory() as session:
        query = select(ProcessedMessage).where(
            ProcessedMessage.read_by_user == False  # noqa: E712
        )
        result = await session.execute(
            query.order_by(ProcessedMessage.received_at.desc()).limit(100)
        )
        messages = list(result.scalars().all())

    if contact_name:
        all_names = list({m.sender_name for m in messages if m.sender_name})
        matches = get_close_matches(contact_name, all_names, n=1, cutoff=0.5)

        if matches:
            matched_name = matches[0]
            messages = [m for m in messages if m.sender_name == matched_name][:5]
        else:
            # Fallback: substring case-insensitive
            messages = [
                m
                for m in messages
                if m.sender_name and contact_name.lower() in m.sender_name.lower()
            ][:5]

        if not messages:
            return AlexaResponse.speak(f"Não há mensagens não lidas de {contact_name}.")
    else:
        messages = messages[:5]

    if not messages:
        return AlexaResponse.speak("Você não tem mensagens não lidas.")

    speech = ""
    for msg in messages:
        preview = msg.content_preview or msg.summary or "mensagem de mídia"
        speech += f"{msg.sender_name} disse: {preview}. "

    return AlexaResponse.speak(speech)
