"""Runtime configuration for Fiados orchestration engine."""

from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache


@dataclass(frozen=True, slots=True)
class Settings:
    """Immutable runtime settings loaded from environment variables."""

    env: str = "sandbox"
    synthetic_mode: bool = True
    log_level: str = "INFO"
    database_url: str = (
        "postgresql+psycopg://fiados_dev:fiados_sandbox_local@localhost:5432/fiados_sandbox"
    )
    redis_url: str = "redis://localhost:6379/0"
    webhook_hmac_secret: str = "whsec_sandbox_synthetic_000000000000000000000000"
    signer_key_id: str = "sandbox-key-ed25519-01"
    default_max_ticket_cents: int = 500_000
    default_max_installments: int = 12
    default_max_dti_ratio: Decimal = Decimal("0.30")

    @classmethod
    def from_env(cls) -> Settings:
        """Instantiate settings from environment variables with safe sandbox defaults."""
        synthetic_raw = os.getenv("FIADOS_SYNTHETIC_MODE", "true").strip().lower()
        return cls(
            env=os.getenv("FIADOS_ENV", "sandbox"),
            synthetic_mode=synthetic_raw in {"1", "true", "yes", "on"},
            log_level=os.getenv("FIADOS_LOG_LEVEL", "INFO").upper(),
            database_url=os.getenv(
                "FIADOS_DATABASE_URL",
                "postgresql+psycopg://fiados_dev:fiados_sandbox_local@localhost:5432/fiados_sandbox",
            ),
            redis_url=os.getenv("FIADOS_REDIS_URL", "redis://localhost:6379/0"),
            webhook_hmac_secret=os.getenv(
                "FIADOS_WEBHOOK_HMAC_SECRET",
                "whsec_sandbox_synthetic_000000000000000000000000",
            ),
            signer_key_id=os.getenv("FIADOS_SIGNER_KEY_ID", "sandbox-key-ed25519-01"),
            default_max_ticket_cents=int(os.getenv("FIADOS_DEFAULT_MAX_TICKET_CENTS", "500000")),
            default_max_installments=int(os.getenv("FIADOS_DEFAULT_MAX_INSTALLMENTS", "12")),
            default_max_dti_ratio=Decimal(os.getenv("FIADOS_DEFAULT_MAX_DTI_RATIO", "0.30")),
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached singleton settings instance."""
    return Settings.from_env()
