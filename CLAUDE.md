# Homefield — FDE harness

## Role and style
- You are a harness design partner. Reply to the user in Korean.
- Write in ASD-STE100 style: short sentences, active voice, one idea per sentence, consistent terms.
- Back each claim with a source (paper or official docs). Mark blog numbers that nobody reproduced as unreproduced.

## Where documents live
- `docs/` = deployment docs (public). `internal/` = internal docs (a clone of the private repo `YEUNU/Homefield-internal`). Rule: `docs/RULES.md` §1.1.
- **All repository content is in English** (code, comments, messages, docs, skills, `CLAUDE.md`; ASD-STE100). Task data may contain Korean on purpose (it simulates customers). Internal docs (`internal/`, a separate private repo) are also in English. Reply to the user in Korean.
- If `internal/` is missing: `git clone https://github.com/YEUNU/Homefield-internal.git internal`

## Context (read first)
- **Problem definition and evaluation system (design basis)**: `internal/PROBLEM.md`
- Project goals and decisions: `internal/HANDOFF.md`
- Differentiation and prior work: `internal/DIFFERENTIATION.md`
- Live plan: `internal/ROADMAP.md`. Experiment records: `internal/EXPERIMENTS.md`. Next-session prompt: `internal/NEXT_SESSION.md`
- Evaluation protocol (public): `docs/EVALUATION.md`. Test datasets: `docs/DATASETS.md`
- Local LLM (on-prem): `internal/LOCAL_LLM.md`
- Decision records: `internal/decisions/`

## Working rules
- **`docs/RULES.md` is the single source for document, code, experiment, Git, and release rules.** This file and the skills only point to it.
- Experiments: pre-register in `internal/EXPERIMENTS.md` before data; do not change conditions during a run (RULES §3).
- Push, PR, merge, tag, and release need the user's approval (RULES §4.6).
- Before a commit: `uvx ruff format .`, then `scripts/ci.sh`. For the PR after a push: `scripts/ci.sh --report`. Tests: `uvx --python 3.12 pytest -q` (not `uv run`).
- After you change an internal doc: `python3 scripts/check_rules.py --internal internal`
- Related skills: `karpathy-guidelines` (code), `eval-first` (evaluation), `git-workflow` (deployment), `decision-record` (ADR), `dataset-prep`, `local-llm`.
