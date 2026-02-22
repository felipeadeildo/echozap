import hashlib
import hmac

from fastapi import HTTPException, Request

from config import settings


async def verify_webhook_hmac(request: Request) -> bytes:
    """Validate X-Hub-Signature-256 sent by go-whatsapp."""
    signature_header = request.headers.get("X-Hub-Signature-256", "")
    body = await request.body()

    if not settings.webhook_secret:
        return body

    expected = "sha256=" + hmac.new(
        settings.webhook_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(signature_header, expected):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    return body
