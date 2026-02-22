import json

import redis.asyncio as aioredis

from config import settings

_redis: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    """Return a singleton async Redis client."""
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


class SessionStore:
    """Redis-backed key-value store for Alexa session state with a 5-minute TTL."""

    TTL = 300  # 5 minutos

    @classmethod
    async def set(cls, session_id: str, key: str, value: object) -> None:
        """Persist a JSON-serialisable value for the given session and key."""
        r = get_redis()
        field = f"alexa:{session_id}:{key}"
        await r.setex(field, cls.TTL, json.dumps(value))

    @classmethod
    async def get(cls, session_id: str, key: str) -> dict | None:
        """Retrieve and deserialise a value from the session store."""
        r = get_redis()
        field = f"alexa:{session_id}:{key}"
        data = await r.get(field)
        return json.loads(data) if data else None

    @classmethod
    async def delete(cls, session_id: str, key: str) -> None:
        """Remove a key from the session store."""
        r = get_redis()
        await r.delete(f"alexa:{session_id}:{key}")


class AlexaResponse:
    """Factory for well-formed Alexa JSON response payloads."""

    @staticmethod
    def speak(text: str, reprompt: str | None = None, end_session: bool = True) -> dict:
        """Build a plain-text speech response, optionally with a reprompt."""
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
        """Build a Dialog.ElicitSlot directive to request a missing intent slot."""
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
