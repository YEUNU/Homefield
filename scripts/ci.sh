#!/usr/bin/env bash
# Local CI (docs/RULES.md §4). It runs on this PC instead of GitHub Actions.
#   scripts/ci.sh            checks only
#   scripts/ci.sh --report   run the checks, then post the result as the GitHub commit status (local-ci) (after HEAD is pushed)
set -uo pipefail
cd "$(dirname "$0")/.."
REPORT=0; [ "${1:-}" = "--report" ] && REPORT=1

fail=0
step() { echo "== $1"; shift; if "$@"; then echo "   ok"; else echo "   FAIL"; fail=1; fi; }
step "ruff check"        uvx ruff check .
step "ruff format"       uvx ruff format --check .
step "pytest"            uvx --python 3.12 pytest -q
step "Rules check"          python3 scripts/check_rules.py
step "Secret scan (gitleaks)" gitleaks git --no-banner --redact .

if [ $REPORT -eq 1 ]; then
  if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
    echo "There are uncommitted changes. Not posting the status." >&2; exit 1
  fi
  sha=$(git rev-parse HEAD)
  state=$([ $fail -eq 0 ] && echo success || echo failure)
  gh api "repos/{owner}/{repo}/statuses/$sha" -f state="$state" -f context=local-ci \
     -f description="local CI on $(hostname -s): ruff, pytest, rules, gitleaks" >/dev/null \
     && echo "== GitHub status local-ci=$state ($sha)"
fi
exit $fail
