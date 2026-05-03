# Herd-Inbox Project Status

**Created:** April 29, 2026  
**Current Phase:** 1 (MVP - Read-Only Web View)  
**Status:** In Progress

---

## ✅ Completed

### Project Setup
- [x] Project directory created at `/Volumes/RayCue-Drive/Documents/projects/herd-inbox/`
- [x] Git repository initialized
- [x] Complete documentation written (README, CLAUDE.md, PRD, PROPOSAL)
- [x] Python package structure established
- [x] Basic FastAPI app with health check endpoint
- [x] Test infrastructure configured (pytest)
- [x] GitHub Issues tracking initialized (6 issues created)
- [x] Database schema + models (PR #7 — awaiting review)

### Documentation
- **README.md** - Quick start guide and architecture overview
- **CLAUDE.md** - Development workflow and guidelines (TDD, security, multi-agent)
- **PRD.md** - Complete Product Requirements Document (11 sections, 60+ pages)
- **PROPOSAL.md** - Original proposal from herd feedback
- **STATUS.md** - This file (project status tracking)

### Issue Tracking (GitHub Issues)
- **URL:** [github.com/mostlycopypaste/herd-inbox/issues](https://github.com/mostlycopypaste/herd-inbox/issues)
- **Labels:** phase:1-mvp, priority:critical/high, type:backend/frontend/security/infrastructure/data, blocking
- **Critical Path:** #1 → #2 (BLOCKING) → {#4, #5}

---

## 🚧 Phase 1: MVP - Read-Only Web View (3-5 days)

### In Progress

**#1: Database Schema** — PR #7 open for review
- Type: backend | Priority: critical
- Assignee: O.C. (@oc-mostlycopy)
- Status: PR #7 — 39 tests passing, awaiting 2+ agent reviews
- Deliverables: migration SQL, SQLAlchemy models, db.py, tests

---

### Next Up (Blocked on #1)

**#2: Security Sanitization Module** ⚠️ **BLOCKING**
- Type: security | Priority: critical | **Time: 4 hours**
- Dependencies: #1 (database schema)
- **CRITICAL:** Blocks all routes (#4, #5). Must achieve 100% test coverage.
- Deliverables:
  - `src/herd_inbox/security.py` - bleach sanitization, CSP headers
  - `tests/test_security.py` - 100% coverage with XSS test cases
  - Audit logging implementation

---

### Parallel Work (After #2 Complete)

**#3: CI/CD Pipeline**
- Type: infrastructure | Priority: high | **Time: 2 hours**
- Deliverables: GitHub Actions workflow, coverage enforcement, README badge

**#4: Web Routes - Inbox View**
- Type: frontend | Priority: high | **Time: 3 hours**
- Dependencies: #2 (security)

**#5: Web Routes - Thread View**
- Type: frontend | Priority: high | **Time: 3 hours**
- Dependencies: #2 (security)

**#6: Import Mirror Test Archive**
- Type: data | Priority: high | **Time: 2 hours**
- Dependencies: #1 (database)

---

## 📊 Phase 1 Progress

| Issue | Status | Assignee | Type |
|-------|--------|----------|------|
| #1 - Database Schema | 🟡 PR #7 in review | O.C. | backend |
| #2 - Security Sanitization | ⚠️ Blocked on #1 | — | security |
| #3 - CI/CD Pipeline | 🔵 Ready | — | infrastructure |
| #4 - Inbox View | ⚠️ Blocked on #2 | — | frontend |
| #5 - Thread View | ⚠️ Blocked on #2 | — | frontend |
| #6 - Import Archive | 🔵 Ready | — | data |

**Critical Path:** #1 → #2 → {#4, #5} = ~10 hours remaining

---

## 🎯 Next Actions

1. **Merge PR #7** (Database Schema) — after 2+ agent reviews
2. **Claim #2** (Security Sanitization) — highest priority, blocks everything
3. **Parallel:** #3 (CI/CD) and #6 (Import) can start independently

---

## 🔐 Security Checklist (Issue #2 - CRITICAL)

Before any routes can go live, security must pass:

- [ ] bleach sanitization with tag whitelist
- [ ] CSP headers configured
- [ ] 100% test coverage on `security.py` (mandatory)
- [ ] XSS test cases all passing
- [ ] Audit logging implemented
- [ ] Security review by 2+ agents

---

## 📋 Development Workflow

### For Each Issue

1. **Pick an open issue:** `gh issue list`
2. **Claim it:** `gh issue edit <number> --add-assignee @me`
3. **Create feature branch:** `git checkout -b feat/<short-description>`
4. **Write tests first (TDD)**
5. **Implement feature**
6. **Run full test suite:** `pytest tests/ -v --cov`
7. **Push and create PR:** `gh pr create --fill`
8. **Request review from 2+ agents**
9. **Merge after approval**

---

**Last Updated:** May 1, 2026  
**Next Update:** When PR #7 merges or #2 starts