"""Run one task inside the gates (internal design harness-core, revision 4, steps B1 and B3).

`run_gated`: the worker is the M0 loop. It gets the task prompt with the customer commands replaced
by gate commands, so every question and every delivery passes `homefield.gate`. When the loop ends,
G1 delivers an answer that was written but not submitted, and the task closes with a reason.

`run_steps`: the 4 steps for a query task. The code owns the order: candidates (steps 1 and 2), ask
about the open items (step 3), deliver one result class with its assumptions (step 4). The model
writes queries and words questions. If steps 1 and 2 give nothing usable, `run_gated` takes over (G7)."""

import shlex
import sys
import time
from pathlib import Path

from homefield import candidates, gate, model
from homefield.events import EventLog
from homefield.loop import run

RULE = (
    "\n\nWhen you deliver, state what you assumed: add --assume '<one assumption that the customer did not "
    "confirm>' to the submit command (repeat it for each assumption), or --no-assumptions if there is none."
)


def run_gated(
    prompt: str,
    cwd: Path,
    cfg: gate.Config,
    real_bin: Path,
    complete=model.complete,
    log: Path | None = None,
    received: bool = True,
    **loop_args,
) -> str:
    """Returns the reason that closes the task (see gate.finalize)."""
    home = cfg.events.parent
    bin_dir = home / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    cfg.dump(home / "gates.json")
    package_root = Path(__file__).resolve().parent.parent
    for name, op in (("ask_user", "ask"), ("submit_answer", "submit")):
        script = bin_dir / name
        script.write_text(
            "#!/bin/sh\n"
            f"PYTHONPATH={shlex.quote(str(package_root))} exec {shlex.quote(sys.executable)} -m homefield.gate {op} "
            f'--config {shlex.quote(str(home / "gates.json"))} --real {shlex.quote(str(Path(real_bin) / name))} "$@"\n'
        )
        script.chmod(0o755)
    prompt = prompt.replace(f"{real_bin}/", f"{bin_dir}/") + RULE
    if received:
        EventLog(cfg.events).append("task.received", request=prompt)
    result = run(prompt, cwd, complete=complete, log=log, **loop_args)
    return gate.finalize(cfg, result.stop, gate.command(Path(real_bin) / "submit_answer"))


QUESTION = """A customer sent this request:

{request}

Before the work starts, one thing must be clear: {item}

Write one short question to the customer about this. Use the words of the customer. Do not name tables,
columns, or SQL. Ask for the exact rule (which values count, which fields, which limits).
Reply with one JSON object and nothing else: {{"question": "<the question>"}}"""

CONFIRMED = "\n\nThe customer answered these questions. Treat the answers as facts of the request:\n"
REJECTED = "\n\nThe customer rejected a delivery. Do not give the same result again. Rejected query and reply:\n"


def open_items(out: dict) -> list[dict]:
    """What the code must ask: the terms that the data does not settle, then the points where queries
    of different result classes use different readings."""
    items = [
        {"kind": "term", "text": t["term"], "ask": f'the meaning of "{t["term"]}" ({t["why"]})'}
        for t in out["unsettled_terms"]
    ]
    class_of = {i: c["result_class"] for c in out["classes"] for i in c["queries"]}
    for p in out["points"]:
        seen = {(class_of[i], q["readings"][p["id"]]) for i, q in enumerate(out["queries"]) if i in class_of}
        if len({c for c, _ in seen}) > 1 and len({r for _, r in seen}) > 1:
            readings = "; ".join(f"({n}) {r}" for n, r in enumerate(p["readings"], 1))
            items.append({"kind": "point", "text": p["text"], "ask": f'"{p["text"]}" can mean: {readings}'})
    return items


def assumptions(out: dict, query: dict) -> list[str]:
    """What the delivered query takes as given without a confirmation of the customer."""
    took = [f"{p['text']}: {p['readings'][query['readings'][p['id']] - 1]}" for p in out["points"]]
    return took + [f'the meaning of "{t["term"]}" is not confirmed' for t in out["unsettled_terms"]]


def run_steps(
    request: str,
    prompt: str,
    cwd: Path,
    cfg: gate.Config,
    real_bin: Path,
    complete=model.complete,
    deadline_s: float | None = None,
    **loop_args,
) -> str:
    """Steps 1 to 4 for one query task. Returns the reason that closes the task."""
    log = EventLog(cfg.events)
    log.append("task.received", request=request)
    ask_customer = gate.command(Path(real_bin) / "ask_user")
    deliver = gate.command(Path(real_bin) / "submit_answer")
    t0 = time.monotonic()

    def late() -> bool:
        return deadline_s is not None and time.monotonic() - t0 > deadline_s

    def propose(extra: str, fallback: dict | None) -> dict | None:
        try:
            return candidates.run(request + extra, cfg.db, complete, log)
        except candidates.StepFailed as e:
            log.append("steps.failed", problem=str(e))
            return fallback

    out = propose("", None)
    if out is None:  # G7
        return run_gated(prompt, cwd, cfg, real_bin, complete, received=False, deadline_s=deadline_s, **loop_args)

    facts = ""
    for item in open_items(out):
        if sum(e["kind"] == "question.asked" for e in log.read()) >= cfg.ask_budget or late():
            break
        ask = QUESTION.format(request=request, item=item["ask"])
        try:
            question = model.ask_json(
                [{"role": "user", "content": ask}], lambda o: candidates.text(o["question"], "a question"), complete
            )
        except ValueError:
            question = f'What exactly do you mean by "{item["text"]}"?'
        facts += f"- Question: {question}\n  Answer: {gate.ask(cfg, question, ask_customer)}\n"
    if facts and not late():
        out = propose(CONFIRMED + facts, out)

    tried, rejected, again = set(), "", False
    while True:
        left = [c for c in out["classes"] if c["result_class"] not in tried]
        if not left:
            if again or not rejected or late():
                break
            again, out = True, propose((CONFIRMED + facts if facts else "") + REJECTED + rejected, out)
            continue
        best = max(left, key=lambda c: len(c["queries"]))  # most queries; the first one on a tie
        tried.add(best["result_class"])
        query = out["queries"][best["queries"][0]]
        cfg.answer_file.write_text(query["sql"] + "\n")
        reply = gate.submit(cfg, assumptions(out, query), deliver)
        if reply.startswith(("ACCEPTED", "BUDGET_EXHAUSTED")):
            break
        if reply.startswith("REJECTED"):
            rejected += f"- {query['sql']}\n  {reply}\n"
    return gate.finalize(cfg, "steps", deliver)
