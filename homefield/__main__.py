"""Standalone run: python3 -m homefield -p "<task>" [--max-turns N] [--log trajectory.jsonl]
[--deadline-s S] [--finalize-turns N]

With --gates-dir, the task runs inside the gates (homefield.procedure): the customer commands under
--real-bin are reached only through homefield.gate, and the events go to <gates-dir>/events.jsonl.
With --request and --db also, the code runs the 4 steps (candidates, ask, deliver) and the worker
loop is only the fallback."""

import argparse
import sys
from functools import partial
from pathlib import Path

from homefield import gate, model
from homefield.loop import run
from homefield.procedure import run_gated, run_steps


def main() -> int:
    ap = argparse.ArgumentParser(prog="homefield")
    ap.add_argument("-p", "--prompt", required=True)
    ap.add_argument("--model", default=model.DEFAULT_MODEL)
    ap.add_argument("--max-turns", type=int, default=40)
    ap.add_argument("--log", type=Path)
    ap.add_argument("--deadline-s", type=float, help="wall-clock budget in seconds")
    ap.add_argument("--finalize-turns", type=int, default=0, help="turns to deliver after a budget runs out (0 = off)")
    ap.add_argument("--gates-dir", type=Path, help="run inside the gates; folder for the event log")
    ap.add_argument("--real-bin", type=Path, help="folder of the real ask_user and submit_answer commands")
    ap.add_argument("--answer-file", type=Path)
    ap.add_argument("--db", type=Path, help="SQLite file of a query task (the answer file is then one query)")
    ap.add_argument("--request", help="the customer request alone; with --db, the task runs as the 4 steps")
    ap.add_argument("--ask-budget", type=int, default=0)
    ap.add_argument("--submit-budget", type=int, default=1)
    args = ap.parse_args()
    if args.gates_dir:
        cwd = Path.cwd()
        cfg = gate.Config(
            events=args.gates_dir.resolve() / "events.jsonl",
            answer_file=cwd / args.answer_file,
            db=cwd / args.db if args.db else None,
            ask_budget=args.ask_budget,
            submit_budget=args.submit_budget,
        )
        loop = dict(log=args.log, max_turns=args.max_turns, deadline_s=args.deadline_s)
        complete = partial(model.complete, model=args.model)
        real = args.real_bin.resolve()
        if args.request and args.db:
            reason = run_steps(
                args.request, args.prompt, cwd, cfg, real, complete, finalize_turns=args.finalize_turns, **loop
            )
        else:
            reason = run_gated(
                args.prompt, cwd, cfg, real, complete=complete, finalize_turns=args.finalize_turns, **loop
            )
        print(f"[homefield] closed={reason}", file=sys.stderr)
        return 0 if reason in ("accepted", "rejected") else 1
    result = run(
        args.prompt,
        Path.cwd(),
        complete=partial(model.complete, model=args.model),
        max_turns=args.max_turns,
        log=args.log,
        deadline_s=args.deadline_s,
        finalize_turns=args.finalize_turns,
    )
    print(result.final)
    print(f"[homefield] stop={result.stop} turns={result.turns}", file=sys.stderr)
    return 0 if result.stop.endswith("final") else 1


if __name__ == "__main__":
    sys.exit(main())
