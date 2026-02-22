import json

import redis.asyncio as aioredis

from config import settings

_redis: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


class SessionStore:
    TTL = 300  # 5 minutos

    @classmethod
    async def set(cls, session_id: str, key: str, value: object) -> None:
        r = get_redis()
        field = f"alexa:{session_id}:{key}"
        await r.setex(field, cls.TTL, json.dumps(value))

    @classmethod
    async def get(cls, session_id: str, key: str) -> object | None:
        r = get_redis()
        field = f"alexa:{session_id}:{key}"
        data = await r.get(field)
        return json.loads(data) if data else None

    @classmethod
    async def delete(cls, session_id: str, key: str) -> None:
        r = get_redis()
        await r.delete(f"alexa:{session_id}:{key}")


class AlexaResponse:
    @staticmethod
    def speak(text: str, reprompt: str | None = None, end_session: bool = True) -> dict:
        response: dict = {
            "version": "1.0",
            "response": {
                "outputSpeech": {"type": "PlainText", "text": text},
                "shouldEndSession": end_session,
            },
        }
        if reprompt:
            response["response"]["reprompt"] = {
                "outputSpeech": {"type": "PlainText", "text": reprompt}
            }
        return response

    @staticmethod
    def elicit_slot(slot_name: str, prompt: str, intent_name: str = "") -> dict:
        return {
            "version": "1.0",
            "response": {
                "outputSpeech": {"type": "PlainText", "text": prompt},
                "directives": [
                    {
                        "type": "Dialog.ElicitSlot",
                        "slotToElicit": slot_name,
                        "updatedIntent": {"name": intent_name, "slots": {}},
                    }
                ],
                "shouldEndSession": False,
            },
        }
