"""License verification service (RSA-signed payloads)."""
from __future__ import annotations

import base64
import json
from datetime import datetime, timedelta, timezone

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from app.core.config import settings


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _as_naive(value: datetime) -> datetime:
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def verify_license_key(key: str) -> dict:
    """Decode and verify a base64(payload).base64(signature) license blob."""
    if not settings.license_public_key:
        raise ValueError("license public key is not configured")
    try:
        payload_b64, signature_b64 = key.split(".", 1)
        payload = json.loads(_b64decode(payload_b64))
        signature = _b64decode(signature_b64)
    except Exception as exc:  # noqa: BLE001
        raise ValueError("malformed license key") from exc

    public_key = serialization.load_pem_public_key(settings.license_public_key.encode())
    try:
        public_key.verify(
            signature,
            payload_b64.encode(),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
    except InvalidSignature as exc:
        raise ValueError("invalid license signature") from exc

    if payload.get("issuer") != settings.license_issuer:
        raise ValueError("unknown license issuer")
    return payload


def license_status(payload: dict) -> tuple[str, datetime | None]:
    """Return (status, expires_at) after validating dates."""
    expires_at = None
    if payload.get("expires_at"):
        expires_at = _as_naive(datetime.fromisoformat(payload["expires_at"]))
        now = _as_naive(datetime.now(timezone.utc))
        if expires_at < now:
            grace = expires_at + timedelta(days=settings.license_grace_days)
            if now > grace:
                return "expired", expires_at
            return "grace", expires_at
    return "active", expires_at
