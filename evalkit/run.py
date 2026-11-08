"""Task x harness runner.

    python3 -m evalkit.run --task tasks/smoke-revenue --harness claude,codex,opencode,mini,openhands

Results: append one line per episode to evals/results/<date>.jsonl.
Episode records go to $HF_RUNS_DIR (default: temp dir/homefield-runs).
Keep episode folders outside the repo.
Inside the repo, a harness would read our CLAUDE.md and skills and spoil the comparison.
"""

import argparse
import json
import os
import signal
import sqlite3
import subprocess
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from evalkit.adapters import ADAPTERS
from evalkit.customer import make_customer
from evalkit.episode import Episode
from homefield import model as llm

PROMPT = """You are a data analyst working for a customer.

Customer request: {request}

The working directory contains: {files}

Rules:
1. Write your final answer as ONE SQLite query in the file `{answer_file}` in the working directory.
   The query's result is your deliverable.
2. To ask the customer a clarifying question, run this shell command: {bin}/ask_user "your question"
   Questions cost the customer's time. Ask only when needed. Budget: {ask} questions.
3. To deliver, run this shell command: {bin}/submit_answer
   It prints ACCEPTED or REJECTED. If REJECTED, revise the query and submit again. Budget: {submit} submissions.
4. Stop as soon as you see ACCEPTED, or BUDGET_EXHAUSTED for submissions.{extra}"""

# Prompt variants. E1 = give an existing harness the "ask first" policy in words only (no mechanism).
VARIANTS = {
    "E0": "",
    "E1": """
5. Before writing the query, list the interpretations of the request that would change the result.
   Ask the customer about each such interpretation before your first submission. Do not guess them.
   For any interpretation you did not confirm, state your assumption in a SQL comment in the answer file.""",
    # E2 = E1 + the anchor-lookup strategy in words only. A control that tests whether
    # the anchor mechanism (our harness) can be reproduced by a prompt.
    "E2": """
5. Before writing the query, list the interpretations of the request that would change the result.
   Customers often cannot answer technical definition questions, but they know numbers from their existing reports.
   If the customer cannot answer a definition question, ask for a number they already know (for example a total
   from their report) and keep only the interpretations whose result matches that number. Do not guess.
   For any interpretation you did not confirm, state your assumption in a SQL comment in the answer file.""",
    # E3 = the strongest prompt control: the anchor strategy as an explicit procedure.
    # If this reproduces the effect, we drop the anchor-mechanism claim.
    "E3": """
5. Follow this procedure exactly:
   a) List every decision in the request that changes the result, with its options, and the candidate queries.
   b) Ask the customer ONE question for a number they already know from their existing reports that would
      distinguish the candidates (for example, the total for the period). Do not ask about technical definitions.
   c) Compute that number with SQL for every candidate interpretation.
   d) Keep only the candidates whose number matches the customer's number (allow small differences).
      If several remain, choose the most likely one.
   e) Write the answer file and submit.
   State any unconfirmed assumption in a SQL comment in the answer file.""",
}


def build_db(task_dir: Path, task: dict, out: Path) -> Path:
    db = out / task["db"]
    con = sqlite3.connect(db)
    con.executescript((task_dir / task["db_sql"]).read_text())
    con.commit()
    con.close()
    return db


