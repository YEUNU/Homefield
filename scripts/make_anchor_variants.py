"""앵커 과제 변형 생성: 고객이 아는 숫자의 정밀도를 바꿔 "앵커 뒤 남는 해석 수 k"를 조절한다.

    python3 scripts/make_anchor_variants.py

기준 과제 tasks/anchor-revenue (k=1)에서 k2, k4, noise 변형을 만든다. DB는 기준 과제의 data.sql을 공유한다.
k는 16개 해석의 10월 총액 중 고객이 말한 숫자·범위와 맞는 것의 개수다 (스크립트가 계산해 확인한다).
"""

import itertools
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "tasks" / "anchor-revenue"
DECISIONS = {
    "tax": ["excl", "incl"],
    "cancel": ["exclude", "include"],
    "refund": ["subtract", "keep"],
    "date": ["order_date", "paid_date"],
}
GOLD = ("excl", "exclude", "subtract", "order_date")
UNKNOWN = (
    "당신은 매출이 기술적으로 어떻게 계산되는지 모른다: "
    "세금 처리, 취소 주문, 반품, 주문일과 결제일 중 어느 날짜를 쓰는지 모른다."
)

VARIANTS = {  # 이름 → (고객 사실 문장, 맞는 총액 범위 [lo, hi], 기대 k)
    "anchor-revenue": ("매달 받는 매출 보고서에서 2026년 10월 전체 고객 매출 합계는 1,645이다.", (1645, 1645), 1),
    "anchor-revenue-k2": (
        "매출 보고서의 2026년 10월 전체 고객 매출 합계는 정확히 기억나지 않지만 1,590에서 1,700 사이였다.",
        (1590, 1700),
        2,
    ),
    "anchor-revenue-k4": (
        "매출 보고서의 2026년 10월 전체 고객 매출 합계는 정확히 기억나지 않지만 1,580에서 1,760 사이였다.",
        (1580, 1760),
        4,
    ),
    "anchor-revenue-noise": (
        "매달 받는 매출 보고서에서 2026년 10월 전체 고객 매출 합계는 1,652이다.",  # 정답 1,645 + 보고서 오차 7
        (1640, 1660),
        1,
    ),
}


def totals(con: sqlite3.Connection) -> dict[tuple, float]:
    out = {}
    for tax, cancel, refund, date in itertools.product(*DECISIONS.values()):
        amt = f"o.total_{tax}_tax"
        ramt = f"r.amount_{tax}_tax"
        status = "AND o.status = 'paid'" if cancel == "exclude" else ""
        sub = (
            f"- COALESCE((SELECT SUM({ramt}) FROM refunds r WHERE r.order_id = o.id), 0)"
            if refund == "subtract"
            else ""
        )
        sql = f"SELECT SUM({amt} {sub}) FROM orders o WHERE o.{date} BETWEEN '2026-10-01' AND '2026-10-31' {status}"
        out[(tax, cancel, refund, date)] = round(con.execute(sql).fetchone()[0], 2)
    return out


def main() -> None:
    base = json.loads((BASE / "task.json").read_text())
    con = sqlite3.connect(":memory:")
    con.executescript((BASE / "data.sql").read_text())
    tot = totals(con)
    for name, (fact, (lo, hi), expected_k) in VARIANTS.items():
        matching = [c for c, v in tot.items() if lo <= v <= hi]
        assert GOLD in matching, f"{name}: 정답 해석이 범위 밖"
        assert len(matching) == expected_k, f"{name}: k={len(matching)} (기대 {expected_k})"
        task = {
            **base,
            "id": name,
            "db_sql": "data.sql" if name == "anchor-revenue" else "../anchor-revenue/data.sql",
            "hidden": {"fact_kind": "anchor", "facts": ["지난달은 2026년 10월이다.", fact, UNKNOWN]},
            "anchor_k": expected_k,
            "notes": (
                f"결정 4개 → 해석 16개. 고객 숫자와 맞는 해석 {expected_k}개 (총액 범위 {lo}–{hi}). "
                "정답 = 세전, 취소 제외, 반품 차감, 주문일 기준 (10월 총액 1,645). make_anchor_variants.py가 생성."
            ),
        }
        out = ROOT / "tasks" / name
        out.mkdir(exist_ok=True)
        (out / "task.json").write_text(json.dumps(task, ensure_ascii=False, indent=2) + "\n")
        print(f"{name}: k={len(matching)} {sorted(tot[c] for c in matching)}")


if __name__ == "__main__":
    main()
