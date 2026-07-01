# Contributing to Herd-Inbox

Thanks for your interest in improving Herd-Inbox! This project is built by a
herd of humans and agents working together. The sections below are the short
version; the authoritative workflow lives in
[`AGENTS.md`](AGENTS.md) and [`CLAUDE.md`](CLAUDE.md).

## Development setup

```bash
# Install dependencies (including dev tools)
uv sync

# Run the test suite
pytest tests/ -v --cov

# Start the dev server
uvicorn herd_inbox.main:app --reload --port 8000
```

## Workflow

1. **Pick up work** from the backlog in [`STATUS.md`](STATUS.md).
2. **Branch** using the naming convention from `CLAUDE.md`:
   `feat/<short-description>`, `fix/<short-description>`, or
   `chore/<short-description>`.
3. **Write tests first (TDD).** New code should ship with tests; `security.py`
   requires 100% coverage.
4. **Run the quality gates** before opening a PR:
   ```bash
   ruff check .
   mypy src/
   pytest tests/ --cov
   ```
5. **Open a PR** with `gh pr create --fill` and reference the STATUS.md item.

## Guidelines

- **Security first.** All user-supplied HTML must be sanitized with `bleach`
  before rendering. See the security requirements in
  [`PRD.md`](PRD.md) §5 and the checklist in `CLAUDE.md`.
- **Keep changes focused.** One concern per PR; don't touch unrelated files.
- **Match the existing style.** `ruff` and `mypy --strict` must pass on the
  files you touch.

## Landing the plane

Follow the session-completion checklist in [`AGENTS.md`](AGENTS.md): file
follow-up work, run the quality gates, and push to remote before ending a
session.

## License

By contributing, you agree that your contributions will be licensed under the
[MIT License](LICENSE).
