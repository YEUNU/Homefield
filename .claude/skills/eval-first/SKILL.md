---
name: eval-first
description: Build the eval before the feature for any harness component (loop, policy engine, uncertainty ledger, ontology pack, P1–P5 stage). Use when starting a new component, changing harness behavior, running a benchmark (BIRD-Interact, Spider 2.0, DABstep, KramaBench, BPI 2019, WWI), or comparing variants with ablation.
---

# Eval First

하네스 동작을 바꾸기 전에 측정 방법을 먼저 만든다.

## 순서
1. **질문 정의**: 이 변경이 어떤 지표를 움직여야 하는가? (`docs/DATASETS.md`의 지표 목록에서 고른다.)
2. **eval 과제 작성**: `evals/<component>/` 아래에 입력·기대 결과를 둔다. 최소 5개. 실패 과제를 포함한다.
3. **기준선 실행**: 변경 전 상태로 evalkit을 돌린다. 결과는 `evals/results/<날짜>.jsonl`에 쌓인다.
4. **구현**.
5. **비교 실행**: 같은 과제, 같은 모델, 같은 반복 수. `python3 -m evalkit.report`로 기준선과 나란히 본다.
6. **ablation**: 구성 요소를 하나씩 끄고 다시 돈다. 효과가 없는 요소는 제거 후보로 기록한다.

## 결과 한 줄마다 기록할 필드
필드 정의는 `docs/EVALUATION.md` §7이 원천이다. evalkit 실행기가 그 형식으로 쓴다.

## 규칙
- 모델은 기본으로 로컬 LLM을 쓴다 (`local-llm` 스킬). 모델 ID를 결과에 반드시 남긴다.
- 표본이 작으면(<30) 결론 대신 "관찰"로 쓴다.
- 벤치마크 수치를 인용할 때 출처 논문과 설정(c-Interact / a-Interact 등)을 같이 적는다.
- eval 없는 PR은 "미검증"으로 표시한다.
