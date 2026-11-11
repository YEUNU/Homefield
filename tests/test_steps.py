"""Steps 3 and 4: open items, questions, delivery of one result class (design harness-core, step B3). No network."""

import json
import sqlite3

import pytest

from homefield import gate
from homefield.events import EventLog
from homefield.procedure import assumptions, open_items, run_steps

ALL = 'SELECT SUM(amount) FROM "order"'
PAID = "SELECT SUM(amount) FROM \"order\" WHERE status = 'paid'"
POINT = {"id": "p1", "text": "revenue", "readings": ["all orders", "paid orders only"]}
COLUMNS = {"columns": {"order": ["status", "amount"]}}


def proposal(*sqls, points=(POINT,), terms=()):
    queries = [{"sql": s, "readings": {p["id"]: min(n, 2) for p in points}} for n, s in enumerate(sqls, 1)]
    return {"points": list(points), "unsettled_terms": list(terms), "queries": queries}


@pytest.fixture
def shop(tmp_path):
    """A database, the real customer commands (scripted replies), and the gate configuration."""
    db = tmp_path / "shop.sqlite"
    con = sqlite3.connect(db)
    con.executescript(
        """CREATE TABLE "order" (id INTEGER PRIMARY KEY, status TEXT, amount REAL);
        INSERT INTO "order" VALUES (1, 'paid', 10.0), (2, 'cancelled', 5.0), (3, 'paid', 7.5);"""
    )
    con.close()
    real = tmp_path / "bin"
    real.mkdir()
    (real / "ask_user").write_text(f'#!/bin/sh\necho "$1" >> "{tmp_path}/asked"\necho "paid orders only"\n')
    (real / "submit_answer").write_text(
        f'#!/bin/sh\ncat "{tmp_path}/work/answer.sql" >> "{tmp_path}/sent"\n'
        f'if grep -q paid "{tmp_path}/work/answer.sql"; then echo ACCEPTED; else echo "REJECTED: no"; fi\n'
    )
    for f in real.iterdir():
        f.chmod(0o755)
    (tmp_path / "work").mkdir()

    def cfg(ask=1, submit=2):
        return gate.Config(tmp_path / "hf" / "events.jsonl", tmp_path / "work" / "answer.sql", db, ask, submit)

    return tmp_path, real, cfg


def says(*replies):
    queue, seen = list(replies), []

    def complete(messages, tools=None):
        seen.append(messages[-1]["content"] if messages[0]["role"] == "user" else messages[1]["content"])
        reply = queue.pop(0)
        return {"role": "assistant", "content": reply if isinstance(reply, str) else json.dumps(reply)}

    complete.seen, complete.queue = seen, queue
    return complete


def kinds(cfg):
    return [e["kind"] for e in EventLog(cfg.events).read()]


def run(shop, complete, **budget):
    tmp_path, real, cfg = shop
    c = cfg(**budget)
    return c, run_steps("What is our revenue?", "PROMPT", tmp_path / "work", c, real, complete)


def test_open_items_are_unsettled_terms_then_points_that_split_the_classes():
    out = proposal(ALL, PAID, terms=[{"term": "our customers", "why": "no column"}])
    out["classes"] = [{"result_class": "a", "queries": [0]}, {"result_class": "b", "queries": [1]}]
    items = open_items(out)
    assert [(i["kind"], i["text"]) for i in items] == [("term", "our customers"), ("point", "revenue")]
    assert items[0]["question"].startswith('What exactly do you mean by "our customers"? Please give the exact rule')
    assert "(1) all orders; (2) paid orders only" in items[1]["ask"]
    out["classes"] = [{"result_class": "a", "queries": [0, 1]}]  # both readings give the same result
    assert [i["kind"] for i in open_items(out)] == ["term"]
    out["classes"] = [{"result_class": "a", "queries": [0]}]  # the second query did not run
    assert [i["kind"] for i in open_items(out)] == ["term"]


def test_a_point_that_names_an_asked_term_is_not_asked_again():
    out = proposal(ALL, PAID, terms=[{"term": "Revenue", "why": "net or gross"}])
    out["classes"] = [{"result_class": "a", "queries": [0]}, {"result_class": "b", "queries": [1]}]
    assert [(i["kind"], i["text"]) for i in open_items(out)] == [("term", "Revenue")]


def test_assumptions_name_the_reading_taken_and_the_unconfirmed_terms():
    out = proposal(ALL, PAID, terms=[{"term": "revenue", "why": ""}])
    assert assumptions(out, out["queries"][1]) == [
        "revenue: paid orders only",
        'the meaning of "revenue" is not confirmed',
    ]


