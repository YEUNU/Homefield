#!/usr/bin/env bash
# Check the local LLM connection: model list and model group info.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] && { set -a; . ./.env; set +a; }
: "${LOCAL_LLM_BASE_URL:?LOCAL_LLM_BASE_URL is not set. Put it in .env}"
if [ -z "${LOCAL_LLM_API_KEY:-}" ]; then
  echo "LOCAL_LLM_API_KEY is not set. Copy .env.example to .env and add the key." >&2; exit 1
fi
# Python's urllib needs a scheme, and the client appends paths to .../v1. curl accepts less, so check here.
if ! [[ "$LOCAL_LLM_BASE_URL" =~ ^https?://[^/]+(/.*)?/v1$ ]]; then
  echo "LOCAL_LLM_BASE_URL must start with http:// or https:// and end with /v1 (for example http://<host>/v1)." >&2; exit 1
fi
auth=(-H "Authorization: Bearer $LOCAL_LLM_API_KEY")
echo "== models"
curl -sf -m 10 "${auth[@]}" "$LOCAL_LLM_BASE_URL/models" | python3 -c 'import json,sys; [print(m["id"]) for m in json.load(sys.stdin)["data"]]'
echo "== model_group/info"
curl -sf -m 10 "${auth[@]}" "${LOCAL_LLM_BASE_URL%/v1}/model_group/info" | python3 -c '
import json,sys
for g in json.load(sys.stdin).get("data",[]):
    print(g.get("model_group"), g.get("mode"), "ctx=",g.get("max_input_tokens"), "tools=",g.get("supports_function_calling"), "vision=",g.get("supports_vision"))'
# The model list can answer while the model behind the proxy is down. Make one small chat call.
model=$(python3 -c "from homefield.model import DEFAULT_MODEL as m; print(m)")  # same default as the harness
echo "== chat ($model)"
body=$(printf '{"model":"%s","messages":[{"role":"user","content":"Reply with the word ok."}],"max_tokens":8}' "$model")
code=$(curl -s -m 120 -o /tmp/check_llm_chat.$$ -w '%{http_code}' "${auth[@]}" -H "Content-Type: application/json" \
  -d "$body" "$LOCAL_LLM_BASE_URL/chat/completions") || code="curl-failed"
if [ "$code" != 200 ]; then
  echo "chat call failed (HTTP $code): $(head -c 300 /tmp/check_llm_chat.$$ 2>/dev/null)" >&2
  rm -f /tmp/check_llm_chat.$$; exit 1
fi
rm -f /tmp/check_llm_chat.$$; echo "   ok"

