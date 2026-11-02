"""Unit tests for Geneva Convention promissory note compilation, validation, and signing."""

from __future__ import annotations

from dataclasses import replace
from datetime import date

import pytest

from fiados.domain.enums import InstrumentStatus
from fiados.domain.exceptions import InstrumentFormalizationError, SignatureVerificationError
from fiados.instruments.geneva_note import GenevaPromissoryNoteCompiler
from fiados.instruments.signature_spi import SyntheticSignatureAdapter
from fiados.ledger.amortization import AmortizationEngine
from tests.conftest import make_synthetic_note, make_synthetic_transaction


def test_compile_series_for_transaction_produces_valid_notes() -> None:
    tx = make_synthetic_transaction(principal_cents=90_000)
    tx.schedule = AmortizationEngine.generate_schedule(
        principal_cents=tx.principal_cents,
        installment_count=3,
        first_due_date=date(2026, 12, 15),
    )
    notes = GenevaPromissoryNoteCompiler.compile_series_for_transaction(
        tx,
        issue_date=date(2026, 10, 31),
    )
    assert len(notes) == 3
    assert [n.series_number for n in notes] == [1, 2, 3]
    assert sum(n.amount_cents for n in notes) == 90_000
    assert all(len(n.canonical_sha256) == 64 for n in notes)


def test_invalid_title_clause_rejected_under_article_75() -> None:
    tx = make_synthetic_transaction()
    invalid_note = replace(make_synthetic_note(tx), title_clause="IOU RECEIPT")
    with pytest.raises(InstrumentFormalizationError, match="Art. 75\\(1\\)"):
        GenevaPromissoryNoteCompiler.validate_note(invalid_note)


def test_maturity_before_issue_date_rejected() -> None:
    tx = make_synthetic_transaction()
    invalid_note = replace(
        make_synthetic_note(tx),
        issue_date=date(2026, 12, 10),
        maturity_date=date(2026, 12, 1),
    )
    with pytest.raises(InstrumentFormalizationError, match="Art. 75\\(3\\)"):
        GenevaPromissoryNoteCompiler.validate_note(invalid_note)


def test_synthetic_signature_sign_and_verify() -> None:
    tx = make_synthetic_transaction()
    note = make_synthetic_note(tx)
    signer = SyntheticSignatureAdapter(key_secret="test-secret-01")

    signed_note = signer.sign_note(note)
    assert signed_note.status == InstrumentStatus.SIGNED
    assert signed_note.signature_token is not None
    assert signer.verify_note_signature(signed_note) is True

    # Tamper with canonical digest after signing
    tampered_note = replace(signed_note, canonical_sha256="b" * 64)
    with pytest.raises(SignatureVerificationError):
        signer.verify_note_signature(tampered_note)
