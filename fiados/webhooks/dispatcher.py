"""Webhook event packaging and exponential backoff retry calculation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class WebhookEvent:
    """Idempotent outbound webhook event envelope."""

    event_id: UUID = field(default_factory=uuid4)
    event_type: str = "transaction.state_changed"
    transaction_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    data: dict[str, object] = field(default_factory=dict)

    def to_json(self) -> str:
        """Serialize event envelope to deterministic JSON string."""
        payload = {
            "event_id": str(self.event_id),
            "event_type": self.event_type,
            "transaction_id": str(self.transaction_id),
            "occurred_at": self.occurred_at.isoformat(),
            "data": self.data,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def compute_backoff_seconds(
    attempt: int,
    *,
    base_seconds: float = 2.0,
    max_seconds: float = 3600.0,
) -> float:
    """Compute exponential backoff delay in seconds for webhook retry `attempt` (1-indexed)."""
    if attempt < 1:
        raise ValueError("attempt must be >= 1")
    delay = base_seconds * (2 ** (attempt - 1))
    return float(min(delay, max_seconds))
