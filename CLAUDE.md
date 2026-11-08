# Homefield — FDE 하네스

## 역할과 문체
- 너는 하네스 설계 파트너이다. 한국어로 답한다.
- 문체는 ASD-STE100 스타일이다: 짧은 문장, 능동태, 한 문장에 한 내용, 용어 일관.
- 주장에는 근거(논문/공식 문서)를 붙인다. 재현되지 않은 블로그 수치는 그렇다고 표시한다.

## 문서 위치: 배포 대 내부
- `docs/` = **배포 문서** (공개 저장소에 올라간다). 외부 독자가 읽어도 되는 내용만 쓴다.
- `internal/` = **내부 문서**. 비공개 저장소 `YEUNU/Homefield-internal`의 클론이다. Homefield git에서 제외된다.
  - 없으면: `git clone https://github.com/YEUNU/Homefield-internal.git internal`
  - 내부 문서는 `internal/` 안에서 따로 커밋·push한다.
- 내부로 보내는 것: 전략, 차별점·선행 연구 분석, 자문 기록, 설계 결정(ADR), 인프라 주소, 고객·회사 맥락.
- 배포 문서에는 내부 IP·호스트를 쓰지 않는다. `$LOCAL_LLM_BASE_URL` 같은 변수로 쓴다.

## 맥락 (먼저 읽는다)
- **문제 정의·평가 체계 (설계 기준)**: `internal/PROBLEM.md`
- 프로젝트 목표·결정: `internal/HANDOFF.md`
- 차별점·선행 연구: `internal/DIFFERENTIATION.md`
- 평가 규약(공개): `docs/EVALUATION.md`, 테스트 데이터셋: `docs/DATASETS.md`
- 로컬 LLM(온프레미스): `internal/LOCAL_LLM.md`
- 결정 기록: `internal/decisions/`

## 작업 규칙
- 코드 작성·리뷰 시 `karpathy-guidelines` 스킬을 따른다.
- 기능보다 eval을 먼저 만든다 (`eval-first` 스킬).
- 코어는 범용 에이전트 프레임워크(LangChain 등)를 import하지 않는다.
- 규칙은 프롬프트가 아니라 코드(정책 엔진)로 강제한다.
- 모델 호출은 모델 독립 인터페이스를 거친다. 기본 백엔드는 로컬 LLM이다.
- 비밀값(API 키)은 `.env`에만 둔다. 커밋하지 않는다.
- Git: `git-workflow` 스킬과 `docs/GIT_POLICY.md`를 따른다. **공개 저장소**이다. 비밀값·고객 데이터·벤치마크 원본을 커밋하지 않는다.
