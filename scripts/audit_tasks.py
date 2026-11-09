"""Mechanical audit of BIRD-derived tasks: does the evidence agree with the gold SQL and with the data?

python3 -I scripts/audit_tasks.py --ids kept.json --out audit.json

Input: a JSON list of BIRD question ids. Reads `data/tasks/bird-<id>-d/task.json` (request, facts, gold SQL, DB).
Output: one record for each item, with flags for a reviewer. The script gives no verdict.

Flags:
- literal_not_in_data: a string literal that the gold SQL compares with a column does not occur in that column.
- evidence_literal_not_in_gold: a quoted literal of the evidence is not in the gold SQL.
- number_not_in_gold: a number that the evidence compares is not in the gold SQL.
- op_mismatch: the evidence and the gold SQL compare the same number with a different operator.
- grain_diff: COUNT(x) over a JOIN gives a different result than COUNT(DISTINCT x).
- agg_over_join: SUM or AVG over a JOIN (the reviewer checks the grain).
- limit_tie / limit_null_top: ORDER BY ... LIMIT 1 has a tie at the top, or a NULL at the top.
- gold_null: the gold result has only NULL cells.
- unparsed: a check could not read the gold SQL (the reviewer does that check by hand).
"""

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from evalkit.check import run_sql, same_rows  # noqa: E402

TIME_LIMIT_S = 60
STRING = r"'((?:[^']|'')*)'"
COLREF = r"((?:\w+\.)?(?:`[^`]+`|\"[^\"]+\"|\w+))"
OP = r"(>\s?=|<\s?=|<>|!=|=|>|<)"
NUMBER = r"(-?\d+(?:\.\d+)?)"
NEGATION = re.compile(r"\b(not|isn't|aren't|abnormal|beyond|out of|outside|exceed|except)\b", re.I)
FLIP = {">": "<", "<": ">", ">=": "<=", "<=": ">=", "=": "="}


def norm_op(op: str) -> str:
    op = op.replace(" ", "")
    return "!=" if op == "<>" else op


def clauses(evidence: str) -> list[str]:
    return [c.strip() for c in evidence.split(";") if c.strip()]


def string_literals(text: str) -> set[str]:
    return {s.replace("''", "'") for s in re.findall(STRING, text)}


def comparisons(text: str) -> set[tuple[str, str]]:
    """(operator, number) pairs. `a < x < b` gives (">", a) and ("<", b). BETWEEN a AND b gives (">=", a), ("<=", b)."""
    out = set()
    for a, op1, _, op2, b in re.findall(NUMBER + r"\s*" + OP + r"\s*([\w`.\" ]+?)\s*" + OP + r"\s*" + NUMBER, text):
        out |= {(FLIP.get(norm_op(op1), "?"), a), (norm_op(op2), b)}
    for a, b in re.findall(r"BETWEEN\s+" + NUMBER + r"\s+AND\s+" + NUMBER, text, re.I):
        out |= {(">=", a), ("<=", b)}
    for op, n in re.findall(OP + r"\s*" + NUMBER + r"(?![\w.])", text):
        out.add((norm_op(op), n))
    return {(op, str(float(n)).rstrip("0").rstrip(".")) for op, n in out}


def aliases(sql: str) -> dict[str, str]:
    """alias or table name -> table name."""
    out = {}
    for table, alias in re.findall(r"(?:FROM|JOIN)\s+[`\"]?(\w+)[`\"]?(?:\s+AS\s+(\w+))?", sql, re.I):
        out[table.lower()] = table
        if alias:
            out[alias.lower()] = table
    return out


def columns(db: Path) -> dict[str, set[str]]:
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        return {t: {r[1].lower() for r in con.execute(f'PRAGMA table_info("{t}")')} for t in tables}
    finally:
        con.close()


def literal_checks(db: Path, sql: str) -> list[str]:
    """Each `col = 'lit'` (also !=, LIKE) of the gold SQL: does the value occur in the column?"""
    flags, alias, cols = [], aliases(sql), columns(db)
    for ref, op, lit in re.findall(COLREF + r"\s*(=|!=|<>|LIKE)\s*" + STRING, sql, re.I):
        lit = lit.replace("''", "'")
        prefix, _, col = ref.rpartition(".")
        col = col.strip('`"')
        tables = [alias[prefix.lower()]] if prefix.lower() in alias else []
        tables = tables or [t for t in set(alias.values()) if col.lower() in cols.get(t, set())]
        if not tables:
            flags.append(f"unparsed: column {ref}")
            continue
        cmp = "LIKE" if op.upper() == "LIKE" else "="
        found = any(
            run_sql(db, f'SELECT 1 FROM "{t}" WHERE "{col}" {cmp} \'{lit.replace(chr(39), chr(39) * 2)}\' LIMIT 1')
            for t in tables
            if col.lower() in cols.get(t, set())
        )
        if not found:
            flags.append(f"literal_not_in_data: {ref} {op} '{lit}'")
    return flags


