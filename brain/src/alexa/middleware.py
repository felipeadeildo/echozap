"""Alexa request signature verification.

Reference: https://developer.amazon.com/docs/custom-skills/host-a-custom-skill-as-a-web-service.html
"""

import base64
import hashlib
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import httpx
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from fastapi import HTTPException, Request


async def verify_alexa_signature(request: Request) -> None:
    cert_url = request.headers.get("SignatureCertChainUrl", "")
    signature_b64 = request.headers.get("Signature", "")
    body = await request.body()

    if not cert_url or not signature_b64:
        raise HTTPException(status_code=400, detail="Missing Alexa signature headers")

    _validate_cert_url(cert_url)

    cert_pem = await _fetch_cert(cert_url)
    cert = x509.load_pem_x509_certificate(cert_pem)

    _validate_cert(cert)

    signature = base64.b64decode(signature_b64)
    try:
        cert.public_key().verify(signature, body, padding.PKCS1v15(), hashes.SHA1())
    except Exception:
        raise HTTPException(status_code=400, detail="Alexa signature verification failed")

    import json

    payload = json.loads(body)
    timestamp_str = payload.get("request", {}).get("timestamp", "")
    if timestamp_str:
        ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        if abs((datetime.now(timezone.utc) - ts).total_seconds()) > 150:
            raise HTTPException(status_code=400, detail="Request timestamp too old")


def _validate_cert_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https":
        raise HTTPException(status_code=400, detail="Cert URL must use HTTPS")
    if parsed.hostname != "s3.amazonaws.com":
        raise HTTPException(status_code=400, detail="Cert URL must be from s3.amazonaws.com")
    if not parsed.path.startswith("/echo.api/"):
        raise HTTPException(status_code=400, detail="Cert URL path invalid")


def _validate_cert(cert: x509.Certificate) -> None:
    now = datetime.now(timezone.utc)
    if cert.not_valid_before_utc > now or cert.not_valid_after_utc < now:
        raise HTTPException(status_code=400, detail="Alexa cert expired")
    san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
    dns_names = san.value.get_values_for_type(x509.DNSName)
    if "echo-api.amazon.com" not in dns_names:
        raise HTTPException(status_code=400, detail="Cert SAN mismatch")


_cert_cache: dict[str, bytes] = {}


async def _fetch_cert(url: str) -> bytes:
    if url in _cert_cache:
        return _cert_cache[url]
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        resp.raise_for_status()
        _cert_cache[url] = resp.content
        return resp.content
