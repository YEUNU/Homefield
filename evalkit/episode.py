"""Episode = one run of one task x one harness.

Common protocol given to the agent (a shell is enough):
- Write the answer to the answer file in the work folder (task["answer_file"]).
- `<bin>/ask_user "question"`  -> prints the customer simulator's reply. There is a question budget.
- `<bin>/submit_answer`    -> ACCEPTED or REJECTED. There is a submit budget.

The gold answer and hidden facts exist only in this process's memory and in copies outside the work folder.
Limit: it runs on the same machine, so an agent that searches the file system
can find the task source. Isolation comes at the Docker stage.
"""

import json
import secrets
import shutil
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from evalkit.check import check_answer

CFC_WEIGHTS = (1, 3, 10)
# Markers of "I don't know" answers. The customer simulator answers in the question's language.
UNKNOWN_MARKS = ("don't know", "do not know", "모르", "모릅")


def is_unknown(answer: str) -> bool:
    low = answer.lower()
    return any(mark in low for mark in UNKNOWN_MARKS)


def guess_baseline(n_interpretations: int, submit_budget: int) -> dict:
    """Baseline for guessing interpretations uniformly, without repeats (0 questions)."""
    tries = min(n_interpretations, submit_budget)
    p = tries / n_interpretations
    rework = (tries - 1) / 2  # expected number of earlier failures given success
    return {"p_success": round(p, 3), "cfc_given_success": {str(r): round(r * rework, 2) for r in CFC_WEIGHTS}}


SHIM = """#!/usr/bin/env python3
import json, sys, urllib.request
URL, SESSION, OP = {url!r}, {session!r}, {op!r}
q = " ".join(sys.argv[1:]).strip()
if OP == "ask" and not q:
    sys.exit('usage: ask_user "question"')
req = urllib.request.Request(URL + "/" + OP, data=json.dumps({{"session": SESSION, "question": q}}).encode(),
                             headers={{"Content-Type": "application/json"}})
print(json.load(urllib.request.urlopen(req, timeout=600))["reply"])
"""


class Episode:
    def __init__(self, task: dict, db_source: Path | None, root: Path, simulate, files: tuple[Path, ...] = ()):
        self.task, self.simulate = task, simulate
        self.root = Path(root)
        self.work, self.bin, self.private = self.root / "work", self.root / "bin", self.root / "private"
        for d in (self.work, self.bin, self.private):
            d.mkdir(parents=True, exist_ok=True)
        self.gold_db = None
        self._copies = [self.work / Path(f).name for f in files]  # deleted in stop()
        if db_source is not None:
            self._copies += [self.work / task["db"], self.private / task["db"]]
            shutil.copy(db_source, self.work / task["db"])
            self.gold_db = self.private / task["db"]
            shutil.copy(db_source, self.gold_db)
        for f in files:  # other source files (CSV, documents) go to the work folder only
            shutil.copy(f, self.work / Path(f).name)
        self.events: list[dict] = []
        self.session = secrets.token_hex(16)
        self._lock = threading.Lock()
        self._server = None
        self.t0 = None

    # --- server ---
    def start(self):
        ep = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                if body.get("session") != ep.session:
                    self.send_response(403)
                    self.end_headers()
                    return
                op = self.path.strip("/")
                reply = ep._ask(body["question"]) if op == "ask" else ep._submit()
                data = json.dumps({"reply": reply}, ensure_ascii=False).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{self._server.server_port}"
        for name, op in (("ask_user", "ask"), ("submit_answer", "submit")):
            p = self.bin / name
            p.write_text(SHIM.format(url=url, session=self.session, op=op))
            p.chmod(0o755)
        self.t0 = time.time()

    def stop(self):
        if self._server:
            self._server.shutdown()
            self._server.server_close()
        (self.root / "events.jsonl").write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in self.events))
        # Delete the source copies (a BIRD DB is up to ~600 MB). Keep the logs, the answer, and agent files.
        for p in self._copies:
            for side in (p, *(p.with_name(p.name + s) for s in ("-journal", "-wal", "-shm"))):
                side.unlink(missing_ok=True)

    # --- behavior ---
    def _count(self, kind: str) -> int:
        return sum(1 for e in self.events if e["kind"] == kind)

    def _log(self, **e):
        e["t"] = round(time.time() - self.t0, 2)
        self.events.append(e)

    def _ask(self, question: str) -> str:
        with self._lock:
            if self._count("ask") >= self.task["budget"]["ask"]:
                self._log(kind="ask_refused", question=question)
                return "BUDGET_EXHAUSTED: no more questions allowed. Decide yourself."
        answer = self.simulate(question)
        with self._lock:
            self._log(kind="ask", question=question, answer=answer, unknown=is_unknown(answer))
        return answer

    def _submit(self) -> str:
        with self._lock:
            if self.accepted():
                return "ACCEPTED (already). Stop now."
            if self._count("submit") >= self.task["budget"]["submit"]:
                return "BUDGET_EXHAUSTED: no more submissions. Stop now."
            answer = self.work / self.task["answer_file"]
            ok, error_kind, preview = check_answer(answer, self.gold_db, self.task["check"])
            # Keep the submission and result in the log only, for post-hoc analysis
            submitted = answer.read_text()[:4000] if answer.exists() else None
            self._log(kind="submit", ok=ok, error_kind=error_kind, result=preview, answer=submitted)
            # Give only what a real customer gives: no remaining count and no error text.
            return "ACCEPTED" if ok else "REJECTED: the customer says this result is not what they need."

    # --- metrics ---
    def accepted(self) -> bool:
        return any(e["kind"] == "submit" and e["ok"] for e in self.events)

    def metrics(self) -> dict:
        subs = [e for e in self.events if e["kind"] == "submit"]
        accepted = self.accepted()
        n_ask = self._count("ask")
        n_rework = sum(1 for e in subs if not e["ok"])
        budget = self.task["budget"]
        cost = {  # cost with failures included: a failure counts as the full budget spent
            str(r): (n_ask + r * n_rework) if accepted else (budget["ask"] + r * budget["submit"]) for r in CFC_WEIGHTS
        }
        return {
            # Did it end with no question and no submission (early stop, asking in chat text
            # instead of the protocol, etc.)? Count it as a failure and track it separately.
            "acted": n_ask + len(subs) > 0,
            "accepted": accepted,
            "n_questions": n_ask,
            "n_unknown": sum(1 for e in self.events if e["kind"] == "ask" and e.get("unknown")),
            "n_submissions": len(subs),
            "n_rework": n_rework,
            "n_rework_interp": sum(1 for e in subs if e.get("error_kind") == "wrong_result"),
            "n_rework_error": sum(1 for e in subs if e.get("error_kind") in ("missing", "sql_error", "format_error")),
            "cost": cost,
            "cfc": {str(r): n_ask + r * n_rework for r in CFC_WEIGHTS} if accepted else None,
        }
