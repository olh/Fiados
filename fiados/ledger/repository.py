"""Repository abstractions and in-memory sandbox store for transactions."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from fiados.domain.models import Transaction


class TransactionRepository(Protocol):
    """Persistence interface for storing and retrieving transactions."""

    def save(self, transaction: Transaction) -> Transaction:
        """Persist or update a transaction aggregate."""
        ...

    def get_by_id(self, transaction_id: UUID) -> Transaction | None:
        """Retrieve a transaction by its unique identifier."""
        ...

    def list_all(self) -> list[Transaction]:
        """List all persisted transactions ordered by creation timestamp."""
        ...


class InMemoryTransactionRepository:
    """Thread-local in-memory repository used for unit tests and local sandbox runs."""

    def __init__(self) -> None:
        self._store: dict[UUID, Transaction] = {}

    def save(self, transaction: Transaction) -> Transaction:
        """Store transaction in memory."""
        self._store[transaction.transaction_id] = transaction
        return transaction

    def get_by_id(self, transaction_id: UUID) -> Transaction | None:
        """Look up transaction by UUID."""
        return self._store.get(transaction_id)

    def list_all(self) -> list[Transaction]:
        """Return all stored transactions ordered by creation time."""
        return sorted(self._store.values(), key=lambda tx: tx.created_at)
