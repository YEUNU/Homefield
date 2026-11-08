---
status: stable
updated: 2026-11-08
audience: public
---
# Homefield rules (documents, code, release)

This document is the single source of rules. Other documents and skills only point to this document.
Code enforces the rules wherever possible. The enforcement tools are in the table in §4.

## 1. Document rules

### 1.1 Location: public and internal
| Location | Repository | Visibility | Content |
|---|---|---|---|
| `docs/` | `YEUNU/Homefield` | **Public** | Usage, evaluation protocol, datasets, harness connection methods, these rules |
| `internal/` | `YEUNU/Homefield-internal` (cloned in the Homefield root, excluded from git) | Private | Strategy, problem definition, analysis of differentiators and prior work, advisory records, design documents, decision records (ADR), infrastructure addresses, customer and company context |

If you are not sure, put the document in `internal/`. Moving a document to the public repository is easy later.

### 1.2 File names
| Type | Location | Name |
|---|---|---|
| Main document | `docs/`, `internal/` | `UPPER_SNAKE.md` (example: `EVALUATION.md`) |
| Design document | `internal/design/` | `kebab-case.md` |
| Decision record | `internal/decisions/` | `NNNN-kebab-case.md` (number = highest existing number + 1) |
| Repository guide | Root of each repository | `README.md` |

### 1.3 Front matter
Every document except `README.md` starts with this front matter.

```yaml
---
status: draft | stable | deprecated    # decision records: accepted | assumed | deprecated | superseded
updated: YYYY-MM-DD
audience: public | internal            # docs/ is public, internal/ is internal
---
```
- When you change the content, change `updated`.
- **Public documents (`docs/`, `README.md`) state only the final state.** Do not write dates, history, or change records (such as "we decided to", "we removed", or version marks). Git and `internal/` keep the history.
- Put a date only in the front matter `updated`.

### 1.4 Language and style (based on ASD-STE100)
- Write public documents (`docs/`, `README.md`, the PR template) in English (ASD-STE100 Simplified Technical English).
- Write internal documents (`internal/`) in Korean.
- Keep identifiers, commands, and file names as they are.
- Code comments and docstrings can be in Korean or English.
- Write one idea in each sentence. Use the active voice. Use short sentences.
- Use the same term for the same object (§1.6).
- Use tables and lists before prose.

### 1.5 Evidence marks
- Add a source (paper ID or URL) to prior work and figures.
- Mark a figure that you did not check in the original source as `(secondary source)`. Mark a figure that you could not check as `(unverified)`.
- Write an experiment result with a sample size below 30 as an "observation", not a "conclusion".
- Mark an initial value or target value that has no basis as `(no basis)`.

### 1.6 Terms
| Term | Meaning |
|---|---|
| harness (하네스) | An execution frame that wraps a model and gives it tools, a loop, and policies |
| task (과제) | One customer request (`tasks/<id>/`) |
| episode (에피소드) | One task × one harness × one run |
| engagement | A group of tasks that continue on the same customer and data |
| ledger (원장) | The structure that records interpretation decisions and assumptions |
| decision / assumption (결정 / 가정) | An interpretation choice that can change the output / a decision that the agent made without asking |
| rework (재작업) | A rejected submission |
| CFC | Cost to first correct answer = question round trips + r × rework |
| process case (프로세스 케이스) | A process-mining term. One process instance in an event log. It is not a "task" |

### 1.7 Paths and secrets
- Write paths in documents relative to the Homefield root (examples: `internal/PROBLEM.md`, `docs/EVALUATION.md`).
- Do not write internal IP addresses, hosts, or keys in `docs/` or in code. Use environment variables such as `$LOCAL_LLM_BASE_URL`.

## 2. Code rules

### 2.1 Language and dependencies
- Use Python 3.11 or later. Use the standard library first.
- To add a runtime external dependency, write a decision record (ADR).
- The harness core must not import a general agent framework (such as LangChain).
- All model calls go through one module (`homefield/model.py`). No other code calls a model directly over HTTP.

### 2.2 Structure and names
| Location | Content |
|---|---|
| `homefield/` | Harness core (model call, loop, tools, CLI) |
| `evalkit/` | Evaluation tool (runner, episode, adapters, scoring, report) |
| `tests/` | pytest tests |
| `tasks/<kebab-id>/` | Task: `task.json` + data generation files |
| `scripts/` | Operation scripts (connection check, rule check) |
| `.claude/skills/` | Claude Code skills |

- Modules, functions, variables: `snake_case`. Classes: `PascalCase`. Constants: `UPPER_SNAKE`.
- Identifiers are in English. Comments and docstrings can be in Korean or English.
- Make each entry point runnable as `python3 -m <package>.<module>`.
- Script names: `<verb>_<noun>` (examples: `check_rules.py`, `check_llm.sh`).
- `docs/EVALUATION.md` §6–7 is the source of harness IDs and result field names. Code and documents use these names exactly.

