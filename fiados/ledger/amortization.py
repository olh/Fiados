"""Installment and amortization schedule calculator with exact cent reconciliation."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from fiados.domain.enums import AmortizationMethod, Currency
from fiados.domain.models import AmortizationSchedule, Installment


def _add_months(base_date: date, months: int) -> date:
    """Advance date by `months` calendar months, clamping to month-end when necessary."""
    month_index = base_date.month - 1 + months
    year = base_date.year + month_index // 12
    month = month_index % 12 + 1
    # Determine max days in target month
    if month == 12:
        next_month_first = date(year + 1, 1, 1)
    else:
        next_month_first = date(year, month + 1, 1)
    max_day = (next_month_first - timedelta(days=1)).day
    day = min(base_date.day, max_day)
    return date(year, month, day)


class AmortizationEngine:
    """Generates installment repayment schedules with exact integer-cent allocation."""

    @classmethod
    def generate_schedule(
        cls,
        *,
        principal_cents: int,
        installment_count: int,
        first_due_date: date,
        monthly_interest_rate: Decimal = Decimal("0.00"),
        method: AmortizationMethod = AmortizationMethod.ZERO_INTEREST,
        currency: Currency = Currency.BRL,
    ) -> AmortizationSchedule:
        """Compute installment breakdown and reconcile rounding residuals on the final payment."""
        if principal_cents <= 0:
            raise ValueError("principal_cents must be strictly positive.")
        if installment_count < 1:
            raise ValueError("installment_count must be at least 1.")
        if monthly_interest_rate < Decimal("0"):
            raise ValueError("monthly_interest_rate cannot be negative.")

        base_principal, remainder = divmod(principal_cents, installment_count)
        installments: list[Installment] = []

        if method == AmortizationMethod.ZERO_INTEREST or monthly_interest_rate == Decimal("0"):
            for idx in range(1, installment_count + 1):
                due = _add_months(first_due_date, idx - 1)
                p_cents = base_principal + (remainder if idx == installment_count else 0)
                installments.append(
                    Installment(
                        installment_number=idx,
                        due_date=due,
                        principal_cents=p_cents,
                        interest_cents=0,
                        total_cents=p_cents,
                    )
                )
        elif method == AmortizationMethod.SIMPLE_INTEREST:
            total_interest_dec = (
                Decimal(principal_cents) * monthly_interest_rate * Decimal(installment_count)
            )
            total_interest_cents = int(
                total_interest_dec.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            )
            base_interest, int_remainder = divmod(total_interest_cents, installment_count)
            for idx in range(1, installment_count + 1):
                due = _add_months(first_due_date, idx - 1)
                p_cents = base_principal + (remainder if idx == installment_count else 0)
                i_cents = base_interest + (int_remainder if idx == installment_count else 0)
                installments.append(
                    Installment(
                        installment_number=idx,
                        due_date=due,
                        principal_cents=p_cents,
                        interest_cents=i_cents,
                        total_cents=p_cents + i_cents,
                    )
                )
        elif method == AmortizationMethod.FRENCH_PRICE:
            rate = monthly_interest_rate
            factor = (Decimal("1") + rate) ** installment_count
            pmt_dec = Decimal(principal_cents) * (rate * factor) / (factor - Decimal("1"))
            fixed_pmt_cents = int(pmt_dec.quantize(Decimal("1"), rounding=ROUND_HALF_UP))

            remaining_balance = principal_cents
            for idx in range(1, installment_count + 1):
                due = _add_months(first_due_date, idx - 1)
                interest_dec = Decimal(remaining_balance) * rate
                i_cents = int(interest_dec.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
                if idx == installment_count:
                    p_cents = remaining_balance
                    total_c = p_cents + i_cents
                else:
                    p_cents = max(0, fixed_pmt_cents - i_cents)
                    total_c = p_cents + i_cents
                remaining_balance -= p_cents
                installments.append(
                    Installment(
                        installment_number=idx,
                        due_date=due,
                        principal_cents=p_cents,
                        interest_cents=i_cents,
                        total_cents=total_c,
                    )
                )
        else:
            raise ValueError(f"Unsupported amortization method: {method}")

        total_int = sum(inst.interest_cents for inst in installments)
        total_pay = sum(inst.total_cents for inst in installments)
        return AmortizationSchedule(
            principal_cents=principal_cents,
            total_interest_cents=total_int,
            total_payable_cents=total_pay,
            monthly_interest_rate=monthly_interest_rate,
            method=method,
            currency=currency,
            installments=tuple(installments),
        )
