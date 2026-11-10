"""Single module for model calls (OpenAI-compatible chat completions). No other module calls the model over HTTP.
Settings come from LOCAL_LLM_BASE_URL and LOCAL_LLM_API_KEY in the .env at the repo root."""

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
    """Return one assistant message: {"role", "content", "tool_calls" (if any)}.
    If temperature or thinking is None, use the server default (same condition as the compared harnesses).
    Thinking models spend tokens on thinking, so keep max_tokens high."""
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
    """Get text only, with no tools. sampling: temperature, thinking."""
    return complete(messages, model=model, max_tokens=max_tokens, **sampling)["content"] or ""


def ask_json(messages: list[dict], check, complete=complete):
    """Get one JSON object from the model. check(obj) returns the value to use or raises ValueError.
    A reply that does not parse or does not pass the check gets one retry; then ValueError."""
    messages = list(messages)
    for _ in (1, 2):
        reply = complete(messages).get("content") or ""
        try:
            start, end = reply.index("{"), reply.rindex("}")
            return check(json.loads(reply[start : end + 1]))
        except (ValueError, KeyError, TypeError, AttributeError) as e:
            problem = f"{type(e).__name__}: {e}"
        messages += [
            {"role": "assistant", "content": reply},
            {"role": "user", "content": f"That reply cannot be used ({problem}). Reply with the JSON object only."},
        ]
    raise ValueError(f"no usable JSON after 2 replies ({problem})")
