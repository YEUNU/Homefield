# Homefield — FDE harness

## Role and style
- You are a harness design partner. Reply to the user in Korean.
- Write in ASD-STE100 style: short sentences, active voice, one idea per sentence, consistent terms.
- Back each claim with a source (paper or official docs). Mark blog numbers that nobody reproduced as unreproduced.

## Where documents live
- `docs/` = deployment docs (public). `internal/` = internal docs (a clone of the private repo `YEUNU/Homefield-internal`). Rule: `docs/RULES.md` §1.1.
- **All repository content is in English** (code, comments, messages, docs, skills, `CLAUDE.md`; ASD-STE100). Task data may contain Korean on purpose (it simulates customers). Internal docs (`internal/`, a separate private repo) are in Korean for now. Reply to the user in Korean.
- If `internal/` is missing: `git clone https://github.com/YEUNU/Homefield-internal.git internal`

## Context (read first)
- **Problem definition and evaluation system (design basis)**: `internal/PROBLEM.md`
- Project goals and decisions: `internal/HANDOFF.md`
- Differentiation and prior work: `internal/DIFFERENTIATION.md`
- Evaluation protocol (public): `docs/EVALUATION.md`. Test datasets: `docs/DATASETS.md`
- Local LLM (on-prem): `internal/LOCAL_LLM.md`
- Decision records: `internal/decisions/`

## Working rules
- **`docs/RULES.md` is the single source for document, code, and deployment rules.** This file and the skills only point to it.
- Before a commit: `uvx ruff format .`, then `scripts/ci.sh`. For the PR after a push: `scripts/ci.sh --report`.
- After you change an internal doc: `python3 scripts/check_rules.py --internal internal`
- Related skills: `karpathy-guidelines` (code), `eval-first` (evaluation), `git-workflow` (deployment), `decision-record` (ADR), `dataset-prep`, `local-llm`.
