"""Deterministic Finite State Machine (FSM) for Fiados transaction lifecycles."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import ClassVar

from fiados.domain.enums import InstrumentStatus, RiskDecision, TransactionState
from fiados.domain.exceptions import HashChainIntegrityError, InvalidStateTransitionError
from fiados.domain.models import StateTransitionRecord, Transaction

GENESIS_HASH = "0" * 64


class TransactionStateMachine:
    """Enforces allowed state transitions and maintains a SHA-256 chained audit trail."""

    ALLOWED_TRANSITIONS: ClassVar[dict[TransactionState, frozenset[TransactionState]]] = {
        TransactionState.DRAFT: frozenset(
            {TransactionState.EVALUATING, TransactionState.CANCELLED}
        ),
        TransactionState.EVALUATING: frozenset(
            {TransactionState.FORMALIZED, TransactionState.CANCELLED}
        ),
        TransactionState.FORMALIZED: frozenset(
            {TransactionState.ACTIVE, TransactionState.CANCELLED}
        ),
        TransactionState.ACTIVE: frozenset(
            {
                TransactionState.SETTLED,
                TransactionState.DEFAULTED,
                TransactionState.RENEGOTIATED,
            }
        ),
        TransactionState.DEFAULTED: frozenset(
            {TransactionState.SETTLED, TransactionState.RENEGOTIATED}
        ),
        TransactionState.RENEGOTIATED: frozenset(
            {TransactionState.ACTIVE, TransactionState.SETTLED, TransactionState.DEFAULTED}
        ),
        TransactionState.SETTLED: frozenset(),
        TransactionState.CANCELLED: frozenset(),
    }

    @staticmethod
    def compute_entry_hash(
        *,
        sequence: int,
        transaction_id_str: str,
        from_state: str,
        to_state: str,
        actor: str,
        reason: str,
        occurred_at_iso: str,
        previous_hash: str,
    ) -> str:
        """Compute canonical SHA-256 digest for a state transition record."""
        payload = (
            f"{sequence}|{transaction_id_str}|{from_state}|{to_state}|"
            f"{actor}|{reason}|{occurred_at_iso}|{previous_hash}"
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @classmethod
    def initialize_audit_trail(
        cls,
        transaction: Transaction,
        *,
        actor: str = "system",
        reason: str = "Transaction initialized in DRAFT state",
    ) -> StateTransitionRecord:
        """Record the genesis state transition when a transaction is created."""
        if transaction.audit_trail:
            return transaction.audit_trail[0]

        now = datetime.now(UTC)
        entry_hash = cls.compute_entry_hash(
            sequence=1,
            transaction_id_str=str(transaction.transaction_id),
            from_state="NONE",
            to_state=transaction.state.value,
            actor=actor,
            reason=reason,
            occurred_at_iso=now.isoformat(),
            previous_hash=GENESIS_HASH,
        )
        record = StateTransitionRecord(
            sequence=1,
            transaction_id=transaction.transaction_id,
            from_state=None,
            to_state=transaction.state,
            actor=actor,
            reason=reason,
            occurred_at=now,
            previous_hash=GENESIS_HASH,
            entry_hash=entry_hash,
        )
        transaction.audit_trail.append(record)
        return record

    @classmethod
    def transition(
        cls,
        transaction: Transaction,
        target_state: TransactionState,
        *,
        actor: str,
        reason: str,
    ) -> StateTransitionRecord:
        """Validate invariants, transition transaction state, and append audit record."""
        if not transaction.audit_trail:
            cls.initialize_audit_trail(transaction)

        current = transaction.state
        allowed = cls.ALLOWED_TRANSITIONS.get(current, frozenset())
        if target_state not in allowed:
            raise InvalidStateTransitionError(
                current.value,
                target_state.value,
                reason="transition not permitted by state machine matrix",
            )

        cls._check_domain_guards(transaction, target_state)

        previous_record = transaction.audit_trail[-1]
        sequence = previous_record.sequence + 1
        now = datetime.now(UTC)

        entry_hash = cls.compute_entry_hash(
            sequence=sequence,
            transaction_id_str=str(transaction.transaction_id),
            from_state=current.value,
            to_state=target_state.value,
            actor=actor,
            reason=reason,
            occurred_at_iso=now.isoformat(),
            previous_hash=previous_record.entry_hash,
        )

        record = StateTransitionRecord(
            sequence=sequence,
            transaction_id=transaction.transaction_id,
            from_state=current,
            to_state=target_state,
            actor=actor,
            reason=reason,
            occurred_at=now,
            previous_hash=previous_record.entry_hash,
            entry_hash=entry_hash,
        )

        transaction.state = target_state
        transaction.updated_at = now
        transaction.audit_trail.append(record)
        return record

    @classmethod
    def _check_domain_guards(
        cls,
        transaction: Transaction,
        target_state: TransactionState,
    ) -> None:
        """Enforce domain preconditions before entering sensitive states."""
        if target_state == TransactionState.FORMALIZED:
            if transaction.risk_decision not in {
                RiskDecision.APPROVED,
                RiskDecision.CONDITIONED,
            }:
                raise InvalidStateTransitionError(
                    transaction.state.value,
                    target_state.value,
                    reason="risk decision must be APPROVED or CONDITIONED before formalization",
                )
            if not transaction.promissory_notes:
                raise InvalidStateTransitionError(
                    transaction.state.value,
                    target_state.value,
                    reason="at least one digital promissory note must be compiled",
                )

        if target_state == TransactionState.ACTIVE:
            if not transaction.promissory_notes:
                raise InvalidStateTransitionError(
                    transaction.state.value,
                    target_state.value,
                    reason="cannot activate transaction without promissory notes",
                )
            unsigned = [
                n for n in transaction.promissory_notes if n.status != InstrumentStatus.SIGNED
            ]
            if unsigned:
                raise InvalidStateTransitionError(
                    transaction.state.value,
                    target_state.value,
                    reason="all promissory notes must be electronically signed before activation",
                )

    @classmethod
    def verify_audit_chain(cls, transaction: Transaction) -> bool:
        """Verify cryptographic continuity of the transaction's state transition log."""
        expected_prev = GENESIS_HASH
        for idx, record in enumerate(transaction.audit_trail, start=1):
            if record.sequence != idx:
                raise HashChainIntegrityError(
                    f"Sequence mismatch at index {idx}: found sequence {record.sequence}."
                )
            if record.previous_hash != expected_prev:
                raise HashChainIntegrityError(
                    f"Broken previous_hash link at sequence {record.sequence}."
                )
            from_str = record.from_state.value if record.from_state is not None else "NONE"
            recomputed = cls.compute_entry_hash(
                sequence=record.sequence,
                transaction_id_str=str(record.transaction_id),
                from_state=from_str,
                to_state=record.to_state.value,
                actor=record.actor,
                reason=record.reason,
                occurred_at_iso=record.occurred_at.isoformat(),
                previous_hash=record.previous_hash,
            )
            if recomputed != record.entry_hash:
                raise HashChainIntegrityError(
                    f"Digest mismatch at sequence {record.sequence}: expected {recomputed}, "
                    f"found {record.entry_hash}."
                )
            expected_prev = record.entry_hash
        return True
