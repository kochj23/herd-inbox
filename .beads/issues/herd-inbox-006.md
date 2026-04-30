# Import Mirror Test Archive

**ID:** herd-inbox-006  
**Type:** backend  
**Priority:** high  
**Phase:** 1  
**Status:** todo  
**Agent Role:** Backend  
**Estimated Time:** 3 hours  
**Dependencies:** herd-inbox-002

## Description

Script to import Mirror Test email archive for MVP demo data.

## Acceptance Criteria

- [ ] `scripts/import_mirror_test.py` reads .eml files
- [ ] Extracts: Message-ID, From, Subject, Body, In-Reply-To
- [ ] Generates TLDR (first 280 chars or LLM summary if available)
- [ ] Inserts into `posts` table
- [ ] Imports at least 50 posts for testing
- [ ] Tests: import success, duplicate handling

## Labels

- phase:1-mvp
- type:backend
- priority:high
- agent:backend
