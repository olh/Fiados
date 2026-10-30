"""Domain enumerations for transaction states, risk decisions, and legal instruments."""

from __future__ import annotations

from enum import StrEnum


class TransactionState(StrEnum):
    """Deterministic lifecycle states for a deferred-payment transaction."""

    DRAFT = "DRAFT"
    EVALUATING = "EVALUATING"
    FORMALIZED = "FORMALIZED"
    ACTIVE = "ACTIVE"
    SETTLED = "SETTLED"
    DEFAULTED = "DEFAULTED"
    RENEGOTIATED = "RENEGOTIATED"
    CANCELLED = "CANCELLED"


class RiskDecision(StrEnum):
    """Outcome of a risk and eligibility evaluation pipeline."""

    APPROVED = "APPROVED"
    CONDITIONED = "CONDITIONED"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    REJECTED = "REJECTED"


class InstrumentStatus(StrEnum):
    """Lifecycle status of a digital promissory note."""

    COMPILED = "COMPILED"
    PENDING_SIGNATURE = "PENDING_SIGNATURE"
    SIGNED = "SIGNED"
    REDEEMED = "REDEEMED"
    PROTESTED = "PROTESTED"
    VOIDED = "VOIDED"


class AmortizationMethod(StrEnum):
    """Supported installment calculation methods."""

    ZERO_INTEREST = "ZERO_INTEREST"
    SIMPLE_INTEREST = "SIMPLE_INTEREST"
    FRENCH_PRICE = "FRENCH_PRICE"


class Currency(StrEnum):
    """Supported ISO 4217 currency codes."""

    BRL = "BRL"
    USD = "USD"
    EUR = "EUR"
