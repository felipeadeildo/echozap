"""Async HTTP client for the WhatsApp Go REST API (go-whatsapp-web-multidevice)."""

import httpx

from config import settings


class WhatsAppClient:
    """
    Async HTTP client for the WhatsApp Go REST API.

    All requests that target a specific connected device include the
    ``X-Device-Id`` header set to the configured device_id.
    """

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=settings.whatsapp_api_url,
            headers={"X-Device-Id": settings.whatsapp_device_id},
            timeout=30.0,
        )

    async def get_messages(self, chat_jid: str, limit: int = 20) -> list[dict]:
        """Fetch recent messages from a chat by JID."""
        resp = await self._client.get(
            f"/chat/{chat_jid}/messages",
            params={"limit": limit},
        )
        resp.raise_for_status()
        return resp.json().get("results", [])

    async def send_message(self, phone: str, text: str) -> dict:
        """Send a text message to a phone number or JID."""
        resp = await self._client.post(
            "/send/message",
            json={"phone": phone, "message": text},
        )
        resp.raise_for_status()
        return resp.json()

    async def find_contact(self, name: str) -> tuple[str, str] | None:
        """Resolve a display name to a (matched_name, jid) tuple via fuzzy local matching."""
        from difflib import get_close_matches

        resp = await self._client.get("/user/my/contacts")
        resp.raise_for_status()
        contacts: list[dict] = resp.json().get("results", {}).get("data", [])

        if not contacts:
            return None

        names = [c.get("name", "") for c in contacts if c.get("name")]
        matches = get_close_matches(name, names, n=1, cutoff=0.5)
        matched_name = matches[0] if matches else None

        if not matched_name:
            # fallback: substring
            matched_name = next(
                (c["name"] for c in contacts if name.lower() in c.get("name", "").lower()),
                None,
            )

        if matched_name:
            contact = next(c for c in contacts if c.get("name") == matched_name)
            jid = contact.get("jid")
            if jid:
                return matched_name, jid

        return None

    async def close(self) -> None:
        """Close the underlying HTTP client connection."""
        await self._client.aclose()


whatsapp_client = WhatsAppClient()
