"""Steps 1 and 2: profile, candidate format, execution, result classes (design harness-core, step B2). No network."""

import json
import sqlite3

import pytest

from homefield import candidates, model, sources
from homefield.events import EventLog


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "shop.sqlite"
    con = sqlite3.connect(path)
    con.executescript(
        """CREATE TABLE customer (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE "order" (id INTEGER PRIMARY KEY, customer_id INTEGER REFERENCES customer(id),
                              status TEXT, amount REAL, note TEXT);
        INSERT INTO customer VALUES (1, 'A'), (2, 'B');
        INSERT INTO "order" VALUES (1, 1, 'paid', 10.0, NULL), (2, 1, 'cancelled', 5.0, 'x'),
                                   (3, 2, 'paid', 7.5, NULL);"""
    )
    con.close()
    return path


def says(*replies):
    """A model that gives the replies in order. Text replies stay as they are; other values become JSON."""
    queue, seen = list(replies), []

    def complete(messages, tools=None):
        seen.append(messages)
        reply = queue.pop(0)
        return {"role": "assistant", "content": reply if isinstance(reply, str) else json.dumps(reply)}

    complete.seen = seen
    return complete


def test_schema_lists_columns_and_keys(db):
    tables = sources.schema(db)
    assert [c["name"] for c in tables["order"]["columns"]] == ["id", "customer_id", "status", "amount", "note"]
    assert tables["order"]["foreign_keys"] == [("customer_id", "customer", "id")]
    text = sources.schema_text(tables)
    assert "customer(id INTEGER PK, name TEXT)" in text and "order.customer_id -> customer.id" in text


def test_profile_gives_counts_ranges_and_the_values_of_small_columns(db):
    prof = sources.profile(db, {"order": ["status", "amount", "note"]}, max_values=2)
    order = prof["order"]
    assert order["rows"] == 3
    assert order["columns"]["status"] == {
        "nulls": 0,
        "distinct": 2,
        "min": "cancelled",
        "max": "paid",
        "values": [("paid", 2), ("cancelled", 1)],
    }
    assert order["columns"]["amount"] == {"nulls": 0, "distinct": 3, "min": 5.0, "max": 10.0}
    assert order["columns"]["note"]["nulls"] == 2
    text = sources.profile_text(prof)
    assert "status: 0 null, values: 'paid' x2, 'cancelled' x1" in text and "amount: 0 null, 3 distinct" in text


def test_profile_marks_what_does_not_fit_the_time_limit(db):
    prof = sources.profile(db, {"order": ["status"]}, timeout_s=0)
    assert "skipped" in prof["order"]["columns"]["status"]
    assert "not profiled" in sources.profile_text(prof)


def test_ask_json_reads_json_inside_other_text():
    complete = says('Here it is:\n```json\n{"a": 1}\n```')
    assert model.ask_json([{"role": "user", "content": "q"}], lambda o: o["a"], complete) == 1


def test_ask_json_retries_once_with_the_problem_then_fails():
    complete = says("no json", {"a": 1})
    assert model.ask_json([{"role": "user", "content": "q"}], lambda o: o["a"], complete) == 1
    assert "cannot be used" in complete.seen[1][-1]["content"] and len(complete.seen[1]) == 3
    with pytest.raises(ValueError):
        model.ask_json([{"role": "user", "content": "q"}], lambda o: o["a"], says({"b": 1}, "still nothing"))


def test_selection_keeps_only_names_of_the_schema(db):
    tables = sources.schema(db)
    obj = {"columns": {"ORDER": ["Status", "nope", "status"], "ghost": ["x"], "customer": []}}
    assert candidates.check_selection(obj, tables) == {"order": ["status"]}
    with pytest.raises(ValueError):
        candidates.check_selection({"columns": {"ghost": ["x"]}}, tables)


POINT = {"id": "p1", "text": "revenue", "readings": ["all orders", "paid orders only"]}


@pytest.mark.parametrize(
    "change, problem",
    [
        ({"queries": []}, "no query"),
        ({"queries": [{"sql": "SELECT 1", "readings": {}}]}, "each query"),
        ({"queries": [{"sql": "SELECT 1", "readings": {"p1": 3}}]}, "from 1 to 2"),
        ({"queries": [{"sql": "SELECT 1", "readings": {"p1": 1, "p9": 1}}]}, "each query"),
        ({"queries": [{"sql": " ", "readings": {"p1": 1}}]}, "non-empty"),
        ({"points": [{**POINT, "readings": ["one"]}]}, "two or more"),
        ({"points": [POINT, POINT]}, "must differ"),
    ],
)
def test_proposal_with_a_broken_link_is_refused(change, problem):
    obj = {"points": [POINT], "queries": [{"sql": "SELECT 1", "readings": {"p1": 1}}], **change}
    with pytest.raises(ValueError, match=problem):
        candidates.check_proposal(obj)


