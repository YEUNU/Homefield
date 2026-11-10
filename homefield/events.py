"""Append-only event log (JSONL). Every state of a task is a view of this log: what was asked,
what was submitted, what is still open. Nothing is edited or deleted."""

import json
from datetime import datetime
from pathlib import Path


class EventLog:
    def __init__(self, path: Path):
        self.path = Path(path)

    def read(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text().splitlines() if line]

    def append(self, kind: str, **data) -> dict:
        event = {"seq": len(self.read()) + 1, "ts": datetime.now().isoformat(timespec="seconds"), "kind": kind, **data}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
        return event
