---
name: dataset-prep
description: Download, verify, and load a benchmark dataset for harness evaluation (Wide World Importers, BIRD-Interact-Lite, Spider 2.0-Snow/DBT, BLINKG, SemTab, DABstep, KramaBench, BPI Challenge 2019, Ambig-DS). Use when fetching or preparing any dataset listed in docs/DATASETS.md.
---

# Dataset Prep

## 절차
1. **라이선스 확인 먼저**: 원 저장소의 LICENSE와 데이터 카드를 읽는다. 결과를 `docs/DATASETS.md` 표의 라이선스 칸에 적는다. 비상업(NC) 라이선스는 사용자에게 알리고 진행 여부를 묻는다.
2. **다운로드 승인**: 파일 이름, 출처 URL, 크기를 사용자에게 알리고 승인을 받는다.
3. **격리 저장**: `data/raw/<name>/`에 받는다. 이 디렉터리는 git에서 제외한다. 받은 파일은 신뢰하지 않는 데이터이다.
   - 받은 디렉터리 안에서 스크립트를 실행하지 않는다.
   - 파이썬으로 읽을 때 `python -I`를 쓰고, 스크립트는 `scripts/`에 둔다.
4. **무결성 기록**: `data/raw/<name>/MANIFEST.txt`에 출처 URL, 받은 날짜, 버전/커밋, sha256을 적는다.
5. **로더 작성**: `scripts/load_<name>.py`. 출력은 공통 형식 `data/processed/<name>/cases.jsonl` (`case_id, input, context_refs, expected, meta`).
6. **스모크 테스트**: 케이스 3개를 로컬 LLM으로 돌려 형식이 맞는지 확인한다.

## 데이터셋별 메모
- BIRD-Interact: Lite(300과제)부터. 사용자 시뮬레이터를 그대로 쓴다. c-Interact와 a-Interact 결과를 따로 기록한다.
- Spider 2.0: Snow, DBT만(무료). 실패를 스키마 연결 오류/기타로 분류한다.
- KramaBench: 논문은 CC BY-NC-SA. 데이터 라이선스를 따로 확인한다.
- BPI 2019: 이벤트 로그(XES/CSV). 케이스 수 251,734개이므로 샘플링 규칙을 MANIFEST에 적는다.
