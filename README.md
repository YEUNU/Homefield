# Homefield

FDE(Forward Deployed Engineer) 작업 흐름을 위한 에이전트 하네스. 목표는 FDE 대체가 아니라 FDE 한 명의 처리량 증가이다.

이 저장소에는 현재 **하네스 비교 평가 도구(evalkit)**가 있다. 같은 모델에서 하네스만 바꿔, 모호한 데이터 분석 요청을 얼마나 적은 상호작용 비용으로 푸는지 잰다.

## 문서
- 평가 규약: [docs/EVALUATION.md](docs/EVALUATION.md)
- 비교 하네스 연결: [docs/HARNESSES.md](docs/HARNESSES.md)
- 테스트 데이터셋: [docs/DATASETS.md](docs/DATASETS.md)
- 기여·Git 정책: [docs/GIT_POLICY.md](docs/GIT_POLICY.md)

## 시작
```bash
git config core.hooksPath .githooks
cp .env.example .env        # OpenAI 호환 LLM 서버 주소와 키
scripts/llm_check.sh        # 연결 확인
uvx --python 3.12 pytest -q # 프로토콜 테스트
python3 -m evalkit.run --task tasks/smoke-revenue --harness claude
```

## 라이선스
[LICENSE](LICENSE)
