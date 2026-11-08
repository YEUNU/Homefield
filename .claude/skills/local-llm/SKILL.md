---
name: local-llm
description: Call the on-prem LLM server configured in LOCAL_LLM_BASE_URL (OpenAI-compatible /v1, chat, embeddings, and the /v1/systemone decision-model endpoint). Use when writing harness code that calls a model, running evals or smoke tests, choosing a model ID, or when the user mentions the local LLM / on-prem model.
---

# Local LLM

Details: `internal/LOCAL_LLM.md`.

## Settings
- `LOCAL_LLM_BASE_URL`: Read it from `.env` (the server address is in the internal doc `internal/LOCAL_LLM.md`)
- Read `LOCAL_LLM_API_KEY` from `.env`. Do not print or commit the key value.
- If the key is missing, ask the user to put it in `.env`. Do not create or guess it.

## First steps
1. Check the connection and the model list with `scripts/check_llm.sh`.
2. Copy the model ID as is from the `/v1/models` result. Do not hardcode it. Keep it as a setting.
3. Check model abilities (context length, tool support, mode) with `/model_group/info`.

## Call examples
```bash
set -a; . ./.env; set +a
curl -s "$LOCAL_LLM_BASE_URL/chat/completions" \
  -H "Authorization: Bearer $LOCAL_LLM_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"<ID>","messages":[{"role":"user","content":"ping"}],
       "max_tokens":256,"chat_template_kwargs":{"enable_thinking":false}}'
```

Decision model:
```bash
curl -s "${LOCAL_LLM_BASE_URL%/v1}/v1/systemone" -H "Authorization: Bearer $LOCAL_LLM_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"<decision model ID>","state":"...","questions":{"q1":{"type":"noul","instructions":"..."}}}'
```

## Rules
- Thinking models: set `max_tokens` high (>=2048) or turn thinking off. If the reply is empty, suspect this cause first.
- The harness core calls this server only over OpenAI-compatible HTTP. Keep server-specific features (`/v1/systemone`) behind an adapter.
- Record the model ID and the thinking setting in eval results.
