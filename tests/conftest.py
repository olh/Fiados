"""Shared synthetic fixtures for Fiados unit and integration tests."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

from fiados.domain.enums import Currency, InstrumentStatus
from fiados.domain.models import Address, DigitalPromissoryNote, Party, Transaction


def make_synthetic_maker() -> Party:
    """Create a synthetic debtor/maker persona with zero real PII."""
    return Party(
        party_id="syn-maker-001",
        legal_name="Alex Example Debtor",
        tax_id="000.000.000-00",
        email="alex.debtor@sandbox.example",
        address=Address(
            street="100 Sandbox Avenue",
            city="Porto Alegre",
            state="RS",
            postal_code="90000-000",
            country="BR",
        ),
        declared_monthly_income_cents=650_000,
    )


def make_synthetic_beneficiary() -> Party:
    """Create a synthetic creditor/beneficiary merchant with zero real PII."""
    return Party(
        party_id="syn-merchant-001",
        legal_name="Horizon Commerce Sandbox Ltda",
        tax_id="00.000.000/0001-00",
        email="billing@horizon-merchant.example",
        address=Address(
            street="200 Innovation Way",
            city="Foz do Iguacu",
            state="PR",
            postal_code="85850-000",
            country="BR",
        ),
    )


def make_synthetic_transaction(principal_cents: int = 120_000) -> Transaction:
    """Instantiate a synthetic DRAFT transaction."""
    return Transaction(
        transaction_id=uuid4(),
        external_order_ref="ORD-SANDBOX-2026-001",
        maker=make_synthetic_maker(),
        beneficiary=make_synthetic_beneficiary(),
        principal_cents=principal_cents,
        currency=Currency.BRL,
        installment_count=3,
        monthly_interest_rate=Decimal("0.015"),
    )


def make_synthetic_note(
    transaction: Transaction,
    *,
    status: InstrumentStatus = InstrumentStatus.COMPILED,
) -> DigitalPromissoryNote:
    """Instantiate a synthetic digital promissory note for testing."""
    assert transaction.maker is not None
    assert transaction.beneficiary is not None
    return DigitalPromissoryNote(
        note_id=uuid4(),
        transaction_id=transaction.transaction_id,
        series_number=1,
        total_in_series=1,
        title_clause="PROMISSORY NOTE",
        unconditional_promise_text=(
            "On 2026-12-01, I unconditionally promise to pay by this sole Promissory Note "
            "to the order of Horizon Commerce Sandbox Ltda the sum of BRL 1200.00."
        ),
        amount_cents=transaction.principal_cents,
        currency=transaction.currency,
        maturity_date=date(2026, 12, 1),
        place_of_payment="Foz do Iguacu/PR - BR",
        place_of_issue="Porto Alegre/RS - BR",
        issue_date=date(2026, 10, 30),
        maker=transaction.maker,
        beneficiary=transaction.beneficiary,
        canonical_sha256="a" * 64,
        status=status,
    )
