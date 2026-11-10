"""Gates between the agent and the customer (internal design harness-core, revision 4, §5).

The agent asks and delivers only through these functions. Each one reads the event log, decides,
and appends what happened. The state is the log, so a gate is a separate short process:

    python3 -m homefield.gate ask --config gates.json "question"
    python3 -m homefield.gate submit --config gates.json [--assume "text"]... | --no-assumptions

G1 end: `finalize` delivers an answer that the agent wrote but did not submit. G2: a result is
submitted at most once. G3: a submission states its assumptions. G4: budgets. G6: the answer runs
read-only as one statement before it goes out. A refusal does not use the budget.
"""

import argparse
import hashlib
import json
import sqlite3
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from homefield.events import EventLog
from homefield.sources import class_id, run_select

FORCED_ASSUMPTION = "Delivered when the budget ran out. The customer did not confirm this reading."
NEED_ASSUMPTIONS = (
    "REFUSED: say what you assumed. Run the command again with --assume '<one assumption that the customer "
    "did not confirm>' (repeat it for each assumption), or with --no-assumptions. This did not use a submission."
)


@dataclass
class Config:
    events: Path
    answer_file: Path
    db: Path | None
    ask_budget: int
    submit_budget: int

    def dump(self, path: Path) -> None:
        path.write_text(
            json.dumps({k: v if v is None or isinstance(v, int) else str(v) for k, v in asdict(self).items()})
        )

    @classmethod
    def load(cls, path: Path) -> "Config":
        d = json.loads(Path(path).read_text())
        return cls(
            Path(d["events"]), Path(d["answer_file"]), d["db"] and Path(d["db"]), d["ask_budget"], d["submit_budget"]
        )


def _refuse(log: EventLog, gate: str, reply: str) -> str:
    log.append("gate.refused", gate=gate, reply=reply)
    return reply


def ask(cfg: Config, question: str, send) -> str:
    log = EventLog(cfg.events)
    if sum(e["kind"] == "question.asked" for e in log.read()) >= cfg.ask_budget:
        return _refuse(log, "G4", "BUDGET_EXHAUSTED: no more questions allowed. Decide yourself.")
    log.append("question.asked", question=question)
    reply = send(question)
    log.append("answer.received", answer=reply)
    return reply


def _answer_class(cfg: Config) -> tuple[str, str, str]:
    """(answer text, class id, problem). The class id is empty when there is a problem."""
    if not cfg.answer_file.exists():
        return "", "", "no answer file"
    text = cfg.answer_file.read_text()
    if cfg.db is None:
        return text, hashlib.sha256(repr(text.strip()).encode()).hexdigest(), ""
    try:
        return text, class_id(run_select(cfg.db, text)), ""
    except (sqlite3.Error, sqlite3.Warning) as e:
        return text, "", f"answer does not run: {e}"


def _submit(cfg: Config, log: EventLog, assumptions: list[str], send, forced: bool) -> str:
    """Checks G4, G6, G2 in this order, then submits. Returns the reply, or a REFUSED line."""
    submitted = [e for e in log.read() if e["kind"] == "answer.submitted"]
    if any(e["accepted"] for e in submitted):
        return "ACCEPTED (already). Stop now."
    if len(submitted) >= cfg.submit_budget:
        return _refuse(log, "G4", "BUDGET_EXHAUSTED: no more submissions. Stop now.")
    text, cls, problem = _answer_class(cfg)
    if problem:
        return _refuse(log, "G6", f"REFUSED: {problem}. Fix the answer file. This did not use a submission.")
    if cls in {e["result_class"] for e in submitted}:
        return _refuse(
            log, "G2", "REFUSED: this result was already rejected. Change the answer. This did not use a submission."
        )
    reply = send()
    log.append(
        "answer.submitted",
        query=text,
        result_class=cls,
        assumptions=assumptions,
        definitions={},  # name -> version of each definition that the query uses (definition layer, later)
        reply=reply,
        accepted=reply.startswith("ACCEPTED"),
        forced=forced,
    )
    return reply


def submit(cfg: Config, assumptions: list[str] | None, send) -> str:
    log = EventLog(cfg.events)
    if assumptions is None:
        return _refuse(log, "G3", NEED_ASSUMPTIONS)
    return _submit(cfg, log, assumptions, send, forced=False)


def finalize(cfg: Config, stop: str, send) -> str:
    """G1: called once when the agent loop has ended. Returns the reason that closes the task."""
    log = EventLog(cfg.events)
    submitted = [e for e in log.read() if e["kind"] == "answer.submitted"]
    if any(e["accepted"] for e in submitted):
        reason = "accepted"
    else:
        reply = _submit(cfg, log, [FORCED_ASSUMPTION], send, forced=True)
        if reply.startswith("ACCEPTED"):
            reason = "accepted"
        elif reply.startswith("REJECTED") or submitted:
            reason = "rejected"
        elif reply.startswith("REFUSED: "):
            reason = reply.removeprefix("REFUSED: ").split(". Fix the answer")[0]
        else:
            reason = "nothing submitted"
    log.append("task.closed", reason=reason, stop=stop)
    return reason


def command(path: Path, *args: str):
    """The real ask or submit command as a function that returns its reply."""

    def send(*more: str) -> str:
        p = subprocess.run([str(path), *args, *more], capture_output=True, text=True, timeout=600)
        return (p.stdout + p.stderr).strip()

    return send


def main() -> int:
    ap = argparse.ArgumentParser(prog="homefield.gate")
    ap.add_argument("op", choices=["ask", "submit"])
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--real", type=Path, required=True, help="the real command behind this gate")
    ap.add_argument("--assume", action="append")
    ap.add_argument("--no-assumptions", action="store_true")
    ap.add_argument("question", nargs="*")
    args = ap.parse_args()
    cfg = Config.load(args.config)
    if args.op == "ask":
        print(ask(cfg, " ".join(args.question), command(args.real)))
    else:
        assumptions = args.assume if args.assume else ([] if args.no_assumptions else None)
        print(submit(cfg, assumptions, command(args.real)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
