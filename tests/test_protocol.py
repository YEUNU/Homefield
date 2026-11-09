import sqlite3
import subprocess

from evalkit.check import same_rows
from evalkit.episode import Episode

TASK = {
    "id": "t",
    "request": "r",
    "answer_file": "answer.sql",
    "db": "data.sqlite",
    "check": {"type": "sql_result", "gold_sql": "SELECT name, v FROM t WHERE v > 1"},
    "hidden": {"facts": ["f"]},
    "budget": {"ask": 2, "submit": 3},
}


def make_episode(tmp_path):
    src = tmp_path / "src.sqlite"
    con = sqlite3.connect(src)
    con.executescript("CREATE TABLE t(name TEXT, v REAL); INSERT INTO t VALUES ('a',1),('b',2),('c',3);")
    con.commit()
    con.close()
    ep = Episode(TASK, src, tmp_path / "ep", simulate=lambda q: f"echo:{q}")
    ep.start()
    return ep


def call(path, *args):
    return subprocess.run([str(path), *args], capture_output=True, text=True, timeout=30).stdout.strip()


def test_same_rows_order_and_tolerance():
    assert same_rows([("a", 1.0), ("b", 2.0)], [("b", 2.0000000001), ("a", 1)])
    assert not same_rows([("a", 1.0)], [("a", 1.1)])
    assert not same_rows([("a", 1.0)], [("a", 1.0), ("b", 2.0)])
    assert not same_rows([("a", 1.0, 3)], [("a", 1.0)])


def test_ask_budget_and_log(tmp_path):
    ep = make_episode(tmp_path)
    try:
        assert call(ep.bin / "ask_user", "Revenue basis?") == "echo:Revenue basis?"
        call(ep.bin / "ask_user", "second")
        assert "BUDGET_EXHAUSTED" in call(ep.bin / "ask_user", "third")
    finally:
        ep.stop()
    m = ep.metrics()
    assert m["n_questions"] == 2


def test_submit_reject_then_accept(tmp_path):
    ep = make_episode(tmp_path)
    try:
        assert call(ep.bin / "submit_answer").startswith("REJECTED")  # no answer file -> rejected
        (ep.work / "answer.sql").write_text("SELECT nope FROM t")  # SQL error
        reply = call(ep.bin / "submit_answer")
        # Information a real customer would not give (remaining count, error text) must not leak
        assert reply.startswith("REJECTED") and "left" not in reply and "nope" not in reply
        last = ep.events[-1]  # reason and submission go to the log only
        assert last["error_kind"] == "sql_error" and last["answer"] == "SELECT nope FROM t"
        (ep.work / "answer.sql").write_text("SELECT name, v FROM t WHERE v >= 2")
        assert call(ep.bin / "submit_answer") == "ACCEPTED"
    finally:
        ep.stop()
    m = ep.metrics()
    assert m["acted"] is True and m["accepted"] is True
    assert m["n_submissions"] == 3
    assert m["n_rework"] == 2
    assert m["n_rework_error"] == 2 and m["n_rework_interp"] == 0  # 1 missing + 1 SQL error
    assert m["cfc"] == {"1": 2, "3": 6, "10": 20}  # 0 questions + r x 2 reworks
    assert m["cost"] == m["cfc"]  # if accepted, cost = CFC


def test_failure_cost_and_validity(tmp_path):
    ep = make_episode(tmp_path)
    try:
        (ep.work / "answer.sql").write_text("SELECT name, v FROM t")  # interpretation error (different result)
        for _ in range(3):
            call(ep.bin / "submit_answer")
    finally:
        ep.stop()
    m = ep.metrics()
    assert m["accepted"] is False and m["cfc"] is None
    assert m["n_rework_interp"] == 3
    assert m["cost"] == {"1": 2 + 3, "3": 2 + 9, "10": 2 + 30}  # question budget 2 + r x submit budget 3
    assert ep.events[-1]["result"].startswith("[")  # result preview


def test_episode_without_any_action_is_flagged(tmp_path):
    ep = make_episode(tmp_path)
    ep.stop()
    m = ep.metrics()
    assert m["acted"] is False and m["accepted"] is False  # counted as a failure


def test_agent_cannot_corrupt_gold_db(tmp_path):
    ep = make_episode(tmp_path)
    try:
        con = sqlite3.connect(ep.work / "data.sqlite")
        con.execute("DELETE FROM t")
        con.commit()
        con.close()
        (ep.work / "answer.sql").write_text("SELECT name, v FROM t WHERE v >= 2")
        assert call(ep.bin / "submit_answer") == "ACCEPTED"  # graded on a copy of the source
    finally:
        ep.stop()


def test_unknown_answers_are_counted(tmp_path):
    src = tmp_path / "src.sqlite"
    sqlite3.connect(src).executescript("CREATE TABLE t(name TEXT, v REAL);")
    ep = Episode(TASK, src, tmp_path / "ep", simulate=lambda q: "I don't know.")
    ep.start()
    try:
        call(ep.bin / "ask_user", "any question")
    finally:
        ep.stop()
    assert ep.metrics()["n_unknown"] == 1


def test_guess_baseline():
    from evalkit.episode import guess_baseline

    b = guess_baseline(4, 3)
    assert b["p_success"] == 0.75
    assert b["cfc_given_success"] == {"1": 1.0, "3": 3.0, "10": 10.0}
    assert guess_baseline(2, 3)["p_success"] == 1.0


