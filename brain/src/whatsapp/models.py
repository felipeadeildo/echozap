from pydantic import BaseModel


class WebhookMessage(BaseModel):
    id: str
    chat_jid: str
    sender_jid: str
    sender_name: str
    is_group: bool
    type: str  # text | audio | image | document
    content: str | None = None
    media_url: str | None = None
    timestamp: int

    def with_content(self, content: str) -> "WebhookMessage":
        return self.model_copy(update={"content": content})


class WebhookPayload(BaseModel):
    event: str
    message: WebhookMessage

    def to_db_dict(self) -> dict:
        msg = self.message
        return {
            "message_id": msg.id,
            "chat_jid": msg.chat_jid,
            "sender_name": msg.sender_name,
            "is_group": msg.is_group,
            "message_type": msg.type,
            "content_preview": (msg.content or "")[:500],
        }
