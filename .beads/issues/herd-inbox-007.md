# CI/CD Pipeline

**ID:** herd-inbox-007  
**Type:** infrastructure  
**Priority:** high  
**Phase:** 1  
**Status:** todo  
**Agent Role:** DevOps  
**Estimated Time:** 2 hours  
**Dependencies:** herd-inbox-001

## Description

GitHub Actions for pytest + security coverage.

## Acceptance Criteria

- [ ] `.github/workflows/test.yml` runs on push + PR
- [ ] Matrix: Python 3.11, 3.12
- [ ] Runs `pytest tests/` with coverage report
- [ ] Fails if security test coverage <100%
- [ ] Badge in README.md

## Labels

- phase:1-mvp
- type:infrastructure
- priority:high
- agent:devops
