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
        assert call(ep.bin / "ask_user", "매출 기준?") == "echo:매출 기준?"
        call(ep.bin / "ask_user", "두번째")
        assert "BUDGET_EXHAUSTED" in call(ep.bin / "ask_user", "세번째")
    finally:
        ep.stop()
    m = ep.metrics()
    assert m["n_questions"] == 2


def test_submit_reject_then_accept(tmp_path):
    ep = make_episode(tmp_path)
    try:
        assert call(ep.bin / "submit_answer").startswith("REJECTED")  # 답 파일 없음 → 거절
        (ep.work / "answer.sql").write_text("SELECT nope FROM t")  # SQL 오류
        reply = call(ep.bin / "submit_answer")
        # 실제 고객이 주지 않는 정보(남은 횟수, 오류 내용)는 새지 않아야 한다
        assert reply.startswith("REJECTED") and "left" not in reply and "nope" not in reply
        last = ep.events[-1]  # 사유·제출물은 로그에만
        assert last["error_kind"] == "sql_error" and last["answer"] == "SELECT nope FROM t"
        (ep.work / "answer.sql").write_text("SELECT name, v FROM t WHERE v >= 2")
        assert call(ep.bin / "submit_answer") == "ACCEPTED"
    finally:
        ep.stop()
    m = ep.metrics()
    assert m["valid"] is True and m["accepted"] is True
    assert m["n_submissions"] == 3
    assert m["n_rework"] == 2
    assert m["n_rework_error"] == 2 and m["n_rework_interp"] == 0  # 누락 1 + SQL 오류 1
    assert m["cfc"] == {"1": 2, "3": 6, "10": 20}  # 질문 0 + r × 재작업 2
    assert m["cost"] == m["cfc"]  # 수락되면 비용 = CFC


def test_failure_cost_and_validity(tmp_path):
    ep = make_episode(tmp_path)
    try:
        (ep.work / "answer.sql").write_text("SELECT name, v FROM t")  # 해석 오류 (결과가 다름)
        for _ in range(3):
            call(ep.bin / "submit_answer")
    finally:
        ep.stop()
    m = ep.metrics()
    assert m["accepted"] is False and m["cfc"] is None
    assert m["n_rework_interp"] == 3
    assert m["cost"] == {"1": 2 + 3, "3": 2 + 9, "10": 2 + 30}  # 질문 예산 2 + r × 제출 예산 3
    assert ep.events[-1]["result"].startswith("[")  # 결과 미리보기


def test_episode_without_any_action_is_invalid(tmp_path):
    ep = make_episode(tmp_path)
    ep.stop()
    assert ep.metrics()["valid"] is False


def test_agent_cannot_corrupt_gold_db(tmp_path):
    ep = make_episode(tmp_path)
    try:
        con = sqlite3.connect(ep.work / "data.sqlite")
        con.execute("DELETE FROM t")
        con.commit()
        con.close()
        (ep.work / "answer.sql").write_text("SELECT name, v FROM t WHERE v >= 2")
        assert call(ep.bin / "submit_answer") == "ACCEPTED"  # 원본 사본으로 채점
    finally:
        ep.stop()


def test_unknown_answers_are_counted(tmp_path):
    src = tmp_path / "src.sqlite"
    sqlite3.connect(src).executescript("CREATE TABLE t(name TEXT, v REAL);")
    ep = Episode(TASK, src, tmp_path / "ep", simulate=lambda q: "I don't know.")
    ep.start()
    try:
        call(ep.bin / "ask_user", "아무 질문")
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
    assert finished_episodes(f, "2026-01-01T09:30:00") == {("t", "bare", "E1", 0)}  # 이전 시각·무효는 다시 돈다
