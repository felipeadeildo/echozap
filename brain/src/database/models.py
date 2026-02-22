import datetime
import enum
import json

from sqlalchemy import Enum as SAEnum
from sqlalchemy import Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UrgencyLevel(enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ProcessedMessage(Base):
    """Log de todas as mensagens recebidas e como foram tratadas."""

    __tablename__ = "processed_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[str] = mapped_column(unique=True, index=True)
    chat_jid: Mapped[str] = mapped_column(index=True)
    sender_name: Mapped[str]
    is_group: Mapped[bool]
    message_type: Mapped[str]  # text | audio | image | document
    content_preview: Mapped[str | None] = mapped_column(Text)
    audio_local_path: Mapped[str | None]
    audio_public_url: Mapped[str | None]
    transcription: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    urgency: Mapped[UrgencyLevel] = mapped_column(SAEnum(UrgencyLevel), default=UrgencyLevel.LOW)
    notified: Mapped[bool] = mapped_column(default=False)
    read_by_user: Mapped[bool] = mapped_column(default=False)
    received_at: Mapped[datetime.datetime] = mapped_column(
        default=datetime.datetime.utcnow
    )
    processed_at: Mapped[datetime.datetime | None]


class UserPreferences(Base):
    """Configurações do usuário (único usuário no sistema self-hosted)."""

    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    vip_contacts: Mapped[str] = mapped_column(Text, default="[]")  # JSON list
    urgent_keywords: Mapped[str] = mapped_column(Text, default="[]")
    quiet_hours_start: Mapped[str] = mapped_column(default="22:00")
    quiet_hours_end: Mapped[str] = mapped_column(default="07:00")
    quiet_hours_allow_vip: Mapped[bool] = mapped_column(default=True)
    notify_on_group_mention: Mapped[bool] = mapped_column(default=True)
    group_notify_threshold: Mapped[int] = mapped_column(default=5)
    important_groups: Mapped[str] = mapped_column(Text, default="[]")
    long_message_threshold: Mapped[int] = mapped_column(default=200)
    language: Mapped[str] = mapped_column(default="pt-BR")
    whisper_transcription: Mapped[bool] = mapped_column(default=True)
    alexa_proactive_token: Mapped[str | None]
    alexa_proactive_token_expires: Mapped[datetime.datetime | None]

    def vip_contacts_list(self) -> list[str]:
        return json.loads(self.vip_contacts)

    def urgent_keywords_list(self) -> list[str]:
        return json.loads(self.urgent_keywords)

    def is_quiet_hours_now(self) -> bool:
        now = datetime.datetime.now().strftime("%H:%M")
        start = self.quiet_hours_start
        end = self.quiet_hours_end
        if start <= end:
            return start <= now < end
        # overnight: e.g. 22:00 - 07:00
        return now >= start or now < end
