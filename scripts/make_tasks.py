"""Make evalkit tasks from open-gold datasets (internal ROADMAP, Experiment 3; docs/DATASETS.md §3).

    python3 -I scripts/make_tasks.py bird --n 20 --seed 0
    python3 -I scripts/make_tasks.py infiagent --n 10 --seed 0

Output: data/tasks/<dataset>-<id>-<condition>/task.json (gitignored, derived from licensed data).
Conditions (same gold): o = facts in the request, no questions; n = request only, no questions;
d = request only, facts known only to the customer simulator.
Every task passes a gold self-check before it is written. Skipped items and their reasons go to
data/tasks/<dataset>-selection.json.
"""

import argparse
import json
import random
import re
import shutil
import sqlite3
import sys
import tempfile
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from evalkit.check import check_exact_answer, check_sql_result  # noqa: E402

RAW, PROCESSED, OUT = ROOT / "data" / "raw", ROOT / "data" / "processed", ROOT / "data" / "tasks"
ASK_BUDGET, SUBMIT_BUDGET = 5, 2
N_EVAL_ONLY_DBS = 3
SQL_TIMEOUT_S = 30


def write_task(task: dict) -> None:
    d = OUT / task["id"]
    d.mkdir(parents=True, exist_ok=True)
    (d / "task.json").write_text(json.dumps(task, ensure_ascii=False, indent=2) + "\n")


def conditions(base: dict, request: str, facts: list[str], fact_text: str) -> list[dict]:
    """O, N, D variants of one item. `fact_text` is how the facts read when they are in the request."""
    out = []
    for cond, req, hidden, ask in (
        ("o", f"{request}\n{fact_text}", [], 0),
        ("n", request, [], 0),
        ("d", request, facts, ASK_BUDGET),
    ):
        t = {**base, "id": f"{base['id']}-{cond}", "condition": cond.upper(), "request": req}
        t["hidden"] = {"fact_kind": "definition", "facts": hidden}
        t["budget"] = {"ask": ask, "submit": SUBMIT_BUDGET}
        out.append(t)
    return out


# --- BIRD Mini-Dev ---
def bird_db(db_id: str) -> Path:
    """Unpack one dev DB (nested zip) to data/processed/bird/<db_id>.sqlite. Only that member is read."""
    out = PROCESSED / "bird" / f"{db_id}.sqlite"
    if out.exists():
        return out
    inner = PROCESSED / "bird" / "dev_databases.zip"
    if not inner.exists():
        inner.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(RAW / "bird-mini-dev" / "dev.zip") as z:
            name = next(n for n in z.namelist() if n.endswith("/dev_databases.zip"))
            with z.open(name) as src, open(inner, "wb") as dst:
                shutil.copyfileobj(src, dst)
    if not re.fullmatch(r"\w+", db_id):
        raise ValueError(f"bad db_id: {db_id}")
    with zipfile.ZipFile(inner) as z:
        name = next(n for n in z.namelist() if n.endswith(f"/{db_id}/{db_id}.sqlite"))
        with z.open(name) as src, open(out, "wb") as dst:  # write to a fixed path: no path escape
            shutil.copyfileobj(src, dst)
    return out


def timed_sql(db: Path, sql: str) -> tuple[list[tuple] | None, str]:
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    t0 = time.time()
    con.set_progress_handler(lambda: int(time.time() - t0 > SQL_TIMEOUT_S), 10_000)
    try:
        return con.execute(sql).fetchall(), ""
    except sqlite3.Error as e:
        return None, f"sql_error: {e}"
    finally:
        con.close()


def apply_edit(question_id, evidence: str, edits: dict[str, str]) -> tuple[str, bool]:
    """(evidence to use, edited or not). `edits` maps a question id to the full edited evidence text."""
    new = edits.get(str(question_id))
    return (evidence, False) if new is None else (new, True)


