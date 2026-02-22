import datetime
from datetime import UTC

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import ProcessedMessage, UrgencyLevel, UserPreferences


class MessageRepo:
    """Repository for CRUD operations on ProcessedMessage records."""

    @staticmethod
    async def create(session: AsyncSession, data: dict) -> ProcessedMessage:
        """Insert a new ProcessedMessage and return the persisted instance."""
        msg = ProcessedMessage(**data)
        session.add(msg)
        await session.commit()
        await session.refresh(msg)
        return msg

    @staticmethod
    async def get_unread_summary(session: AsyncSession) -> list[dict]:
        """Return per-chat unread counts and highest urgency level."""
        result = await session.execute(
            select(ProcessedMessage).where(ProcessedMessage.read_by_user == False)  # noqa: E712
        )
        messages = result.scalars().all()

        grouped: dict[str, dict] = {}
        for msg in messages:
            key = msg.chat_jid
            if key not in grouped:
                grouped[key] = {"name": msg.sender_name, "count": 0, "urgency": "LOW"}
            grouped[key]["count"] += 1
            current = UrgencyLevel[grouped[key]["urgency"]]
            if UrgencyLevel[msg.urgency.value].value > current.value:
                grouped[key]["urgency"] = msg.urgency.value

        return list(grouped.values())

    @staticmethod
    async def update_audio(
        session: AsyncSession,
        record_id: int,
        local_path: str,
        public_url: str,
        transcription: str | None,
    ) -> None:
        """Update audio paths and transcription for a processed message."""
        msg = await session.get(ProcessedMessage, record_id)
        if msg:
            msg.audio_local_path = local_path
            msg.audio_public_url = public_url
            msg.transcription = transcription
            await session.commit()

    @staticmethod
    async def update_classification(
        session: AsyncSession,
        record_id: int,
        urgency: str,
        summary: str,
        notified: bool,
    ) -> None:
        """Update urgency, summary, and notified status after AI classification."""
        msg = await session.get(ProcessedMessage, record_id)
        if msg:
            msg.urgency = UrgencyLevel[urgency]
            msg.summary = summary
            msg.notified = notified
            msg.processed_at = datetime.datetime.now(UTC)
            await session.commit()

    @staticmethod
    async def get_since_hours(session: AsyncSession, hours: int) -> list[ProcessedMessage]:
        """Return all messages received within the last N hours."""
        since = datetime.datetime.now(UTC) - datetime.timedelta(hours=hours)
        result = await session.execute(
            select(ProcessedMessage).where(ProcessedMessage.received_at >= since)
        )
        return list(result.scalars().all())

    @staticmethod
    async def mark_read(session: AsyncSession, chat_jid: str) -> None:
        """Mark all unread messages in a given chat as read."""
        result = await session.execute(
            select(ProcessedMessage).where(
                ProcessedMessage.chat_jid == chat_jid,
                ProcessedMessage.read_by_user == False,  # noqa: E712
            )
        )
        for msg in result.scalars().all():
            msg.read_by_user = True
        await session.commit()


class PreferencesRepo:
    """Repository for reading and updating UserPreferences (single-user system)."""

    @staticmethod
    async def get(session: AsyncSession) -> UserPreferences:
        """Fetch the user preferences row, creating it with defaults if absent."""
        result = await session.execute(select(UserPreferences).where(UserPreferences.id == 1))
        prefs = result.scalar_one_or_none()
        if prefs is None:
            prefs = UserPreferences(id=1)
            session.add(prefs)
            await session.commit()
            await session.refresh(prefs)
        return prefs

    @staticmethod
    async def update_token(
        session: AsyncSession,
        token: str,
        expires: datetime.datetime,
    ) -> None:
        """Persist a new Alexa proactive token and its expiration timestamp."""
        prefs = await PreferencesRepo.get(session)
        prefs.alexa_proactive_token = token
        prefs.alexa_proactive_token_expires = expires
        await session.commit()
