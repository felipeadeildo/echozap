"""Webhook processing pipeline — classifies and routes incoming WhatsApp messages."""

import logging

from agents.base import WhatsAppDeps
from agents.classifier import classifier_agent
from agents.summarizer import summarizer_agent
from audio.processor import AudioProcessor
from database.engine import async_session_factory
from database.repo import MessageRepo, PreferencesRepo
from notifications.proactive import ProactiveNotifier
from whatsapp.client import whatsapp_client
from whatsapp.models import WebhookPayload

logger = logging.getLogger(__name__)


async def process_incoming_message(payload: WebhookPayload) -> None:
    """Async pipeline executed as a FastAPI background task for each incoming message."""
    msg = payload.payload

    async with async_session_factory() as session:
        # 1. Persist raw message to DB
        record = await MessageRepo.create(session, payload.to_db_dict())
        if record is None:
            logger.debug("Duplicate webhook for message %s, skipping.", payload.payload.id)
            return

        # 2. Process audio when present
        transcription: str | None = None
        public_url: str | None = None
        if msg.message_type == "audio" and msg.audio:
            try:
                local_path, public_url, transcription = await AudioProcessor.process(
                    message_id=msg.id,
                    local_audio_path=msg.audio,
                )
                await MessageRepo.update_audio(
                    session, record.id, local_path, public_url, transcription
                )
            except Exception:
                logger.exception("Failed to process audio for message %s", msg.id)

        # 3. Fetch recent conversation context
        recent = await whatsapp_client.get_messages(msg.chat_id, limit=10)

        # 4. Load user preferences
        prefs = await PreferencesRepo.get(session)

    effective_content = transcription or msg.body or ""

    deps = WhatsAppDeps(
        chat_jid=msg.chat_id,
        recent_messages=recent,
        preferences=prefs,
        whatsapp_client=whatsapp_client,
    )

    try:
        decision = await classifier_agent.run(
            f"Mensagem de {msg.from_name}: {effective_content}",
            deps=deps,
        )
        result = decision.output
    except Exception:
        logger.exception("Classifier agent failed for message %s", msg.id)
        return

    # 5. Update DB with classification result
    async with async_session_factory() as session:
        await MessageRepo.update_classification(
            session,
            record.id,
            urgency=result.urgency,
            summary=result.summary,
            notified=result.should_notify,
        )

    # 6. Act on urgency level
    if not result.should_notify:
        return

    if result.urgency == "CRITICAL":
        await ProactiveNotifier.notify_text(
            sender=msg.from_name,
            content=effective_content[:200],
            urgency="CRITICAL",
        )

    elif result.urgency == "HIGH":
        try:
            summary = await summarizer_agent.run("Resuma esta conversa", deps=deps)
            await ProactiveNotifier.notify_text(
                sender=msg.from_name,
                content=summary.output.summary,
                urgency="HIGH",
            )
        except Exception:
            logger.exception("Summarizer failed for message %s", msg.id)

    elif result.urgency == "MEDIUM":
        if msg.message_type == "audio" and public_url:
            await ProactiveNotifier.notify_audio(
                sender=msg.from_name,
                audio_url=public_url,
                transcription=transcription,
            )
        else:
            await ProactiveNotifier.notify_silent()
