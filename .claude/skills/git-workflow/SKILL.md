---
name: git-workflow
description: Branch, commit, PR, and release rules for the Homefield repos (public YEUNU/Homefield, private YEUNU/Homefield-internal). Use whenever creating a branch, writing a commit message, opening a PR, tagging a release, or deciding whether a file may be committed or which repo a document belongs in.
---

# Git Workflow

규칙 원천: `docs/RULES.md` §3 (배포), §1.1 (문서 위치), §2.4 (커밋 금지 대상). 여기서 규칙을 반복하지 않는다.

## 체크리스트
1. `main`이면 브랜치를 먼저 만든다 (RULES §3.2).
2. 문서라면 위치를 정한다: 공개 `docs/` 또는 비공개 `internal/` (RULES §1.1). 애매하면 `internal/`.
3. 커밋 전 검사: `uvx ruff format .` 후 `scripts/ci.sh`. push 뒤 `scripts/ci.sh --report`로 PR에 `local-ci` 상태를 올린다 (RULES §4.1).
4. 커밋 메시지 형식은 RULES §3.3. hook이 막으면 `--no-verify`로 우회하지 않고 원인을 고친다.
5. push, PR, 태그, force-push, 기록 재작성, 저장소 설정 변경은 사용자 승인 후에만 한다 (RULES §3.6).
6. `internal/`은 별도 저장소다. 그 안에서 따로 커밋·push한다.
