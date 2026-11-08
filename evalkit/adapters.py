"""비교 하네스 어댑터. 각 함수는 (명령, 추가 환경변수)를 돌려준다. 모든 설정은 에피소드 폴더 안에 격리한다.
연결 방식 근거: docs/HARNESSES.md"""
import json
import os
from pathlib import Path


def _home(ep, name: str) -> Path:
    p = ep.root / "home" / name
    p.mkdir(parents=True, exist_ok=True)
    return p


def claude(ep, prompt: str, model: str, env: dict):
    return (
        ["npx", "-y", "@anthropic-ai/claude-code@latest", "-p", prompt,
         "--allowedTools", "Bash,Read,Write,Edit,Glob,Grep", "--output-format", "json"],
        {
            "CLAUDE_CONFIG_DIR": str(_home(ep, "claude")),
            "ANTHROPIC_BASE_URL": env["LOCAL_LLM_BASE_URL"].removesuffix("/v1"),
            "ANTHROPIC_AUTH_TOKEN": env["LOCAL_LLM_API_KEY"],
            "ANTHROPIC_API_KEY": "",
            "ANTHROPIC_MODEL": model,
            "ANTHROPIC_SMALL_FAST_MODEL": model,
            "ANTHROPIC_DEFAULT_HAIKU_MODEL": model,
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        },
    )


def codex(ep, prompt: str, model: str, env: dict):
    home = _home(ep, "codex")
    (home / "config.toml").write_text(
        f'model = "{model}"\nmodel_provider = "local"\n'
        f'[model_providers.local]\nname = "local"\nbase_url = "{env["LOCAL_LLM_BASE_URL"]}"\n'
        f'env_key = "LOCAL_LLM_API_KEY"\nwire_api = "responses"\n'
    )
    return (
        ["npx", "-y", "@openai/codex@latest", "exec", "--skip-git-repo-check", "-s", "workspace-write",
         "-c", "sandbox_workspace_write.network_access=true", prompt],
        {"CODEX_HOME": str(home), "LOCAL_LLM_API_KEY": env["LOCAL_LLM_API_KEY"]},
    )


def opencode(ep, prompt: str, model: str, env: dict):
    home = _home(ep, "opencode")
    cfg = {
        "$schema": "https://opencode.ai/config.json",
        "provider": {"local": {
            "npm": "@ai-sdk/openai-compatible", "name": "Local LLM",
            "options": {"baseURL": env["LOCAL_LLM_BASE_URL"], "apiKey": env["LOCAL_LLM_API_KEY"]},
            "models": {model: {"name": model, "tool_call": True}},
        }},
        "model": f"local/{model}",
        "permission": {"bash": "allow", "edit": "allow", "external_directory": "allow"},
    }
    (home / "opencode.json").write_text(json.dumps(cfg))
    xdg = {f"XDG_{k}_HOME": str(home / k.lower()) for k in ("CONFIG", "DATA", "CACHE", "STATE")}
    return (["npx", "-y", "opencode-ai@latest", "run", prompt], {"OPENCODE_CONFIG": str(home / "opencode.json"), **xdg})


def mini(ep, prompt: str, model: str, env: dict):
    return (
        ["uvx", "--python", "3.12", "--from", "mini-swe-agent", "--with", "mcp", "mini", "-m", f"openai/{model}",
         "-t", prompt, "-y", "-l", "0", "--exit-immediately", "-o", str(ep.root / "traj.json")],
        {
            "MSWEA_GLOBAL_CONFIG_DIR": str(_home(ep, "mini")),
            "MSWEA_CONFIGURED": "true",
            "MSWEA_COST_TRACKING": "ignore_errors",
            "OPENAI_API_BASE": env["LOCAL_LLM_BASE_URL"],
            "OPENAI_API_KEY": env["LOCAL_LLM_API_KEY"],
        },
    )


def openhands(ep, prompt: str, model: str, env: dict):
    return (
        ["uvx", "--python", "3.12", "openhands", "--headless", "--yolo", "--override-with-envs",
         "--exit-without-confirmation", "-t", prompt],
        {
            "HOME": str(_home(ep, "openhands")),
            "UV_CACHE_DIR": os.environ.get("UV_CACHE_DIR", str(Path.home() / ".cache" / "uv")),
            "OPENHANDS_SUPPRESS_BANNER": "1",
            "LLM_MODEL": f"openai/{model}",
            "LLM_BASE_URL": env["LOCAL_LLM_BASE_URL"],
            "LLM_API_KEY": env["LOCAL_LLM_API_KEY"],
        },
    )


ADAPTERS = {"claude": claude, "codex": codex, "opencode": opencode, "mini": mini, "openhands": openhands}
