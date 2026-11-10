"""Gates G1-G4 and G6 over the event log (internal design harness-core, revision 4, step B1). No network."""

import json
import sqlite3

import pytest

from evalkit.check import same_rows
from homefield import gate
from homefield.events import EventLog
from homefield.procedure import run_gated
from homefield.sources import result_key


class Customer:
    """Stands for the real ask and submit commands."""

    def __init__(self, verdicts=()):
        self.verdicts, self.asked, self.submitted = list(verdicts), [], 0

    def ask(self, question):
        self.asked.append(question)
        return "pre-tax"

    def submit(self):
        self.submitted += 1
        return self.verdicts.pop(0)


@pytest.fixture
def cfg(tmp_path):
    db = tmp_path / "shop.sqlite"
    con = sqlite3.connect(db)
    con.executescript("CREATE TABLE t (x INTEGER, y REAL); INSERT INTO t VALUES (1, 0.5), (2, 1.5);")
    con.close()
    return gate.Config(
        events=tmp_path / "events.jsonl", answer_file=tmp_path / "answer.sql", db=db, ask_budget=1, submit_budget=2
    )


def kinds(cfg):
    return [e["kind"] for e in EventLog(cfg.events).read()]


def test_event_log_appends_in_order(tmp_path):
    log = EventLog(tmp_path / "e.jsonl")
    log.append("task.received", request="r")
    log.append("question.asked", question="q")
    events = EventLog(tmp_path / "e.jsonl").read()
    assert [(e["seq"], e["kind"]) for e in events] == [(1, "task.received"), (2, "question.asked")]
    assert events[0]["request"] == "r" and "ts" in events[0]


def test_ask_stays_inside_the_budget(cfg):
    customer = Customer()
    assert gate.ask(cfg, "Is revenue pre-tax?", customer.ask) == "pre-tax"
    reply = gate.ask(cfg, "And cancellations?", customer.ask)
    assert reply.startswith("BUDGET_EXHAUSTED") and customer.asked == ["Is revenue pre-tax?"]
    assert kinds(cfg) == ["question.asked", "answer.received", "gate.refused"]


def test_submit_needs_an_explicit_assumption_list(cfg):
    cfg.answer_file.write_text("SELECT x FROM t")
    customer = Customer(["ACCEPTED"])
    reply = gate.submit(cfg, None, customer.submit)
    assert reply.startswith("REFUSED") and "--no-assumptions" in reply and customer.submitted == 0
    assert gate.submit(cfg, [], customer.submit) == "ACCEPTED"


def test_submit_refuses_a_query_that_does_not_run_and_keeps_the_budget(cfg):
    customer = Customer(["ACCEPTED"])
    cfg.answer_file.write_text("SELECT nope FROM t")
    assert "does not run" in gate.submit(cfg, [], customer.submit)
    cfg.answer_file.write_text("DELETE FROM t")
    assert gate.submit(cfg, [], customer.submit).startswith("REFUSED")
    cfg.answer_file.write_text("SELECT x FROM t; SELECT y FROM t")
    assert gate.submit(cfg, [], customer.submit).startswith("REFUSED")
    assert customer.submitted == 0
    cfg.answer_file.write_text("SELECT x FROM t")
    assert gate.submit(cfg, [], customer.submit) == "ACCEPTED"


def test_same_result_is_not_submitted_twice(cfg):
    customer = Customer(["REJECTED: no", "ACCEPTED"])
    cfg.answer_file.write_text("SELECT x FROM t ORDER BY x")
    assert gate.submit(cfg, [], customer.submit).startswith("REJECTED")
    cfg.answer_file.write_text("SELECT x FROM t ORDER BY x DESC")  # other text, same rows
    assert "already" in gate.submit(cfg, [], customer.submit) and customer.submitted == 1
    cfg.answer_file.write_text("SELECT y FROM t")
    assert gate.submit(cfg, ["y is the amount"], customer.submit) == "ACCEPTED"


def test_submit_stops_at_the_budget_and_after_acceptance(cfg):
    customer = Customer(["REJECTED: no", "REJECTED: no"])
    for sql in ("SELECT x FROM t", "SELECT y FROM t"):
        cfg.answer_file.write_text(sql)
        gate.submit(cfg, [], customer.submit)
    cfg.answer_file.write_text("SELECT x, y FROM t")
    assert gate.submit(cfg, [], customer.submit).startswith("BUDGET_EXHAUSTED") and customer.submitted == 2


def test_submission_event_holds_query_class_assumptions_and_definition_links(cfg):
    cfg.answer_file.write_text("SELECT x FROM t")
    gate.submit(cfg, ["x is the amount"], Customer(["ACCEPTED"]).submit)
    event = EventLog(cfg.events).read()[-1]
    assert event["kind"] == "answer.submitted" and event["accepted"] is True
    assert event["query"] == "SELECT x FROM t" and event["assumptions"] == ["x is the amount"]
    assert event["definitions"] == {} and len(event["result_class"]) == 64


