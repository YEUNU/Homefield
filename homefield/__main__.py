"""Standalone run: python3 -m homefield -p "<task>" [--max-turns N] [--log trajectory.jsonl]"""

import argparse
import sys
from functools import partial
from pathlib import Path

from homefield import model
from homefield.loop import run


def main() -> int:
    ap = argparse.ArgumentParser(prog="homefield")
    ap.add_argument("-p", "--prompt", required=True)
    ap.add_argument("--model", default=model.DEFAULT_MODEL)
    ap.add_argument("--max-turns", type=int, default=40)
    ap.add_argument("--log", type=Path)
    args = ap.parse_args()
    result = run(
        args.prompt,
        Path.cwd(),
        complete=partial(model.complete, model=args.model),
        max_turns=args.max_turns,
        log=args.log,
    )
    print(result.final)
    print(f"[homefield] stop={result.stop} turns={result.turns}", file=sys.stderr)
    return 0 if result.stop == "final" else 1


if __name__ == "__main__":
    sys.exit(main())
