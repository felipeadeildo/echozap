import logging
from datetime import UTC, datetime, timedelta

import httpx

from config import settings
from database.engine import async_session_factory
from database.repo import PreferencesRepo

logger = logging.getLogger(__name__)


class ProactiveNotifier:
    """Sends proactive Alexa notifications using the Alexa Proactive Events API."""

    EVENTS_URL = "https://api.amazonalexa.com/v1/proactiveEvents/"
    TOKEN_URL = "https://api.amazon.com/auth/o2/token"

    @classmethod
    async def notify_text(cls, sender: str, content: str, urgency: str) -> None:  # noqa: ARG003
        """Deliver a proactive message-alert event to the user's Alexa device."""
        token = await cls._get_token()
        if not token:
            logger.warning("No Alexa token available, skipping notification")
            return

        now = datetime.now(UTC)
        payload = {
            "timestamp": now.isoformat(),
            "referenceId": f"msg-{now.timestamp()}",
            "expiryTime": (now + timedelta(hours=1)).isoformat(),
            "event": {
                "name": "AMAZON.MessageAlert.Activated",
                "payload": {
                    "state": {"status": "UNREAD", "freshness": "NEW"},
                    "messageGroup": {
                        "creator": {"name": sender},
                        "count": 1,
                        "urgency": urgency,
                    },
                },
            },
            "relevantAudience": {
                "type": "Unicast",
                "payload": {"user": {"userId": settings.alexa_user_id}},
            },
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                cls.EVENTS_URL,
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code not in (200, 202):
                logger.error("Proactive event failed: %s %s", resp.status_code, resp.text)

    @classmethod
    async def notify_audio(cls, sender: str, audio_url: str, transcription: str | None) -> None:  # noqa: ARG003
        """Notify Alexa about a new audio message, using the transcription as content."""
        content = transcription or f"Áudio de {sender}"
        await cls.notify_text(sender=sender, content=content, urgency="MEDIUM")

    @classmethod
    async def notify_silent(cls) -> None:
        """Trigger a silent LED-only notification (not yet implemented)."""
        logger.debug("Silent notification (LED only) — not yet implemented")

    @classmethod
    async def _get_token(cls) -> str | None:
        if not settings.alexa_client_id or not settings.alexa_client_secret:
            return None

        async with async_session_factory() as session:
            prefs = await PreferencesRepo.get(session)

            now = datetime.now(UTC)
            if (
                prefs.alexa_proactive_token
                and prefs.alexa_proactive_token_expires
                and prefs.alexa_proactive_token_expires.replace(tzinfo=UTC) > now
            ):
                return prefs.alexa_proactive_token

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    cls.TOKEN_URL,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": settings.alexa_client_id,
                        "client_secret": settings.alexa_client_secret,
                        "scope": "alexa::proactive_events",
                    },
                )
                resp.raise_for_status()

            token_data = resp.json()
            expires = now + timedelta(seconds=token_data["expires_in"] - 60)

            await PreferencesRepo.update_token(session, token_data["access_token"], expires)
            return token_data["access_token"]
