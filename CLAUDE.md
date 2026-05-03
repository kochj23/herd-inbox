# Herd-Inbox Development Guide

## Project Overview

Email-centric platform for herd communication. Core principle: **Email is the data. The web layer is the lens.**

**Goal:** Reduce token costs by 99% (50 tokens vs 10K per email scan decision)

## Development Workflow

### Issue Tracking

We use **GitHub Issues** for issue tracking: [github.com/mostlycopypaste/herd-inbox/issues](https://github.com/mostlycopypaste/herd-inbox/issues)

```bash
# List open issues
gh issue list

# View issue details
gh issue view <number>

# Comment on an issue
gh issue comment <number> --body "Starting work on this"

# Claim an issue
gh issue edit <number> --add-assignee @me
```

### TDD Workflow

**Always follow Test-Driven Development:**

1. Pick issue from `gh issue list`
2. Create feature branch: `feat/<short-description>`
3. **Write tests first** (this is mandatory)
4. Implement feature to make tests pass
5. Run tests: `pytest tests/ -v --cov`
6. Create PR with template
7. Peer review (2+ reviewers for security issues)
8. Merge after CI passes

### Branch Strategy

```
feat/<short-description>
fix/<short-description>
chore/<short-description>
```

Squash merge to main. Delete branch after merge.

### Testing Requirements

- **Security module (security.py):** 100% test coverage (mandatory)
- **Overall project:** >80% test coverage
- **All tests must pass** before PR approval

Run coverage report:
```bash
pytest tests/ --cov=herd_inbox --cov-report=term-missing
```

## Security-First Development

**Issue #2 (Security Sanitization) is BLOCKING** - no routes can be implemented before security sanitization is complete.

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
from herd_inbox.db import init_db, get_connection, drop_tables

@pytest.fixture
def db_conn(tmp_path):
    """Empty test database, cleaned up after test."""
    db_path = tmp_path / "test.db"
    conn = init_db(db_path)
    yield conn
    conn.close()
    drop_tables(db_path)
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

Use GitHub issue comments for design decisions and progress updates:
```bash
gh issue comment <number> --body "Used bleach instead of html5lib - better XSS protection"
```

## Critical Dependencies

**Phase 1 Critical Path:**
```
#1 (Scaffolding ✅) → #1 (Database) → #2 (Security-BLOCKING) → {#4, #5, #6}
```

**Issue #2 blocks everything** - prioritize security implementation.

## Local Development

### Database

SQLite with WAL mode. Database file: `herd_inbox.db` (gitignored)

### Environment Variables

Copy `.envrc.template` to `.envrc`:
```bash
export DATABASE_URL="sqlite:///./herd_inbox.db"
export SECRET_KEY="dev-secret-key"
```

### Dev Server

```bash
uvicorn herd_inbox.main:app --reload --port 8000
```

## PR Template

```markdown
## Issue
Closes #<number>

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
- [GitHub Issues](https://github.com/mostlycopypaste/herd-inbox/issues) - Issue tracking