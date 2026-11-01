"""HMAC-SHA256 webhook payload signer and replay-protected signature verifier."""

from __future__ import annotations

import hashlib
import hmac
import time

from fiados.domain.exceptions import SignatureVerificationError


class WebhookSigner:
    """Signs and verifies merchant webhook notifications using HMAC-SHA256."""

    def __init__(self, secret: str, *, tolerance_seconds: int = 300) -> None:
        if not secret:
            raise ValueError("Webhook HMAC secret cannot be empty.")
        self._secret_bytes = secret.encode("utf-8")
        self.tolerance_seconds = tolerance_seconds

    def sign_payload(self, payload_body: str, *, timestamp: int | None = None) -> str:
        """Generate a header value formatted as 't=<unix_ts>,v1=<hmac_sha256>'."""
        effective_ts = timestamp if timestamp is not None else int(time.time())
        signed_content = f"{effective_ts}.{payload_body}".encode("utf-8")
        digest = hmac.new(self._secret_bytes, signed_content, hashlib.sha256).hexdigest()
        return f"t={effective_ts},v1={digest}"

    def verify_header(
        self,
        payload_body: str,
        signature_header: str,
        *,
        current_timestamp: int | None = None,
    ) -> bool:
        """Verify HMAC signature and enforce replay-window tolerance."""
        parts: dict[str, str] = {}
        for item in signature_header.split(","):
            if "=" in item:
                k, v = item.strip().split("=", 1)
                parts[k] = v

        if "t" not in parts or "v1" not in parts:
            raise SignatureVerificationError("Malformed webhook signature header.")

        try:
            header_ts = int(parts["t"])
        except ValueError as exc:
            raise SignatureVerificationError("Invalid timestamp in webhook header.") from exc

        now_ts = current_timestamp if current_timestamp is not None else int(time.time())
        if abs(now_ts - header_ts) > self.tolerance_seconds:
            raise SignatureVerificationError(
                "Webhook timestamp outside allowed replay tolerance window."
            )

        expected_header = self.sign_payload(payload_body, timestamp=header_ts)
        expected_sig = expected_header.split(",v1=", 1)[1]

        if not hmac.compare_digest(parts["v1"], expected_sig):
            raise SignatureVerificationError("Webhook HMAC digest mismatch.")
        return True
