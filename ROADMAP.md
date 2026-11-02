# Fiados Development Roadmap

This document tracks the planned architecture and engineering milestones for **Fiados** (~160 hours of planned independent development).

---

## Sprint 1: Core Domain & Persistent Ledger Layer (40h) — *In Progress*
- [x] Define core domain enumerations (`TransactionState`, `RiskDecision`, `InstrumentStatus`, `AmortizationMethod`, `Currency`).
- [x] Implement deterministic finite-state machine (`TransactionStateMachine`) with SHA-256 hash-chained audit records.
- [x] Implement exact-cent installment calculator (`AmortizationEngine`) supporting Zero-Interest, Simple Interest, and French Price amortization.
- [ ] Implement SQLAlchemy 2.0 async ORM models (`TransactionModel`, `PromissoryNoteModel`, `AuditTrailModel`) backed by PostgreSQL.
- [ ] Add Alembic migration scripts and transactional unit-of-work repository implementation.
- [ ] Add property-based state machine fuzzing tests with `hypothesis`.

## Sprint 2: Legal Credit Instrument Engine & Cryptographic Audit (40h) — *Planned*
- [x] Implement Geneva Convention Uniform Law (Article 75) structural validator and canonical SHA-256 digest compiler.
- [x] Define `SignatureProvider` SPI and deterministic HMAC-SHA256 sandbox adapter.
- [ ] Build PDF/A-1b document renderer for printable and archivable digital promissory notes with embedded metadata and QR verification codes.
- [ ] Implement asymmetric Ed25519 / RSA-PSS keypair signing adapter and RFC 3161 trusted timestamping authority (TSA) client interface.
- [ ] Implement endorsement (`endosso`) and guarantee (`aval`) chain-of-title extensions per Articles 11–20 and 30–32 of the Geneva Uniform Law.

## Sprint 3: Pluggable Risk & Eligibility Middleware (30h) — *Planned*
- [x] Implement base `RiskOrchestrator` and core heuristic rules (`MaxTicketLimitRule`, `InstallmentCountCapRule`, `DebtToIncomeRatioRule`).
- [x] Implement deterministic zero-PII `SyntheticKYCAdapter`.
- [ ] Add declarative JSON/YAML policy configuration loader per merchant profile.
- [ ] Implement sliding-window velocity and concurrency limiters backed by Redis.
- [ ] Add manual-review queue states and operator decision resolution endpoints.

## Sprint 4: Asynchronous Merchant Integration & Webhook Bus (30h) — *Planned*
- [x] Implement HMAC-SHA256 webhook payload signer with replay-window protection (`WebhookSigner`).
- [x] Implement exponential backoff retry schedule calculator.
- [ ] Build async background worker queue for reliable outbound HTTP webhook delivery with dead-letter queue (DLQ) persistence.
- [ ] Implement idempotency-key middleware (`Idempotency-Key` HTTP header) for all mutating `POST` endpoints.
- [ ] Create merchant settlement reconciliation endpoints (partial payments, early payoff discount calculation, default protest triggers).

## Sprint 5: Developer Tooling, CLI & OpenAPI SDKs (20h) — *Planned*
- [x] Create initial `python -m fiados.manage` CLI with `migrate` and `simulate` commands.
- [ ] Expand CLI with interactive audit-chain verifier, note inspector, and webhook replay debugger.
- [ ] Publish complete OpenAPI 3.1 specification and automated integration test suite in GitHub Actions CI.
- [ ] Package and publish initial release to PyPI.
