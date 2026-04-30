# Herd-Inbox Development Guide

## Project Overview

Email-centric platform for herd communication. Core principle: **Email is the data. The web layer is the lens.**

**Goal:** Reduce token costs by 99% (50 tokens vs 10K per email scan decision)

## Development Workflow

### Issue Tracking

We use **beads** for issue tracking:

```bash
# List ready issues (no blockers)
beads:ready

# Show issue details
beads:show herd-inbox-NNN

# Update status
beads:update herd-inbox-NNN --status in_progress

# Mark completed
beads:update herd-inbox-NNN --status completed
```

### TDD Workflow

**Always follow Test-Driven Development:**

1. Pick issue from `beads:ready`
2. Create feature branch: `feature/herd-inbox-NNN-description`
3. **Write tests first** (this is mandatory)
4. Implement feature to make tests pass
5. Run tests: `pytest tests/ -v --cov`
6. Create PR with template
7. Peer review (2+ reviewers for security issues)
8. Merge after CI passes

### Branch Strategy

```
feature/herd-inbox-NNN-short-description
bugfix/herd-inbox-NNN-bug-name
```

Squash merge to main. Delete branch after merge.

### Testing Requirements

- **Security module (security.py):** 100% test coverage (mandatory)
- **Overall project:** >80% test coverage
- **All tests must pass** before PR approval

Run coverage report:
```bash
pytest tests/ --cov=src/herd_inbox --cov-report=term-missing
```

## Security-First Development

**Issue herd-inbox-003 is BLOCKING** - no routes can be implemented before security sanitization is complete.

### Security Checklist

- [ ] HTML sanitization with bleach (whitelist: p, a, em, strong, code, pre)
- [ ] CSP headers: `default-src 'self'; script-src 'none'`
- [ ] Rate limiting: 10 req/min per API key
- [ ] Audit logging for all POST requests
- [ ] 100% test coverage on security.py

### XSS Test Cases (Mandatory)

Every HTML rendering route must test:
- `<script>alert("XSS")</script>`
- `<img src="x" onerror="alert(1)">`
- `<a href="javascript:alert(1)">link</a>`
- `<a href="data:text/html,<script>alert(1)</script>">link</a>`

## Code Style

### Python (uv + ruff)

```bash
# Format code
ruff format src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

### Type Hints

Use type hints for all function signatures:

```python
def sanitize_html(html_content: str) -> str:
    ...
```

### Error Handling

Let exceptions bubble up unless you can handle them meaningfully. Don't catch and log - let FastAPI's error handlers deal with it.

### Comments

Only add comments when:
- Purpose is non-obvious
- Deviating from standard approach
- Documenting unavoidable gotchas

## Testing Patterns

### Fixtures (conftest.py)

```python
import pytest
from src.herd_inbox.db import create_tables

@pytest.fixture
def db():
    """Empty test database"""
    conn = create_tables(":memory:")
    yield conn
    conn.close()

@pytest.fixture
def seeded_db():
    """Database with test data"""
    conn = create_tables(":memory:")
    # Insert test data
    yield conn
    conn.close()
```

### Test Organization

Use Arrange-Act-Assert pattern:

```python
def test_sanitize_removes_script_tags():
    # Arrange
    malicious = '<script>alert("XSS")</script><p>Safe</p>'
    
    # Act
    result = sanitize_html(malicious)
    
    # Assert
    assert '<script>' not in result
    assert '<p>Safe</p>' in result
```

## Multi-Agent Coordination

### Agent Roles

- **Infrastructure:** Scaffolding, CI/CD, deployment
- **Security:** Sanitization, API keys, rate limiting
- **Backend:** Database, API endpoints, digest logic
- **Full-Stack:** Web routes with templates
- **DevOps:** Fly.io, backups, monitoring
- **Docs:** API docs, README updates

### Communication

Post progress to herd-inbox-standup space:
```
✅ herd-inbox-003 complete | 🚧 herd-inbox-004 50% | ⚠️ Blocked on security review
```

Use issue comments for design decisions:
```bash
beads:comments add herd-inbox-003 "Used bleach instead of html5lib - better XSS protection"
```

## Critical Dependencies

**Phase 1 Critical Path:**
```
001 (scaffolding) → 002 (database) → 003 (security-BLOCKING) → {004, 005, 006, 007}
```

**Issue 003 blocks everything** - prioritize security implementation.

## Local Development

### Database

SQLite with WAL mode:
```python
conn.execute("PRAGMA journal_mode=WAL")
```

Database file: `herd_inbox.db` (gitignored)

### Environment Variables

Copy `.envrc.template` to `.envrc`:
```bash
export DATABASE_URL="sqlite:///./herd_inbox.db"
export SECRET_KEY="dev-secret-key"
```

### Dev Server

```bash
uvicorn src.herd_inbox.main:app --reload --port 8000
```

## PR Template

```markdown
## Issue
Closes #herd-inbox-NNN

## Description
[Brief description of changes]

## Changes
- [List of changes]

## Testing
- [x] All tests pass locally
- [x] Coverage requirements met
- [x] Manual testing completed

## Checklist
- [x] Tests written first (TDD)
- [x] CI passes
- [x] Follows code style
- [x] Documentation updated

## Reviewers
@AgentRole @AgentRole
```

## Verification

### Phase 1 MVP Success Criteria

- [ ] Browse Mirror Test archive in web UI
- [ ] TLDR mode: <50 tokens to scan 50 posts
- [ ] Thread view renders sanitized HTML
- [ ] XSS attempts blocked and logged
- [ ] CI/CD passing
- [ ] Security test coverage: 100%
- [ ] Overall coverage: >80%
- [ ] Response time: <200ms for inbox

## Resources

- [PRD.md](PRD.md) - Full requirements
- [PROPOSAL.md](PROPOSAL.md) - Original proposal
- [Plan](/Users/kduane/.claude/plans/delightful-finding-wand.md) - Implementation plan
- [API Docs](docs/API.md) - API reference (Phase 2+)
