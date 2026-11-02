"""Unit tests for the pluggable risk evaluation pipeline and synthetic KYC adapter."""

from __future__ import annotations

from dataclasses import replace

from fiados.domain.enums import RiskDecision
from fiados.risk.pipeline import RiskOrchestrator
from tests.conftest import make_synthetic_maker, make_synthetic_transaction


def test_eligible_transaction_approved() -> None:
    tx = make_synthetic_transaction(principal_cents=90_000)
    orchestrator = RiskOrchestrator()
    report = orchestrator.evaluate_transaction(tx)

    assert report.decision == RiskDecision.APPROVED
    assert report.kyc_result.verified is True
    assert tx.risk_decision == RiskDecision.APPROVED
    assert report.final_score > 800


def test_excessive_ticket_size_rejected() -> None:
    tx = make_synthetic_transaction(principal_cents=850_000)
    orchestrator = RiskOrchestrator()
    report = orchestrator.evaluate_transaction(tx)

    assert report.decision == RiskDecision.REJECTED
    assert tx.risk_decision == RiskDecision.REJECTED


def test_blocklisted_synthetic_tax_id_fails_kyc() -> None:
    tx = make_synthetic_transaction(principal_cents=50_000)
    tx.maker = replace(make_synthetic_maker(), tax_id="000.000.000-99")
    orchestrator = RiskOrchestrator()
    report = orchestrator.evaluate_transaction(tx)

    assert report.decision == RiskDecision.REJECTED
    assert report.kyc_result.verified is False
    assert "SYNTHETIC_BLOCKLIST_MATCH" in report.kyc_result.flags
