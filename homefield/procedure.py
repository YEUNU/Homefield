"""Run one task inside the gates (internal design harness-core, revision 4, step B1).

The worker is the M0 loop. It gets the task prompt with the customer commands replaced by gate
commands, so every question and every delivery passes `homefield.gate`. When the loop ends, G1
delivers an answer that was written but not submitted, and the task closes with a reason."""

import shlex
import sys
from pathlib import Path

from homefield import gate, model
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
    EventLog(cfg.events).append("task.received", request=prompt)
    result = run(prompt, cwd, complete=complete, log=log, **loop_args)
    return gate.finalize(cfg, result.stop, gate.command(Path(real_bin) / "submit_answer"))
