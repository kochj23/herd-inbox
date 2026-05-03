# Agent Instructions

This project uses **GitHub Issues** for issue tracking at [github.com/mostlycopypaste/herd-inbox/issues](https://github.com/mostlycopypaste/herd-inbox/issues).

## Quick Reference

```bash
gh issue list                    # List open issues
gh issue view <number>           # View issue details
gh issue comment <number> --body "..."   # Comment on an issue
gh issue edit <number> --add-assignee @me  # Claim an issue
gh pr list                       # List open PRs
gh pr create --fill              # Create a PR from current branch
```

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create GitHub issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished issues, comment on in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds