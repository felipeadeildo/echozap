"""Pydantic models for the WhatsApp Go REST API webhook payloads."""

from pydantic import BaseModel


class MessagePayload(BaseModel):
    """Inner payload of a webhook event — the actual message fields."""

    id: str
    chat_id: str  # JID of the chat (e.g. "5511999999999@s.whatsapp.net" or "...@g.us")
    from_: str | None = None  # sender JID (alias for 'from' — reserved keyword)
    from_name: str = ""  # display name of the sender
    body: str | None = None  # text body (for text messages)
    audio: str | None = None  # local file path to OGG audio (voice notes)
    image: str | None = None  # local file path to image
    document: str | None = None  # local file path to document
    timestamp: int | str | None = None

    model_config = {"populate_by_name": True}

    @property
    def is_group(self) -> bool:
        """Return True when this message comes from a group chat."""
        return self.chat_id.endswith("@g.us")

    @property
    def message_type(self) -> str:
        """Infer message type from which media field is populated."""
        if self.audio:
            return "audio"
        if self.image:
            return "image"
        if self.document:
            return "document"
        return "text"

    @property
    def content(self) -> str | None:
        """Return the text content or None for pure media messages."""
        return self.body or None


class WebhookPayload(BaseModel):
    """Top-level envelope sent by the WhatsApp Go REST container on each event."""

    event: str  # e.g. "message", "read", "typing", ...
    device_id: str
    payload: MessagePayload

    def to_db_dict(self) -> dict:
        """Convert to a dict suitable for inserting into the processed_messages table."""
        msg = self.payload
        return {
            "message_id": msg.id,
            "chat_jid": msg.chat_id,
            "sender_name": msg.from_name,
            "is_group": msg.is_group,
            "message_type": msg.message_type,
            "content_preview": (msg.body or "")[:500],
        }
