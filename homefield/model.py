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
    max_tokens: int = 2048,
    temperature: float = 0.0,
) -> dict:
    """assistant 메시지 하나를 돌려준다: {"role", "content", "tool_calls"(있으면)}."""
    env = load_env()
    body = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "chat_template_kwargs": {"enable_thinking": False},
    }
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


def chat(messages: list[dict], model: str = DEFAULT_MODEL, max_tokens: int = 512) -> str:
    """도구 없이 텍스트만 받는다."""
    return complete(messages, model=model, max_tokens=max_tokens)["content"] or ""
