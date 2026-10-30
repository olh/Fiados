"""Core domain models for deferred-payment transactions and promissory notes."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from fiados.domain.enums import (
    AmortizationMethod,
    Currency,
    InstrumentStatus,
    RiskDecision,
    TransactionState,
)


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class Address:
    """Postal address for a transaction party or place of payment/issue."""

    street: str
    city: str
    state: str
    postal_code: str
    country: str = "BR"

    def formatted_locality(self) -> str:
        """Return 'City/State - Country' string used in legal credit instruments."""
        return f"{self.city}/{self.state} - {self.country}"


@dataclass(frozen=True, slots=True)
class Party:
    """Legal entity or individual participating as maker (debtor) or beneficiary (creditor)."""

    party_id: str
    legal_name: str
    tax_id: str  # Synthetic identifier in sandbox mode
    email: str
    address: Address
    declared_monthly_income_cents: int = 0


@dataclass(frozen=True, slots=True)
class Installment:
    """Single scheduled installment within an amortization schedule."""

    installment_number: int
    due_date: date
    principal_cents: int
    interest_cents: int
    total_cents: int
    paid_cents: int = 0

    @property
    def is_settled(self) -> bool:
        """Return True if the installment has been paid in full."""
        return self.paid_cents >= self.total_cents


@dataclass(frozen=True, slots=True)
class AmortizationSchedule:
    """Complete repayment schedule for a deferred-payment transaction."""

    principal_cents: int
    total_interest_cents: int
    total_payable_cents: int
    monthly_interest_rate: Decimal
    method: AmortizationMethod
    currency: Currency
    installments: tuple[Installment, ...]


@dataclass(frozen=True, slots=True)
class DigitalPromissoryNote:
    """Digital promissory note structured according to the 1930 Geneva Convention (Art. 75)."""

    note_id: UUID
    transaction_id: UUID
    series_number: int
    total_in_series: int
    title_clause: str
    unconditional_promise_text: str
    amount_cents: int
    currency: Currency
    maturity_date: date
    place_of_payment: str
    place_of_issue: str
    issue_date: date
    maker: Party
    beneficiary: Party
    canonical_sha256: str
    status: InstrumentStatus = InstrumentStatus.COMPILED
    signature_token: str | None = None
    signed_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class StateTransitionRecord:
    """Immutable audit log entry recording a state transition with hash chaining."""

    sequence: int
    transaction_id: UUID
    from_state: TransactionState | None
    to_state: TransactionState
    actor: str
    reason: str
    occurred_at: datetime
    previous_hash: str
    entry_hash: str


@dataclass(slots=True)
class Transaction:
    """Aggregate root representing a deferred-payment transaction lifecycle."""

    transaction_id: UUID = field(default_factory=uuid4)
    external_order_ref: str = ""
    maker: Party | None = None
    beneficiary: Party | None = None
    principal_cents: int = 0
    currency: Currency = Currency.BRL
    installment_count: int = 1
    monthly_interest_rate: Decimal = Decimal("0.00")
    amortization_method: AmortizationMethod = AmortizationMethod.ZERO_INTEREST
    state: TransactionState = TransactionState.DRAFT
    risk_decision: RiskDecision | None = None
    risk_score: int | None = None
    schedule: AmortizationSchedule | None = None
    promissory_notes: list[DigitalPromissoryNote] = field(default_factory=list)
    audit_trail: list[StateTransitionRecord] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)
