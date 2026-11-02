"""Unit tests for HMAC-SHA256 webhook signing, replay protection, and retry backoff."""

from __future__ import annotations

import pytest

from fiados.domain.exceptions import SignatureVerificationError
from fiados.webhooks.dispatcher import WebhookEvent, compute_backoff_seconds
from fiados.webhooks.signer import WebhookSigner


def test_webhook_sign_and_verify_roundtrip() -> None:
    signer = WebhookSigner("whsec_test_secret_123", tolerance_seconds=300)
    event = WebhookEvent(event_type="transaction.activated", data={"status": "ACTIVE"})
    body = event.to_json()

    header = signer.sign_payload(body, timestamp=1_700_000_000)
    assert signer.verify_header(body, header, current_timestamp=1_700_000_120) is True


def test_webhook_replay_attack_outside_window_rejected() -> None:
    signer = WebhookSigner("whsec_test_secret_123", tolerance_seconds=300)
    body = '{"event":"test"}'
    header = signer.sign_payload(body, timestamp=1_700_000_000)

    with pytest.raises(SignatureVerificationError, match="replay tolerance"):
        signer.verify_header(body, header, current_timestamp=1_700_000_500)


def test_exponential_backoff_calculation() -> None:
    assert compute_backoff_seconds(1, base_seconds=2.0) == 2.0
    assert compute_backoff_seconds(2, base_seconds=2.0) == 4.0
    assert compute_backoff_seconds(4, base_seconds=2.0) == 16.0
    assert compute_backoff_seconds(20, base_seconds=2.0, max_seconds=60.0) == 60.0
