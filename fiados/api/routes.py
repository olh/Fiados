"""Application orchestration service and HTTP route handlers."""

from __future__ import annotations

from uuid import UUID, uuid4

from fiados.api.schemas import CreateTransactionRequest, TransactionSummaryResponse
from fiados.domain.enums import RiskDecision, TransactionState
from fiados.domain.models import Transaction
from fiados.instruments.geneva_note import GenevaPromissoryNoteCompiler
from fiados.instruments.signature_spi import SignatureProvider, SyntheticSignatureAdapter
from fiados.ledger.amortization import AmortizationEngine
from fiados.ledger.repository import InMemoryTransactionRepository, TransactionRepository
from fiados.ledger.state_machine import TransactionStateMachine
from fiados.risk.pipeline import RiskOrchestrator
from fiados.sandbox.fixtures import SyntheticSandboxFactory


class TransactionOrchestrationService:
    """Coordinates domain workflows across ledger, risk, and instrument engines."""

    def __init__(
        self,
        *,
        repository: TransactionRepository | None = None,
        risk_orchestrator: RiskOrchestrator | None = None,
        signature_provider: SignatureProvider | None = None,
    ) -> None:
        self.repository: TransactionRepository = repository or InMemoryTransactionRepository()
        self.risk_orchestrator: RiskOrchestrator = risk_orchestrator or RiskOrchestrator()
        self.signature_provider: SignatureProvider = (
            signature_provider or SyntheticSignatureAdapter()
        )

    def create_transaction(
        self, request: CreateTransactionRequest
    ) -> TransactionSummaryResponse:
        """Create a new DRAFT transaction and initialize its hash-chained audit log."""
        idx = request.synthetic_persona_index
        tx = Transaction(
            transaction_id=uuid4(),
            external_order_ref=request.external_order_ref,
            maker=SyntheticSandboxFactory.create_maker(index=idx),
            beneficiary=SyntheticSandboxFactory.create_beneficiary(index=idx),
            principal_cents=request.principal_cents,
            currency=request.currency,
            installment_count=request.installment_count,
            monthly_interest_rate=request.monthly_interest_rate,
            amortization_method=request.amortization_method,
        )
        tx.schedule = AmortizationEngine.generate_schedule(
            principal_cents=request.principal_cents,
            installment_count=request.installment_count,
            first_due_date=request.first_due_date,
            monthly_interest_rate=request.monthly_interest_rate,
            method=request.amortization_method,
            currency=request.currency,
        )
        TransactionStateMachine.initialize_audit_trail(tx, actor="api-gateway")
        self.repository.save(tx)
        return TransactionSummaryResponse.from_domain(tx)

    def evaluate_and_formalize(self, transaction_id: UUID) -> TransactionSummaryResponse:
        """Run risk evaluation and, if eligible, compile Geneva promissory notes."""
        tx = self._get_or_raise(transaction_id)
        TransactionStateMachine.transition(
            tx,
            TransactionState.EVALUATING,
            actor="api-gateway",
            reason="Triggered risk and eligibility evaluation",
        )
        report = self.risk_orchestrator.evaluate_transaction(tx)
        if report.decision in {RiskDecision.APPROVED, RiskDecision.CONDITIONED}:
            notes = GenevaPromissoryNoteCompiler.compile_series_for_transaction(tx)
            tx.promissory_notes = notes
            TransactionStateMachine.transition(
                tx,
                TransactionState.FORMALIZED,
                actor="instrument-engine",
                reason=f"Compiled {len(notes)} Geneva Convention promissory notes",
            )
        self.repository.save(tx)
        return TransactionSummaryResponse.from_domain(tx)

    def sign_and_activate(self, transaction_id: UUID) -> TransactionSummaryResponse:
        """Electronically sign all compiled promissory notes and transition to ACTIVE."""
        tx = self._get_or_raise(transaction_id)
        tx.promissory_notes = [
            self.signature_provider.sign_note(note) for note in tx.promissory_notes
        ]
        TransactionStateMachine.transition(
            tx,
            TransactionState.ACTIVE,
            actor="signature-service",
            reason="All promissory notes electronically signed and verified",
        )
        self.repository.save(tx)
        return TransactionSummaryResponse.from_domain(tx)

    def get_summary(self, transaction_id: UUID) -> TransactionSummaryResponse:
        """Return current summary for a transaction."""
        tx = self._get_or_raise(transaction_id)
        return TransactionSummaryResponse.from_domain(tx)

    def _get_or_raise(self, transaction_id: UUID) -> Transaction:
        tx = self.repository.get_by_id(transaction_id)
        if tx is None:
            raise KeyError(f"Transaction {transaction_id} not found.")
        return tx
