"""Data sources: read-only execution with a time limit, and the identity of a result.

Two answers are "the same result" when they give the same rows in any order. The rule follows the
grader of the evaluation kit (numbers equal after rounding to 6 places), but this package does not
import the kit; a test keeps the two rules equal."""

import hashlib
import sqlite3
import time
from pathlib import Path

SQL_TIME_LIMIT_S = 30


def run_select(db: Path, sql: str, timeout_s: float = SQL_TIME_LIMIT_S) -> list[tuple]:
    """Run one statement on a read-only connection. Raises sqlite3.Error for a write, for more than
    one statement, for an error in the query, and when the time limit is reached."""
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    deadline = time.monotonic() + timeout_s
    con.set_progress_handler(lambda: time.monotonic() > deadline, 10_000)
    try:
        return con.execute(sql).fetchall()
    except sqlite3.OperationalError as e:
        if time.monotonic() > deadline:
            raise sqlite3.OperationalError(f"timeout after {timeout_s:g}s") from e
        raise
    finally:
        con.close()


def _cell(c):
    if isinstance(c, (int, float)):
        return (0, round(c, 6))
    return (1, type(c).__name__, str(c))


def result_key(rows: list[tuple]) -> tuple:
    """Equal keys = the same result (order-free; duplicate rows count)."""
    return tuple(sorted(tuple(_cell(c) for c in row) for row in rows))


def class_id(rows: list[tuple]) -> str:
    """Short, stable name of a result class."""
    return hashlib.sha256(repr(result_key(rows)).encode()).hexdigest()


def quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def schema(db: Path) -> dict:
    """{table: {"columns": [{"name", "type", "pk"}], "foreign_keys": [(column, other table, other column)]}}"""
    out = {}
    for (table,) in run_select(db, "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"):
        columns = [
            {"name": name, "type": ctype or "", "pk": bool(pk)}
            for _, name, ctype, _, _, pk in run_select(db, f"PRAGMA table_info({quote(table)})")
        ]
        keys = [(r[3], r[2], r[4]) for r in run_select(db, f"PRAGMA foreign_key_list({quote(table)})")]
        out[table] = {"columns": columns, "foreign_keys": keys}
    return out


def schema_text(tables: dict) -> str:
    lines = []
    for table, t in tables.items():
        cols = ", ".join(f"{c['name']} {c['type']}".strip() + (" PK" if c["pk"] else "") for c in t["columns"])
        lines.append(f"{table}({cols})")
        lines += [f"  {table}.{a} -> {other}.{b or '(primary key)'}" for a, other, b in t["foreign_keys"]]
    return "\n".join(lines)


def _clip(value, width: int = 60):
    return value[:width] + "…" if isinstance(value, str) and len(value) > width else value


def profile(db: Path, wanted: dict[str, list[str]], max_values: int = 20, timeout_s: float = 60) -> dict:
    """Facts about the wanted columns: {table: {"rows", "columns": {column: {"nulls", "distinct", "min",
    "max", "values" (value and count, only when there are at most max_values)}}}}.
    One time limit covers the whole profile. A column that does not fit gets {"skipped": reason}."""
    deadline = time.monotonic() + timeout_s
    out = {}
    for table, columns in wanted.items():
        t = out[table] = {"rows": None, "columns": {}}
        for column in columns:
            c, left = quote(column), deadline - time.monotonic()
            try:
                if left <= 0:
                    raise sqlite3.OperationalError("profile time limit")
                sql = f"SELECT COUNT(*), COUNT({c}), COUNT(DISTINCT {c}), MIN({c}), MAX({c}) FROM {quote(table)}"
                rows, filled, distinct, low, high = run_select(db, sql, left)[0]
                t["rows"] = rows
                facts = {"nulls": rows - filled, "distinct": distinct, "min": _clip(low), "max": _clip(high)}
                if distinct <= max_values:
                    sql = f"SELECT {c}, COUNT(*) FROM {quote(table)} WHERE {c} IS NOT NULL GROUP BY 1 ORDER BY 2 DESC"
                    facts["values"] = [
                        (_clip(v), n) for v, n in run_select(db, sql, max(deadline - time.monotonic(), 0.001))
                    ]
            except sqlite3.Error as e:
                facts = {"skipped": str(e)}
            t["columns"][column] = facts
    return out


def profile_text(prof: dict) -> str:
    lines = []
    for table, t in prof.items():
        lines.append(f"{table}: {t['rows'] if t['rows'] is not None else 'unknown'} rows")
        for column, f in t["columns"].items():
            if "skipped" in f:
                lines.append(f"  {column}: not profiled ({f['skipped']})")
            elif "values" in f:
                values = ", ".join(f"{v!r} x{n}" for v, n in f["values"])
                lines.append(f"  {column}: {f['nulls']} null, values: {values}")
            else:
                lines.append(
                    f"  {column}: {f['nulls']} null, {f['distinct']} distinct, min {f['min']!r}, max {f['max']!r}"
                )
    return "\n".join(lines)