def grain_checks(db: Path, sql: str, gold: list[tuple]) -> list[str]:
    if not re.search(r"\bJOIN\b", sql, re.I):
        return []
    flags = []
    counts = re.findall(r"COUNT\(\s*(?!DISTINCT)([^()*]+?)\s*\)", sql, re.I)
    for arg in dict.fromkeys(counts):
        variant = re.sub(r"COUNT\(\s*" + re.escape(arg) + r"\s*\)", f"COUNT(DISTINCT {arg})", sql, flags=re.I)
        try:
            other = run_sql(db, variant, TIME_LIMIT_S)
        except sqlite3.Error as e:
            flags.append(f"unparsed: COUNT(DISTINCT {arg}) variant: {e}")
            continue
        if not same_rows(other, gold):
            flags.append(f"grain_diff: COUNT({arg}) {gold[:1]} vs COUNT(DISTINCT {arg}) {other[:1]}")
    if re.search(r"\b(SUM|AVG)\s*\(", sql, re.I) or re.search(r"COUNT\(\s*\*\s*\)", sql, re.I):
        flags.append("agg_over_join")
    return flags


def limit_checks(db: Path, sql: str) -> list[str]:
    m = re.search(r"ORDER BY\s+(.+?)\s*(ASC|DESC)?\s+LIMIT\s+1\s*;?\s*$", sql, re.I | re.S)
    if not m:
        return ["unparsed: LIMIT"] if re.search(r"\bLIMIT\b", sql, re.I) else []
    key, direction = m.group(1), m.group(2) or "ASC"
    head = re.match(r"\s*SELECT\s+(?:DISTINCT\s+)?(.*?)\s+FROM\s", sql, re.I | re.S)
    if not head or "(" in head.group(1) and "SELECT" in head.group(1).upper() or "," in key:
        return ["unparsed: LIMIT key"]
    probe = f"SELECT {key} AS k {sql[head.end(1) : m.start()]} ORDER BY {key} {direction} LIMIT 2"
    try:
        top = run_sql(db, probe, TIME_LIMIT_S)
    except sqlite3.Error as e:
        return [f"unparsed: LIMIT probe: {e}"]
    flags = []
    if top and top[0][0] is None:
        flags.append("limit_null_top")
    if len(top) == 2 and top[0][0] == top[1][0]:
        flags.append(f"limit_tie: top two keys are both {top[0][0]!r}")
    return flags


def kinds(evidence: str) -> list[str]:
    """Rough ambiguity type of the facts (descriptive only)."""
    out = []
    if re.search(OP + r"\s*" + STRING, evidence) or re.search(STRING + r"\s+(is|refers|means|stands)", evidence):
        out.append("value_code")
    if comparisons(re.sub(STRING, "", evidence)) - {("=", "0"), ("=", "1")} and re.search(r"[<>]|BETWEEN", evidence):
        out.append("threshold")
    if re.search(r"\b(SUBTRACT|DIVIDE|MULTIPLY|SUM|COUNT|AVG|MAX|MIN|percentage|ratio|calculation)\b", evidence, re.I):
        out.append("formula")
    return out or ["column_map"]


def audit(qid: int) -> dict:
    task = json.loads((ROOT / "data" / "tasks" / f"bird-{qid}-d" / "task.json").read_text())
    db, sql = Path(task["db_file"]), task["check"]["gold_sql"]
    evidence = " ".join(task["hidden"]["facts"])
    gold = run_sql(db, sql)
    flags = literal_checks(db, sql)
    gold_strings = {s.lower() for s in string_literals(sql)}
    for lit in sorted(string_literals(evidence)):
        if lit.lower() not in gold_strings and lit.lower() not in sql.lower():
            flags.append(f"evidence_literal_not_in_gold: '{lit}'")
    ev_cmp, gold_cmp = comparisons(re.sub(STRING, "", evidence)), comparisons(re.sub(STRING, "", sql))
    gold_numbers = {n for _, n in gold_cmp} | set(re.findall(r"(?<![\w.])\d+(?:\.\d+)?", re.sub(STRING, "", sql)))
    negated = bool(NEGATION.search(task["request"] + " " + evidence))
    for op, n in sorted(ev_cmp):
        if n not in gold_numbers and str(int(float(n))) not in gold_numbers:
            flags.append(f"number_not_in_gold: {op} {n}")
        elif op in FLIP and (op, n) not in gold_cmp and any(g == n for _, g in gold_cmp):
            flags.append(f"op_mismatch{' (negation in text)' if negated else ''}: evidence {op} {n}")
    flags += grain_checks(db, sql, gold) + limit_checks(db, sql)
    if gold and all(c is None for row in gold for c in row):
        flags.append("gold_null")
    return {
        "id": qid,
        "db_id": task["source"]["db_id"],
        "difficulty": task["difficulty"],
        "request": task["request"],
        "clauses": clauses(evidence),
        "gold_sql": sql,
        "gold_rows": len(gold),
        "kinds": kinds(evidence),
        "flags": flags,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", type=Path, required=True, help="JSON list of BIRD question ids")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    records = [audit(q) for q in json.loads(args.ids.read_text())]
    args.out.write_text(json.dumps(records, ensure_ascii=False, indent=1))
    flagged = sum(1 for r in records if r["flags"])
    print(f"{len(records)} items, {flagged} with flags -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
