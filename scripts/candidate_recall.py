#!/usr/bin/env python3
"""Candidate recall of steps 1 and 2 (internal design harness-core, step B2): the share of tasks where
one result class equals the gold result. The model sees the request only. It calls the local model.

  python3 scripts/candidate_recall.py --tasks <file with task folders, comma or line separated> --out rows.jsonl
"""

import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from homefield import candidates, sources  # noqa: E402


def one(folder: Path) -> dict:
    task = json.loads((folder / "task.json").read_text())
    db = Path(task["db_file"])
    row = {"task_id": task["id"], "hit": False, "classes": 0, "queries": 0, "points": 0, "terms": 0, "failed": ""}
    try:
        gold = sources.class_id(sources.run_select(db, task["check"]["gold_sql"], 120))
        out = candidates.run(task["request"], db)
    except Exception as e:  # one task must not stop the measurement; the row keeps the reason
        return {**row, "failed": f"{type(e).__name__}: {e}"}
    row.update(
        hit=any(c["result_class"] == gold for c in out["classes"]),
        classes=len(out["classes"]),
        queries=len(out["queries"]),
        points=len(out["points"]),
        terms=len(out["unsettled_terms"]),
    )
    return row


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--jobs", type=int, default=2)
    args = ap.parse_args()
    folders = [Path(p) for p in re.split(r"[,\s]+", args.tasks.read_text().strip())]
    with ThreadPoolExecutor(args.jobs) as pool, open(args.out, "a") as f:
        rows = []
        for row in pool.map(one, folders):
            rows.append(row)
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()
    hits, failed = sum(r["hit"] for r in rows), sum(bool(r["failed"]) for r in rows)
    print(f"tasks={len(rows)} recall={hits}/{len(rows)} failed_steps={failed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
