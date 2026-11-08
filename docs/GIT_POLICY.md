# Git·배포 정책

저장소: `YEUNU/Homefield` (**공개 저장소**). 이 사실이 아래 규칙의 기준이다.

## 1. 공개 저장소 규칙 (가장 중요)
- 비밀값(API 키, 토큰, 비밀번호)을 커밋하지 않는다. `.env`만 쓴다.
- 고객 데이터, 고객 이름, 고객 스키마, 현장 메모를 커밋하지 않는다. Engagement 상태는 저장소 밖(`$HOMEFIELD_STATE_DIR`)에 둔다.
- 벤치마크 원본 데이터를 커밋하지 않는다 (`data/`는 git 제외). 재배포 라이선스가 다르다.
- 강제 수단: pre-commit hook(로컬) + CI 비밀 검사(gitleaks). 규칙을 문서가 아니라 코드로 강제한다.

## 2. 브랜치
- `main`: 항상 동작하는 상태. 직접 push 금지. PR로만 병합한다.
- 작업 브랜치: `<유형>/<짧은-설명>`. 유형은 `feat`, `fix`, `eval`, `docs`, `chore`, `exp`.
  - `exp/*`: 실험용. 병합하지 않아도 된다. 결과는 `docs/decisions/`에 남긴다.
- 병합 방식: squash merge. 병합 후 브랜치를 지운다.

## 3. 커밋 메시지
Conventional Commits를 쓴다: `<유형>(<범위>): <요약>`.
- 범위 예: `core`, `policy`, `state`, `eval`, `adapter`, `onto`, `p1`…`p5`, `skills`, `docs`.
- 요약은 명령형, 72자 이내. 본문에 "왜"를 쓴다.
- 예: `feat(policy): 철수 조건을 코드 정책으로 추가`

## 4. PR 조건
- CI 통과 (비밀 검사 + 테스트).
- 하네스 동작을 바꾸면 eval 결과를 PR 본문에 붙인다. 없으면 "미검증" 라벨을 단다.
- 설계 결정을 포함하면 `docs/decisions/`에 기록을 추가한다.

## 5. 릴리스·배포
- 버전: SemVer `vMAJOR.MINOR.PATCH`. 1.0 전에는 MINOR 증가가 호환 깨짐을 뜻할 수 있다.
- 릴리스 = `main`의 커밋에 annotated tag `vX.Y.Z`를 단다. GitHub Release 노트에 변경점과 eval 요약을 쓴다.
- 배포 산출물: 단독 CLI 패키지, Claude Code 플러그인(skill·hook·MCP). 고객 현장 설치는 온프레미스 모델 기준으로 한다.
- 태그·릴리스·push는 사람이 승인한 뒤에만 한다.

## 6. 로컬 설정 (클론 직후 1회)
```bash
git config core.hooksPath .githooks
cp .env.example .env   # 키를 넣는다
```
