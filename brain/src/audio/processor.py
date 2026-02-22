import asyncio
import logging
from pathlib import Path

import httpx

from config import settings

logger = logging.getLogger(__name__)

MEDIA_DIR = Path(settings.media_dir)


class AudioProcessor:
    @staticmethod
    async def process(
        message_id: str, download_url: str
    ) -> tuple[str, str, str | None]:
        """
        1. Baixa OGG do WhatsApp Go API
        2. Converte para MP3 via ffmpeg
        3. Transcreve com Whisper (se habilitado)
        4. Retorna (local_path, public_url, transcription)
        """
        MEDIA_DIR.mkdir(parents=True, exist_ok=True)

        # Download
        async with httpx.AsyncClient() as client:
            resp = await client.get(download_url)
            resp.raise_for_status()
            ogg_path = MEDIA_DIR / f"{message_id}.ogg"
            ogg_path.write_bytes(resp.content)

        # Conversão OGG → MP3
        mp3_path = MEDIA_DIR / f"{message_id}.mp3"
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-i",
            str(ogg_path),
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
        ogg_path.unlink(missing_ok=True)

        public_url = f"{settings.public_base_url}/media/{message_id}.mp3"

        transcription = None
        if settings.whisper_enabled:
            try:
                transcription = await _transcribe(mp3_path)
            except Exception:
                logger.exception("Whisper transcription failed for %s", message_id)

        return str(mp3_path), public_url, transcription


async def _transcribe(mp3_path: Path) -> str:
    from faster_whisper import WhisperModel

    loop = asyncio.get_event_loop()

    def _run() -> str:
        model = WhisperModel(settings.whisper_model, device="cpu", compute_type="int8")
        segments, _ = model.transcribe(str(mp3_path), language="pt")
        return " ".join(s.text for s in segments).strip()

    return await loop.run_in_executor(None, _run)
