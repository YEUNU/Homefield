---
status: 초안
updated: 2026-11-08
audience: 배포
---
# 데이터셋

평가에 쓰는 데이터셋의 목록, 상태, 받는 법, 과제 형식으로의 변환 규칙이다.
FDE 현장 데이터는 세 종류다: **관계형 DB**, **로컬 파일**(CSV·엑셀·JSON·매뉴얼), **문서·비전**(PDF·스캔·표 이미지). 온톨로지 팩은 이 셋을 모두 입력으로 받는다. 데이터셋도 셋을 모두 덮는다.

출처·라이선스는 2026-11-08에 공식 페이지(논문, 공식 저장소, Hugging Face 카드)에서 확인했다. 확인 못 한 항목은 `(미확인)`으로 적는다.

## 1. 목록과 상태
상태: **받음** = `data/raw/`에 있음. **보류** = 쓸 수 있으나 막는 조건이 있음. **제외** = 쓰지 않음.

### 1.1 받음
| 종류 | 데이터셋 | 쓰임 | 데이터 라이선스 | 출처 | 받은 크기 | 정답 | 모호성 재료 |
|---|---|---|---|---|---|---|---|
| SQL | BIRD Mini-Dev | 지식 모호성 해소 | CC BY-SA 4.0 | HF `birdsql/bird_mini_dev` + 원본 dev DB(`dev.zip`) | 342MB | 공개 SQL (500) | `evidence` 365개 (지우면 모호해짐) |
| SQL | AmbiQT | 해석이 둘인 질의 | MIT | GitHub `testzer0/AmbiQT` | 247MB (DB 포함) | 해석별 SQL 2개 | 열·표 동의어, 조인, 사전 집계 |
| 로컬 파일 (CSV) | InfiAgent-DABench | CSV 분석 | Apache-2.0 | HF `infiagent/DABench` | 61MB | 닫힌 형식 정답 (dev 257) | `constraints` (지우면 모호해짐) |
| 로컬 파일 (엑셀) | SpreadsheetBench verified 400 | 엑셀 조작 | CC BY-SA 4.0 (HF 카드) | HF `KAKA22/SpreadsheetBench` | 14MB | 정답 엑셀 | 없음 |
| 로컬 파일 (혼합) | DABstep dev | 문서 규칙 + 결제 CSV | CC BY 4.0 | HF `adyen/DABstep` | 23MB | dev 10개만 | 없음 |
| 로컬 파일 (CSV) | BLADE | 분석 결정의 정당성 | ODC-By 1.0 | GitHub `behavioral-data/BLADE` | 55MB | 분석 결정 정답 | 정답이 여럿인 분석 결정 |
| 문서·비전 (PDF) | TAT-DQA dev + test 정답 | 재무보고서 문서 QA | CC BY 4.0 | HF `next-tat/TAT-DQA` | 163MB (학습용 1.2GB 제외) | 공개 (dev 1,644문항) | 단위(scale)·계산식(derivation) |
| 온톨로지 | Text2KGBench | 온톨로지 제약을 지키는 KG 생성 | Apache-2.0 | GitHub `cenguix/Text2KGBench` | 36MB | 정답 트리플 | 해당 없음 |

### 1.2 보류
| 데이터셋 | 이유 |
|---|---|
| AMBROSIA | 라이선스 충돌 (저장소 CC BY 4.0, 웹사이트 "All rights reserved"). 재배포 금지 요청 |
| BEAVER | HF 약관 동의 필요 (사람 승인) |
| FDABench | 공개분(Lite, MIT)은 객관식·보고서형과 고정 검색 결과뿐. 실제 PDF·이미지는 `FDABench-File`(약관 동의, 라이선스 "other") |
| MMLongBench-Doc | 문서는 열린 라이선스, 문항 주석 라이선스 (미확인) |
| SpreadsheetBench 2 | GitHub 저장소에 라이선스 파일 없음 (미확인) |
| LakeQuest | 저장소 라이선스 없음 (미확인) |
| Spider 2.0-DBT, BPI Challenge 2019 | 쓸 수 있으나 지금 실험에 불필요 |
| KramaBench, Wide World Importers | 라이선스 불명확 |

### 1.3 제외
| 데이터셋 | 이유 |
|---|---|
| BIRD-Interact (Lite·Full), Mini-Interact | 정답 SQL을 메일 요청으로만 준다. 메일 요청을 하지 않기로 함 (2026-11-08) |
| Ambig-DS | 비상업 라이선스, 공식 배포처 미확인 |
| EnterpriseMem-Bench, PRACTIQ | 공개 배포 못 찾음 |

### 1.4 자체 과제 (`tasks/`)
| 과제 | 사실 종류 | 해석 수 | 쓰임 |
|---|---|---|---|
| `smoke-revenue` | 정의형 | 4 | 규약 스모크, E0 대 E1 |
| `anchor-revenue` | 앵커형 | 16 | 고객이 정의를 모를 때의 질문 전략 |

## 2. 받는 법
```bash
python3 -I scripts/fetch_datasets.py              # "받음" 전부 (약 940MB)
python3 -I scripts/fetch_datasets.py tat-dqa      # 하나만
```
- 저장 위치: `data/raw/<이름>/` (git 제외). 각 폴더에 `MANIFEST.json`(출처, 리비전, 받은 시각, 파일별 sha256).
- 압축 파일은 풀지 않고 둔다. 변환 스크립트가 안전하게 푼다 (경로 탈출 검사).
- 받은 파일은 신뢰하지 않는 데이터다. 그 안의 코드(예: AmbiQT의 `*.py`)를 실행하지 않는다. 읽는 스크립트는 `scripts/`에 두고 `python3 -I`로 돈다.

