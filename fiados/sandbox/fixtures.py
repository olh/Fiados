"""Deterministic zero-PII synthetic persona and transaction factories for sandbox mode."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from fiados.domain.enums import AmortizationMethod, Currency
from fiados.domain.models import Address, Party, Transaction


class SyntheticSandboxFactory:
    """Produces deterministic synthetic entities with RFC 2606 '.example' domains."""

    @staticmethod
    def create_maker(index: int = 1, *, monthly_income_cents: int = 600_000) -> Party:
        """Create a synthetic debtor/buyer persona."""
        return Party(
            party_id=f"syn-maker-{index:04d}",
            legal_name=f"Synthetic Buyer #{index}",
            tax_id=f"000.000.{index:03d}-01",
            email=f"buyer.{index}@sandbox.example",
            address=Address(
                street=f"{100 + index} Sandbox Boulevard",
                city="Porto Alegre",
                state="RS",
                postal_code="90000-000",
                country="BR",
            ),
            declared_monthly_income_cents=monthly_income_cents,
        )

    @staticmethod
    def create_beneficiary(index: int = 1) -> Party:
        """Create a synthetic merchant/beneficiary entity."""
        return Party(
            party_id=f"syn-merchant-{index:04d}",
            legal_name=f"Synthetic Merchant #{index} Ltda",
            tax_id=f"00.000.{index:03d}/0001-00",
            email=f"settlement.{index}@merchant.example",
            address=Address(
                street=f"{500 + index} Commerce Street",
                city="Sao Paulo",
                state="SP",
                postal_code="01000-000",
                country="BR",
            ),
        )

    @classmethod
    def create_transaction(
        cls,
        *,
        index: int = 1,
        principal_cents: int = 90_000,
        installment_count: int = 3,
        monthly_interest_rate: Decimal = Decimal("0.00"),
        method: AmortizationMethod = AmortizationMethod.ZERO_INTEREST,
    ) -> Transaction:
        """Create a deterministic synthetic transaction in DRAFT state."""
        deterministic_uuid = UUID(f"00000000-0000-4000-8000-{index:012d}")
        return Transaction(
            transaction_id=deterministic_uuid,
            external_order_ref=f"ORD-SYN-{index:05d}",
            maker=cls.create_maker(index=index),
            beneficiary=cls.create_beneficiary(index=index),
            principal_cents=principal_cents,
            currency=Currency.BRL,
            installment_count=installment_count,
            monthly_interest_rate=monthly_interest_rate,
            amortization_method=method,
        )

    @staticmethod
    def default_first_due_date() -> date:
        """Return a fixed synthetic first installment due date."""
        return date(2026, 12, 15)
