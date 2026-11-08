---
status: 확정
updated: 2026-11-08
audience: 배포
---
# Homefield 규칙 (문서·코드·배포)

이 문서가 규칙의 단일 원천이다. 다른 문서·스킬은 이 문서를 가리키기만 한다.
규칙은 가능한 한 코드로 강제한다. 강제 수단은 §4 표에 있다.

## 1. 문서 규칙

### 1.1 위치: 배포 대 내부
| 위치 | 저장소 | 공개 | 넣는 것 |
|---|---|---|---|
| `docs/` | `YEUNU/Homefield` | **공개** | 사용법, 평가 규약, 데이터셋, 하네스 연결 방법, 이 규칙 |
| `internal/` | `YEUNU/Homefield-internal` (Homefield 루트에 클론, git 제외) | 비공개 | 전략, 문제 정의, 차별점·선행 연구 분석, 자문 기록, 설계 문서, 결정 기록(ADR), 인프라 주소, 고객·회사 맥락 |

판단이 어려우면 `internal/`에 둔다. 공개는 나중에 옮겨서 한다.

### 1.2 파일 이름
| 종류 | 위치 | 이름 |
|---|---|---|
| 주요 문서 | `docs/`, `internal/` | `UPPER_SNAKE.md` (예: `EVALUATION.md`) |
| 설계 문서 | `internal/design/` | `kebab-case.md` |
| 결정 기록 | `internal/decisions/` | `NNNN-kebab-case.md` (번호 = 기존 최대 + 1) |
| 저장소 안내 | 각 저장소 루트 | `README.md` |

### 1.3 머리말 (front matter)
`README.md`를 뺀 모든 문서는 첫 줄에 다음 머리말을 둔다.

```yaml
---
status: 초안 | 확정 | 폐기          # 결정 기록은: 결정 | 가정 | 폐기 | 대체됨
updated: YYYY-MM-DD
audience: 배포 | 내부               # docs/ 는 배포, internal/ 은 내부
---
```
- 내용을 바꾸면 `updated`를 고친다.
- 버전 표기(v0.1 등)는 제목에 쓰지 않는다. 변경 이력은 git이 맡는다. 큰 변경은 본문 첫머리에 한 줄로 적는다.

### 1.4 문체 (ASD-STE100 기반)
- 한국어로 쓴다. 식별자·명령·파일 이름은 원문 그대로 둔다.
- 한 문장에 한 내용. 능동태. 짧은 문장.
- 같은 대상에는 같은 용어를 쓴다 (§1.6).
- 표와 목록을 산문보다 먼저 쓴다.

### 1.5 근거 표기
- 선행 연구·수치에는 출처(논문 ID 또는 URL)를 붙인다.
- 원문을 직접 확인하지 않은 수치는 `(2차 자료)`, 확인하지 못한 것은 `(미확인)`으로 표시한다.
- 표본 30 미만의 실험 결과는 "결론"이 아니라 "관찰"로 쓴다.
- 근거 없는 초기값·목표값은 `(근거 없음)`으로 표시한다.

### 1.6 용어
| 용어 | 뜻 |
|---|---|
| 하네스 | 모델을 감싸 도구·루프·정책을 주는 실행 틀 |
| 과제 | 고객 요청 1건 (`tasks/<id>/`) |
| 에피소드 | 과제 1개 × 하네스 1개 × 실행 1회 |
| engagement | 같은 고객·데이터 위에서 이어지는 과제 묶음 |
| 원장 | 해석 결정과 가정을 기록하는 구조 |
| 결정 / 가정 | 산출물을 바꿀 수 있는 해석 선택 / 묻지 않고 확정한 결정 |
| 재작업 | 거절된 제출 |
| CFC | 첫 정답까지 상호작용 비용 = 질문 왕복 + r × 재작업 |
| 프로세스 케이스 | 프로세스 마이닝 용어. 이벤트 로그의 프로세스 인스턴스 1개. "과제"와 다르다 |

### 1.7 경로와 비밀
- 문서 안 경로는 Homefield 루트 기준으로 쓴다 (예: `internal/PROBLEM.md`, `docs/EVALUATION.md`).
- `docs/`와 코드에는 내부 IP·호스트·키를 쓰지 않는다. `$LOCAL_LLM_BASE_URL` 같은 환경변수로 쓴다.

## 2. 코드 규칙

### 2.1 언어와 의존성
- Python 3.11 이상. 표준 라이브러리를 먼저 쓴다.
- 런타임 외부 의존성을 추가하려면 결정 기록(ADR)을 남긴다.
- 하네스 코어는 범용 에이전트 프레임워크(LangChain 등)를 import하지 않는다.
- 모델 호출은 한 모듈(현재 `evalkit/llm.py`)을 거친다. 다른 곳에서 HTTP로 모델을 직접 부르지 않는다.

### 2.2 구조와 이름
| 위치 | 내용 |
|---|---|
| `evalkit/` | 평가 도구 (실행기, 에피소드, 어댑터, 채점, 보고) |
| `tests/` | pytest 테스트 |
| `tasks/<kebab-id>/` | 과제: `task.json` + 데이터 생성 파일 |
| `scripts/` | 운영 스크립트 (연결 확인, 규칙 검사) |
| `.claude/skills/` | Claude Code 스킬 |

- 모듈·함수·변수: `snake_case`. 클래스: `PascalCase`. 상수: `UPPER_SNAKE`.
- 식별자는 영어. 주석·docstring은 한국어로 써도 된다.
- 실행 진입점은 `python3 -m <패키지>.<모듈>` 형태로 둔다.
- 스크립트 이름: `<동사>_<명사>` (예: `check_rules.py`, `check_llm.sh`).
- 하네스 ID·결과 필드 이름은 `docs/EVALUATION.md` §6–7이 원천이다. 코드와 문서는 그 이름을 그대로 쓴다.

