"""Pluggable risk evaluation rule chain and decisioning orchestrator."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from fiados.domain.enums import RiskDecision
from fiados.domain.models import Transaction
from fiados.risk.kyc_spi import KYCProvider, KYCVerificationResult, SyntheticKYCAdapter


@dataclass(frozen=True, slots=True)
class RuleOutcome:
    """Result of evaluating a single policy rule in the risk pipeline."""

    rule_name: str
    decision: RiskDecision
    reason: str
    score_delta: int = 0


@dataclass(frozen=True, slots=True)
class RiskEvaluationReport:
    """Consolidated report emitted by the RiskOrchestrator."""

    decision: RiskDecision
    final_score: int
    kyc_result: KYCVerificationResult
    rule_outcomes: tuple[RuleOutcome, ...]


class RiskRule(Protocol):
    """Protocol for composable credit and eligibility policy rules."""

    def evaluate(self, transaction: Transaction) -> RuleOutcome:
        """Evaluate rule against a transaction candidate."""
        ...


class MaxTicketLimitRule:
    """Enforces maximum principal amount per transaction."""

    def __init__(self, max_ticket_cents: int = 500_000) -> None:
        self.max_ticket_cents = max_ticket_cents

    def evaluate(self, transaction: Transaction) -> RuleOutcome:
        if transaction.principal_cents > self.max_ticket_cents:
            return RuleOutcome(
                rule_name="MaxTicketLimitRule",
                decision=RiskDecision.REJECTED,
                reason=(
                    f"Principal ({transaction.principal_cents} cents) exceeds policy cap "
                    f"({self.max_ticket_cents} cents)."
                ),
                score_delta=-300,
            )
        return RuleOutcome(
            rule_name="MaxTicketLimitRule",
            decision=RiskDecision.APPROVED,
            reason="Principal within policy ticket limit.",
            score_delta=25,
        )


class InstallmentCountCapRule:
    """Enforces maximum number of deferred installments."""

    def __init__(self, max_installments: int = 12) -> None:
        self.max_installments = max_installments

    def evaluate(self, transaction: Transaction) -> RuleOutcome:
        if transaction.installment_count > self.max_installments:
            return RuleOutcome(
                rule_name="InstallmentCountCapRule",
                decision=RiskDecision.CONDITIONED,
                reason=(
                    f"Requested installments ({transaction.installment_count}) exceed "
                    f"standard cap ({self.max_installments})."
                ),
                score_delta=-80,
            )
        return RuleOutcome(
            rule_name="InstallmentCountCapRule",
            decision=RiskDecision.APPROVED,
            reason="Installment count within standard policy.",
            score_delta=15,
        )


class DebtToIncomeRatioRule:
    """Checks estimated monthly installment burden against declared monthly income."""

    def __init__(self, max_dti_ratio: Decimal = Decimal("0.30")) -> None:
        self.max_dti_ratio = max_dti_ratio

    def evaluate(self, transaction: Transaction) -> RuleOutcome:
        maker = transaction.maker
        if maker is None or maker.declared_monthly_income_cents <= 0:
            return RuleOutcome(
                rule_name="DebtToIncomeRatioRule",
                decision=RiskDecision.MANUAL_REVIEW,
                reason="Maker monthly income not declared or zero.",
                score_delta=-50,
            )

        estimated_monthly_cents = Decimal(transaction.principal_cents) / Decimal(
            max(1, transaction.installment_count)
        )
        dti = estimated_monthly_cents / Decimal(maker.declared_monthly_income_cents)

        if dti > self.max_dti_ratio * Decimal("1.5"):
            return RuleOutcome(
                rule_name="DebtToIncomeRatioRule",
                decision=RiskDecision.REJECTED,
                reason=f"Estimated DTI ratio ({dti:.2f}) severely exceeds policy threshold.",
                score_delta=-250,
            )
        if dti > self.max_dti_ratio:
            return RuleOutcome(
                rule_name="DebtToIncomeRatioRule",
                decision=RiskDecision.CONDITIONED,
                reason=f"Estimated DTI ratio ({dti:.2f}) requires down-payment or longer term.",
                score_delta=-60,
            )
        return RuleOutcome(
            rule_name="DebtToIncomeRatioRule",
            decision=RiskDecision.APPROVED,
            reason=f"Estimated DTI ratio ({dti:.2f}) within healthy limit.",
            score_delta=40,
        )


DECISION_PRECEDENCE: dict[RiskDecision, int] = {
    RiskDecision.APPROVED: 0,
    RiskDecision.CONDITIONED: 1,
    RiskDecision.MANUAL_REVIEW: 2,
    RiskDecision.REJECTED: 3,
}


class RiskOrchestrator:
    """Coordinates KYC verification and sequential risk rule evaluation."""

    def __init__(
        self,
        *,
        kyc_provider: KYCProvider | None = None,
        rules: list[RiskRule] | None = None,
    ) -> None:
        self._kyc_provider: KYCProvider = kyc_provider or SyntheticKYCAdapter()
        self._rules: list[RiskRule] = (
            rules
            if rules is not None
            else [
                MaxTicketLimitRule(),
                InstallmentCountCapRule(),
                DebtToIncomeRatioRule(),
            ]
        )

    def evaluate_transaction(self, transaction: Transaction) -> RiskEvaluationReport:
        """Run KYC check and policy rules, updating transaction risk fields."""
        if transaction.maker is None:
            raise ValueError("Transaction must have a maker assigned before risk evaluation.")

        kyc_result = self._kyc_provider.verify_party(transaction.maker)
        if not kyc_result.verified:
            transaction.risk_decision = RiskDecision.REJECTED
            transaction.risk_score = kyc_result.identity_score
            return RiskEvaluationReport(
                decision=RiskDecision.REJECTED,
                final_score=kyc_result.identity_score,
                kyc_result=kyc_result,
                rule_outcomes=(),
            )

        outcomes: list[RuleOutcome] = []
        worst_decision = RiskDecision.APPROVED
        running_score = kyc_result.identity_score

        for rule in self._rules:
            outcome = rule.evaluate(transaction)
            outcomes.append(outcome)
            running_score += outcome.score_delta
            if DECISION_PRECEDENCE[outcome.decision] > DECISION_PRECEDENCE[worst_decision]:
                worst_decision = outcome.decision

        clamped_score = max(0, min(1000, running_score))
        transaction.risk_decision = worst_decision
        transaction.risk_score = clamped_score

        return RiskEvaluationReport(
            decision=worst_decision,
            final_score=clamped_score,
            kyc_result=kyc_result,
            rule_outcomes=tuple(outcomes),
        )
