---
status: 초안
updated: 2026-11-08
audience: 배포
---
# 데이터셋

평가에 쓰는 데이터셋의 목록, 상태, 받는 법, 과제 형식으로의 변환 규칙이다.
출처·라이선스는 2026-11-08에 공식 페이지(논문, 공식 저장소, Hugging Face 카드)에서 확인했다. 확인 못 한 항목은 `(미확인)`으로 적는다.

## 1. 목록과 상태
상태: **받음** = `data/raw/`에 있음. **보류** = 쓸 수 있으나 막는 조건이 있음. **제외** = 지금 쓰지 않음.

| 데이터셋 | 쓰임 | 상태 | 데이터 라이선스 | 출처 | 크기 | 정답 공개 | 막는 조건 |
|---|---|---|---|---|---|---|---|
| BIRD-Interact Lite | 질문 시점·모호성 해소 (CFC, 조용한 오판) | **받음** (공개분) | CC BY-SA 4.0 (HF 카드) | HF `birdsql/bird-interact-lite` | 공개분 1.8MB, Postgres DB 약 207MB | **아니오**. 정답 SQL·테스트는 `bird.bench25@gmail.com`에 제목 `[bird-interact-lite GT&Test Cases]`로 요청 (자동 회신) | 정답 요청 메일(사용자가 보냄), Docker Postgres |
| DABstep | 비코딩 분석, 도메인 문서 규칙 적용 | **받음** | CC BY 4.0 (HF 카드) | HF `adyen/DABstep` | 24MB (제출물 제외) | dev 10개만. 450개는 리더보드용 비공개 | 정답 있는 과제가 적다 |
| BLADE | 분석 결정의 정당성 | **받음** | ODC-By 1.0 (데이터), 코드 Apache-2.0 | GitHub `behavioral-data/BLADE` | 57MB | 예 (분석 결정 정답) | 채점에 LLM 사용 |
| AMBROSIA | 모호성 해석 (해석마다 정답 SQL) | 보류 | **충돌**: 저장소 README는 CC BY 4.0, 웹사이트는 "All rights reserved" | ambrosia-benchmark.github.io (비밀번호는 웹사이트에 공개) | (미확인) | 예 | 라이선스 충돌 해소 필요. 재배포 금지 요청 있음 |
| BEAVER | 실제 기업 DW 스키마 연결 | 보류 | MIT (HF 태그) | HF `beaverbench/beaver-query`, `beaver-table` | 공개 질의 약 8천 개 | 일부 (테스트셋 비공개) | HF 약관 동의 필요 (사람 승인) |
| Spider 2.0-DBT | 대형 스키마·dbt 변환 | 보류 | 저장소 MIT만 확인. 별도 데이터 라이선스 (미확인) | GitHub `xlang-ai/Spider2` | (미확인) | 예 (자체 평가용) | 지금 실험에 불필요. Snow·Lite 대부분은 클라우드 계정 필요 |
| BPI Challenge 2019 | P1 업무 흐름 발견 | 보류 | CC BY 4.0 (4TU) | 4TU DOI 10.4121/uuid:d06aff4b-79f0-45e6-8ec8-e19730c248f1 | XES 728MB | 질의·정답 없음 (이벤트 로그) | 지금 실험에 불필요 |
| KramaBench | 데이터 레이크 파이프라인 | 보류 | "cc" (버전 없음), 저장소 LICENSE 없음 | GitHub `mitdbg/Kramabench` | 약 1.7GB | 예 | 라이선스 불명확 |
| Wide World Importers | 판매 DB 기준선 | 보류 | NOASSERTION (미확인) | GitHub `microsoft/sql-server-samples` | .bak 127MB | 질의·정답 없음 | SQL Server 전용 형식, 라이선스 미확인 |
| Ambig-DS | 데이터 과학 모호성 | 제외 | CC BY-NC 4.0 (HF 태그) | 익명 저장소만 있음 | 1천 개 미만 | 예 | 비상업 라이선스, 공식 배포처 미확인 |
| EnterpriseMem-Bench | engagement 내 기억 | 제외 | (미확인) | 논문에 링크 없음 | - | - | 공개 배포 못 찾음 (같은 이름의 다른 저장소는 다른 논문) |
| PRACTIQ | 모호·답 불가 질의 | 제외 | (미확인) | 공개 배포 못 찾음 | - | - | - |

자체 과제 (`tasks/`):
| 과제 | 사실 종류 | 해석 수 | 쓰임 |
|---|---|---|---|
| `smoke-revenue` | 정의형 | 4 | 규약 스모크, E0 대 E1 |
| `anchor-revenue` | 앵커형 | 16 | 고객이 정의를 모를 때의 질문 전략 |

