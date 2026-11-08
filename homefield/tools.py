"""도구. M0는 셸 하나만 둔다 (공통 규약의 ask_user·submit_answer도 셸 명령이다)."""

import subprocess
from pathlib import Path

BASH = {
    "type": "function",
    "function": {
        "name": "bash",
        "description": "Run a shell command in the working directory. Returns the exit code and combined output.",
        "parameters": {
            "type": "object",
            "properties": {"command": {"type": "string", "description": "The shell command to run."}},
            "required": ["command"],
        },
    },
}


def run_bash(command: str, cwd: Path, timeout: int = 120, limit: int = 10_000) -> str:
    try:
        p = subprocess.run(["bash", "-c", command], cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return f"exit=timeout after {timeout}s"
    out = p.stdout + p.stderr
    if len(out) > limit:  # 앞뒤를 남기고 가운데를 자른다
        half = limit // 2
        out = f"{out[:half]}\n... [{len(out) - limit} chars truncated] ...\n{out[-half:]}"
    return f"exit={p.returncode}\n{out}"
