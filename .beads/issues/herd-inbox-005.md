# Web Routes - Thread View

**ID:** herd-inbox-005  
**Type:** frontend  
**Priority:** high  
**Phase:** 1  
**Status:** todo  
**Agent Role:** Full-Stack  
**Estimated Time:** 2 hours  
**Dependencies:** herd-inbox-003

## Description

Implement `GET /thread/{id}` with full post + comments.

## Acceptance Criteria

- [ ] Route in `routes/web.py`
- [ ] `templates/thread.html` with full markdown rendering
- [ ] Shows: full body, token cost, comments list
- [ ] Sanitized HTML rendering
- [ ] Tests: valid ID, invalid ID (404), XSS attempts

## Labels

- phase:1-mvp
- type:frontend
- priority:high
- agent:full-stack
