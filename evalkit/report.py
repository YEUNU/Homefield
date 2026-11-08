"""결과 jsonl 요약: 변형 × 하네스별 평균.

python3 -m evalkit.report evals/results/2026-11-08.jsonl --since 2026-11-08T17:30 --task tasks/smoke-revenue
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

from evalkit.episode import CFC_WEIGHTS, guess_baseline

# 옛 필드 이름 → 현재 이름 (2026-11-08 이름 정규화 이전 결과 호환)
LEGACY_KEYS = {"case_id": "task_id", "prompt_variant": "variant", "success": "accepted"}


def normalize(row: dict) -> dict:
    if "prompt_variant" in row:  # 옛 형식에서 "variant"는 하네스였다
        row = {**row, "harness": row.pop("variant")}
    return {LEGACY_KEYS.get(k, k): v for k, v in row.items()}


def load(path: Path, since: str) -> list[dict]:
    rows = [normalize(json.loads(line)) for line in path.read_text().splitlines() if line.strip()]
    return [r for r in rows if r["ts"] >= since and "variant" in r and "harness" in r]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results", type=Path)
    ap.add_argument("--since", default="", help="이 시각 이후 행만 (ISO 문자열 비교)")
    ap.add_argument("--task", type=Path, help="과제 폴더. 주면 추측 기준선을 함께 출력")
    args = ap.parse_args()

    groups = defaultdict(list)
    for r in load(args.results, args.since):
        groups[(r["variant"], r["harness"])].append(r)

    cfc_cols = " | ".join(f"CFC r={w}" for w in CFC_WEIGHTS)
    head = f"| 변형 | 하네스 | n | 수락률 | 질문 | 모름 | 재작업 | {cfc_cols} | 시간(s) |"
    print(head)
    print("|" + "---|" * (head.count("|") - 1))
    for (variant, harness), rs in sorted(groups.items()):
        ok = [r for r in rs if r["accepted"]]
        cfc = [mean(r["cfc"][str(w)] for r in ok) if ok else float("nan") for w in CFC_WEIGHTS]
        cells = [
            variant,
            harness,
            str(len(rs)),
            f"{len(ok)}/{len(rs)}",
            f"{mean(r['n_questions'] for r in rs):.1f}",
            f"{mean(r.get('n_unknown', 0) for r in rs):.1f}",
            f"{mean(r['n_rework'] for r in rs):.1f}",
            *(f"{c:.1f}" for c in cfc),
            f"{mean(r['latency_s'] for r in rs):.0f}",
        ]
        print("| " + " | ".join(cells) + " |")
    print("\nCFC는 수락된 실행만 평균한다. 수락률과 함께 읽는다.")

    if args.task:
        task = json.loads((args.task / "task.json").read_text())
        b = guess_baseline(task["n_interpretations"], task["budget"]["submit"])
        print(
            f"\n추측 기준선 (해석 {task['n_interpretations']}개, 제출 예산 {task['budget']['submit']}, 질문 0): "
            f"수락 확률 {b['p_success']}, 수락 시 CFC {b['cfc_given_success']}"
        )


if __name__ == "__main__":
    main()