def test_one_class_and_nothing_open_is_delivered_without_a_question(shop):
    cfg, reason = run(shop, says(COLUMNS, proposal(PAID, points=())))
    assert reason == "accepted" and not (shop[0] / "asked").exists()
    assert kinds(cfg) == ["task.received", "profile.done", "candidates.done", "answer.submitted", "task.closed"]
    assert EventLog(cfg.events).read()[3]["assumptions"] == []


def test_classes_that_differ_lead_to_a_question_and_a_second_round_with_the_answer(shop):
    complete = says(
        COLUMNS,
        proposal(ALL, PAID),
        {"question": "Does revenue include cancelled orders?"},
        COLUMNS,
        proposal(PAID, points=()),
    )
    cfg, reason = run(shop, complete)
    assert reason == "accepted" and complete.queue == []
    assert (shop[0] / "asked").read_text() == "Does revenue include cancelled orders?\n"
    assert "Answer: paid orders only" in complete.seen[3] and "Treat the answers as facts" in complete.seen[3]
    assert (shop[0] / "sent").read_text() == PAID + "\n"
    submitted = [e for e in EventLog(cfg.events).read() if e["kind"] == "answer.submitted"]
    assert len(submitted) == 1 and submitted[0]["assumptions"] == []


def test_without_a_question_budget_the_largest_class_goes_out_with_its_assumption(shop):
    complete = says(COLUMNS, proposal(ALL, PAID, "SELECT 17.5"))
    cfg, reason = run(shop, complete, ask=0)
    assert reason == "accepted" and not (shop[0] / "asked").exists()
    event = next(e for e in EventLog(cfg.events).read() if e["kind"] == "answer.submitted")
    assert event["query"].strip() == PAID and event["assumptions"] == ["revenue: paid orders only"]


def test_a_rejected_class_is_followed_by_the_next_class(shop):
    cfg, reason = run(shop, says(COLUMNS, proposal(ALL, PAID)), ask=0)
    assert reason == "accepted"
    assert (shop[0] / "sent").read_text() == ALL + "\n" + PAID + "\n"


def test_after_a_rejection_with_no_class_left_the_candidates_are_generated_once_more(shop):
    complete = says(COLUMNS, proposal(ALL, points=()), COLUMNS, proposal(ALL, PAID))
    cfg, reason = run(shop, complete, ask=0)
    assert reason == "accepted" and complete.queue == []
    assert "rejected a delivery" in complete.seen[2] and ALL in complete.seen[2]
    assert (shop[0] / "sent").read_text() == ALL + "\n" + PAID + "\n"  # the rejected result did not go out twice


def test_the_task_closes_as_rejected_when_the_budget_ends(shop):
    complete = says(COLUMNS, proposal(ALL, 'SELECT COUNT(*) FROM "order"', PAID))
    cfg, reason = run(shop, complete, ask=0, submit=2)
    assert reason == "rejected" and kinds(cfg)[-1] == "task.closed"
    assert sum(k == "answer.submitted" for k in kinds(cfg)) == 2


def test_a_question_that_the_model_cannot_word_falls_back_to_a_plain_one(shop):
    complete = says(COLUMNS, proposal(ALL, PAID), "?", "?", COLUMNS, proposal(PAID, points=()))
    cfg, reason = run(shop, complete)
    assert reason == "accepted"
    assert (shop[0] / "asked").read_text() == 'What exactly do you mean by "revenue"?\n'


def test_when_the_steps_give_nothing_the_worker_loop_takes_over(shop):
    tmp_path, real, cfg = shop
    c = cfg()

    def call(command):
        fn = {"name": "bash", "arguments": json.dumps({"command": command})}
        return {"role": "assistant", "content": None, "tool_calls": [{"id": "c", "type": "function", "function": fn}]}

    replies = [
        {"role": "assistant", "content": "?"},
        {"role": "assistant", "content": "?"},  # step 1 fails twice
        call(f'echo "{PAID.replace(chr(34), chr(92) + chr(34))}" > answer.sql'),
        call(f"{tmp_path}/hf/bin/submit_answer --no-assumptions"),
        {"role": "assistant", "content": "done"},
    ]
    prompt = f"Deliver with {real}/submit_answer"
    reason = run_steps("What is our revenue?", prompt, tmp_path / "work", c, real, lambda m, tools=None: replies.pop(0))
    assert reason == "accepted"
    assert kinds(c) == ["task.received", "steps.failed", "answer.submitted", "task.closed"]
