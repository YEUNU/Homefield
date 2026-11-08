"""로컬 LLM 최소 클라이언트 (OpenAI 호환 chat). 설정은 저장소 루트 .env에서 읽는다."""
import json
import os
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = "google/gemma-4-31B-it"


def load_env() -> dict:
    env = {}
    path = ROOT / ".env"
    if path.exists():
        for line in path.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return {**env, **{k: v for k, v in os.environ.items() if k.startswith("LOCAL_LLM_")}}


def chat(messages: list[dict], model: str = DEFAULT_MODEL, max_tokens: int = 512, temperature: float = 0.0) -> str:
    env = load_env()
    body = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    req = urllib.request.Request(
        env["LOCAL_LLM_BASE_URL"].rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {env['LOCAL_LLM_API_KEY']}"},
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)["choices"][0]["message"]["content"] or ""
