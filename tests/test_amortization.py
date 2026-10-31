"""Unit tests for installment amortization schedule calculations."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from fiados.domain.enums import AmortizationMethod
from fiados.ledger.amortization import AmortizationEngine


def test_zero_interest_exact_cent_reconciliation() -> None:
    # 100.00 BRL (10,000 cents) across 3 installments -> 3333, 3333, 3334
    schedule = AmortizationEngine.generate_schedule(
        principal_cents=10_000,
        installment_count=3,
        first_due_date=date(2026, 11, 15),
        method=AmortizationMethod.ZERO_INTEREST,
    )
    assert schedule.total_interest_cents == 0
    assert schedule.total_payable_cents == 10_000
    assert [i.principal_cents for i in schedule.installments] == [3333, 3333, 3334]
    assert [i.due_date for i in schedule.installments] == [
        date(2026, 11, 15),
        date(2026, 12, 15),
        date(2027, 1, 15),
    ]


def test_simple_interest_schedule() -> None:
    schedule = AmortizationEngine.generate_schedule(
        principal_cents=30_000,
        installment_count=3,
        first_due_date=date(2026, 11, 10),
        monthly_interest_rate=Decimal("0.02"),
        method=AmortizationMethod.SIMPLE_INTEREST,
    )
    # 2% per month * 3 months = 6% of 30,000 = 1,800 cents total interest (600/month)
    assert schedule.total_interest_cents == 1_800
    assert schedule.total_payable_cents == 31_800
    assert all(i.total_cents == 10_600 for i in schedule.installments)


def test_french_price_schedule_principal_sum_invariant() -> None:
    schedule = AmortizationEngine.generate_schedule(
        principal_cents=100_000,
        installment_count=6,
        first_due_date=date(2026, 1, 31),
        monthly_interest_rate=Decimal("0.015"),
        method=AmortizationMethod.FRENCH_PRICE,
    )
    assert sum(i.principal_cents for i in schedule.installments) == 100_000
    assert schedule.total_interest_cents > 0
    # Verify month-end clamping (Jan 31 -> Feb 28)
    assert schedule.installments[1].due_date == date(2026, 2, 28)


def test_invalid_principal_raises_value_error() -> None:
    with pytest.raises(ValueError, match="principal_cents"):
        AmortizationEngine.generate_schedule(
            principal_cents=0,
            installment_count=2,
            first_due_date=date(2026, 12, 1),
        )
