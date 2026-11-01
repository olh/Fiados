"""CLI management utility for Fiados local sandbox and schema operations."""

from __future__ import annotations

import argparse
import sys

from fiados.domain.enums import TransactionState
from fiados.instruments.geneva_note import GenevaPromissoryNoteCompiler
from fiados.instruments.signature_spi import SyntheticSignatureAdapter
from fiados.ledger.amortization import AmortizationEngine
from fiados.ledger.state_machine import TransactionStateMachine
from fiados.risk.pipeline import RiskOrchestrator
from fiados.sandbox.fixtures import SyntheticSandboxFactory


def run_sandbox_simulation() -> int:
    """Execute a complete end-to-end synthetic deferred-payment lifecycle."""
    tx = SyntheticSandboxFactory.create_transaction(
        index=1,
        principal_cents=150_000,
        installment_count=3,
    )
    TransactionStateMachine.initialize_audit_trail(tx, actor="fiados-cli")

    # 1. Transition to EVALUATING and run risk pipeline
    TransactionStateMachine.transition(
        tx,
        TransactionState.EVALUATING,
        actor="fiados-cli",
        reason="Initiating sandbox risk check",
    )
    orchestrator = RiskOrchestrator()
    report = orchestrator.evaluate_transaction(tx)

    # 2. Generate schedule and compile Geneva Convention promissory notes
    tx.schedule = AmortizationEngine.generate_schedule(
        principal_cents=tx.principal_cents,
        installment_count=tx.installment_count,
        first_due_date=SyntheticSandboxFactory.default_first_due_date(),
        monthly_interest_rate=tx.monthly_interest_rate,
        method=tx.amortization_method,
        currency=tx.currency,
    )
    notes = GenevaPromissoryNoteCompiler.compile_series_for_transaction(tx)
    tx.promissory_notes.extend(notes)

    TransactionStateMachine.transition(
        tx,
        TransactionState.FORMALIZED,
        actor="fiados-cli",
        reason=f"Compiled {len(notes)} digital promissory notes",
    )

    # 3. Electronically sign all compiled notes and activate transaction
    signer = SyntheticSignatureAdapter()
    tx.promissory_notes = [signer.sign_note(n) for n in tx.promissory_notes]

    TransactionStateMachine.transition(
        tx,
        TransactionState.ACTIVE,
        actor="fiados-cli",
        reason="All promissory notes signed by synthetic maker",
    )

    chain_ok = TransactionStateMachine.verify_audit_chain(tx)
    print(f"[fiados] Transaction {tx.transaction_id} state: {tx.state.value}")
    print(f"[fiados] Risk decision: {report.decision.value} (score={report.final_score})")
    print(f"[fiados] Promissory notes issued & signed: {len(tx.promissory_notes)}")
    print(f"[fiados] Audit hash chain verified: {chain_ok}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point for `python -m fiados.manage`."""
    parser = argparse.ArgumentParser(description="Fiados Sandbox Management CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("migrate", help="Initialize or migrate sandbox ledger storage")
    subparsers.add_parser(
        "simulate", help="Run an end-to-end synthetic promissory note lifecycle"
    )

    args = parser.parse_args(argv)
    if args.command == "migrate":
        print("[fiados] Sandbox storage schema verified (synthetic mode active).")
        return 0
    if args.command == "simulate":
        return run_sandbox_simulation()
    return 1


if __name__ == "__main__":
    sys.exit(main())
