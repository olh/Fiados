"""Integration tests for the TransactionOrchestrationService and CLI simulation."""

from __future__ import annotations

from uuid import UUID

from fiados.api.routes import TransactionOrchestrationService
from fiados.api.schemas import CreateTransactionRequest
from fiados.domain.enums import RiskDecision, TransactionState
from fiados.manage import main as cli_main


def test_orchestration_service_full_lifecycle() -> None:
    service = TransactionOrchestrationService()
    req = CreateTransactionRequest(
        external_order_ref="ORD-API-001",
        principal_cents=120_000,
        installment_count=4,
    )
    created = service.create_transaction(req)
    assert created.state == TransactionState.DRAFT
    assert created.audit_chain_length == 1

    tx_uuid = UUID(created.transaction_id)
    formalized = service.evaluate_and_formalize(tx_uuid)
    assert formalized.state == TransactionState.FORMALIZED
    assert formalized.risk_decision == RiskDecision.APPROVED
    assert formalized.promissory_note_count == 4

    activated = service.sign_and_activate(tx_uuid)
    assert activated.state == TransactionState.ACTIVE
    assert activated.audit_chain_length == 4


def test_cli_manage_simulate_and_migrate_commands() -> None:
    assert cli_main(["migrate"]) == 0
    assert cli_main(["simulate"]) == 0
