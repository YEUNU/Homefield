# 평가 규약 (evalkit)

Homefield는 에이전트 하네스를 같은 모델·같은 조건에서 비교한다. 이 문서는 그 규약을 설명한다.

## 1. 측정 대상
모호한 데이터 분석 요청에서, 숨겨진 고객 의도에 맞는 첫 정답까지 드는 **상호작용 비용**.

- **주 지표 CFC** (cost to first correct) = `질문 왕복 수 + r × 재작업 수`
  - 재작업 = 거절된 제출. 데모에서 틀린 결과를 보여 준 것에 해당한다.
  - r은 재작업 1회가 질문 1회보다 몇 배 비싼지이다. 모르는 값이므로 r ∈ {1, 3, 10}을 모두 보고한다.
  - 예산 안에 수락되지 않으면 실패이다. CFC는 수락된 실행만 평균하고, 수락률과 함께 읽는다.
- 보조 지표: 수락률, 질문 수, "모름" 답 수, 재작업 수, 실행 시간.
- **추측 기준선**: 질문 없이 해석을 균등하게 추측할 때의 수락 확률과 CFC. 결과 표에 함께 적는다.

## 2. 과제 형식 (`tasks/<id>/task.json`)
| 필드 | 뜻 |
|---|---|
| `request` | 고객의 모호한 요청 |
| `db`, `db_sql` | SQLite DB와 생성 SQL |
| `answer_file` | 에이전트가 답 SQL을 쓸 파일 |
| `check.gold_sql` | 정답 SQL. 결과 집합을 비교한다 (순서 무시, 수치 허용 오차 1e-6) |
| `hidden.facts` | 고객 시뮬레이터만 아는 사실 |
| `budget.ask`, `budget.submit` | 질문·제출 예산 |
| `n_interpretations` | 결과를 바꾸는 해석 조합 수 (추측 기준선 계산용) |

## 3. 에이전트에게 주는 공통 규약
셸만 있으면 어느 하네스에서도 같다.

- 답: 작업 폴더의 답 파일에 SQL 1개를 쓴다.
- 질문: `<bin>/ask_user "질문"` → 고객 시뮬레이터의 답을 출력한다.
- 제출: `<bin>/submit_answer` → `ACCEPTED` 또는 `REJECTED`.
  - 거절 메시지는 실제 고객이 주는 정보만 준다. 남은 횟수나 SQL 오류 내용은 알려 주지 않는다.

고객 시뮬레이터는 `hidden.facts`만 안다. 사실 밖 질문에는 `I don't know.`라고 답한다. 정답 SQL은 모른다.

## 4. 공정성 규칙
1. 모델을 고정하고 하네스만 바꾼다.
2. 모든 하네스에 같은 도구(셸), 같은 규약, 같은 예산을 준다.
3. 하네스별 프롬프트 튜닝은 하지 않는다. 프롬프트 변형(E0, E1 …)은 모든 하네스에 똑같이 적용한다.
4. 에피소드는 저장소 밖에서 실행한다. 저장소 안이면 하네스가 이 저장소의 지침 파일을 읽어 비교가 오염된다.
5. 정답 DB는 작업 폴더 밖 사본으로 채점한다. 에이전트가 작업 폴더 DB를 바꿔도 채점에 영향이 없다.
6. 반복 실행한다. 반복은 바깥 고리에 둔다.

한계: 에이전트와 시뮬레이터가 같은 머신에서 돈다. 에이전트가 파일 시스템을 뒤지면 과제 원본을 찾을 수 있다. 컨테이너 격리는 다음 단계이다.

## 5. 실행
```bash
cp .env.example .env    # LOCAL_LLM_BASE_URL, LOCAL_LLM_API_KEY
python3 -m evalkit.run --task tasks/smoke-revenue --harness claude,codex,opencode,mini,openhands --variant E0,E1 --repeat 3
python3 -m evalkit.report evals/results/<날짜>.jsonl --task tasks/smoke-revenue
```
- 결과: `evals/results/<날짜>.jsonl` (git 제외)
- 에피소드 기록: `$HF_RUNS_DIR` (기본: 임시 폴더/homefield-runs)
- 하네스 연결 방법: `docs/HARNESSES.md`

## 6. 프롬프트 변형
| ID | 내용 |
|---|---|
| E0 | 기본 규약만 |
| E1 | E0 + "결과를 바꾸는 해석을 나열하고, 첫 제출 전에 각각 물어라. 확인 못 한 해석은 가정으로 밝혀라" |
