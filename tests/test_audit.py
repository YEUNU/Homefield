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