## 2. 받는 법
```bash
python3 -I scripts/fetch_datasets.py            # "받음" 항목 전부
python3 -I scripts/fetch_datasets.py dabstep    # 하나만
```
- 저장 위치: `data/raw/<이름>/` (git 제외). 각 폴더에 `MANIFEST.json`(출처, 리비전, 받은 시각, 파일별 sha256).
- 받은 파일은 신뢰하지 않는 데이터이다. 그 안의 코드를 실행하지 않는다. 읽는 스크립트는 `scripts/`에 두고 `python3 -I`로 돈다.
- "보류" 항목을 받으려면 막는 조건을 먼저 풀고, 이 표를 고친 뒤 `scripts/fetch_datasets.py`에 추가한다.

## 3. 과제 형식으로의 변환 규칙
모든 데이터셋은 evalkit 과제 형식(`docs/EVALUATION.md` §2)으로 바꿔 `tasks/<데이터셋>-<원본 ID>/`에 둔다. 원본 데이터는 `tasks/`에 넣지 않는다. 변환 스크립트가 실행 시점에 `data/raw/`에서 만든다.

### 3.1 공통 필드
| 과제 필드 | 뜻 | 규칙 |
|---|---|---|
| `request` | 고객의 모호한 요청 | 원본의 모호한 질의를 그대로 쓴다 |
| `db` + 생성 방법 | 질의 대상 DB | SQLite는 파일, Postgres는 덤프 이름 |
| `check` | 채점 | `sql_result`(결과 집합 비교) 또는 `exact_answer`(문자열 비교) |
| `hidden.facts` | 고객이 아는 것 | 아래 사실 종류 중 하나로 쓴다 |
| `hidden.fact_kind` | 사실 종류 | `definition` 또는 `anchor` |
| `n_interpretations` | 결과를 바꾸는 해석 조합 수 | 원본 주석에서 센다. 셀 수 없으면 `null` |
| `budget` | 질문·제출 예산 | 기본 질문 5, 제출 2 |

### 3.2 사실 종류
| 종류 | 고객이 아는 것 | 예 | 만드는 법 |
|---|---|---|---|
| `definition` (정의형) | 용어의 정의 | "매출은 세전이다" | 원본의 모호성 주석·지식 베이스 항목을 자연어로 옮긴다 |
| `anchor` (앵커형) | 기존 보고서의 숫자. 정의는 모른다 | "10월 매출 보고서 총액은 1,645이다" | 정답 SQL을 **정답보다 거친 입도**로 집계해 만든다 (예: 상위 3명 → 전체 합계). 정답 행을 그대로 노출하는 값은 쓰지 않는다 |

앵커형 사실은 정답에서 만들어지므로 순환성이 있다. 만드는 규칙(어떤 집계를 쓰는가)은 과제마다 고정하고 `task.json`의 `notes`에 적는다.

### 3.3 데이터셋별 규칙
| 데이터셋 | `request` | `check` | `hidden.facts` | `n_interpretations` | 남은 작업 |
|---|---|---|---|---|---|
| BIRD-Interact Lite | `amb_user_query` | `sql_result` (Postgres), 정답 `sol_sql` | 정의형: `user_query_ambiguity.critical_ambiguity`의 용어별 뜻 + `knowledge_ambiguity`로 지운 지식 베이스 항목. 앵커형: `sol_sql` 결과의 거친 집계 | 2^(핵심 모호성 수), 근사 | 정답 받기, evalkit Postgres 채점기 |
| AMBROSIA | `question` | `sql_result` (SQLite), 숨은 의도 = 해석 1개의 `gold_queries` | 정의형: 그 해석의 자연어 설명. 앵커형: 해석별 결과의 거친 집계 중 해석들을 가르는 값 | 해석 수 (원본에 있음) | 라이선스 해소 |
| DABstep | `question` + `guidelines` | `exact_answer` | 없음 (모호성 주석 없음) | `null` | evalkit `exact_answer` 채점기. 정답 있는 dev 10개만 |
| BLADE | 연구 질문 | LLM 채점 (원본 평가기) | 해당 없음 | 해당 없음 | 조용한 오판 보조 지표용. 변환 보류 |

## 4. 우선순위
1. `anchor-revenue` (자체): 앵커형 질문 전략 검증. 바로 실행 가능.
2. BIRD-Interact Lite: 정답을 받으면 정의형·앵커형 둘 다로 변환. 우리 평가의 주 데이터셋.
3. AMBROSIA: 라이선스가 풀리면 앵커형 변환에 가장 잘 맞는다 (해석마다 정답 SQL이 있다).
4. DABstep dev, BLADE: 비코딩 분석 확장 때.
