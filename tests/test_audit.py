import importlib.util
import sqlite3
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "audit_tasks", Path(__file__).parent.parent / "scripts" / "audit_tasks.py"
)
audit_tasks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_tasks)


def make_db(tmp_path):
    db = tmp_path / "d.sqlite"
    con = sqlite3.connect(db)
    con.executescript(
        "CREATE TABLE p(id INTEGER, sex TEXT); INSERT INTO p VALUES (1,'F'),(2,'M');"
        "CREATE TABLE lab(id INTEGER, v REAL); INSERT INTO lab VALUES (1,5),(1,7),(1,7),(2,3);"
    )
    con.commit()
    con.close()
    return db


def test_comparisons_read_ranges_and_spaced_operators():
    assert audit_tasks.comparisons("29 < N < 52") == {(">", "29"), ("<", "52")}
    assert audit_tasks.comparisons("x BETWEEN 60 AND 65") == {(">=", "60"), ("<=", "65")}
    assert audit_tasks.comparisons("CRE > = 1.5") == {(">=", "1.5")}


def test_literal_check_finds_a_value_that_is_not_in_the_column(tmp_path):
    db = make_db(tmp_path)
    assert audit_tasks.literal_checks(db, "SELECT COUNT(*) FROM p AS T1 WHERE T1.sex = 'F'") == []
    flags = audit_tasks.literal_checks(db, "SELECT COUNT(*) FROM p AS T1 WHERE T1.sex = 'female'")
    assert len(flags) == 1 and flags[0].startswith("literal_not_in_data")


def test_grain_check_compares_count_with_count_distinct(tmp_path):
    db = make_db(tmp_path)
    sql = "SELECT COUNT(T1.id) FROM p AS T1 INNER JOIN lab AS T2 ON T1.id = T2.id WHERE T2.v > 4"
    flags = audit_tasks.grain_checks(db, sql, audit_tasks.run_sql(db, sql))
    assert len(flags) == 1 and flags[0].startswith("grain_diff")


def test_limit_check_reports_a_tie_at_the_top(tmp_path):
    db = make_db(tmp_path)
    assert audit_tasks.limit_checks(db, "SELECT id FROM lab ORDER BY v DESC LIMIT 1") != []
    assert audit_tasks.limit_checks(db, "SELECT id FROM lab ORDER BY v ASC LIMIT 1") == []


def test_make_tasks_apply_edit_replaces_only_listed_items():
    path = Path(__file__).parent.parent / "scripts" / "make_tasks.py"
    spec = importlib.util.spec_from_file_location("make_tasks", path)
    make_tasks = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(make_tasks)
    edits = {"7": "new text"}
    assert make_tasks.apply_edit(7, "old", edits) == ("new text", True)
    assert make_tasks.apply_edit(8, "old", edits) == ("old", False)


def test_bird_train_pool_caps_items_per_db_and_skips_big_dbs(tmp_path, monkeypatch):
    import json
    import sqlite3
    import zipfile

    path = Path(__file__).parent.parent / "scripts" / "make_tasks.py"
    spec = importlib.util.spec_from_file_location("make_tasks", path)
    mt = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mt)

    def db_file(name: str, n_rows: int) -> Path:
        p = tmp_path / f"{name}.sqlite"
        con = sqlite3.connect(p)
        con.execute("CREATE TABLE t (x TEXT)")
        con.executemany("INSERT INTO t VALUES (?)", [("v" * 100,)] * n_rows)
        con.commit()
        con.close()
        return p

    folder = tmp_path / "processed"
    folder.mkdir()
    with zipfile.ZipFile(folder / "train_databases.zip", "w") as z:
        z.write(db_file("small", 3), "train_databases/small/small.sqlite")
        z.write(db_file("big", 5000), "train_databases/big/big.sqlite")
    rows = [
        {"db_id": "small", "question": f"q{i}", "evidence": "x is the value", "SQL": "SELECT x FROM t"}
        for i in range(5)
    ]
    rows.append({"db_id": "small", "question": "no evidence", "evidence": "", "SQL": "SELECT x FROM t"})
    rows.append({"db_id": "big", "question": "big", "evidence": "x is the value", "SQL": "SELECT x FROM t"})
    with zipfile.ZipFile(tmp_path / "train.zip", "w") as z:
        z.writestr("train/train.json", json.dumps(rows))

    monkeypatch.setattr(mt, "BIRD_SPLITS", {"train": (tmp_path / "train.zip", folder)})
    monkeypatch.setattr(mt, "OUT", tmp_path / "tasks")
    monkeypatch.setattr(mt, "TRAIN_MAX_DB_BYTES", 100_000)
    monkeypatch.setattr(mt, "TRAIN_MAX_PER_DB", 2)
    report = mt.make_bird_train(10, 0, {})

    assert report["excluded_big_dbs"] == ["big"]
    assert len(report["picked"]) == 2 and set(report["picked"]) <= {0, 1, 2, 3, 4}
    made = sorted(p.name for p in (tmp_path / "tasks").iterdir())
    assert made == sorted(f"birdtrain-{i}-{c}" for i in report["picked"] for c in "ond")
    task = json.loads((tmp_path / "tasks" / made[0] / "task.json").read_text())
    assert task["source"]["dataset"] == "bird-train"
