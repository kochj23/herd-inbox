# Database Schema

**ID:** herd-inbox-002  
**Type:** backend  
**Priority:** critical  
**Phase:** 1  
**Status:** todo  
**Agent Role:** Backend  
**Estimated Time:** 3 hours  
**Dependencies:** herd-inbox-001

## Description

Implement SQLite schema with 5 tables (posts, comments, subscriptions, api_keys, audit_log).

## Acceptance Criteria

- [ ] `src/herd_inbox/db.py` with table creation
- [ ] Migration script `migrations/001_initial_schema.sql`
- [ ] WAL mode enabled for concurrency
- [ ] Test fixtures for empty/seeded database

## Labels

- phase:1-mvp
- type:backend
- priority:critical
- agent:backend

## Blocks

- herd-inbox-003
- herd-inbox-006
