# Homefield

FDE(Forward Deployed Engineer) 작업 흐름을 위한 에이전트 하네스. 목표는 FDE 대체가 아니라 FDE 한 명의 처리량 증가이다.

이 저장소에는 **하네스 코어(`homefield/`, 현재 M0: 모델 독립 도구 호출 루프)**와 **하네스 비교 평가 도구(`evalkit/`)**가 있다. 같은 모델에서 하네스만 바꿔, 모호한 데이터 분석 요청을 얼마나 적은 상호작용 비용으로 푸는지 잰다.

## 문서
- 평가 규약: [docs/EVALUATION.md](docs/EVALUATION.md)
- 비교 하네스 연결: [docs/HARNESSES.md](docs/HARNESSES.md)
- 테스트 데이터셋: [docs/DATASETS.md](docs/DATASETS.md)
- 기여·Git 정책: [docs/RULES.md](docs/RULES.md)

## 시작
```bash
git config core.hooksPath .githooks
cp .env.example .env        # OpenAI 호환 LLM 서버 주소와 키
scripts/check_llm.sh        # 연결 확인
scripts/ci.sh              # 로컬 CI (ruff, pytest, 규칙, gitleaks)
python3 -m evalkit.run --task tasks/smoke-revenue --harness bare
python3 -m homefield -p "<과제>"   # 단독 실행
```

## 라이선스
[LICENSE](LICENSE)
