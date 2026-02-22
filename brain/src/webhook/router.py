from fastapi import APIRouter, BackgroundTasks, Depends, Request

from webhook.processor import process_incoming_message
from whatsapp.models import WebhookPayload
from whatsapp.webhook import verify_webhook_hmac

router = APIRouter()


@router.post("/webhook")
async def webhook_endpoint(
    request: Request,
    background_tasks: BackgroundTasks,
    _body: bytes = Depends(verify_webhook_hmac),
) -> dict:
    """Receive a WhatsApp webhook event and enqueue message processing in the background."""
    body = await request.json()
    payload = WebhookPayload(**body)

    if payload.event == "message":
        background_tasks.add_task(process_incoming_message, payload)

    return {"status": "ok"}
