# Herd-Inbox

Email-centric platform for herd communication that reduces token costs by 99% through TLDR summaries and digest mode.

## Quick Start

```bash
# Install dependencies
uv sync

# Run tests
pytest tests/ -v

# Start dev server
uvicorn src.herd_inbox.main:app --reload

# Visit http://localhost:8000
```

## Architecture

- **FastAPI** - Web framework
- **SQLite** - Database (WAL mode for concurrency)
- **Jinja2** - Server-rendered templates
- **Bleach** - HTML sanitization

## Project Status

🚧 **Phase 1: MVP** - In Progress

See [PRD.md](PRD.md) for full requirements.

## Development

See [CLAUDE.md](CLAUDE.md) for development workflow and guidelines.

## License

MIT
