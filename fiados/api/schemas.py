"""API request and response payloads for Fiados transaction orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from fiados.domain.enums import (
    AmortizationMethod,
    Currency,
    RiskDecision,
    TransactionState,
)
from fiados.domain.models import Transaction


@dataclass(frozen=True, slots=True)
class CreateTransactionRequest:
    """Payload to initiate a new deferred-payment transaction."""

    external_order_ref: str
    principal_cents: int
    installment_count: int = 3
    first_due_date: date = date(2026, 12, 15)
    monthly_interest_rate: Decimal = Decimal("0.00")
    amortization_method: AmortizationMethod = AmortizationMethod.ZERO_INTEREST
    currency: Currency = Currency.BRL
    synthetic_persona_index: int = 1


@dataclass(frozen=True, slots=True)
class TransactionSummaryResponse:
    """Serializable summary of a transaction and its promissory notes."""

    transaction_id: str
    external_order_ref: str
    state: TransactionState
    principal_cents: int
    currency: Currency
    installment_count: int
    risk_decision: RiskDecision | None
    risk_score: int | None
    promissory_note_count: int
    audit_chain_length: int

    @classmethod
    def from_domain(cls, tx: Transaction) -> TransactionSummaryResponse:
        """Convert domain Transaction aggregate into a summary response DTO."""
        return cls(
            transaction_id=str(tx.transaction_id),
            external_order_ref=tx.external_order_ref,
            state=tx.state,
            principal_cents=tx.principal_cents,
            currency=tx.currency,
            installment_count=tx.installment_count,
            risk_decision=tx.risk_decision,
            risk_score=tx.risk_score,
            promissory_note_count=len(tx.promissory_notes),
            audit_chain_length=len(tx.audit_trail),
        )