def run_episode(
    task_dir: Path, task: dict, harness: str, variant: str, rep: int, model: str, timeout: int, runs: Path, src_db: Path
) -> dict:
    root = runs / task["id"] / f"{harness}__{variant}__r{rep}"
    ep = Episode(task, src_db, root, simulate=make_customer(task))
    ep.start()
    prompt = PROMPT.format(
        request=task["request"],
        files=", ".join(sorted(p.name for p in ep.work.iterdir())),
        answer_file=task["answer_file"],
        bin=ep.bin,
        ask=task["budget"]["ask"],
        submit=task["budget"]["submit"],
        extra=VARIANTS[variant],
    )
    cmd, extra = ADAPTERS[harness](ep, prompt, model, llm.load_env())
    env = {**os.environ, **extra, "PATH": f"{ep.bin}:{os.environ['PATH']}"}
    note, t0 = "ok", time.time()
    with open(root / "stdout.txt", "w") as out:
        proc = subprocess.Popen(
            cmd,
            cwd=ep.work,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=out,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            rc = proc.wait(timeout=timeout)
            note = f"exit={rc}"
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            note = "timeout"
    latency = round(time.time() - t0, 1)
    ep.stop()
    return {
        "task_id": task["id"],
        "harness": harness,
        "variant": variant,
        "repeat": rep,
        "model": model,
        "ts": datetime.now().isoformat(timespec="seconds"),
        **ep.metrics(),
        "tokens_in": None,
        "tokens_out": None,
        "silent_error": None,
        "latency_s": latency,
        "notes": note,
        "episode_dir": str(root),
    }


def finished_episodes(results: Path, since: str) -> set[tuple]:
    """Set of (task, harness, variant, repeat) for episodes recorded since `since` in the results file."""
    if not results.exists():
        return set()
    done = set()
    for line in results.read_text().splitlines():
        r = json.loads(line)
        if r.get("ts", "") >= since and "harness" in r:
            done.add((r["task_id"], r["harness"], r["variant"], r["repeat"]))
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True, help="comma-separated list")
    ap.add_argument("--harness", default=",".join(ADAPTERS))
    ap.add_argument("--model", default=llm.DEFAULT_MODEL)
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--variant", default="E0", help="comma-separated list: E0,E1")
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--jobs", type=int, default=1, help="number of episodes to run at the same time")
    ap.add_argument("--resume", default="", help="skip episodes already in the results file since this time (ISO)")
    args = ap.parse_args()

    runs_root = Path(os.environ.get("HF_RUNS_DIR", Path(tempfile.gettempdir()) / "homefield-runs"))
    runs = runs_root / datetime.now().strftime("%Y%m%d-%H%M%S")
    tasks = []
    for t in args.task.split(","):
        task_dir = Path(t)
        task = json.loads((task_dir / "task.json").read_text())
        (runs / task["id"]).mkdir(parents=True)
        tasks.append((task_dir, task, build_db(task_dir, task, runs / task["id"])))
    results = llm.ROOT / "evals" / "results"
    results.mkdir(parents=True, exist_ok=True)
    out = results / f"{datetime.now():%Y-%m-%d}.jsonl"

    # Repeats are the outer loop: if the server state drifts over time,
    # the drift spreads evenly over harnesses and variants.
    jobs = [
        (task_dir, task, src_db, h, v, rep)
        for rep in range(args.repeat)
        for task_dir, task, src_db in tasks
        for v in args.variant.split(",")
        for h in args.harness.split(",")
    ]
    if args.resume:
        done = finished_episodes(out, args.resume)
        jobs = [j for j in jobs if (j[1]["id"], j[3], j[4], j[5]) not in done]
        print(f"resume: {len(done)} finished episodes skipped, {len(jobs)} to run", flush=True)
    lock = threading.Lock()

    def one(job):
        task_dir, task, src_db, h, v, rep = job
        row = run_episode(task_dir, task, h, v, rep, args.model, args.timeout, runs, src_db)
        with lock:
            with open(out, "a") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            print(
                f"r{rep} {task['id']} {v} {h:10s} acted={row['acted']!s:5s} accepted={row['accepted']!s:5s} "
                f"q={row['n_questions']} unk={row['n_unknown']} sub={row['n_submissions']} "
                f"rework={row['n_rework_interp']}/{row['n_rework_error']} {row['latency_s']}s {row['notes']}",
                flush=True,
            )

    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        list(pool.map(one, jobs))
    print(f"results: {out}\nepisodes: {runs}")


if __name__ == "__main__":
    main()
