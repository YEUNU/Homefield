"""결과 jsonl 요약: 하네스 × 프롬프트 변형별 평균.

    python3 -m evalkit.report evals/results/2026-11-08.jsonl --since 2026-11-08T18:00 --task tasks/smoke-revenue
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

from evalkit.episode import CFC_WEIGHTS, guess_baseline


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results")
    ap.add_argument("--since", default="", help="이 시각 이후 행만 (ISO 문자열 비교)")
    ap.add_argument("--task", help="과제 폴더. 주면 추측 기준선을 함께 출력")
    args = ap.parse_args()

    rows = [json.loads(l) for l in Path(args.results).read_text().splitlines() if l.strip()]
    rows = [r for r in rows if r["ts"] >= args.since and "prompt_variant" in r]
    groups = defaultdict(list)
    for r in rows:
        groups[(r["prompt_variant"], r["variant"])].append(r)

    head = "| 변형 | 하네스 | n | 수락률 | 질문 | 모름 | 재작업 | " + " | ".join(f"CFC r={w}" for w in CFC_WEIGHTS) + " | 시간(s) |"
    print(head)
    print("|" + "---|" * (head.count("|") - 1))
    for (v, h), rs in sorted(groups.items()):
        ok = [r for r in rs if r["success"]]
        cfc = [mean(r["cfc"][str(w)] for r in ok) if ok else float("nan") for w in CFC_WEIGHTS]
        print(f"| {v} | {h} | {len(rs)} | {len(ok)}/{len(rs)} | {mean(r['n_questions'] for r in rs):.1f} | "
              f"{mean(r.get('n_unknown', 0) for r in rs):.1f} | {mean(r['n_rework'] for r in rs):.1f} | "
              + " | ".join(f"{c:.1f}" for c in cfc) + f" | {mean(r['latency_s'] for r in rs):.0f} |")
    print("\nCFC는 수락된 실행만 평균한다. 수락률과 함께 읽는다.")

    if args.task:
        task = json.loads((Path(args.task) / "task.json").read_text())
        b = guess_baseline(task["n_interpretations"], task["budget"]["submit"])
        print(f"\n추측 기준선 (해석 {task['n_interpretations']}개, 제출 예산 {task['budget']['submit']}, 질문 0): "
              f"수락 확률 {b['p_success']}, 수락 시 CFC {b['cfc_given_success']}")


if __name__ == "__main__":
    main()
