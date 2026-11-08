"""Summarize a results jsonl: by variant x harness.

    python3 -m evalkit.report evals/results/<date>.jsonl --task tasks/anchor-revenue [--since 2026-11-08T18:00]

- Episodes that end with no question and no submission (no action) count as failures.
  Their number is shown separately.
- Acceptance uses the Wilson 95% interval. Cost is the mean over all episodes
  (failures included) ± a 95% interval (normal approximation).
"""

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev

from evalkit.episode import CFC_WEIGHTS, guess_baseline

# Old field name -> current name (compatible with results from before the rename)
LEGACY_KEYS = {"case_id": "task_id", "prompt_variant": "variant", "success": "accepted"}


def normalize(row: dict, budget: dict | None) -> dict:
    if "prompt_variant" in row:  # in the old format "variant" was the harness
        row = {**row, "harness": row.pop("variant")}
    row = {LEGACY_KEYS.get(k, k): v for k, v in row.items()}
    row.setdefault("acted", row.get("valid", row.get("n_questions", 0) + row.get("n_submissions", 0) > 0))
    if "cost" not in row and budget:  # old row: recompute the cost with failures included
        row["cost"] = {
            str(r): (row["n_questions"] + r * row["n_rework"])
            if row["accepted"]
            else budget["ask"] + r * budget["submit"]
            for r in CFC_WEIGHTS
        }
    return row


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    center = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (max(0.0, center - half), min(1.0, center + half))


def mean_ci(xs: list[float]) -> str:
    if not xs:
        return "-"
    if len(xs) < 2:
        return f"{xs[0]:.1f}"
    return f"{mean(xs):.1f}±{1.96 * stdev(xs) / math.sqrt(len(xs)):.1f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results", type=Path)
    ap.add_argument(
        "--task", type=Path, help="task folder. If given, report only rows of that task and show the guessing baseline"
    )
    ap.add_argument("--since", default="", help="only rows since this time (ISO string compare)")
    args = ap.parse_args()

    task = json.loads((args.task / "task.json").read_text()) if args.task else None
    rows = [json.loads(line) for line in args.results.read_text().splitlines() if line.strip()]
    rows = [normalize(r, task["budget"] if task else None) for r in rows]
    rows = [r for r in rows if r["ts"] >= args.since and "variant" in r and "harness" in r]
    if task:
        rows = [r for r in rows if r["task_id"] == task["id"]]

    groups = defaultdict(list)
    for r in rows:
        groups[(r["variant"], r["harness"])].append(r)

    cost_cols = " | ".join(f"cost r={w}" for w in CFC_WEIGHTS)
    head = (
        "| variant | harness | n | no action | acceptance [95% CI] | questions | unknown | rework interp/error | "
        f"{cost_cols} | time(s) |"
    )
    print(head)
    print("|" + "---|" * (head.count("|") - 1))
    for (variant, harness), all_rows in sorted(groups.items()):
        rs = all_rows  # episodes with no action count as failures too
        if not rs:
            print(
                f"| {variant} | {harness} | 0 | {len(all_rows)} | - | - | - | - |" + " - |" * len(CFC_WEIGHTS) + " - |"
            )
            continue
        k = sum(r["accepted"] for r in rs)
        lo, hi = wilson(k, len(rs))
        cells = [
            variant,
            harness,
            str(len(rs)),
            str(sum(not r["acted"] for r in rs)),
            f"{k}/{len(rs)} [{lo:.2f}, {hi:.2f}]",
            f"{mean(r['n_questions'] for r in rs):.1f}",
            f"{mean(r.get('n_unknown', 0) for r in rs):.1f}",
            f"{mean(r.get('n_rework_interp', r['n_rework']) for r in rs):.1f}/"
            f"{mean(r.get('n_rework_error', 0) for r in rs):.1f}",
            *(mean_ci([r["cost"][str(w)] for r in rs if "cost" in r]) for w in CFC_WEIGHTS),
            f"{mean(r['latency_s'] for r in rs):.0f}",
        ]
        print("| " + " | ".join(cells) + " |")
    print(
        "\ncost = questions + r x reworks if accepted; question budget + r x submit budget if failed.\n"
        "Reworks in old rows are not split into interp/error."
    )

    if task and task.get("n_interpretations"):
        b = guess_baseline(task["n_interpretations"], task["budget"]["submit"])
        print(
            f"\nGuessing baseline ({task['n_interpretations']} interpretations, "
            f"submit budget {task['budget']['submit']}, 0 questions): "
            f"acceptance probability {b['p_success']}, CFC if accepted {b['cfc_given_success']}"
        )


if __name__ == "__main__":
    main()
