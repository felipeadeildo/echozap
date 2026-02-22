from alexa.session import AlexaResponse
from database.engine import async_session_factory
from database.repo import MessageRepo


async def handle(body: dict) -> dict:
    async with async_session_factory() as session:
        unread = await MessageRepo.get_unread_summary(session)

    if not unread:
        return AlexaResponse.speak("Você não tem mensagens não lidas.")

    total = sum(u["count"] for u in unread)
    urgent = [u for u in unread if u["urgency"] in ("HIGH", "CRITICAL")]

    speech = f"Você tem {total} mensagem{'ns' if total > 1 else ''} "
    speech += f"em {len(unread)} conversa{'s' if len(unread) > 1 else ''}. "

    if urgent:
        names = ", ".join(u["name"] for u in urgent[:3])
        speech += f"Urgentes: {names}."

    return AlexaResponse.speak(speech)
