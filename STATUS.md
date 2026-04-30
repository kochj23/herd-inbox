# Herd-Inbox Project Status

**Created:** April 29, 2026  
**Current Phase:** 1 (MVP - Read-Only Web View)  
**Status:** Ready to Begin Implementation

---

## ✅ Completed

### Project Setup
- [x] Project directory created at `/Volumes/RayCue-Drive/Documents/projects/herd-inbox/`
- [x] Git repository initialized
- [x] Complete documentation written (README, CLAUDE.md, PRD, PROPOSAL)
- [x] Python package structure established
- [x] Basic FastAPI app with health check endpoint
- [x] Test infrastructure configured (pytest)
- [x] Beads issue tracking initialized
- [x] Phase 1 issues created (herd-inbox-001 through herd-inbox-007)

### Documentation
- **README.md** - Quick start guide and architecture overview
- **CLAUDE.md** - Development workflow and guidelines (TDD, security, multi-agent)
- **PRD.md** - Complete Product Requirements Document (11 sections, 60+ pages)
- **PROPOSAL.md** - Original proposal from herd feedback
- **STATUS.md** - This file (project status tracking)

### Issue Tracking (Beads)
- **Configuration:** `.beads/config.json` with labels and workflow
- **Phase 1 Issues:** 7 issues created (001-007)
- **Critical Path Identified:** 001 → 002 → 003 (BLOCKING) → {004, 005, 006, 007}

---

## 🚧 Phase 1: MVP - Read-Only Web View (3-5 days)

### Ready to Work (No Blockers)

**herd-inbox-001: Project Scaffolding** ✅ COMPLETE
- Type: infrastructure | Priority: critical
- Agent: Infrastructure
- Status: Foundation complete, ready to mark as done
- Files: pyproject.toml, main.py, README.md, tests/

---

### Next Up (Sequential)

**herd-inbox-002: Database Schema**
- Type: backend | Priority: critical | **Time: 3 hours**
- Agent: Backend
- Dependencies: herd-inbox-001 ✅
- Status: **READY TO START**
- Deliverables:
  - `src/herd_inbox/db.py` - Table creation with WAL mode
  - `migrations/001_initial_schema.sql` - Schema SQL
  - `tests/test_db.py` - Database tests with fixtures

**herd-inbox-003: Security Sanitization Module** ⚠️ **BLOCKING**
- Type: security | Priority: critical | **Time: 4 hours**
- Agent: Security
- Dependencies: herd-inbox-002
- Status: Blocked (waiting on 002)
- **CRITICAL:** Blocks all routes (004, 005). Must achieve 100% test coverage.
- Deliverables:
  - `src/herd_inbox/security.py` - bleach sanitization, CSP headers
  - `tests/test_security.py` - 100% coverage with XSS test cases
  - Audit logging implementation

---

### Parallel Work (After 003 Complete)

These can be worked on in parallel once security (003) is complete:

**herd-inbox-004: Web Routes - Inbox View**
- Type: frontend | Priority: high | **Time: 3 hours**
- Agent: Full-Stack
- Dependencies: herd-inbox-003 ⚠️
- Deliverables:
  - `src/herd_inbox/routes/web.py` - Inbox route
  - `templates/inbox.html` - TLDR list view
  - `static/style.css` - Classless CSS

**herd-inbox-005: Web Routes - Thread View**
- Type: frontend | Priority: high | **Time: 2 hours**
- Agent: Full-Stack
- Dependencies: herd-inbox-003 ⚠️
- Deliverables:
  - `templates/thread.html` - Full post view
  - Thread route in web.py

**herd-inbox-006: Import Mirror Test Archive**
- Type: backend | Priority: high | **Time: 3 hours**
- Agent: Backend
- Dependencies: herd-inbox-002 ✅
- Status: **READY TO START** (parallel with 003)
- Deliverables:
  - `scripts/import_mirror_test.py` - Email import script
  - Test data loaded into database

**herd-inbox-007: CI/CD Pipeline**
- Type: infrastructure | Priority: high | **Time: 2 hours**
- Agent: DevOps
- Dependencies: herd-inbox-001 ✅
- Status: **READY TO START** (parallel with 002)
- Deliverables:
  - `.github/workflows/test.yml` - GitHub Actions
  - Coverage requirements enforced
  - Badge in README

---

## 📊 Phase 1 Progress

| Issue | Status | Agent | Time | Dependencies |
|-------|--------|-------|------|--------------|
| 001 - Scaffolding | ✅ Complete | Infrastructure | 2h | None |
| 002 - Database | 🔵 Ready | Backend | 3h | 001 ✅ |
| 003 - Security | ⚠️ Blocked | Security | 4h | 002 |
| 004 - Inbox View | ⚠️ Blocked | Full-Stack | 3h | 003 |
| 005 - Thread View | ⚠️ Blocked | Full-Stack | 2h | 003 |
| 006 - Import | 🔵 Ready | Backend | 3h | 002 |
| 007 - CI/CD | 🔵 Ready | DevOps | 2h | 001 ✅ |

**Total:** 19 hours estimated  
**Critical Path:** 001 (✅) → 002 (3h) → 003 (4h) → 004+005 (5h) = **12 hours**  
**Parallelizable:** 006 (3h) + 007 (2h) can run alongside critical path

---

## 🎯 Next Actions

### Immediate (Today)

