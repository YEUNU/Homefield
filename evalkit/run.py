"""과제 × 하네스 실행기.

    python3 -m evalkit.run --task tasks/smoke-revenue --harness claude,codex,opencode,mini,openhands

결과: evals/results/<날짜>.jsonl 에 한 줄씩 추가. 에피소드 기록은 $HF_RUNS_DIR (기본: 임시 폴더/homefield-runs).
에피소드 폴더는 저장소 밖에 둔다. 저장소 안이면 하네스가 우리 CLAUDE.md·스킬을 읽어 비교가 오염된다.
"""

import argparse
import json
import os
import signal
import sqlite3
import subprocess
import tempfile
import time
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

# 프롬프트 변형. E1 = 기존 하네스에 "먼저 물어라" 정책을 말로만 준다 (메커니즘 없이).
VARIANTS = {
    "E0": "",
    "E1": """
5. Before writing the query, list the interpretations of the request that would change the result.
   Ask the customer about each such interpretation before your first submission. Do not guess them.
   For any interpretation you did not confirm, state your assumption in a SQL comment in the answer file.""",
    # E2 = E1 + 앵커 조회 전략을 말로만 준다. 앵커 메커니즘(우리 하네스)이 프롬프트로 재현되는지 가르는 대조군.
    "E2": """
5. Before writing the query, list the interpretations of the request that would change the result.
   Customers often cannot answer technical definition questions, but they know numbers from their existing reports.
   If the customer cannot answer a definition question, ask for a number they already know (for example a total
   from their report) and keep only the interpretations whose result matches that number. Do not guess.
   For any interpretation you did not confirm, state your assumption in a SQL comment in the answer file.""",
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
    root = runs / f"{task['id']}__{harness}__{variant}__r{rep}"
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    ap.add_argument("--harness", default=",".join(ADAPTERS))
    ap.add_argument("--model", default=llm.DEFAULT_MODEL)
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--variant", default="E0", help="쉼표로 여러 개: E0,E1")
    ap.add_argument("--repeat", type=int, default=1)
    args = ap.parse_args()

    task_dir = Path(args.task)
    task = json.loads((task_dir / "task.json").read_text())
    runs_root = Path(os.environ.get("HF_RUNS_DIR", Path(tempfile.gettempdir()) / "homefield-runs"))
    runs = runs_root / datetime.now().strftime("%Y%m%d-%H%M%S")
    runs.mkdir(parents=True)
    src_db = build_db(task_dir, task, runs)
    results = llm.ROOT / "evals" / "results"
    results.mkdir(parents=True, exist_ok=True)
    out = results / f"{datetime.now():%Y-%m-%d}.jsonl"

    # 반복을 바깥 고리로 둔다: 서버 상태가 시간에 따라 바뀌어도 하네스·변형에 고르게 퍼진다.
    for rep in range(args.repeat):
        for v in args.variant.split(","):
            for h in args.harness.split(","):
                row = run_episode(task_dir, task, h, v, rep, args.model, args.timeout, runs, src_db)
                with open(out, "a") as f:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
                print(
                    f"r{rep} {v} {h:10s} accepted={row['accepted']!s:5s} q={row['n_questions']} "
                    f"unk={row['n_unknown']} sub={row['n_submissions']} rework={row['n_rework']} "
                    f"cfc={row['cfc']} {row['latency_s']}s {row['notes']}",
                    flush=True,
                )
    print(f"results: {out}\nepisodes: {runs}")


if __name__ == "__main__":
    main()
