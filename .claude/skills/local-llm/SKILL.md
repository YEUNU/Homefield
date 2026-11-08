---
name: local-llm
description: Call the on-prem LLM server configured in LOCAL_LLM_BASE_URL (OpenAI-compatible /v1, chat, embeddings, and the /v1/systemone decision-model endpoint). Use when writing harness code that calls a model, running evals or smoke tests, choosing a model ID, or when the user mentions the local LLM / 로컬 LLM / 온프레미스 모델.
---

# Local LLM

상세 문서: `internal/LOCAL_LLM.md`.

## 설정
- `LOCAL_LLM_BASE_URL`: `.env`에서 읽는다 (서버 주소는 내부 문서 `internal/LOCAL_LLM.md`)
- `LOCAL_LLM_API_KEY`는 `.env`에서 읽는다. 키 값을 출력하거나 커밋하지 않는다.
- 키가 없으면 사용자에게 `.env`에 넣어 달라고 요청한다. 직접 만들거나 추측하지 않는다.

## 먼저 할 일
1. `scripts/check_llm.sh`로 연결과 모델 목록을 확인한다.
2. 모델 ID는 `/v1/models` 결과에서 그대로 복사한다. 하드코딩하지 말고 설정값으로 둔다.
3. 모델 능력(문맥 길이, 도구 지원, mode)은 `/model_group/info`로 확인한다.

## 호출 예
```bash
set -a; . ./.env; set +a
curl -s "$LOCAL_LLM_BASE_URL/chat/completions" \
  -H "Authorization: Bearer $LOCAL_LLM_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"<ID>","messages":[{"role":"user","content":"ping"}],
       "max_tokens":256,"chat_template_kwargs":{"enable_thinking":false}}'
```

판단 모델:
```bash
curl -s "${LOCAL_LLM_BASE_URL%/v1}/v1/systemone" -H "Authorization: Bearer $LOCAL_LLM_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"<판단 모델 ID>","state":"...","questions":{"q1":{"type":"noul","instructions":"..."}}}'
```

## 규칙
- thinking 모델: `max_tokens`를 넉넉히(≥2048) 두거나 thinking을 끈다. 빈 응답이면 이 원인을 먼저 의심한다.
- 하네스 코어는 이 서버를 OpenAI 호환 HTTP로만 호출한다. 서버 전용 기능(`/v1/systemone`)은 어댑터 뒤에 둔다.
- eval 결과에는 모델 ID와 thinking 설정을 기록한다.
