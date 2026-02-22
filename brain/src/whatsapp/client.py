import httpx

from config import settings


class WhatsAppClient:
    """Async HTTP client for the WhatsApp Go REST API."""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(base_url=settings.whatsapp_api_url, timeout=30.0)

    async def get_messages(self, chat_jid: str, limit: int = 20) -> list[dict]:
        """Fetch recent messages from a chat by JID."""
        resp = await self._client.get(
            "/api/messages",
            params={"jid": chat_jid, "limit": limit},
        )
        resp.raise_for_status()
        return resp.json().get("results", [])

    async def send_message(self, phone: str, text: str) -> dict:
        """Send a text message to a phone number or JID."""
        resp = await self._client.post(
            "/api/send/message",
            json={"phone": phone, "message": text},
        )
        resp.raise_for_status()
        return resp.json()

    async def find_contact(self, name: str) -> str | None:
        """Resolve contact name to JID."""
        resp = await self._client.get("/api/contacts", params={"search": name})
        resp.raise_for_status()
        contacts = resp.json().get("results", [])
        if contacts:
            return contacts[0].get("jid")
        return None

    async def close(self) -> None:
        """Close the underlying HTTP client connection."""
        await self._client.aclose()


whatsapp_client = WhatsAppClient()
