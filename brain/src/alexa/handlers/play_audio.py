from alexa.session import AlexaResponse
from database.engine import async_session_factory
from database.models import ProcessedMessage
from sqlalchemy import select


async def handle(body: dict) -> dict:
    slots = body.get("request", {}).get("intent", {}).get("slots", {})
    contact_name = slots.get("ContactName", {}).get("value")

    async with async_session_factory() as session:
        query = (
            select(ProcessedMessage)
            .where(
                ProcessedMessage.message_type == "audio",
                ProcessedMessage.audio_public_url.isnot(None),
            )
            .order_by(ProcessedMessage.received_at.desc())
            .limit(1)
        )
        if contact_name:
            query = query.where(ProcessedMessage.sender_name.ilike(f"%{contact_name}%"))

        result = await session.execute(query)
        msg = result.scalar_one_or_none()

    if not msg or not msg.audio_public_url:
        name_part = f" de {contact_name}" if contact_name else ""
        return AlexaResponse.speak(f"Não há áudios disponíveis{name_part}.")

    transcription = msg.transcription or ""
    sender = msg.sender_name

    return {
        "version": "1.0",
        "response": {
            "outputSpeech": {
                "type": "SSML",
                "ssml": f"<speak>Áudio de {sender}. {transcription} <audio src=\"{msg.audio_public_url}\"/></speak>",
            },
            "directives": [
                {
                    "type": "AudioPlayer.Play",
                    "playBehavior": "REPLACE_ALL",
                    "audioItem": {
                        "stream": {
                            "token": str(msg.id),
                            "url": msg.audio_public_url,
                            "offsetInMilliseconds": 0,
                        }
                    },
                }
            ],
            "shouldEndSession": True,
        },
    }
