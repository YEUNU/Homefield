---
name: git-workflow
description: Branch, commit, PR, and release rules for the Homefield repo (public GitHub repo YEUNU/Homefield). Use whenever creating a branch, writing a commit message, opening a PR, tagging a release, or deciding whether a file may be committed.
---

# Git Workflow

정책 원문: `docs/GIT_POLICY.md`.

## 체크리스트
1. `main`이면 먼저 브랜치를 만든다: `<feat|fix|eval|docs|chore|exp>/<짧은-설명>`.
2. 커밋 전에 staged 파일을 본다. 다음은 절대 커밋하지 않는다 (공개 저장소):
   - `.env`, 키·토큰, `data/`, 고객 이름·스키마·현장 메모, Engagement 상태.
3. 커밋 메시지: `<유형>(<범위>): <요약>`. 본문에 "왜". hook이 형식을 검사한다.
4. hook이 막으면 우회(`--no-verify`)하지 않는다. 원인을 고친다.
5. push, PR 생성, 태그, 릴리스는 사용자 승인 후에만 한다.
6. PR 본문: 템플릿을 채우고 eval 결과를 붙인다. 없으면 "미검증"이라고 쓴다.
7. 병합은 squash. 직접 `main`에 push하지 않는다.

## 클론 직후
```bash
git config core.hooksPath .githooks
```