def test_finished_episodes_for_resume(tmp_path):
    import json

    from evalkit.run import finished_episodes

    f = tmp_path / "r.jsonl"
    rows = [
        {"ts": "2026-01-01T10:00:00", "valid": True, "task_id": "t", "harness": "bare", "variant": "E1", "repeat": 0},
        {"ts": "2026-01-01T09:00:00", "valid": True, "task_id": "t", "harness": "bare", "variant": "E1", "repeat": 1},
        {"ts": "2026-01-01T10:00:00", "valid": False, "task_id": "t", "harness": "bare", "variant": "E1", "repeat": 2},
    ]
    f.write_text("".join(json.dumps(r) + "\n" for r in rows))
    assert finished_episodes(f, "2026-01-01T09:30:00") == {
        ("t", "bare", "E1", 0),
        ("t", "bare", "E1", 2),
    }  # only the earlier times run again


def test_anchor_interpretations_map_back():
    import sqlite3
    from pathlib import Path

    from evalkit.anchor import GOLD, INTERPRETATIONS, result_index, top3_sql, totals

    con = sqlite3.connect(":memory:")
    con.executescript(Path("tasks/anchor-revenue/data.sql").read_text())
    assert len(INTERPRETATIONS) == 16 and totals(con)[GOLD] == 1645.0
    index = result_index(con)
    assert len(index) == 16  # every interpretation has a distinct top-3 result
    gold_rows = con.execute(top3_sql(GOLD)).fetchall()
    assert index[tuple(sorted((n, round(v, 2)) for n, v in gold_rows))] == GOLD


def test_unknown_detection_korean_and_english():
    from evalkit.episode import is_unknown

    assert is_unknown("I don't know.")
    assert is_unknown("저는 매출이 기술적으로 어떻게 계산되는지 모릅니다.")
    assert is_unknown("모르겠습니다.")
    assert not is_unknown("매출 합계는 1,645입니다.")


def test_exact_answer_values():
    from evalkit.check import parse_pairs, value_eq

    assert parse_pairs("@mean_fare[34.65], @fit[poor fit]") == {"mean_fare": "34.65", "fit": "poor fit"}
    assert value_eq("34.6512", "34.65") and not value_eq("34.66", "34.65")  # gold precision
    assert value_eq("3", "3.0") and value_eq("Poor Fit ", "poor fit") and not value_eq("good", "poor")


def test_file_task_exact_answer(tmp_path):
    csv = tmp_path / "t.csv"
    csv.write_text("a\n1\n2\n")
    task = {
        **TASK,
        "answer_file": "answer.txt",
        "check": {"type": "exact_answer", "answers": [["mean", "1.50"], ["n", "2"]]},
    }
    del task["db"]
    ep = Episode(task, None, tmp_path / "ep", simulate=lambda q: "", files=(csv,))
    ep.start()
    try:
        assert (ep.work / "t.csv").exists() and not any(ep.private.iterdir())  # source in work only
        (ep.work / "answer.txt").write_text("no pairs here")
        assert call(ep.bin / "submit_answer").startswith("REJECTED")  # format error
        (ep.work / "answer.txt").write_text("@mean[1.5] @n[2] @extra[x]")
        assert call(ep.bin / "submit_answer") == "ACCEPTED"
    finally:
        ep.stop()
    m = ep.metrics()
    assert m["n_rework_error"] == 1 and m["n_rework_interp"] == 0


def test_answer_rule_for_each_check_type():
    from evalkit.run import ANSWER_RULES, PROMPT, VARIANTS

    for kind, (rule, noun) in ANSWER_RULES.items():
        text = PROMPT.format(
            request="r",
            files="f",
            answer_rule=rule.format(answer_file="a"),
            deliverable=noun,
            bin="/b",
            ask=0,
            submit=2,
            extra=VARIANTS["E0"],
        )
        assert "`a`" in text and f"revise the {noun}" in text, kind
    assert "ONE SQLite query" in ANSWER_RULES["sql_result"][0]


def test_stop_deletes_source_copies_keeps_records(tmp_path):
    # Each BIRD episode copied a DB of up to ~600 MB twice and never deleted it (S1' disk crash).
    ep = make_episode(tmp_path)
    (ep.work / "answer.sql").write_text("SELECT name, v FROM t WHERE v > 1")
    (ep.work / "data.sqlite-journal").write_text("x")  # SQLite side file left by an agent
    (ep.work / "notes.py").write_text("print(1)")  # agent's own work stays
    assert call(ep.bin / "submit_answer") == "ACCEPTED"
    ep.stop()
    assert not (ep.work / "data.sqlite").exists()
    assert not (ep.work / "data.sqlite-journal").exists()
    assert not (ep.private / "data.sqlite").exists()
    assert (ep.work / "answer.sql").exists() and (ep.work / "notes.py").exists()
    assert (ep.root / "events.jsonl").exists()
    assert ep.metrics()["accepted"]


def test_stop_deletes_copied_files(tmp_path):
    csv = tmp_path / "t.csv"
    csv.write_text("x\n1\n")
    task = {**TASK, "db": None, "answer_file": "answer.txt"}
    ep = Episode(task, None, tmp_path / "ep", simulate=lambda q: "", files=(csv,))
    ep.start()
    ep.stop()
    assert not (ep.work / "t.csv").exists() and csv.exists()
