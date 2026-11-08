"""M0 loop: call the model, run the tools, append the results to the conversation.
It ends when a reply has no tool call.
The model is injected as the complete function (default: homefield.model.complete)."""

import json
import time
from dataclasses import dataclass
from pathlib import Path

from homefield import model
from homefield.tools import BASH, run_bash

SYSTEM = (
    "You are an agent working in a shell. Use the bash tool to inspect files and run commands "
    "in the current working directory. Follow the task's rules exactly. "
    "When the task is finished, reply with a short final message and no tool call."
)

FINALIZE = (
    "You have run out of {what}. Stop exploring now. In the next {n} turns, deliver your best answer "
    "exactly as the task's rules say (write the answer, then submit it). If no option fits exactly, "
    "deliver the closest one and state your assumptions."
)


@dataclass
class Result:
    final: str
    stop: str  # "final" | "max_turns" | "deadline" (finalize: the stop that started it, then "+final" or "+cap")
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


def run(
    task: str,
    cwd: Path,
    complete=model.complete,
    max_turns: int = 40,
    log: Path | None = None,
    deadline_s: float | None = None,
    finalize_turns: int = 0,
) -> Result:
    """With finalize_turns > 0: when the turn cap or the deadline is reached, send FINALIZE and allow
    finalize_turns more turns to deliver (Experiment K0, internal ROADMAP). With 0: M0 behavior."""
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": task}]
    logged = 0

    def flush():
        nonlocal logged
        if log:
            with open(log, "a") as f:
                f.writelines(json.dumps(m, ensure_ascii=False) + "\n" for m in messages[logged:])
        logged = len(messages)

    t0 = time.monotonic()
    turn, limit, cause = 0, max_turns, ""
    while turn < limit:
        turn += 1
        msg = complete(messages, tools=[BASH])
        messages.append(msg)
        calls = msg.get("tool_calls") or []
        if not calls:
            flush()
            return Result(msg.get("content") or "", f"{cause}+final" if cause else "final", turn, messages)
        for call in calls:
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": _execute(call, cwd)})
        flush()
        if cause or not finalize_turns:
            if not cause and deadline_s is not None and time.monotonic() - t0 > deadline_s:
                return Result("", "deadline", turn, messages)
            continue
        if turn >= max_turns or (deadline_s is not None and time.monotonic() - t0 > deadline_s):
            cause = "max_turns" if turn >= max_turns else "deadline"
            what = "turns" if cause == "max_turns" else "time"
            messages.append({"role": "user", "content": FINALIZE.format(what=what, n=finalize_turns)})
            limit = turn + finalize_turns
    return Result("", f"{cause}+cap" if cause else "max_turns", turn, messages)
