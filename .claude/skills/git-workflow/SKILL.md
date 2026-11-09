---
name: git-workflow
description: Branch, commit, PR, and release rules for the Homefield repos (public YEUNU/Homefield, private YEUNU/Homefield-internal). Use whenever creating a branch, writing a commit message, opening a PR, tagging a release, or deciding whether a file may be committed or which repo a document belongs in.
---

# Git Workflow

Rule source: `docs/RULES.md` §4 (Git), §5 (release and deployment), §1.1 (document location), §2.4 (what must not be committed). Do not repeat the rules here.

## Checklist
1. If you are on `main`, create a branch first (RULES §4.3). One PR holds one purpose.
2. For a document, choose the location: public `docs/` or private `internal/` (RULES §1.1). If unsure, use `internal/`.
3. Check the Git identity before the first commit on a machine (RULES §4.2). If it is not set, pass it with `git -c`.
4. Checks before a commit: `uvx ruff format .`, then `scripts/ci.sh`. After a push, post the `local-ci` status to the PR with `scripts/ci.sh --report` (RULES §6.1).
5. Commit message format: RULES §4.4. If a hook blocks the commit, fix the cause. Do not bypass it with `--no-verify`.
6. Push, PR, merge, tag, force-push, history rewrite, and repo settings changes need user approval first, in both repositories (RULES §4.6).
7. `internal/` is a separate repo. Commit there separately, then run `python3 scripts/check_rules.py --internal internal` (RULES §4.1).
8. Before a tag: check the release gate (RULES §5.2).
