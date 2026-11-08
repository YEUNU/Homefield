"""에피소드 = 과제 1개 × 하네스 1개 실행.

에이전트에게 주는 공통 규약 (셸만 있으면 된다):
- 답은 작업 폴더의 답 파일(task["answer_file"])에 쓴다.
- `<bin>/ask_user "질문"`  → 고객 시뮬레이터의 답을 출력한다. 질문 예산이 있다.
- `<bin>/submit_answer`    → ACCEPTED 또는 REJECTED. 제출 예산이 있다.

정답·숨은 사실은 이 프로세스 메모리와 작업 폴더 밖 사본에만 있다.
한계: 같은 머신에서 돌므로 에이전트가 파일 시스템을 뒤지면 과제 원본을 찾을 수 있다. 격리는 Docker 단계에서 한다.
"""
import json
import secrets
import shutil
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from evalkit.check import check_sql_result

CFC_WEIGHTS = (1, 3, 10)

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
    def __init__(self, task: dict, db_source: Path, root: Path, simulate):
        self.task, self.simulate = task, simulate
        self.root = Path(root)
        self.work, self.bin, self.private = self.root / "work", self.root / "bin", self.root / "private"
        for d in (self.work, self.bin, self.private):
            d.mkdir(parents=True, exist_ok=True)
        shutil.copy(db_source, self.work / task["db"])
        self.gold_db = self.private / task["db"]
        shutil.copy(db_source, self.gold_db)
        self.events: list[dict] = []
        self.session = secrets.token_hex(16)
        self._lock = threading.Lock()
        self._server = None
        self.t0 = None

    # --- 서버 ---
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

    # --- 동작 ---
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
            self._log(kind="ask", question=question, answer=answer)
        return answer

    def _submit(self) -> str:
        with self._lock:
            if self.accepted():
                return "ACCEPTED (already). Stop now."
            if self._count("submit") >= self.task["budget"]["submit"]:
                return "BUDGET_EXHAUSTED: no more submissions. Stop now."
            ok, detail = check_sql_result(self.work / self.task["answer_file"], self.gold_db, self.task["check"])
            self._log(kind="submit", ok=ok, detail=detail)
            if ok:
                return "ACCEPTED"
            left = self.task["budget"]["submit"] - self._count("submit")
            return f"REJECTED: the customer says this result is not what they need. {detail} (submissions left: {left})".strip()

    # --- 지표 ---
    def accepted(self) -> bool:
        return any(e["kind"] == "submit" and e["ok"] for e in self.events)

    def metrics(self) -> dict:
        subs = [e for e in self.events if e["kind"] == "submit"]
        accepted = self.accepted()
        n_ask = self._count("ask")
        n_rework = sum(1 for e in subs if not e["ok"])
        return {
            "accepted": accepted,
            "n_questions": n_ask,
            "n_submissions": len(subs),
            "n_rework": n_rework,
            "cfc": {str(r): n_ask + r * n_rework for r in CFC_WEIGHTS} if accepted else None,
        }
