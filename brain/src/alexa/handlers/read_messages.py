from alexa.session import AlexaResponse
from database.engine import async_session_factory
from database.models import ProcessedMessage
from database.repo import MessageRepo
from sqlalchemy import select


async def handle(body: dict) -> dict:
    slots = body.get("request", {}).get("intent", {}).get("slots", {})
    contact_name = slots.get("ContactName", {}).get("value")

    async with async_session_factory() as session:
        query = select(ProcessedMessage).where(
            ProcessedMessage.read_by_user == False  # noqa: E712
        )
        if contact_name:
            query = query.where(ProcessedMessage.sender_name.ilike(f"%{contact_name}%"))
        result = await session.execute(query.order_by(ProcessedMessage.received_at.desc()).limit(5))
        messages = result.scalars().all()

    if not messages:
        name_part = f" de {contact_name}" if contact_name else ""
        return AlexaResponse.speak(f"Não há mensagens não lidas{name_part}.")

    speech = ""
    for msg in messages:
        speech += f"{msg.sender_name} disse: {msg.content_preview or msg.summary or 'mensagem de mídia'}. "

    return AlexaResponse.speak(speech)
