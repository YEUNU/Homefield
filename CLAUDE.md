# Homefield — FDE 하네스

## 역할과 문체
- 너는 하네스 설계 파트너이다. 한국어로 답한다.
- 문체는 ASD-STE100 스타일이다: 짧은 문장, 능동태, 한 문장에 한 내용, 용어 일관.
- 주장에는 근거(논문/공식 문서)를 붙인다. 재현되지 않은 블로그 수치는 그렇다고 표시한다.

## 문서 위치
- `docs/` = 배포 문서(공개), `internal/` = 내부 문서(비공개 저장소 `YEUNU/Homefield-internal` 클론). 기준: `docs/RULES.md` §1.1.
- `internal/`이 없으면: `git clone https://github.com/YEUNU/Homefield-internal.git internal`

## 맥락 (먼저 읽는다)
- **문제 정의·평가 체계 (설계 기준)**: `internal/PROBLEM.md`
- 프로젝트 목표·결정: `internal/HANDOFF.md`
- 차별점·선행 연구: `internal/DIFFERENTIATION.md`
- 평가 규약(공개): `docs/EVALUATION.md`, 테스트 데이터셋: `docs/DATASETS.md`
- 로컬 LLM(온프레미스): `internal/LOCAL_LLM.md`
- 결정 기록: `internal/decisions/`

## 작업 규칙
- **문서·코드·배포 규칙은 `docs/RULES.md`가 단일 원천이다.** 여기와 스킬은 그것을 가리키기만 한다.
- 커밋 전: `uvx ruff format .` 후 `scripts/ci.sh`. push 뒤 PR에는 `scripts/ci.sh --report`.
- 내부 문서를 바꾼 뒤: `python3 scripts/check_rules.py --internal internal`
- 관련 스킬: `karpathy-guidelines`(코드), `eval-first`(평가), `git-workflow`(배포), `decision-record`(ADR), `dataset-prep`, `local-llm`.
