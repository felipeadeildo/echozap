"""Audio processing: convert OGG voice notes to MP3 and transcribe with Whisper."""

import asyncio
import logging
import shutil
from pathlib import Path

from config import settings

logger = logging.getLogger(__name__)

MEDIA_DIR = Path(settings.media_dir)


class AudioProcessor:
    """Handles converting and transcribing WhatsApp voice note messages."""

    @staticmethod
    async def process(message_id: str, local_audio_path: str) -> tuple[str, str, str | None]:
        """
        Convert a local OGG file to MP3 and optionally transcribe it.

        The WhatsApp Go container writes audio to a local path inside the shared
        volume (e.g. ``/data/media/xxxx.ogg``). This method converts it to MP3
        for Alexa playback and runs Whisper if enabled.

        Returns:
            Tuple of ``(local_mp3_path, public_url, transcription_or_None)``.

        """
        MEDIA_DIR.mkdir(parents=True, exist_ok=True)

        ogg_src = Path(local_audio_path)
        ogg_dst = MEDIA_DIR / f"{message_id}.ogg"

        # Copy to our media dir if the file lives elsewhere
        if ogg_src != ogg_dst:
            shutil.copy2(ogg_src, ogg_dst)

        # Convert OGG → MP3
        mp3_path = MEDIA_DIR / f"{message_id}.mp3"
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-i",
            str(ogg_dst),
            "-codec:a",
            "libmp3lame",
            "-q:a",
            "4",
            str(mp3_path),
            "-y",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        ogg_dst.unlink(missing_ok=True)

        public_url = f"{settings.public_base_url}/media/{message_id}.mp3"

        transcription = None
        if settings.whisper_enabled:
            try:
                transcription = await _transcribe(mp3_path)
            except Exception:
                logger.exception("Whisper transcription failed for %s", message_id)

        return str(mp3_path), public_url, transcription


async def _transcribe(mp3_path: Path) -> str:
    """Run faster-whisper transcription in a thread pool executor."""
    from faster_whisper import WhisperModel

    loop = asyncio.get_event_loop()

    def _run() -> str:
        model = WhisperModel(settings.whisper_model, device="cpu", compute_type="int8")
        segments, _ = model.transcribe(str(mp3_path), language="pt")
        return " ".join(s.text for s in segments).strip()

    return await loop.run_in_executor(None, _run)
