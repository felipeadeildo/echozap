from pydantic import BaseModel


class WebhookMessage(BaseModel):
    """Parsed representation of a single incoming WhatsApp message from the webhook."""

    id: str
    chat_jid: str
    sender_jid: str
    sender_name: str
    is_group: bool
    type: str  # text | audio | image | document
    content: str | None = None
    media_url: str | None = None
    timestamp: int

    def with_content(self, content: str) -> WebhookMessage:
        """Return a copy of this message with the content field replaced."""
        return self.model_copy(update={"content": content})


class WebhookPayload(BaseModel):
    """Top-level webhook envelope containing the event type and message data."""

    event: str
    message: WebhookMessage

    def to_db_dict(self) -> dict:
        """Convert the payload into a dict suitable for inserting into the database."""
        msg = self.message
        return {
            "message_id": msg.id,
            "chat_jid": msg.chat_jid,
            "sender_name": msg.sender_name,
            "is_group": msg.is_group,
            "message_type": msg.type,
            "content_preview": (msg.content or "")[:500],
        }
