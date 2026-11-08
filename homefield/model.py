"""모델 호출 단일 모듈 (OpenAI 호환 chat completions). 다른 모듈은 HTTP로 모델을 직접 부르지 않는다.
설정은 저장소 루트 .env의 LOCAL_LLM_BASE_URL, LOCAL_LLM_API_KEY."""

import json
import os
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = os.environ.get("HOMEFIELD_MODEL", "google/gemma-4-31B-it")


def load_env() -> dict:
    env = {}
    path = ROOT / ".env"
    if path.exists():
        for line in path.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return {**env, **{k: v for k, v in os.environ.items() if k.startswith("LOCAL_LLM_")}}


def complete(
    messages: list[dict],
    tools: list[dict] | None = None,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 8192,
    temperature: float | None = None,
    thinking: bool | None = None,
) -> dict:
    """assistant 메시지 하나를 돌려준다: {"role", "content", "tool_calls"(있으면)}.
    temperature·thinking이 None이면 서버 기본값을 쓴다 (비교 하네스들과 같은 조건).
    thinking 모델은 생각에 토큰을 쓰므로 max_tokens를 넉넉히 둔다."""
    env = load_env()
    body = {"model": model, "messages": messages, "max_tokens": max_tokens}
    if temperature is not None:
        body["temperature"] = temperature
    if thinking is not None:
        body["chat_template_kwargs"] = {"enable_thinking": thinking}
    if tools:
        body["tools"] = tools
    req = urllib.request.Request(
        env["LOCAL_LLM_BASE_URL"].rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {env['LOCAL_LLM_API_KEY']}"},
    )
    with urllib.request.urlopen(req, timeout=600) as r:
        msg = json.load(r)["choices"][0]["message"]
    out = {"role": "assistant", "content": msg.get("content")}
    if msg.get("tool_calls"):
        out["tool_calls"] = [
            {"id": c["id"], "type": "function", "function": {k: c["function"][k] for k in ("name", "arguments")}}
            for c in msg["tool_calls"]
        ]
    return out


def chat(messages: list[dict], model: str = DEFAULT_MODEL, max_tokens: int = 512, **sampling) -> str:
    """도구 없이 텍스트만 받는다. sampling: temperature, thinking."""
    return complete(messages, model=model, max_tokens=max_tokens, **sampling)["content"] or ""
