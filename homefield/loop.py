"""M0 loop: call the model, run the tools, append the results to the conversation.
It ends when a reply has no tool call.
The model is injected as the complete function (default: homefield.model.complete)."""

import json
from dataclasses import dataclass
from pathlib import Path

from homefield import model
from homefield.tools import BASH, run_bash

SYSTEM = (
    "You are an agent working in a shell. Use the bash tool to inspect files and run commands "
    "in the current working directory. Follow the task's rules exactly. "
    "When the task is finished, reply with a short final message and no tool call."
)


@dataclass
class Result:
    final: str
    stop: str  # "final" | "max_turns"
    turns: int
    messages: list[dict]


def _execute(call: dict, cwd: Path) -> str:
    name = call["function"]["name"]
    if name != "bash":
        return f"error: unknown tool {name!r}. Only 'bash' is available."
    try:
        args = json.loads(call["function"]["arguments"] or "{}")
    except json.JSONDecodeError as e:
        return f"error: arguments are not valid JSON ({e})."
    return run_bash(args.get("command", ""), cwd)


def run(task: str, cwd: Path, complete=model.complete, max_turns: int = 40, log: Path | None = None) -> Result:
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": task}]
    logged = 0

    def flush():
        nonlocal logged
        if log:
            with open(log, "a") as f:
                f.writelines(json.dumps(m, ensure_ascii=False) + "\n" for m in messages[logged:])
        logged = len(messages)

    for turn in range(1, max_turns + 1):
        msg = complete(messages, tools=[BASH])
        messages.append(msg)
        calls = msg.get("tool_calls") or []
        if not calls:
            flush()
            return Result(msg.get("content") or "", "final", turn, messages)
        for call in calls:
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": _execute(call, cwd)})
        flush()
    return Result("", "max_turns", max_turns, messages)
