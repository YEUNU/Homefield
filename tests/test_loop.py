"""M0 loop test. The model is replaced by a fake function that answers from a script (no network)."""

import json

from homefield.loop import run
from homefield.tools import run_bash


def call(command: str, cid: str = "c1") -> dict:
    return {"id": cid, "type": "function", "function": {"name": "bash", "arguments": json.dumps({"command": command})}}


def scripted(*replies):
    replies = list(replies)
    seen = []

    def complete(messages, tools=None):
        seen.append([m["role"] for m in messages])
        return replies.pop(0)

    complete.seen = seen
    return complete


def test_runs_tool_then_stops_on_final_answer(tmp_path):
    complete = scripted(
        {"role": "assistant", "content": None, "tool_calls": [call("echo hi > f.txt")]},
        {"role": "assistant", "content": "done"},
    )
    result = run("make f.txt", tmp_path, complete=complete)
    assert (tmp_path / "f.txt").read_text() == "hi\n"
    assert result.final == "done" and result.stop == "final" and result.turns == 2
    tool_msg = result.messages[3]
    assert tool_msg["role"] == "tool" and tool_msg["tool_call_id"] == "c1" and tool_msg["content"].startswith("exit=0")
    assert complete.seen[1] == ["system", "user", "assistant", "tool"]  # the tool result goes into the next call


def test_stops_at_max_turns(tmp_path):
    complete = scripted(*[{"role": "assistant", "content": None, "tool_calls": [call("true")]} for _ in range(3)])
    result = run("loop", tmp_path, complete=complete, max_turns=3)
    assert result.stop == "max_turns" and result.turns == 3


def test_bad_arguments_and_unknown_tool_are_reported_not_raised(tmp_path):
    bad = {"id": "b", "type": "function", "function": {"name": "bash", "arguments": "{not json"}}
    unknown = {"id": "u", "type": "function", "function": {"name": "python", "arguments": "{}"}}
    complete = scripted(
        {"role": "assistant", "content": None, "tool_calls": [bad, unknown]},
        {"role": "assistant", "content": "ok"},
    )
    result = run("x", tmp_path, complete=complete)
    contents = [m["content"] for m in result.messages if m["role"] == "tool"]
    assert contents[0].startswith("error: arguments") and contents[1].startswith("error: unknown tool")


def test_trajectory_log(tmp_path):
    log = tmp_path / "traj.jsonl"
    run("x", tmp_path, complete=scripted({"role": "assistant", "content": "ok"}), log=log)
    roles = [json.loads(line)["role"] for line in log.read_text().splitlines()]
    assert roles == ["system", "user", "assistant"]


def test_run_bash_truncates_and_times_out(tmp_path):
    out = run_bash("python3 -c 'print(\"x\" * 50000)'", tmp_path, limit=1000)
    assert out.startswith("exit=0") and len(out) < 1200 and "truncated" in out
    assert run_bash("sleep 3", tmp_path, timeout=1).startswith("exit=timeout")


def test_finalize_after_turn_cap_delivers(tmp_path):
    tool = {"role": "assistant", "content": None, "tool_calls": [call("true")]}
    complete = scripted(tool, tool, tool, {"role": "assistant", "content": "submitted"})
    result = run("loop", tmp_path, complete=complete, max_turns=2, finalize_turns=3)
    assert result.stop == "max_turns+final" and result.turns == 4 and result.final == "submitted"
    finalize = result.messages[6]  # system, user, (assistant, tool) x2, then the finalize message
    assert finalize["role"] == "user" and "run out of turns" in finalize["content"]
    assert sum(m["role"] == "user" for m in result.messages) == 2  # sent once


def test_finalize_turns_are_capped(tmp_path):
    complete = scripted(*[{"role": "assistant", "content": None, "tool_calls": [call("true")]} for _ in range(5)])
    result = run("loop", tmp_path, complete=complete, max_turns=2, finalize_turns=3)
    assert result.stop == "max_turns+cap" and result.turns == 5


def test_finalize_on_deadline(tmp_path):
    tool = {"role": "assistant", "content": None, "tool_calls": [call("true")]}
    complete = scripted(tool, {"role": "assistant", "content": "ok"})
    result = run("loop", tmp_path, complete=complete, max_turns=40, deadline_s=0, finalize_turns=1)
    assert result.stop == "deadline+final" and "run out of time" in result.messages[4]["content"]


def test_default_has_no_finalize(tmp_path):
    complete = scripted(*[{"role": "assistant", "content": None, "tool_calls": [call("true")]} for _ in range(2)])
    result = run("loop", tmp_path, complete=complete, max_turns=2)
    assert result.stop == "max_turns" and result.turns == 2
    assert sum(m["role"] == "user" for m in result.messages) == 1
