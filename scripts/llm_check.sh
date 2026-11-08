#!/usr/bin/env bash
# 로컬 LLM 연결 확인: 모델 목록 + 모델 그룹 정보.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] && { set -a; . ./.env; set +a; }
: "${LOCAL_LLM_BASE_URL:=http://192.168.10.10/v1}"
if [ -z "${LOCAL_LLM_API_KEY:-}" ]; then
  echo "LOCAL_LLM_API_KEY 없음. .env.example을 .env로 복사하고 키를 넣는다." >&2; exit 1
fi
auth=(-H "Authorization: Bearer $LOCAL_LLM_API_KEY")
echo "== models"
curl -sf -m 10 "${auth[@]}" "$LOCAL_LLM_BASE_URL/models" | python3 -c 'import json,sys; [print(m["id"]) for m in json.load(sys.stdin)["data"]]'
echo "== model_group/info"
curl -sf -m 10 "${auth[@]}" "${LOCAL_LLM_BASE_URL%/v1}/model_group/info" | python3 -c '
import json,sys
for g in json.load(sys.stdin).get("data",[]):
    print(g.get("model_group"), g.get("mode"), "ctx=",g.get("max_input_tokens"), "tools=",g.get("supports_function_calling"), "vision=",g.get("supports_vision"))'