### 2.3 Quality
- Lint and format: `ruff check` and `ruff format --check` must pass (settings: `pyproject.toml`). Before you commit, run `uvx ruff format .`.
- When you change behavior, change the tests at the same time. Unit tests do not call the network or an LLM (replace the simulator with a function).
- For a change to harness behavior, attach the eval result to the PR (`eval-first` skill). If there is none, write "unverified".
- Follow the `karpathy-guidelines` skill when you write code: do only what is requested, keep it simple, and change only what is necessary.

### 2.4 Secrets and data
- Keep secret values only in `.env`. Do not print them, log them, or commit them.
- Do not commit: `.env`, key files, `data/`, `evals/results/`, customer data, names, or schemas, engagement state.
- Do not commit original benchmark data. Write the license in `docs/DATASETS.md`.

## 3. Release rules

### 3.1 Repositories
| Repository | Visibility | Branch rule |
|---|---|---|
| `YEUNU/Homefield` | Public | All of §3.2–3.5 |
| `YEUNU/Homefield-internal` | Private | Direct commits to `main` are allowed. The commit message format (§3.3) is the same |

### 3.2 Branches
- `main`: always in a working state. Direct push is forbidden. Merge only through a PR.
- Work branch: `<type>/<kebab-description>`. Types: `feat`, `fix`, `eval`, `docs`, `chore`, `exp`, `refactor`, `test`.
- `exp/*`: for experiments. You do not have to merge them. Record the results in `internal/decisions/`.
- Merge: squash merge. Delete the branch after the merge.

### 3.3 Commit messages
- Format: `<type>(<scope>): <summary>`. The summary has at most 72 characters. Write the "why" in the body.
- Scope examples: `core`, `policy`, `state`, `eval`, `evalkit`, `adapter`, `onto`, `p1`…`p5`, `skills`, `docs`, `rules`.

### 3.4 PR
- Local CI must pass: after you push, run `scripts/ci.sh --report` to set the commit status `local-ci`=success. GitHub Actions is not used (§4.1).
- Fill in the PR template. Give the eval result or "unverified".
- If the PR has a design decision, add a record to `internal/decisions/` and write only its number in the PR (the content is private).

### 3.5 Release
- Version: SemVer `vMAJOR.MINOR.PATCH`. Before 1.0, a MINOR increase can break compatibility.
- A release is an annotated tag on a `main` commit. Write the changes and an eval summary in the GitHub Release notes.
- Deliverables: a standalone CLI package and a Claude Code plugin (skill, hook, MCP). Installation at a customer site assumes an on-premises model.

### 3.6 Actions that need human approval
push, PR creation, tag, release, force-push, history rewrite, change of repository settings or visibility.

## 4. Enforcement tools
| Rule | Tool | Location |
|---|---|---|
| Do not commit secrets, key files, or `data/` | pre-commit hook, local CI gitleaks | `.githooks/pre-commit`, `scripts/ci.sh` |
| No private IP addresses (10/8, 172.16/12, 192.168/16) | pre-commit, local CI | `scripts/check_rules.py` |
| Do not track `internal/` | `.gitignore`, local CI | `scripts/check_rules.py` |
| Document front matter and name rules | pre-commit, local CI | `scripts/check_rules.py` |
| Commit message format | commit-msg hook | `.githooks/commit-msg` |
| Lint and format | local CI | `ruff check`, `ruff format --check` |
| Tests | local CI | `pytest` |
| Full check before push | pre-push hook | `.githooks/pre-push` → `scripts/ci.sh` |
| No direct push to `main`, PR and `local-ci` required, no force-push or deletion | GitHub branch protection | Configured. Administrator bypass is for emergencies only |
| Style, evidence marks, no history in public documents | Human review, rule check (dates in body) | `scripts/check_rules.py` |

### 4.1 Local CI
- CI runs on the developer PC, not on GitHub Actions (`scripts/ci.sh`). Checks: ruff check, ruff format, pytest, rule check, gitleaks.
- The `pre-push` hook runs it automatically before each push. If it fails, the push is blocked.
- To show the result on a PR, run `scripts/ci.sh --report` after the push. This records the GitHub commit status `local-ci`.
- Do not use a self-hosted GitHub runner. In a public repository, code from an external PR can run on this PC.
- Required tools: `uv` (uvx), `gitleaks` (Homebrew), `gh` (logged in).

## 5. First-time setup
```bash
git config core.hooksPath .githooks
brew install gitleaks    # for local CI
git clone https://github.com/YEUNU/Homefield-internal.git internal   # if you have access
cp .env.example .env
```
