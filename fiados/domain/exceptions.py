"""Custom domain exceptions for Fiados orchestration workflows."""

from __future__ import annotations


class FiadosError(Exception):
    """Base exception for all Fiados domain and orchestration errors."""


class InvalidStateTransitionError(FiadosError):
    """Raised when an illegal transition is attempted on the transaction state machine."""

    def __init__(self, current_state: str, target_state: str, reason: str = "") -> None:
        detail = f" ({reason})" if reason else ""
        super().__init__(
            f"Cannot transition transaction from '{current_state}' to '{target_state}'{detail}."
        )
        self.current_state = current_state
        self.target_state = target_state
        self.reason = reason


class RiskPolicyViolationError(FiadosError):
    """Raised when a transaction fails mandatory risk or eligibility constraints."""


class InstrumentFormalizationError(FiadosError):
    """Raised when a digital promissory note fails Geneva Convention validation."""


class SignatureVerificationError(FiadosError):
    """Raised when an electronic signature or cryptographic digest cannot be verified."""


class HashChainIntegrityError(FiadosError):
    """Raised when the audit ledger hash chain exhibits tampering or discontinuity."""
