"""결과 jsonl 요약: 변형 × 하네스별.

    python3 -m evalkit.report evals/results/<날짜>.jsonl --task tasks/anchor-revenue [--since 2026-11-08T18:00]

- 무효 에피소드(질문·제출이 모두 0)는 따로 세고 통계에서 뺀다.
- 수락률은 Wilson 95% 구간, 비용은 실패 포함 평균 ± 95% 구간(정규 근사)으로 낸다.
"""

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev

from evalkit.episode import CFC_WEIGHTS, guess_baseline

# 옛 필드 이름 → 현재 이름 (이름 정규화 이전 결과 호환)
LEGACY_KEYS = {"case_id": "task_id", "prompt_variant": "variant", "success": "accepted"}


def normalize(row: dict, budget: dict | None) -> dict:
    if "prompt_variant" in row:  # 옛 형식에서 "variant"는 하네스였다
        row = {**row, "harness": row.pop("variant")}
    row = {LEGACY_KEYS.get(k, k): v for k, v in row.items()}
    row.setdefault("valid", row.get("n_questions", 0) + row.get("n_submissions", 0) > 0)
    if "cost" not in row and budget:  # 옛 행: 실패 포함 비용을 다시 계산
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
    ap.add_argument("--task", type=Path, help="과제 폴더. 주면 그 과제 행만 보고, 추측 기준선을 낸다")
    ap.add_argument("--since", default="", help="이 시각 이후 행만 (ISO 문자열 비교)")
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

    cost_cols = " | ".join(f"비용 r={w}" for w in CFC_WEIGHTS)
    head = f"| 변형 | 하네스 | n | 무효 | 수락률 [95% 구간] | 질문 | 모름 | 재작업 해석/오류 | {cost_cols} | 시간(s) |"
    print(head)
    print("|" + "---|" * (head.count("|") - 1))
    for (variant, harness), all_rows in sorted(groups.items()):
        rs = [r for r in all_rows if r["valid"]]
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
            str(len(all_rows) - len(rs)),
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
        "\n비용 = 수락이면 질문 + r × 재작업, 실패면 질문 예산 + r × 제출 예산.\n"
        "옛 행의 재작업은 해석/오류를 나누지 않았다."
    )

    if task and task.get("n_interpretations"):
        b = guess_baseline(task["n_interpretations"], task["budget"]["submit"])
        print(
            f"\n추측 기준선 (해석 {task['n_interpretations']}개, 제출 예산 {task['budget']['submit']}, 질문 0): "
            f"수락 확률 {b['p_success']}, 수락 시 CFC {b['cfc_given_success']}"
        )


if __name__ == "__main__":
    main()
