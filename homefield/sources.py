"""Data sources: read-only execution with a time limit, and the identity of a result.

Two answers are "the same result" when they give the same rows in any order. The rule follows the
grader of the evaluation kit (numbers equal after rounding to 6 places), but this package does not
import the kit; a test keeps the two rules equal."""

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
