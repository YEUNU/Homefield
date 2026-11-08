"""제출물 채점. 답 SQL을 원본 DB 사본에서 실행해 정답 SQL 결과와 비교한다."""

import math
import sqlite3
from pathlib import Path


def run_sql(db: Path, sql: str) -> list[tuple]:
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        return con.execute(sql).fetchall()
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


def check_sql_result(answer: Path, gold_db: Path, spec: dict) -> tuple[bool, str, str | None]:
    """(정답 여부, 거절 종류, 결과 미리보기). 거절 종류: "" | "missing" | "sql_error" | "wrong_result"."""
    if not answer.exists():
        return False, "missing", None
    try:
        got = run_sql(gold_db, answer.read_text())
    except sqlite3.Error as e:
        return False, "sql_error", str(e)
    gold = run_sql(gold_db, spec["gold_sql"])
    ok = same_rows(got, gold, spec.get("ordered", False))
    return ok, "" if ok else "wrong_result", repr(got[:10])
