# Security Sanitization Module ⚠️ BLOCKING

**ID:** herd-inbox-003  
**Type:** security  
**Priority:** critical  
**Phase:** 1  
**Status:** todo  
**Agent Role:** Security  
**Estimated Time:** 4 hours  
**Dependencies:** herd-inbox-002

## Description

Implement prompt injection defense with bleach, CSP headers, audit logging.

**⚠️ BLOCKING:** This issue blocks all user-facing routes. Must ship before any routes can be implemented.

## Acceptance Criteria

- [ ] `src/herd_inbox/security.py` with `sanitize_html()` function
- [ ] Bleach whitelist: p, a, em, strong, code, pre tags only
- [ ] CSP headers: `default-src 'self'; script-src 'none'`
- [ ] `tests/test_security.py` with 100% coverage
- [ ] Test cases: `<script>`, `<img onerror>`, `data:` URIs, `javascript:` URIs
- [ ] Audit logging for sanitization events

## Test Cases (Mandatory)

```python
# Must block ALL of these:
'<script>alert("XSS")</script>'
'<img src="x" onerror="alert(1)">'
'<a href="javascript:alert(1)">link</a>'
'<a href="data:text/html,<script>alert(1)</script>">link</a>'
'<iframe src="evil.com"></iframe>'
'<object data="evil.swf"></object>'
'<svg onload="alert(1)"></svg>'
```

## Labels

- phase:1-mvp
- type:security
- priority:critical
- agent:security

## Blocks

- herd-inbox-004
- herd-inbox-005