### 2.3 품질
- 린트·서식: `ruff check`와 `ruff format --check` 통과 (설정: `pyproject.toml`). 커밋 전에 `uvx ruff format .`을 돌린다.
- 동작을 바꾸면 테스트를 같이 바꾼다. 단위 테스트는 네트워크·LLM을 부르지 않는다 (시뮬레이터는 함수로 대체).
- 하네스 동작 변경은 eval 결과를 PR에 붙인다 (`eval-first` 스킬). 없으면 "미검증"이라고 쓴다.
- 코드 작성은 `karpathy-guidelines` 스킬을 따른다: 요청된 것만, 단순하게, 필요한 곳만 바꾼다.

### 2.4 비밀과 데이터
- 비밀값은 `.env`에만 둔다. 출력·로그·커밋하지 않는다.
- 커밋 금지: `.env`, 키 파일, `data/`, `evals/results/`, 고객 데이터·이름·스키마, Engagement 상태.
- 벤치마크 원본 데이터는 커밋하지 않는다. 라이선스는 `docs/DATASETS.md`에 적는다.

## 3. 배포 규칙

### 3.1 저장소
| 저장소 | 공개 | 브랜치 규칙 |
|---|---|---|
| `YEUNU/Homefield` | 공개 | §3.2–3.5 전부 |
| `YEUNU/Homefield-internal` | 비공개 | `main`에 직접 커밋 허용. 커밋 메시지 형식(§3.3)은 같다 |

### 3.2 브랜치
- `main`: 항상 동작하는 상태. 직접 push 금지. PR로만 병합한다.
- 작업 브랜치: `<유형>/<kebab-설명>`. 유형: `feat`, `fix`, `eval`, `docs`, `chore`, `exp`, `refactor`, `test`.
- `exp/*`: 실험용. 병합하지 않아도 된다. 결과는 `internal/decisions/`에 남긴다.
- 병합: squash merge. 병합 뒤 브랜치를 지운다.

### 3.3 커밋 메시지
- 형식: `<유형>(<범위>): <요약>`. 요약은 72자(글자 수) 이내. 본문에 "왜"를 쓴다.
- 범위 예: `core`, `policy`, `state`, `eval`, `evalkit`, `adapter`, `onto`, `p1`…`p5`, `skills`, `docs`, `rules`.

### 3.4 PR
- 로컬 CI 통과: push 뒤 `scripts/ci.sh --report`로 커밋 상태 `local-ci`=success를 올린다. GitHub Actions는 쓰지 않는다 (§4.1).
- PR 본문은 템플릿을 채운다. eval 결과 또는 "미검증".
- 설계 결정이 있으면 `internal/decisions/`에 기록을 추가하고 PR에는 번호만 적는다 (내용은 비공개).

### 3.5 릴리스
- 버전: SemVer `vMAJOR.MINOR.PATCH`. 1.0 전에는 MINOR 증가가 호환 깨짐일 수 있다.
- 릴리스 = `main` 커밋에 annotated tag. GitHub Release 노트에 변경점과 eval 요약을 쓴다.
- 산출물: 단독 CLI 패키지, Claude Code 플러그인(skill·hook·MCP). 고객 현장 설치는 온프레미스 모델 기준이다.

### 3.6 사람의 승인이 필요한 동작
push, PR 생성, 태그, 릴리스, force-push, 기록 재작성, 저장소 설정·공개 범위 변경.

## 4. 강제 수단
| 규칙 | 수단 | 위치 |
|---|---|---|
| 비밀·키 파일·`data/` 커밋 금지 | pre-commit hook, 로컬 CI gitleaks | `.githooks/pre-commit`, `scripts/ci.sh` |
| 사설 IP(10/8, 172.16/12, 192.168/16) 금지 | pre-commit, 로컬 CI | `scripts/check_rules.py` |
| `internal/` 추적 금지 | `.gitignore`, 로컬 CI | `scripts/check_rules.py` |
| 문서 머리말·이름 규칙 | pre-commit, 로컬 CI | `scripts/check_rules.py` |
| 커밋 메시지 형식 | commit-msg hook | `.githooks/commit-msg` |
| 린트·서식 | 로컬 CI | `ruff check`, `ruff format --check` |
| 테스트 | 로컬 CI | `pytest` |
| push 전 전체 검사 | pre-push hook | `.githooks/pre-push` → `scripts/ci.sh` |
| `main` 직접 push 금지 | GitHub 브랜치 보호 | **미설정** (저장소 설정 변경은 사람 승인 필요) |
| 문체·근거 표기 | 사람 리뷰 | - |

### 4.1 로컬 CI
- CI는 GitHub Actions가 아니라 개발자 PC에서 돈다 (`scripts/ci.sh`). 검사: ruff check, ruff format, pytest, 규칙 검사, gitleaks.
- `pre-push` hook이 push 전에 자동으로 돌린다. 실패하면 push가 막힌다.
- PR에 결과를 보이려면 push 뒤 `scripts/ci.sh --report`를 돌린다. GitHub 커밋 상태 `local-ci`가 기록된다.
- 자체 호스팅 GitHub 러너는 쓰지 않는다. 공개 저장소에서는 외부 PR 코드가 이 PC에서 실행될 위험이 있다.
- 필요 도구: `uv`(uvx), `gitleaks`(Homebrew), `gh`(로그인 상태).

## 5. 처음 설정
```bash
git config core.hooksPath .githooks
brew install gitleaks    # 로컬 CI용
git clone https://github.com/YEUNU/Homefield-internal.git internal   # 권한이 있을 때
cp .env.example .env
```