def test_proposal_keeps_at_most_k_queries_and_allows_no_points():
    obj = {"queries": [{"sql": f"SELECT {i}"} for i in range(6)], "unsettled_terms": [{"term": "active"}]}
    out = candidates.check_proposal(obj, k=4)
    assert len(out["queries"]) == 4 and out["points"] == []
    assert out["unsettled_terms"] == [{"term": "active", "why": ""}]


def test_execute_groups_equal_results_and_repairs_once(db):
    queries = [
        {"sql": 'SELECT SUM(amount) FROM "order"'},
        {"sql": "SELECT SUM(amount) FROM \"order\" WHERE status = 'paid'"},
        {"sql": 'SELECT 22.5 FROM "order" LIMIT 1'},  # other text, same result as the first
        {"sql": "SELECT SUM(amount) FROM orders"},  # error; the repair gives the second query
        {"sql": "SELECT nope"},  # error; the repair fails too
        {"sql": 'DELETE FROM "order"'},  # refused by the read-only connection
    ]
    asked = []

    def repair(query, error):
        asked.append((query["sql"], error))
        return {3: "SELECT 17.5", 4: "SELECT still_nope"}.get(len(asked) + 2)

    classes = candidates.execute(db, queries, repair)
    assert [c["queries"] for c in classes] == [[0, 2], [1, 3]]
    assert classes[0]["rows"] == [(22.5,)] and queries[3]["sql"] == "SELECT 17.5" and queries[3]["error"] is None
    assert queries[4]["result_class"] is None and "still_nope" in queries[4]["error"]
    assert queries[5]["result_class"] is None and len(asked) == 3
    assert sqlite3.connect(db).execute('SELECT COUNT(*) FROM "order"').fetchone() == (3,)


def test_run_end_to_end_logs_profile_and_candidates(db, tmp_path):
    complete = says(
        {"columns": {"order": ["status", "amount"]}},
        {
            "points": [POINT],
            "unsettled_terms": [{"term": "revenue", "why": "no column says net or gross"}],
            "queries": [
                {"sql": 'SELECT SUM(amount) FROM "order"', "readings": {"p1": 1}},
                {"sql": "SELECT SUM(amount) FROM orders WHERE status = 'paid'", "readings": {"p1": 2}},
            ],
        },
        {"sql": "SELECT SUM(amount) FROM \"order\" WHERE status = 'paid'"},
    )
    events = EventLog(tmp_path / "events.jsonl")
    out = candidates.run("What is our revenue?", db, complete, events)
    assert [c["rows"] for c in out["classes"]] == [[(22.5,)], [(17.5,)]]
    assert "'paid' x2" in complete.seen[1][0]["content"]  # the profile reaches step 2
    assert "no such table: orders" in complete.seen[2][0]["content"]
    logged = events.read()
    assert [e["kind"] for e in logged] == ["profile.done", "candidates.done"]
    assert logged[0]["columns"] == {"order": ["status", "amount"]}
    assert [c["rows"] for c in logged[1]["classes"]] == [1, 1] and logged[1]["unsettled_terms"][0]["term"] == "revenue"


def test_run_fails_as_a_step_when_nothing_is_usable(db):
    with pytest.raises(candidates.StepFailed, match="profile"):
        candidates.run("r", db, says("?", "?"))
    with pytest.raises(candidates.StepFailed, match="candidates"):
        candidates.run("r", db, says({"columns": {"order": ["id"]}}, "?", "?"))
    one_bad_query = {"queries": [{"sql": "SELECT nope"}]}
    with pytest.raises(candidates.StepFailed, match="no query runs"):
        candidates.run("r", db, says({"columns": {"order": ["id"]}}, one_bad_query, "?", "?"))


def test_with_a_request_the_unsettled_terms_must_occur_in_it_and_come_once():
    terms = [{"term": "Net Profit"}, {"term": "unit_price"}, {"term": "net profit"}]
    out = candidates.check_proposal(
        {"queries": [{"sql": "SELECT 1"}], "unsettled_terms": terms}, request="Top net profit?"
    )
    assert out["unsettled_terms"] == [{"term": "Net Profit", "why": ""}]
