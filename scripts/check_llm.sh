#!/usr/bin/env bash
# Check the local LLM connection: model list and model group info.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] && { set -a; . ./.env; set +a; }
: "${LOCAL_LLM_BASE_URL:?LOCAL_LLM_BASE_URL is not set. Put it in .env}"
if [ -z "${LOCAL_LLM_API_KEY:-}" ]; then
  echo "LOCAL_LLM_API_KEY is not set. Copy .env.example to .env and add the key." >&2; exit 1
fi
auth=(-H "Authorization: Bearer $LOCAL_LLM_API_KEY")
echo "== models"
curl -sf -m 10 "${auth[@]}" "$LOCAL_LLM_BASE_URL/models" | python3 -c 'import json,sys; [print(m["id"]) for m in json.load(sys.stdin)["data"]]'
echo "== model_group/info"
curl -sf -m 10 "${auth[@]}" "${LOCAL_LLM_BASE_URL%/v1}/model_group/info" | python3 -c '
import json,sys
for g in json.load(sys.stdin).get("data",[]):
    print(g.get("model_group"), g.get("mode"), "ctx=",g.get("max_input_tokens"), "tools=",g.get("supports_function_calling"), "vision=",g.get("supports_vision"))'
