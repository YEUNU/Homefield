#!/usr/bin/env bash
# 로컬 CI (docs/RULES.md §4). GitHub Actions 대신 이 PC에서 돈다.
#   scripts/ci.sh            검사만
#   scripts/ci.sh --report   검사 후 결과를 GitHub 커밋 상태(local-ci)로 올린다 (HEAD가 push된 뒤에)
set -uo pipefail
cd "$(dirname "$0")/.."
REPORT=0; [ "${1:-}" = "--report" ] && REPORT=1

fail=0
step() { echo "== $1"; shift; if "$@"; then echo "   ok"; else echo "   FAIL"; fail=1; fi; }
step "ruff check"        uvx ruff check .
step "ruff format"       uvx ruff format --check .
step "pytest"            uvx --python 3.12 pytest -q
step "규칙 검사"          python3 scripts/check_rules.py
step "비밀 검사 (gitleaks)" gitleaks git --no-banner --redact .

if [ $REPORT -eq 1 ]; then
  if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
    echo "커밋하지 않은 변경이 있다. 상태를 올리지 않는다." >&2; exit 1
  fi
  sha=$(git rev-parse HEAD)
  state=$([ $fail -eq 0 ] && echo success || echo failure)
  gh api "repos/{owner}/{repo}/statuses/$sha" -f state="$state" -f context=local-ci \
     -f description="local CI on $(hostname -s): ruff, pytest, rules, gitleaks" >/dev/null \
     && echo "== GitHub 상태 local-ci=$state ($sha)"
fi
exit $fail