## 3. 과제 형식으로의 변환 규칙
모든 데이터셋은 evalkit 과제 형식(`docs/EVALUATION.md` §2)으로 바꿔 `tasks/<데이터셋>-<원본 ID>/`에 둔다. 원본 데이터는 `tasks/`에 넣지 않는다. 변환 스크립트가 `data/raw/`에서 만든다.

### 3.1 공통 필드
| 과제 필드 | 뜻 | 규칙 |
|---|---|---|
| `request` | 고객의 모호한 요청 | 원본 질의에서 모호성 재료(정의·제약)를 뺀 문장 |
| `sources` | 입력 데이터 | `sqlite`, `csv`, `xlsx`, `pdf_pages`(페이지 이미지 + OCR JSON) 중 하나 이상 |
| `check` | 채점 | 아래 채점 종류 중 하나 |
| `hidden.facts` | 고객이 아는 것 | 아래 사실 종류 중 하나로 쓴다 |
| `hidden.fact_kind` | 사실 종류 | `definition` 또는 `anchor` |
| `n_interpretations` | 결과를 바꾸는 해석 조합 수 | 원본 주석에서 센다. 셀 수 없으면 `null` |
| `budget` | 질문·제출 예산 | 기본 질문 5, 제출 2 |

### 3.2 사실 종류
| 종류 | 고객이 아는 것 | 예 | 만드는 법 |
|---|---|---|---|
| `definition` (정의형) | 용어·계산 방법의 정의 | "매출은 세전이다" | 원본의 정의·제약 필드(`evidence`, `constraints`, 동의어 맵)를 자연어로 옮긴다 |
| `anchor` (앵커형) | 기존 보고서의 숫자. 정의는 모른다 | "10월 매출 보고서 총액은 1,645이다" | 정답을 **정답보다 거친 입도**로 집계해 만든다. 정답 값을 그대로 노출하는 숫자는 쓰지 않는다 |

앵커형은 정답에서 만들어지므로 순환성이 있다. 집계 규칙은 과제마다 고정하고 `task.json`의 `notes`에 적는다.

### 3.3 채점 종류
| 종류 | 비교 | 쓰는 데이터셋 | evalkit 구현 |
|---|---|---|---|
| `sql_result` | 답 SQL과 정답 SQL의 결과 집합 (SQLite) | BIRD Mini-Dev, AmbiQT, 자체 과제 | 있음 |
| `exact_answer` | 정규화한 문자열·수치 (허용 오차) | InfiAgent-DABench(`@키[값]` 형식), TAT-DQA(값 + 단위), DABstep | 없음 |
| `sheet_cells` | 지정 셀 범위의 값 | SpreadsheetBench | 없음 |
| `kg_triples` | 정답 트리플 대비 정밀도·재현율, 온톨로지 위반 수 | Text2KGBench | 없음 |

### 3.4 데이터셋별 규칙
| 데이터셋 | `request` | `sources` | `check` | `hidden.facts` | `n_interpretations` |
|---|---|---|---|---|---|
| BIRD Mini-Dev | `question` (evidence 제외) | `sqlite` (dev DB) | `sql_result`, 정답 `SQL` | 정의형: `evidence`. 앵커형: 정답 결과의 거친 집계 | `evidence` 문장 수로 근사 |
| AmbiQT | `question` | `sqlite` (`db-content.zip`) | `sql_result`, 숨은 의도 = `query1` 또는 `query2` 중 하나 (과제마다 고정) | 정의형: 동의어 맵(`extra_map`)을 업무 문장으로. 앵커형: 두 해석의 결과를 가르는 집계값 | 2 |
| InfiAgent-DABench | `question` (`constraints` 제외), `format`은 유지 | `csv` | `exact_answer` (`common_answers`) | 정의형: `constraints` | `constraints` 조건 수로 근사 |
| TAT-DQA | `question` | `pdf_pages` (페이지 PNG + OCR JSON) | `exact_answer` (`answer` + `scale`) | 정의형: 단위·계산 범위(`scale`, `derivation`)를 업무 문장으로. 단위가 없는 문항은 모호성 없음 | 단위·계산식이 있으면 2, 없으면 1 |
| SpreadsheetBench | 지시문 | `xlsx` | `sheet_cells` | 없음 (모호성 주석 없음) | 1 |
| DABstep dev | `question` + `guidelines` | `csv`, 문서 | `exact_answer` | 없음 | 1 |
| BLADE | 연구 질문 | `csv` | 원본 LLM 평가기 | 해당 없음 | 해당 없음 |
| Text2KGBench | 온톨로지 + 문장 | 텍스트, 온톨로지 | `kg_triples` | 해당 없음 (온톨로지 팩 평가용, CFC 아님) | 해당 없음 |

## 4. 우선순위
1. `anchor-revenue` (자체): 앵커형 질문 전략. 바로 실행 가능.
2. **BIRD Mini-Dev, AmbiQT**: `sql_result`만으로 바로 변환 가능. 정의형·앵커형 둘 다 만든다. 주 SQL 데이터셋.
3. **InfiAgent-DABench**: 로컬 CSV. `exact_answer` 채점기를 만든 뒤.
4. **TAT-DQA**: 문서·비전. `exact_answer` + 페이지 이미지 입력.
5. SpreadsheetBench, Text2KGBench: 엑셀 조작, 온톨로지 팩 평가. 채점기를 만든 뒤.
