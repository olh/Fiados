"""Service Provider Interface (SPI) for KYC / identity verification and synthetic mock."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from fiados.domain.models import Party


@dataclass(frozen=True, slots=True)
class KYCVerificationResult:
    """Result returned by an identity and KYC verification provider."""

    party_id: str
    verified: bool
    identity_score: int  # 0 to 1000
    flags: tuple[str, ...] = ()


class KYCProvider(Protocol):
    """Pluggable interface for identity and antifraud verification services."""

    def verify_party(self, party: Party) -> KYCVerificationResult:
        """Verify identity attributes for a transaction party."""
        ...


class SyntheticKYCAdapter:
    """Deterministic zero-PII KYC adapter for sandbox simulation and testing."""

    def verify_party(self, party: Party) -> KYCVerificationResult:
        """Simulate KYC verification based on synthetic tax ID suffixes."""
        cleaned_tax_id = party.tax_id.strip()
        if cleaned_tax_id.endswith("99"):
            return KYCVerificationResult(
                party_id=party.party_id,
                verified=False,
                identity_score=180,
                flags=("SYNTHETIC_BLOCKLIST_MATCH",),
            )
        if cleaned_tax_id.endswith("55"):
            return KYCVerificationResult(
                party_id=party.party_id,
                verified=True,
                identity_score=580,
                flags=("SYNTHETIC_THIN_FILE",),
            )
        return KYCVerificationResult(
            party_id=party.party_id,
            verified=True,
            identity_score=850,
            flags=(),
        )
