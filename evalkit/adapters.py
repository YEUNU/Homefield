"""비교 하네스 어댑터. 각 함수는 (명령, 추가 환경변수)를 돌려준다. 모든 설정은 에피소드 폴더 안에 격리한다.
연결 방식 근거: docs/HARNESSES.md"""

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 재현성을 위해 버전을 고정한다. goose는 Homebrew 설치본을 쓴다 (실행 시 버전을 확인해 기록).
VERSIONS = {
    "claude": "2.1.319",
    "codex": "0.167.0",
    "opencode": "1.19.5",
    "qwen": "0.27.0",
    "openhands": "1.16.0",
    "mini": "2.4.6",
    "goose": "1.57.0",
}


def _home(ep, name: str) -> Path:
    p = ep.root / "home" / name
    p.mkdir(parents=True, exist_ok=True)
    return p


def claude(ep, prompt: str, model: str, env: dict):
    return (
        [
            "npx",
            "-y",
            f"@anthropic-ai/claude-code@{VERSIONS['claude']}",
            "-p",
            prompt,
            "--allowedTools",
            "Bash,Read,Write,Edit,Glob,Grep",
            "--output-format",
            "json",
        ],
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
        [
            "npx",
            "-y",
            f"@openai/codex@{VERSIONS['codex']}",
            "exec",
            "--skip-git-repo-check",
            "-s",
            "workspace-write",
            "-c",
            "sandbox_workspace_write.network_access=true",
            prompt,
        ],
        {"CODEX_HOME": str(home), "LOCAL_LLM_API_KEY": env["LOCAL_LLM_API_KEY"]},
    )


def opencode(ep, prompt: str, model: str, env: dict):
    home = _home(ep, "opencode")
    cfg = {
        "$schema": "https://opencode.ai/config.json",
        "provider": {
            "local": {
                "npm": "@ai-sdk/openai-compatible",
                "name": "Local LLM",
                "options": {"baseURL": env["LOCAL_LLM_BASE_URL"], "apiKey": env["LOCAL_LLM_API_KEY"]},
                "models": {model: {"name": model, "tool_call": True}},
            }
        },
        "model": f"local/{model}",
        "permission": {"bash": "allow", "edit": "allow", "external_directory": "allow"},
    }
    (home / "opencode.json").write_text(json.dumps(cfg))
    xdg = {f"XDG_{k}_HOME": str(home / k.lower()) for k in ("CONFIG", "DATA", "CACHE", "STATE")}
    return (
        ["npx", "-y", f"opencode-ai@{VERSIONS['opencode']}", "run", prompt],
        {"OPENCODE_CONFIG": str(home / "opencode.json"), **xdg},
    )


def mini(ep, prompt: str, model: str, env: dict):
    return (
        [
            "uvx",
            "--python",
            "3.12",
            "--from",
            f"mini-swe-agent=={VERSIONS['mini']}",
            "--with",
            "mcp",
            "mini",
            "-m",
            f"openai/{model}",
            "-t",
            prompt,
            "-y",
            "-l",
            "0",
            "--exit-immediately",
            "-o",
            str(ep.root / "traj.json"),
        ],
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
        [
            "uvx",
            "--python",
            "3.12",
            "--from",
            f"openhands=={VERSIONS['openhands']}",
            "openhands",
            "--headless",
            "--yolo",
            "--override-with-envs",
            "--exit-without-confirmation",
            "-t",
            prompt,
        ],
        {
            "HOME": str(_home(ep, "openhands")),
            "UV_CACHE_DIR": os.environ.get("UV_CACHE_DIR", str(Path.home() / ".cache" / "uv")),
            "OPENHANDS_SUPPRESS_BANNER": "1",
            "LLM_MODEL": f"openai/{model}",
            "LLM_BASE_URL": env["LOCAL_LLM_BASE_URL"],
            "LLM_API_KEY": env["LOCAL_LLM_API_KEY"],
        },
    )


def qwen(ep, prompt: str, model: str, env: dict):
    return (
        ["npx", "-y", f"@qwen-code/qwen-code@{VERSIONS['qwen']}", "-p", prompt, "--yolo", "--auth-type", "openai"],
        {
            "HOME": str(_home(ep, "qwen")),
            "npm_config_cache": os.environ.get("npm_config_cache", str(Path.home() / ".npm")),
            "QWEN_CODE_SUPPRESS_YOLO_WARNING": "1",
            "OPENAI_API_KEY": env["LOCAL_LLM_API_KEY"],
            "OPENAI_BASE_URL": env["LOCAL_LLM_BASE_URL"],
            "OPENAI_MODEL": model,
        },
    )


def goose(ep, prompt: str, model: str, env: dict):
    home = _home(ep, "goose")
    return (
        ["goose", "run", "--no-session", "-t", prompt],
        {
            "HOME": str(home),
            "XDG_CONFIG_HOME": str(home / ".config"),
            "GOOSE_PROVIDER": "openai",
            "GOOSE_MODEL": model,
            "GOOSE_MODE": "auto",
            "GOOSE_DISABLE_KEYRING": "1",
            "OPENAI_API_KEY": env["LOCAL_LLM_API_KEY"],
            "OPENAI_HOST": env["LOCAL_LLM_BASE_URL"].removesuffix("/v1"),
            "OPENAI_BASE_PATH": "v1/chat/completions",
        },
    )


def bare(ep, prompt: str, model: str, env: dict):
    """우리 하네스 M0: 모델 독립 도구 호출 루프 (homefield)."""
    return (
        ["python3", "-m", "homefield", "-p", prompt, "--model", model, "--log", str(ep.root / "trajectory.jsonl")],
        {"PYTHONPATH": str(ROOT)},
    )


ADAPTERS = {
    "bare": bare,
    "claude": claude,
    "codex": codex,
    "opencode": opencode,
    "qwen": qwen,
    "openhands": openhands,
    "goose": goose,
    "mini": mini,
}
