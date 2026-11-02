# Contributing to Fiados

Thank you for your interest in contributing to **Fiados**!

## Privacy & Synthetic-Only Policy

Fiados maintains a strict **Zero-PII** development policy:
- Never include real consumer names, national ID numbers, emails, phone numbers, or addresses in code, tests, fixtures, or commit messages.
- Use `fiados.sandbox.fixtures.SyntheticSandboxFactory` and RFC 2606 reserved domains (`.example`) for all tests and local simulations.
- Never commit API keys, private cryptographic keys, or production `.env` files.

## Development Workflow

1. Fork and clone the repository.
2. Create a feature branch (`git checkout -b feat/your-feature`).
3. Ensure all new domain logic includes unit tests under `tests/`.
4. Run formatting, linting, type-checking, and tests before opening a Pull Request:
   ```bash
   ruff check .
   ruff format --check .
   mypy fiados/
   pytest --cov=fiados tests/
   ```

## License

By contributing to Fiados, you agree that your contributions will be licensed under its [MIT License](LICENSE).
