"""Geneva Convention (1930 Uniform Law, Art. 75) digital promissory note compiler and validator."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from uuid import uuid4

from fiados.domain.enums import InstrumentStatus
from fiados.domain.exceptions import InstrumentFormalizationError
from fiados.domain.models import DigitalPromissoryNote, Transaction

ACCEPTED_TITLE_CLAUSES = frozenset(
    {
        "PROMISSORY NOTE",
        "NOTA PROMISSORIA",
        "NOTA PROMISSÓRIA",
        "PAGARE",
        "PAGARÉ",
    }
)


class GenevaPromissoryNoteCompiler:
    """Compiles and validates digital promissory notes under the 1930 Geneva Convention."""

    @classmethod
    def validate_note(cls, note: DigitalPromissoryNote) -> None:
        """Validate the essential legal requirements defined in Article 75 of the Uniform Law."""
        normalized_title = note.title_clause.strip().upper()
        if normalized_title not in ACCEPTED_TITLE_CLAUSES:
            raise InstrumentFormalizationError(
                f"Invalid title clause '{note.title_clause}'. Must explicitly state "
                "'PROMISSORY NOTE' (or recognized statutory equivalent) per Art. 75(1)."
            )

        if note.amount_cents <= 0:
            raise InstrumentFormalizationError(
                "Promissory note amount_cents must be a determinate positive sum per Art. 75(2)."
            )

        if not any(
            phrase in note.unconditional_promise_text.lower()
            for phrase in ("unconditionally promise to pay", "pagarei por esta")
        ):
            raise InstrumentFormalizationError(
                "Body text must contain an explicit unconditional promise to pay per Art. 75(2)."
            )

        if note.maturity_date < note.issue_date:
            raise InstrumentFormalizationError(
                f"Maturity date ({note.maturity_date}) cannot precede issue date "
                f"({note.issue_date}) per Art. 75(3)."
            )

        if not note.place_of_payment.strip():
            raise InstrumentFormalizationError(
                "Place of payment must be explicitly specified per Art. 75(4)."
            )

        if not note.beneficiary.legal_name.strip() or not note.beneficiary.tax_id.strip():
            raise InstrumentFormalizationError(
                "Beneficiary legal name and identifier are required per Art. 75(5)."
            )

        if not note.place_of_issue.strip():
            raise InstrumentFormalizationError(
                "Place of issue must be explicitly specified per Art. 75(6)."
            )

        if not note.maker.legal_name.strip() or not note.maker.tax_id.strip():
            raise InstrumentFormalizationError(
                "Maker (issuer) legal name and identifier are required per Art. 75(7)."
            )

    @staticmethod
    def compute_canonical_sha256(
        *,
        transaction_id_str: str,
        series_number: int,
        total_in_series: int,
        title_clause: str,
        unconditional_promise_text: str,
        amount_cents: int,
        currency_code: str,
        maturity_date_iso: str,
        place_of_payment: str,
        place_of_issue: str,
        issue_date_iso: str,
        maker_tax_id: str,
        beneficiary_tax_id: str,
    ) -> str:
        """Compute deterministic SHA-256 hash over canonical JSON fields of the note."""
        canonical_dict = {
            "amount_cents": amount_cents,
            "beneficiary_tax_id": beneficiary_tax_id,
            "currency": currency_code,
            "issue_date": issue_date_iso,
            "maker_tax_id": maker_tax_id,
            "maturity_date": maturity_date_iso,
            "place_of_issue": place_of_issue,
            "place_of_payment": place_of_payment,
            "series_number": series_number,
            "title_clause": title_clause,
            "total_in_series": total_in_series,
            "transaction_id": transaction_id_str,
            "unconditional_promise_text": unconditional_promise_text,
        }
        serialized = json.dumps(canonical_dict, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @classmethod
    def compile_series_for_transaction(
        cls,
        transaction: Transaction,
        *,
        issue_date: date | None = None,
        title_clause: str = "PROMISSORY NOTE",
    ) -> list[DigitalPromissoryNote]:
        """Compile a validated series of digital promissory notes from a transaction schedule."""
        if transaction.maker is None or transaction.beneficiary is None:
            raise InstrumentFormalizationError(
                "Transaction must have both maker and beneficiary defined."
            )
        if transaction.schedule is None or not transaction.schedule.installments:
            raise InstrumentFormalizationError(
                "Transaction must have a generated amortization schedule before note compilation."
            )

        effective_issue_date = issue_date or transaction.created_at.date()
        place_of_payment = transaction.beneficiary.address.formatted_locality()
        place_of_issue = transaction.maker.address.formatted_locality()
        total_notes = len(transaction.schedule.installments)
        compiled_notes: list[DigitalPromissoryNote] = []

        for inst in transaction.schedule.installments:
            formatted_amount = f"{inst.total_cents / 100:.2f}"
            promise_text = (
                f"On {inst.due_date.isoformat()}, I, {transaction.maker.legal_name} "
                f"({transaction.maker.tax_id}), unconditionally promise to pay by this "
                f"{title_clause} ({inst.installment_number}/{total_notes}) to the order of "
                f"{transaction.beneficiary.legal_name} ({transaction.beneficiary.tax_id}) "
                f"the determinate sum of {transaction.currency.value} {formatted_amount}, "
                f"payable at {place_of_payment}."
            )
            digest = cls.compute_canonical_sha256(
                transaction_id_str=str(transaction.transaction_id),
                series_number=inst.installment_number,
                total_in_series=total_notes,
                title_clause=title_clause,
                unconditional_promise_text=promise_text,
                amount_cents=inst.total_cents,
                currency_code=transaction.currency.value,
                maturity_date_iso=inst.due_date.isoformat(),
                place_of_payment=place_of_payment,
                place_of_issue=place_of_issue,
                issue_date_iso=effective_issue_date.isoformat(),
                maker_tax_id=transaction.maker.tax_id,
                beneficiary_tax_id=transaction.beneficiary.tax_id,
            )
            note = DigitalPromissoryNote(
                note_id=uuid4(),
                transaction_id=transaction.transaction_id,
                series_number=inst.installment_number,
                total_in_series=total_notes,
                title_clause=title_clause,
                unconditional_promise_text=promise_text,
                amount_cents=inst.total_cents,
                currency=transaction.currency,
                maturity_date=inst.due_date,
                place_of_payment=place_of_payment,
                place_of_issue=place_of_issue,
                issue_date=effective_issue_date,
                maker=transaction.maker,
                beneficiary=transaction.beneficiary,
                canonical_sha256=digest,
                status=InstrumentStatus.COMPILED,
            )
            cls.validate_note(note)
            compiled_notes.append(note)

        return compiled_notes
