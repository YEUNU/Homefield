"""Interpretation space of the anchor tasks and per-episode diagnostics.

The anchor tasks have 4 decisions -> 16 interpretations. This module builds the SQL of each
interpretation, maps a submitted result back to its interpretation, and computes the
pre-registered diagnostics (internal ROADMAP, decision rule D').
"""

import ast
import itertools
import json
import sqlite3
from pathlib import Path

DECISIONS = {
    "tax": ["excl", "incl"],
    "cancel": ["exclude", "include"],
    "refund": ["subtract", "keep"],
    "date": ["order_date", "paid_date"],
}
GOLD = ("excl", "exclude", "subtract", "order_date")
INTERPRETATIONS = list(itertools.product(*DECISIONS.values()))

# Heuristics over customer-simulator answers (Korean or English).
UNKNOWN_MARKS = ("모르", "모릅", "don't know", "do not know")
APPROVAL_MARKS = ("진행하셔도", "계산해 주세요", "그렇게 하세요", "go ahead", "proceed with")


def _parts(tax: str, cancel: str, refund: str, date: str) -> tuple[str, str, str]:
    amount = f"o.total_{tax}_tax"
    status = "AND o.status = 'paid'" if cancel == "exclude" else ""
    sub = (
        f"- COALESCE((SELECT SUM(r.amount_{tax}_tax) FROM refunds r WHERE r.order_id = o.id), 0)"
        if refund == "subtract"
        else ""
    )
    where = f"o.{date} BETWEEN '2026-10-01' AND '2026-10-31' {status}"
    return amount, sub, where


def total_sql(interp: tuple) -> str:
    amount, sub, where = _parts(*interp)
    return f"SELECT SUM({amount} {sub}) FROM orders o WHERE {where}"


def top3_sql(interp: tuple) -> str:
    amount, sub, where = _parts(*interp)
    return (
        f"SELECT c.name, SUM({amount} {sub}) AS revenue FROM orders o JOIN customers c ON c.id = o.customer_id "
        f"WHERE {where} GROUP BY c.id ORDER BY revenue DESC LIMIT 3"
    )


def totals(con: sqlite3.Connection) -> dict[tuple, float]:
    return {i: round(con.execute(total_sql(i)).fetchone()[0], 2) for i in INTERPRETATIONS}


def _key(rows) -> tuple:
    return tuple(sorted((str(n), round(float(v), 2)) for n, v in rows))


def result_index(con: sqlite3.Connection) -> dict[tuple, tuple]:
    """Map the (order-free) top-3 result of each interpretation back to the interpretation."""
    return {_key(con.execute(top3_sql(i)).fetchall()): i for i in INTERPRETATIONS}


def diagnostics(episode_dir: Path, consistent: set[tuple], index: dict[tuple, tuple]) -> dict:
    """Pre-registered diagnostics of one episode, computed from its events.jsonl."""
    path = Path(episode_dir) / "events.jsonl"
    events = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
    answers = [e["answer"] for e in events if e["kind"] == "ask"]
    mapped = []
    for e in events:
        if e["kind"] != "submit" or not e.get("result"):
            continue
        try:
            mapped.append(index.get(_key(ast.literal_eval(e["result"]))))
        except (ValueError, SyntaxError, TypeError):
            mapped.append(None)
    known = [m for m in mapped if m is not None]
    return {
        "n_mapped": len(known),
        "n_in_set": sum(m in consistent for m in known),
        "duplicate": len(known) != len(set(known)),
        "first_gold": bool(mapped) and mapped[0] == GOLD,
        "has_first": bool(mapped),
        "unknown": sum(any(m in a for m in UNKNOWN_MARKS) for a in answers),
        "approvals": sum(any(m in a for m in APPROVAL_MARKS) for a in answers),
    }
