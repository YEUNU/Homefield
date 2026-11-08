---
status: 초안
updated: 2026-11-08
audience: 배포
---
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

## 6. 하네스 ID
비교 대상은 인지도와 역할로 고른다. 기준: (1) 현업 사용량·GitHub 스타, (2) 공개 리더보드(Terminal-Bench, SWE-bench) 등장, (3) OpenAI 호환 로컬 모델로 headless 실행 가능.

| 단계 | ID | 하네스 | 고른 이유 | 연결 |
|---|---|---|---|---|
| A. 현업 대표 | `claude` | Claude Code | 상용 코딩 에이전트 대표. FDE가 실제로 쓰는 도구 | 확인됨 |
| | `codex` | Codex CLI | 오픈소스 상용 하네스, 약 126k 스타 (2차 자료) | 확인됨 |
| | `opencode` | OpenCode | 오픈소스 최다 스타, 약 209k (2차 자료) | 확인됨 |
| | `qwen` | Qwen Code | Gemini CLI 계열(약 107k 스타)의 오픈 모델용 포크. Gemini CLI 본체는 존속 여부가 불분명하고 OpenAI 호환 연결이 없다 | 확인됨 |
| B. 오픈소스 범용 | `openhands` | OpenHands CLI | 범용 에이전트. TheAgentCompany 기본 기준선 | 확인됨 |
| | `goose` | Goose | 범용 오픈소스 에이전트, 약 55k 스타 (2차 자료) | 확인됨 |
| C. 연구 기준선 | `mini` | mini-swe-agent | SWE-bench·Terminal-Bench 논문의 최소 기준선 | 확인됨 |
| | `terminus` | Terminus 2 | Terminal-Bench 공식 참조 에이전트 | 미확인 (Terminal-Bench 실행 틀 필요) |
| | `bare` | 단순 도구 호출 루프 | 하네스 효과의 하한선. 직접 작성 | 미구현 |
| | `bird-official` | BIRD-Interact 공식 기준선 | 과제 출처 벤치마크의 기준선 | 미구현 |

뺀 것과 이유:
- Aider (약 49k 스타): 파일 편집 중심이라 셸 규약과 맞지 않고, 2026-05 이후 커밋이 없다 (2차 자료).
- Cline, Kilo Code: IDE 확장이 본체라 headless 비교에 맞지 않는다.
- Gemini CLI 본체: 위 `qwen` 설명 참고.

스타 수는 2026-08~09 기준 2차 자료이다 (morphllm.com, openalternative.co). 실제 수치는 각 저장소에서 확인한다.

## 7. 결과 필드 (`evals/results/<날짜>.jsonl`, 한 줄 = 에피소드 1개)
| 필드 | 뜻 |
|---|---|
| `task_id` | 과제 ID |
| `harness` | 하네스 ID (§6) |
| `variant` | 프롬프트 변형 (§8) |
| `repeat` | 반복 번호 (0부터) |
| `model` | 모델 ID |
| `ts` | 기록 시각 (ISO 8601) |
| `accepted` | 예산 안에 수락되었는가 |
| `n_questions`, `n_unknown` | 질문 수, 그중 "모름" 답 수 |
| `n_submissions`, `n_rework` | 제출 수, 그중 거절 수 |
| `cfc` | `{"1": …, "3": …, "10": …}`. 수락되지 않으면 `null` |
| `tokens_in`, `tokens_out`, `silent_error` | 예약 필드. 아직 `null` |
| `latency_s` | 하네스 실행 시간 |
| `notes` | 종료 코드 또는 `timeout` |
| `episode_dir` | 에피소드 기록 폴더 |

## 8. 프롬프트 변형
| ID | 내용 |
|---|---|
| E0 | 기본 규약만 |
| E1 | E0 + "결과를 바꾸는 해석을 나열하고, 첫 제출 전에 각각 물어라. 확인 못 한 해석은 가정으로 밝혀라" |