def test_finalize_delivers_an_unsent_answer_when_the_loop_ended_without_one(cfg):
    customer = Customer(["REJECTED: no", "ACCEPTED"])
    cfg.answer_file.write_text("SELECT x FROM t")
    gate.submit(cfg, [], customer.submit)
    cfg.answer_file.write_text("SELECT y FROM t")  # the agent revised the file but never submitted it
    assert gate.finalize(cfg, "max_turns", customer.submit) == "accepted"
    events = EventLog(cfg.events).read()
    assert events[-2]["kind"] == "answer.submitted" and events[-2]["forced"] is True
    assert events[-2]["assumptions"] == [gate.FORCED_ASSUMPTION]
    assert events[-1] == {**events[-1], "kind": "task.closed", "reason": "accepted", "stop": "max_turns"}


def test_finalize_closes_with_a_reason_and_no_submission(cfg):
    customer = Customer()
    assert gate.finalize(cfg, "max_turns", customer.submit) == "no answer file"
    cfg.answer_file.write_text("SELECT nope FROM t")
    assert gate.finalize(cfg, "final", customer.submit).startswith("answer does not run")
    assert customer.submitted == 0
    assert kinds(cfg) == ["gate.refused", "task.closed", "gate.refused", "task.closed"]


def test_finalize_does_nothing_after_acceptance(cfg):
    customer = Customer(["ACCEPTED"])
    cfg.answer_file.write_text("SELECT x FROM t")
    gate.submit(cfg, [], customer.submit)
    assert gate.finalize(cfg, "final", customer.submit) == "accepted" and customer.submitted == 1


def test_file_answers_without_a_database_use_the_text_as_the_class(tmp_path):
    cfg = gate.Config(tmp_path / "e.jsonl", tmp_path / "answer.txt", None, ask_budget=0, submit_budget=2)
    customer = Customer(["REJECTED: no", "ACCEPTED"])
    cfg.answer_file.write_text("@mean[1.5]\n")
    assert gate.submit(cfg, [], customer.submit).startswith("REJECTED")
    cfg.answer_file.write_text("@mean[1.5]")
    assert "already" in gate.submit(cfg, [], customer.submit)
    cfg.answer_file.write_text("@mean[2.5]")
    assert gate.submit(cfg, [], customer.submit) == "ACCEPTED"


@pytest.mark.parametrize(
    "a, b",
    [
        ([(1, "x"), (2, "y")], [(2, "y"), (1, "x")]),
        ([(0.1 + 0.2,)], [(0.3,)]),
        ([(1,), (1,)], [(1,)]),
        ([(1, None)], [(1, "None")]),
        ([(1,)], [(1.0,)]),
        ([("1",)], [(1,)]),
    ],
)
def test_result_key_agrees_with_the_grader(a, b):
    assert (result_key(a) == result_key(b)) == same_rows(a, b)


def test_gated_run_end_to_end(tmp_path, cfg):
    """The agent calls the commands of the task prompt. They reach the real commands only through the gates."""
    real = tmp_path / "bin"
    real.mkdir()
    (real / "ask_user").write_text('#!/bin/sh\necho "pre-tax"\n')
    (real / "submit_answer").write_text(f'#!/bin/sh\necho x >> "{tmp_path}/real_calls"\necho "REJECTED: no"\n')
    for f in real.iterdir():
        f.chmod(0o755)
    work = tmp_path / "work"
    work.mkdir()
    cfg = gate.Config(tmp_path / "hf" / "events.jsonl", work / "answer.sql", cfg.db, ask_budget=1, submit_budget=2)

    def call(command):
        fn = {"name": "bash", "arguments": json.dumps({"command": command})}
        return {"role": "assistant", "content": None, "tool_calls": [{"id": "c", "type": "function", "function": fn}]}

    prompts = []

    def complete(messages, tools=None):
        prompts.append(messages[1]["content"])
        return replies.pop(0)

    replies = [
        call("echo 'SELECT x FROM t' > answer.sql"),
        call(f"{tmp_path}/hf/bin/submit_answer"),  # no assumption list: refused by G3
        call(f"{tmp_path}/hf/bin/submit_answer --no-assumptions"),
        call("echo 'SELECT y FROM t' > answer.sql"),
        {"role": "assistant", "content": "I stop here."},  # never submits the second answer: G1 does
    ]
    reason = run_gated(f"Deliver with {real}/submit_answer", work, cfg, real, complete=complete)

    assert f"{real}/" not in prompts[0] and f"{tmp_path}/hf/bin/submit_answer" in prompts[0]
    assert (tmp_path / "real_calls").read_text() == "x\nx\n"
    assert reason == "rejected"
    assert kinds(cfg) == ["task.received", "gate.refused", "answer.submitted", "answer.submitted", "task.closed"]
