import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from agents.base import WhatsAppDeps
from agents.summarizer import summarizer_agent
from database.engine import async_session_factory
from database.repo import MessageRepo, PreferencesRepo
from notifications.proactive import ProactiveNotifier
from whatsapp.client import whatsapp_client

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def _group_by_chat(messages: list) -> dict:
    grouped: dict = {}
    for msg in messages:
        key = msg.sender_name
        grouped.setdefault(key, []).append(msg)
    return grouped


@scheduler.scheduled_job("cron", hour=8, minute=0)
async def morning_digest() -> None:
    """Todo dia às 8h: notifica resumo das mensagens das últimas 8 horas."""
    async with async_session_factory() as session:
        overnight = await MessageRepo.get_since_hours(session, 8)
        if not overnight:
            return

        prefs = await PreferencesRepo.get(session)

    grouped = _group_by_chat(overnight)
    summary_parts = []

    for chat_name, msgs in grouped.items():
        try:
            deps = WhatsAppDeps(
                chat_jid=msgs[0].chat_jid,
                recent_messages=[
                    {"content": m.content_preview, "sender": m.sender_name} for m in msgs
                ],
                preferences=prefs,
                whatsapp_client=whatsapp_client,
            )
            result = await summarizer_agent.run("Resuma brevemente", deps=deps)
            summary_parts.append(f"{chat_name}: {result.output.summary}")
        except Exception:
            logger.exception("Morning digest summarizer failed for %s", chat_name)

    if summary_parts:
        full = "Bom dia! Resumo da noite: " + ". ".join(summary_parts)
        await ProactiveNotifier.notify_text("Sistema", full, "MEDIUM")


@scheduler.scheduled_job("interval", hours=24)
async def cleanup_old_media() -> None:
    """Remove MP3s com mais de 7 dias."""
    import time
    from pathlib import Path

    from config import settings

    media_dir = Path(settings.media_dir)
    if not media_dir.exists():
        return

    cutoff = time.time() - 7 * 24 * 3600
    removed = 0
    for f in media_dir.glob("*.mp3"):
        if f.stat().st_mtime < cutoff:
            f.unlink(missing_ok=True)
            removed += 1

    if removed:
        logger.info("Cleaned up %d old MP3 files", removed)
