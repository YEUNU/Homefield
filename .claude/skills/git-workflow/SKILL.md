---
name: git-workflow
description: Branch, commit, PR, and release rules for the Homefield repos (public YEUNU/Homefield, private YEUNU/Homefield-internal). Use whenever creating a branch, writing a commit message, opening a PR, tagging a release, or deciding whether a file may be committed or which repo a document belongs in.
---

# Git Workflow

Rule source: `docs/RULES.md` §3 (deployment), §1.1 (document location), §2.4 (what must not be committed). Do not repeat the rules here.

## Checklist
1. If you are on `main`, create a branch first (RULES §3.2).
2. For a document, choose the location: public `docs/` or private `internal/` (RULES §1.1). If unsure, use `internal/`.
3. Checks before a commit: `uvx ruff format .`, then `scripts/ci.sh`. After a push, post the `local-ci` status to the PR with `scripts/ci.sh --report` (RULES §4.1).
4. Commit message format: RULES §3.3. If a hook blocks the commit, fix the cause. Do not bypass it with `--no-verify`.
5. Push, PR, tag, force-push, history rewrite, and repo settings changes need user approval first (RULES §3.6).
6. `internal/` is a separate repo. Commit and push there separately.
