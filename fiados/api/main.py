"""FastAPI application entrypoint for Fiados orchestration service."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any
from uuid import UUID

from fiados import __version__, get_settings
from fiados.api.routes import TransactionOrchestrationService
from fiados.api.schemas import CreateTransactionRequest

service = TransactionOrchestrationService()


def create_app() -> Any:
    """Instantiate FastAPI application when FastAPI runtime is available."""
    from fastapi import FastAPI, HTTPException

    settings = get_settings()
    application = FastAPI(
        title="Fiados Orchestration Engine",
        description=(
            "Open-source universal deferred-payment (BNPL) and digital promissory note "
            "orchestration API."
        ),
        version=__version__,
    )

    @application.get("/health", tags=["system"])
    def healthcheck() -> dict[str, object]:
        return {
            "status": "ok",
            "version": __version__,
            "environment": settings.env,
            "synthetic_mode": settings.synthetic_mode,
        }

    @application.post("/v1/transactions", tags=["transactions"], status_code=201)
    def create_transaction_endpoint(payload: CreateTransactionRequest) -> dict[str, object]:
        summary = service.create_transaction(payload)
        return asdict(summary)

    @application.post("/v1/transactions/{transaction_id}/formalize", tags=["transactions"])
    def formalize_transaction_endpoint(transaction_id: UUID) -> dict[str, object]:
        try:
            summary = service.evaluate_and_formalize(transaction_id)
            return asdict(summary)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @application.post("/v1/transactions/{transaction_id}/activate", tags=["transactions"])
    def activate_transaction_endpoint(transaction_id: UUID) -> dict[str, object]:
        try:
            summary = service.sign_and_activate(transaction_id)
            return asdict(summary)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @application.get("/v1/transactions/{transaction_id}", tags=["transactions"])
    def get_transaction_endpoint(transaction_id: UUID) -> dict[str, object]:
        try:
            summary = service.get_summary(transaction_id)
            return asdict(summary)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    return application


try:
    app = create_app()
except ModuleNotFoundError:  # Allows importing orchestration service without FastAPI installed
    app = None
