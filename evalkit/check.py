"""Grade a submission.

- `sql_result`: run the answer SQL on a copy of the source DB and compare with the gold SQL result.
- `exact_answer`: parse `@key[value]` pairs from the answer file and compare with the gold pairs.
"""

import math
import re
import sqlite3
import time
from pathlib import Path

# Time limit for the answer SQL of one submission. It must stay well below the tool timeout of every
# harness (the `bare` bash tool stops a command after 120 s), so that the agent always gets a reply.
SQL_TIME_LIMIT_S = 60


def run_sql(db: Path, sql: str, timeout_s: float | None = None) -> list[tuple]:
    """Run read-only. With `timeout_s`, stop the query after that time and raise sqlite3.OperationalError."""
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        if timeout_s is None:
            return con.execute(sql).fetchall()
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


def _cell_eq(x, y, tol: float) -> bool:
    if isinstance(x, (int, float)) and isinstance(y, (int, float)):
        return math.isclose(x, y, rel_tol=tol, abs_tol=tol)
    return x == y


def _row_key(row: tuple) -> tuple:
    return tuple((0, round(c, 6)) if isinstance(c, (int, float)) else (1, str(c)) for c in row)


def same_rows(got: list[tuple], gold: list[tuple], ordered: bool = False, tol: float = 1e-6) -> bool:
    if len(got) != len(gold):
        return False
    if not ordered:
        got, gold = sorted(got, key=_row_key), sorted(gold, key=_row_key)
    for a, b in zip(got, gold, strict=True):
        if len(a) != len(b) or not all(_cell_eq(x, y, tol) for x, y in zip(a, b, strict=True)):
            return False
    return True


def check_sql_result(
    answer: Path, gold_db: Path, spec: dict, gold: list[tuple] | None = None, timeout_s: float | None = SQL_TIME_LIMIT_S
) -> tuple[bool, str, str | None]:
    """(correct or not, rejection kind, result preview).

    Rejection kind: "" | "missing" | "sql_error" | "wrong_result". An answer SQL that runs longer than
    `timeout_s` is a "sql_error" with the preview "timeout after <n>s".
    `gold`: the gold result if the caller already has it. Otherwise the gold SQL runs here."""
    if not answer.exists():
        return False, "missing", None
    try:
        got = run_sql(gold_db, answer.read_text(), timeout_s)
    except sqlite3.Error as e:
        return False, "sql_error", str(e)
    if gold is None:
        gold = run_sql(gold_db, spec["gold_sql"])
    ok = same_rows(got, gold, spec.get("ordered", False))
    return ok, "" if ok else "wrong_result", repr(got[:10])


ANSWER_PAIR = re.compile(r"@(\w+)\[(.*?)\]")


def parse_pairs(text: str) -> dict[str, str]:
    """`@mean_fare[34.65] @n[3]` -> {"mean_fare": "34.65", "n": "3"}. The last value of a key wins."""
    return {k.strip(): v.strip() for k, v in ANSWER_PAIR.findall(text)}


def value_eq(got: str, gold: str) -> bool:
    """Numbers: equal at the precision of the gold value (|got - gold| <= half a unit of its last decimal).
    Other values: equal after strip and lower-case."""
    try:
        x, g = float(got), float(gold)
    except ValueError:
        return got.strip().lower() == gold.strip().lower()
    decimals = len(gold.split(".")[1]) if "." in gold else 0
    return abs(x - g) <= 0.5 * 10**-decimals + 1e-9


def check_exact_answer(answer: Path, spec: dict) -> tuple[bool, str, str | None]:
    """Every gold key must be present with an equal value. Extra keys are ignored.

    Rejection kind: "" | "missing" | "format_error" | "wrong_result"."""
    if not answer.exists():
        return False, "missing", None
    got = parse_pairs(answer.read_text())
    if not got:
        return False, "format_error", None
    ok = all(k in got and value_eq(got[k], v) for k, v in spec["answers"])
    return ok, "" if ok else "wrong_result", repr(got)


def check_answer(
    answer: Path, gold_db: Path | None, spec: dict, gold: list[tuple] | None = None
) -> tuple[bool, str, str | None]:
    if spec["type"] == "sql_result":
        return check_sql_result(answer, gold_db, spec, gold)
    if spec["type"] == "exact_answer":
        return check_exact_answer(answer, spec)
    raise ValueError(f"unknown check type: {spec['type']}")
