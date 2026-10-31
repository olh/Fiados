"""Service Provider Interface (SPI) for electronic signature providers and sandbox signer."""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import replace
from datetime import UTC, datetime
from typing import Protocol

from fiados.domain.enums import InstrumentStatus
from fiados.domain.exceptions import SignatureVerificationError
from fiados.domain.models import DigitalPromissoryNote


class SignatureProvider(Protocol):
    """Pluggable interface for electronic signature engines."""

    def sign_note(
        self,
        note: DigitalPromissoryNote,
        *,
        signer_ip: str = "127.0.0.1",
        signed_at: datetime | None = None,
    ) -> DigitalPromissoryNote:
        """Apply electronic signature to a compiled digital promissory note."""
        ...

    def verify_note_signature(self, note: DigitalPromissoryNote) -> bool:
        """Verify authenticity and integrity of a signed digital promissory note."""
        ...


class SyntheticSignatureAdapter:
    """Deterministic HMAC-SHA256 electronic signature adapter for local sandbox and tests."""

    def __init__(self, key_secret: str = "sandbox-key-ed25519-01") -> None:
        self._key_bytes = key_secret.encode("utf-8")

    def _compute_token(
        self,
        *,
        note_id_str: str,
        canonical_sha256: str,
        maker_tax_id: str,
        signed_at_iso: str,
    ) -> str:
        payload = f"{note_id_str}:{canonical_sha256}:{maker_tax_id}:{signed_at_iso}".encode(
            "utf-8"
        )
        digest = hmac.new(self._key_bytes, payload, hashlib.sha256).hexdigest()
        return f"syn_sig_v1_{digest}"

    def sign_note(
        self,
        note: DigitalPromissoryNote,
        *,
        signer_ip: str = "127.0.0.1",
        signed_at: datetime | None = None,
    ) -> DigitalPromissoryNote:
        """Produce a signed copy of the digital promissory note with a verifiable token."""
        del signer_ip  # Reserved for audit metadata enrichment in external providers
        effective_time = signed_at or datetime.now(UTC)
        token = self._compute_token(
            note_id_str=str(note.note_id),
            canonical_sha256=note.canonical_sha256,
            maker_tax_id=note.maker.tax_id,
            signed_at_iso=effective_time.isoformat(),
        )
        return replace(
            note,
            status=InstrumentStatus.SIGNED,
            signature_token=token,
            signed_at=effective_time,
        )

    def verify_note_signature(self, note: DigitalPromissoryNote) -> bool:
        """Verify that the note is marked SIGNED and its signature token matches its digest."""
        if note.status != InstrumentStatus.SIGNED or not note.signature_token or not note.signed_at:
            raise SignatureVerificationError(
                f"Promissory note {note.note_id} is not in a signed state."
            )
        expected = self._compute_token(
            note_id_str=str(note.note_id),
            canonical_sha256=note.canonical_sha256,
            maker_tax_id=note.maker.tax_id,
            signed_at_iso=note.signed_at.isoformat(),
        )
        if not hmac.compare_digest(note.signature_token, expected):
            raise SignatureVerificationError(
                f"Signature verification failed for promissory note {note.note_id}."
            )
        return True