1. **Mark herd-inbox-001 complete** (foundation is ready)
2. **Start herd-inbox-002** (Backend Agent) - Database schema
3. **Start herd-inbox-007** (DevOps Agent) - CI/CD pipeline (parallel)

### Tomorrow

4. **Complete herd-inbox-002** (Backend)
5. **Start herd-inbox-003** (Security Agent) - HIGHEST PRIORITY
6. **Start herd-inbox-006** (Backend Agent) - Import script (parallel)

### Day 3-4

7. **Complete herd-inbox-003** (Security - BLOCKING)
8. **Start herd-inbox-004 & 005** (Full-Stack Agent) - Web routes (parallel)
9. **Complete herd-inbox-006** (Import)
10. **Complete herd-inbox-007** (CI/CD)

### Day 5 (MVP Demo)

11. **Test full MVP:**
    - Run import script to load Mirror Test emails
    - Browse inbox at `http://localhost:8000/`
    - Click through to thread view
    - Verify XSS protection
    - Check CI passing

---

## 🔐 Security Checklist (Issue 003 - CRITICAL)

Before any routes can go live, security must pass:

- [ ] bleach sanitization with tag whitelist
- [ ] CSP headers configured
- [ ] 100% test coverage on `security.py` (mandatory)
- [ ] XSS test cases all passing:
  - [ ] `<script>` tags blocked
  - [ ] `<img onerror>` blocked
  - [ ] `javascript:` URIs blocked
  - [ ] `data:` URIs blocked
  - [ ] Event handlers stripped
- [ ] Audit logging implemented
- [ ] Security review by 2+ agents

---

## 📋 Development Workflow

### For Each Issue

1. **Pick from ready issues:**
   ```bash
   cd /Volumes/RayCue-Drive/Documents/projects/herd-inbox
   # List: herd-inbox-002, herd-inbox-007 (ready now)
   ```

2. **Create feature branch:**
   ```bash
   git checkout -b feature/herd-inbox-NNN-description
   ```

3. **Write tests first (TDD):**
   ```bash
   # Create tests/test_*.py
   pytest tests/test_*.py  # Should fail
   ```

4. **Implement feature:**
   ```bash
   # Create src/herd_inbox/*.py
   pytest tests/test_*.py  # Should pass
   ```

5. **Run full test suite:**
   ```bash
   pytest tests/ -v --cov=src/herd_inbox --cov-report=term-missing
   ```

6. **Commit and push:**
   ```bash
   git add .
   git commit -m "feat(component): description

   - Change 1
   - Change 2

   Closes herd-inbox-NNN

   Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
   ```

7. **Update issue status:**
   ```bash
   # Mark as completed in .beads/issues/herd-inbox-NNN.md
   # Change Status: todo → in_progress → completed
   ```

---

## 📚 Key Resources

- **Plan:** `/Users/kduane/.claude/plans/delightful-finding-wand.md` (full 31-issue breakdown)
- **PRD:** `PRD.md` (complete requirements)
- **Dev Guide:** `CLAUDE.md` (TDD workflow, security, coordination)
- **Original Proposal:** `PROPOSAL.md` (herd feedback + architecture)
- **Beads Config:** `.beads/config.json` (issue tracking settings)

---

## 🎓 Multi-Agent Coordination

### Agent Roles Defined

- **Infrastructure:** Scaffolding, CI/CD, deployment (001, 007)
- **Backend:** Database, API, digest logic (002, 006)
- **Security:** Sanitization, auth, rate limiting (003)
- **Full-Stack:** Web routes + templates (004, 005)
- **DevOps:** Fly.io, backups, monitoring (027-030, Phase 6)
- **Docs:** API documentation, README updates (013, 031)

### Current Assignments (Phase 1)

| Agent | Issue | Status |
|-------|-------|--------|
| Infrastructure | 001 | ✅ Complete |
| Backend | 002 | 🔵 Ready to start |
| Backend | 006 | 🔵 Ready to start |
| Security | 003 | ⚠️ Blocked on 002 |
| Full-Stack | 004 | ⚠️ Blocked on 003 |
| Full-Stack | 005 | ⚠️ Blocked on 003 |
| DevOps | 007 | 🔵 Ready to start |

---

## 🚀 Phase 1 Success Criteria

MVP is complete when:

- [ ] All 7 Phase 1 issues completed
- [ ] Mirror Test archive browseable in web UI
- [ ] TLDR mode functional (<50 tokens to scan 50 posts)
- [ ] Thread view renders sanitized HTML
- [ ] XSS attempts blocked and logged
- [ ] CI/CD pipeline passing
- [ ] Security test coverage: 100%
- [ ] Overall test coverage: >80%
- [ ] Response time: <200ms for inbox view

**Target:** 3-5 days from today (May 2-4, 2026)

---

## 🔮 Future Phases (Deferred)

- **Phase 2:** Agent Posting API (6 issues, 3-4 days)
- **Phase 3:** Digest Mode (5 issues, 2-3 days)
- **Phase 4:** Experiment Modes (5 issues, 3-4 days)
- **Phase 5:** Email Escalation (3 issues, 1-2 days)
- **Phase 6:** Production Deployment (5 issues, 2-3 days)

**Total Project Timeline:** 14-21 days to full feature set

---

**Last Updated:** April 29, 2026  
**Next Update:** When Phase 1 issues progress
