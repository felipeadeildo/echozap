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
    """Pipeline assíncrono executado em background task."""
    msg = payload.message

    async with async_session_factory() as session:
        # 1. Salvar raw no DB
        record = await MessageRepo.create(session, payload.to_db_dict())

        # 2. Processar áudio se houver
        transcription = None
        public_url = None
        if msg.type == "audio" and msg.media_url:
            try:
                local_path, public_url, transcription = await AudioProcessor.process(
                    message_id=msg.id,
                    download_url=msg.media_url,
                )
                await MessageRepo.update_audio(
                    session, record.id, local_path, public_url, transcription
                )
                msg = msg.with_content(transcription or "[áudio sem transcrição]")
            except Exception:
                logger.exception("Failed to process audio for message %s", msg.id)

        # 3. Buscar contexto da conversa
        recent = await whatsapp_client.get_messages(msg.chat_jid, limit=10)

        # 4. Classificar
        prefs = await PreferencesRepo.get(session)

    deps = WhatsAppDeps(
        chat_jid=msg.chat_jid,
        recent_messages=recent,
        preferences=prefs,
        whatsapp_client=whatsapp_client,
    )

    try:
        decision = await classifier_agent.run(
            f"Mensagem de {msg.sender_name}: {msg.content or ''}",
            deps=deps,
        )
        result = decision.output
    except Exception:
        logger.exception("Classifier agent failed for message %s", msg.id)
        return

    # 5. Atualizar DB com resultado da classificação
    async with async_session_factory() as session:
        await MessageRepo.update_classification(
            session,
            record.id,
            urgency=result.urgency,
            summary=result.summary,
            notified=result.should_notify,
        )

    # 6. Agir conforme urgência
    if not result.should_notify:
        return

    if result.urgency == "CRITICAL":
        await ProactiveNotifier.notify_text(
            sender=msg.sender_name,
            content=(msg.content or "")[:200],
            urgency="CRITICAL",
        )

    elif result.urgency == "HIGH":
        try:
            summary = await summarizer_agent.run("Resuma esta conversa", deps=deps)
            await ProactiveNotifier.notify_text(
                sender=msg.sender_name,
                content=summary.output.summary,
                urgency="HIGH",
            )
        except Exception:
            logger.exception("Summarizer failed for message %s", msg.id)

    elif result.urgency == "MEDIUM":
        if msg.type == "audio" and public_url:
            await ProactiveNotifier.notify_audio(
                sender=msg.sender_name,
                audio_url=public_url,
                transcription=transcription,
            )
        else:
            await ProactiveNotifier.notify_silent()
