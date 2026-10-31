"""Unit tests for the deterministic transaction state machine and SHA-256 hash chain."""

from __future__ import annotations

from dataclasses import replace

import pytest

from fiados.domain.enums import InstrumentStatus, RiskDecision, TransactionState
from fiados.domain.exceptions import HashChainIntegrityError, InvalidStateTransitionError
from fiados.ledger.state_machine import GENESIS_HASH, TransactionStateMachine
from tests.conftest import make_synthetic_note, make_synthetic_transaction


def test_happy_path_lifecycle_and_hash_chain() -> None:
    tx = make_synthetic_transaction()
    genesis = TransactionStateMachine.initialize_audit_trail(tx, actor="merchant-api")
    assert genesis.sequence == 1
    assert genesis.previous_hash == GENESIS_HASH
    assert tx.state == TransactionState.DRAFT

    # DRAFT -> EVALUATING
    TransactionStateMachine.transition(
        tx,
        TransactionState.EVALUATING,
        actor="risk-engine",
        reason="Starting eligibility evaluation",
    )
    assert tx.state == TransactionState.EVALUATING

    # Satisfy guards for FORMALIZED
    tx.risk_decision = RiskDecision.APPROVED
    note = make_synthetic_note(tx, status=InstrumentStatus.COMPILED)
    tx.promissory_notes.append(note)

    # EVALUATING -> FORMALIZED
    TransactionStateMachine.transition(
        tx,
        TransactionState.FORMALIZED,
        actor="instrument-engine",
        reason="Promissory note compiled",
    )
    assert tx.state == TransactionState.FORMALIZED

    # Sign note to satisfy guard for ACTIVE
    tx.promissory_notes[0] = replace(note, status=InstrumentStatus.SIGNED)

    # FORMALIZED -> ACTIVE
    TransactionStateMachine.transition(
        tx,
        TransactionState.ACTIVE,
        actor="signature-webhook",
        reason="Maker signed digital promissory note",
    )
    assert tx.state == TransactionState.ACTIVE

    # ACTIVE -> SETTLED
    TransactionStateMachine.transition(
        tx,
        TransactionState.SETTLED,
        actor="settlement-worker",
        reason="All installments paid in full",
    )
    assert tx.state == TransactionState.SETTLED
    assert len(tx.audit_trail) == 5
    assert TransactionStateMachine.verify_audit_chain(tx) is True


def test_illegal_transition_raises_error() -> None:
    tx = make_synthetic_transaction()
    with pytest.raises(InvalidStateTransitionError):
        TransactionStateMachine.transition(
            tx,
            TransactionState.SETTLED,
            actor="attacker",
            reason="Skip evaluation and formalization",
        )


def test_formalization_without_approved_risk_fails() -> None:
    tx = make_synthetic_transaction()
    TransactionStateMachine.transition(
        tx,
        TransactionState.EVALUATING,
        actor="risk-engine",
        reason="Evaluating",
    )
    tx.risk_decision = RiskDecision.REJECTED
    tx.promissory_notes.append(make_synthetic_note(tx))

    with pytest.raises(InvalidStateTransitionError, match="APPROVED or CONDITIONED"):
        TransactionStateMachine.transition(
            tx,
            TransactionState.FORMALIZED,
            actor="instrument-engine",
            reason="Attempt formalization despite rejection",
        )


def test_tampered_audit_record_detected_by_hash_chain() -> None:
    tx = make_synthetic_transaction()
    TransactionStateMachine.transition(
        tx,
        TransactionState.EVALUATING,
        actor="risk-engine",
        reason="Evaluating",
    )
    # Tamper with the reason of the second record without updating its hash
    tampered = replace(tx.audit_trail[1], reason="Tampered reason")
    tx.audit_trail[1] = tampered

    with pytest.raises(HashChainIntegrityError, match="Digest mismatch"):
        TransactionStateMachine.verify_audit_chain(tx)