def make_bird(n: int, seed: int, edits: dict[str, str]) -> dict:
    """BIRD dev (`dev.json` in dev.zip, 1,534 questions), not the 2026 Mini-Dev file: the 2026 update
    clarified the ambiguous output contracts inside the questions, so removing evidence leaves little ambiguity."""
    with zipfile.ZipFile(RAW / "bird-mini-dev" / "dev.zip") as z:
        rows = json.loads(z.read(next(n for n in z.namelist() if n.endswith("/dev.json"))))
    dbs = sorted({r["db_id"] for r in rows})
    eval_only = sorted(random.Random(seed).sample(dbs, N_EVAL_ONLY_DBS))
    pool = [
        r
        for r in rows
        if r["evidence"].strip() and r["difficulty"] in ("moderate", "challenging") and r["db_id"] not in eval_only
    ]
    random.Random(seed).shuffle(pool)
    picked, skipped, edited = [], [], []
    for r in pool:
        if len(picked) == n:
            break
        db = bird_db(r["db_id"])
        gold, err = timed_sql(db, r["SQL"])
        if err or not gold:
            skipped.append({"question_id": r["question_id"], "reason": err or "empty gold result"})
            continue
        base = {
            "id": f"bird-{r['question_id']}",
            "source": {"dataset": "bird-dev", "question_id": r["question_id"], "db_id": r["db_id"]},
            "db": f"{r['db_id']}.sqlite",
            "db_file": str(db.resolve()),
            "answer_file": "answer.sql",
            "check": {"type": "sql_result", "gold_sql": r["SQL"]},
            "n_interpretations": None,
            "difficulty": r.get("difficulty"),
        }
        evidence, is_edited = apply_edit(r["question_id"], r["evidence"], edits)
        tasks = conditions(base, r["question"], [evidence], f"Definitions: {evidence}")
        if is_edited:  # N has no facts, so its file stays the same
            for t in tasks:
                if t["condition"] != "N":
                    t["source"] = {**t["source"], "evidence_edited": True}
        with tempfile.TemporaryDirectory() as tmp:  # self-check: the gold SQL as an answer is accepted
            ans = Path(tmp) / "answer.sql"
            ans.write_text(r["SQL"])
            ok, kind, _ = check_sql_result(ans, db, base["check"])
        if not ok:
            skipped.append({"question_id": r["question_id"], "reason": f"self-check failed: {kind}"})
            continue
        for t in tasks:
            write_task(t)
        picked.append(r["question_id"])
        if is_edited:
            edited.append(r["question_id"])
    return {
        "dataset": "bird-dev",
        "seed": seed,
        "eval_only_dbs": eval_only,
        "picked": picked,
        "edited": sorted(edited),
        "skipped": skipped,
    }


# --- InfiAgent-DABench ---
def make_infiagent(n: int, seed: int, edits: dict[str, str]) -> dict:
    if edits:
        raise ValueError("--edits is for the bird dataset only")
    src = RAW / "infiagent-dabench"
    questions = [json.loads(x) for x in (src / "da-dev-questions.jsonl").open()]
    labels = {r["id"]: r["common_answers"] for r in map(json.loads, (src / "da-dev-labels.jsonl").open())}
    pool = [q for q in questions if q.get("constraints", "").strip() and q["id"] in labels]
    random.Random(seed).shuffle(pool)
    picked, skipped = [], []
    for q in pool:
        if len(picked) == n:
            break
        csv = src / "da-dev-tables" / q["file_name"]
        if not csv.exists():
            skipped.append({"id": q["id"], "reason": "missing file"})
            continue
        spec = {"type": "exact_answer", "answers": labels[q["id"]]}
        with tempfile.TemporaryDirectory() as tmp:  # self-check
            ans = Path(tmp) / "answer.txt"
            ans.write_text(" ".join(f"@{k}[{v}]" for k, v in spec["answers"]))
            ok, kind, _ = check_exact_answer(ans, spec)
        if not ok:
            skipped.append({"id": q["id"], "reason": f"self-check failed: {kind}"})
            continue
        base = {
            "id": f"infiagent-{q['id']}",
            "source": {"dataset": "infiagent-dabench", "id": q["id"], "level": q.get("level")},
            "files": [str(csv.resolve())],
            "answer_file": "answer.txt",
            "check": spec,
            "n_interpretations": None,
        }
        request = f"{q['question']}\nAnswer format: {q['format']}"
        for t in conditions(base, request, [q["constraints"]], f"Requirements: {q['constraints']}"):
            write_task(t)
        picked.append(q["id"])
    return {"dataset": "infiagent-dabench", "seed": seed, "picked": picked, "skipped": skipped}


MAKERS = {"bird": make_bird, "infiagent": make_infiagent}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dataset", choices=MAKERS)
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--edits", type=Path, help='JSON {"evidence": {"<question id>": "<edited evidence text>"}} (bird)')
    args = ap.parse_args()
    edits = json.loads(args.edits.read_text())["evidence"] if args.edits else {}
    report = MAKERS[args.dataset](args.n, args.seed, edits)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{args.dataset}-selection.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "skipped"}), f"skipped={len(report['skipped'])}")
    if len(report["picked"]) < args.n:
        sys.exit(f"only {len(report['picked'])} of {args.n} items passed")


if __name__ == "__main__":
    main()
