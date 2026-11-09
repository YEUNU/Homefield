---
status: stable
updated: 2026-11-10
audience: public
---
# Homefield rules (documents, code, experiments, Git, release)

This document is the single source of rules. Other documents and skills only point to this document.

Principles:
1. **One home for each fact.** A rule, a term, a field name, or a plan has one source document. Other documents link to it.
2. **Code enforces the rules wherever possible.** The enforcement tools are in the table in §6. A rule with no tool names its reviewer.
3. **Public content states the final state.** History and reasons stay in Git and in `internal/`.
4. **A person approves each action that leaves this machine or that cannot be undone** (§4.6).

## 1. Document rules

### 1.1 Location: public and internal
| Location | Repository | Visibility | Content |
|---|---|---|---|
| `docs/` | `YEUNU/Homefield` | **Public** | Usage, evaluation protocol, datasets, harness connection methods, these rules |
| `internal/` | `YEUNU/Homefield-internal` (cloned in the Homefield root, excluded from git) | Private | Strategy, problem definition, analysis of differentiators and prior work, design documents, decision records (ADR), experiment records, infrastructure addresses, customer and company context |

If you are not sure, put the document in `internal/`. Moving a document to the public repository is easy later.

### 1.2 File names and document types
| Type | Location | Name | Role |
|---|---|---|---|
| Main document | `docs/`, `internal/` | `UPPER_SNAKE.md` (example: `EVALUATION.md`) | One subject for each document |
| Design document | `internal/design/` | `kebab-case.md` | Design of one component |
| Decision record | `internal/decisions/` | `NNNN-kebab-case.md` (number = highest existing number + 1) | One decision or one unconfirmed assumption |
| Result archive | `internal/results/` | `<date>_<name>.tar.gz` and a `README.md` that lists the contents | Raw rows and episode logs that must outlive a machine |
| Repository guide | Root of each repository | `README.md` | Entry point and document index |

Fixed roles of the internal main documents:
| Document | The only place for |
|---|---|
| `PROBLEM.md` | The problem, the boundary of the claim, the metric definitions |
| `ROADMAP.md` | The current plan, stage status, and open decisions |
| `EXPERIMENTS.md` | Pre-registrations, amendments, run notes, and results (§3) |
| `NEXT_SESSION.md` | The handover prompt for the next work session. It points to the other documents and does not hold results |

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
- Write all repository content (code, comments, docstrings, messages, docs, skills, `CLAUDE.md`) in English (ASD-STE100 Simplified Technical English).
- Task data and the code that handles customer language may contain other languages on purpose (it simulates customers).
- Write internal documents (`internal/`) in English too.
- Keep identifiers, commands, and file names as they are.
- Write one idea in each sentence. Use the active voice. Use short sentences.
- Use the same term for the same object (§1.6).
- Use tables and lists before prose.

### 1.5 Evidence marks
- Add a source (paper ID or URL) to prior work and figures.
- Mark a figure that you did not check in the original source as `(secondary source)`. Mark a figure that you could not check as `(unverified)`.
- Write an experiment result with a sample size below 30 as an "observation", not a "conclusion".
- Mark an initial value or target value that has no basis as `(no basis)`.
- A figure from our own runs names its raw source (result file, run folder, or log).

### 1.6 Terms
| Term | Meaning |
|---|---|
| harness | An execution frame that wraps a model and gives it tools, a loop, and policies |
| task | One customer request (`tasks/<id>/`) |
| episode | One task × one harness × one run |
| engagement | A group of tasks that continue on the same customer and data |
| ledger | The structure that records interpretation decisions and assumptions |
| decision / assumption | An interpretation choice that can change the output / a decision that the agent made without asking |
| rework | A rejected submission |
| CFC | Cost to first correct answer = question round trips + r × rework |
| pre-registration | A decision rule that is written and committed before the data that it judges |
| development pool / evaluation pool | Tasks that we may look at while we build the harness / tasks that only judge it |
| process case | A process-mining term. One process instance in an event log. It is not a "task" |

### 1.7 Paths and secrets
- Write paths in documents relative to the Homefield root (examples: `internal/PROBLEM.md`, `docs/EVALUATION.md`).
- Do not write internal IP addresses, hosts, or keys in `docs/` or in code. Use environment variables such as `$LOCAL_LLM_BASE_URL`.
- Do not write personal e-mail addresses in the public repository.

### 1.8 Document upkeep
- A change that makes another document wrong corrects that document in the same commit. Example: a result that changes a stage status also changes `internal/ROADMAP.md`.
- A reference to a section of this document uses the form `RULES §<number>`. The rule check rejects a reference to a section that does not exist.
- Do not copy a rule, a field list, or a plan into a second document. Link to its home.
- When a document is no longer correct and nobody will correct it, set `status: deprecated` and name its replacement in the first line.

## 2. Code rules

### 2.1 Language and dependencies
- Use Python 3.11 or later. Use the standard library first.
- To add a runtime external dependency, write a decision record (ADR).
- The harness core must not import a general agent framework (such as LangChain).
- All model calls go through one module (`homefield/model.py`). No other code calls a model directly over HTTP.

### 2.2 Structure and names
| Location | Content | In git |
|---|---|---|
| `homefield/` | Harness core (model call, loop, tools, CLI) | Yes |
| `evalkit/` | Evaluation tool (runner, episode, adapters, scoring, report) | Yes |
| `tests/` | pytest tests | Yes |
| `tasks/<kebab-id>/` | Tasks that we wrote: `task.json` + data generation files | Yes |
| `scripts/` | Operation scripts (connection check, rule check, dataset fetch, task generation) | Yes |
| `.claude/skills/` | Claude Code skills | Yes |
| `data/raw/`, `data/processed/` | Downloaded and converted benchmark data | No |
| `data/tasks/` | Tasks generated from licensed data. `scripts/make_tasks.py` generates them again from a seed | No |
| `evals/results/` | Result rows of evalkit runs | No |

- Modules, functions, variables: `snake_case`. Classes: `PascalCase`. Constants: `UPPER_SNAKE`.
- Make each entry point runnable as `python3 -m <package>.<module>`.
- Script names: `<verb>_<noun>` (examples: `check_rules.py`, `check_llm.sh`).
- `docs/EVALUATION.md` is the source of harness IDs and result field names. Code and documents use these names exactly.

### 2.3 Quality
- Lint and format: `ruff check` and `ruff format --check` must pass (settings: `pyproject.toml`). Before you commit, run `uvx ruff format .`.
- When you change behavior, change the tests at the same time. Write the test first for a defect fix. Unit tests do not call the network or an LLM (replace the simulator with a function).
- For a change to harness behavior, attach the eval result to the PR (`eval-first` skill). If there is none, write "unverified".
- A change to what the agent sees or to how a submission is scored is a protocol change. Update `docs/EVALUATION.md` in the same PR, and do not merge it while a run is in progress (§3.2).
- Follow the `karpathy-guidelines` skill when you write code: do only what is requested, keep it simple, and change only what is necessary.

### 2.4 Secrets and data
- Keep secret values only in `.env`. Do not print them, log them, or commit them.
- Do not commit: `.env`, key files, `data/`, `evals/results/`, customer data, names, or schemas, engagement state.
- Do not commit original benchmark data. Write the license in `docs/DATASETS.md`.
- Treat downloaded files as untrusted data. Do not run code from a download folder. Read them with `python3 -I` from a script in `scripts/`.

### 2.5 Environment and tools
- Run tools through `uvx` (`uvx ruff`, `uvx --python 3.12 pytest -q`). Do not use `uv run`: it writes a lock file, and the project has no runtime dependency to lock.
- Each machine has its own `.env`. The value of `LOCAL_LLM_BASE_URL` has a scheme and ends with `/v1`. Run `scripts/check_llm.sh` after you write or change `.env`.
- Run folders live outside the repository. Set `HF_RUNS_DIR` and pass it explicitly to a detached run.
- `data/` can be a link to a larger disk. Code reads it only through the paths in §2.2.

## 3. Experiment rules

The records are in `internal/EXPERIMENTS.md`. The public protocol is in `docs/EVALUATION.md`.

### 3.1 Before the data
- Pre-register each experiment before any of its data exists: the question, the conditions, the sample, the command, the decision rule, and the next action for each verdict.
- Commit the pre-registration before the run starts. The commit order is the proof.
- Name the comparator in advance. Do not select the best arm after the run.
- State the smallest effect that the sample can detect. If the sample cannot detect the effect of interest, the experiment is a check, not a claim.

### 3.2 During a run
- Do not change conditions, code, model, or budgets during a run. A run uses one commit of `main`.
- Run `scripts/check_llm.sh` and one smoke episode before a long run.
- Run long jobs detached, with their output in a log file under `HF_RUNS_DIR`.
- A defect that you find during a run goes in the run note. Repair it after the run, not during it.

### 3.3 Records
- Each run note gives: the code commit, the command, the start and end time, the result file, the run folder, and the count of episodes by exit kind.
- A record is append-only after its data exists. Correct an error with a dated amendment that states the reason. Do not edit the earlier text.
- An amendment before data may change the design. An amendment after data may not change the decision rule; it can only add a new rule that is marked as post hoc.
- Set aside an invalid run with a suffix that names the cause (example: `.invalid-baseurl`). Do not delete it, and do not use it in a verdict.
- Before a machine is cleared, archive the rows and episode logs that a verdict used (§1.2, result archive). Remove source data copies and check that the archive holds no secret.

### 3.4 Task pools
- The evaluation pool judges the harness. Do not read its items, results, or failures while you build or tune our harness.
- The development pool is a separate draw. State the source of each pool before the first run that uses it.
- A filter or audit step that selects evaluation tasks is blind to the results of the experiment that uses them.
- Evaluation-only databases stay unused until the experiment that names them.

### 3.5 Claims and review
- Check each claim against the raw rows and logs before you write it. Mark a number that you did not check as `(unverified)`.
- A claim about our harness needs a prompt-only control: the same procedure given as text to an existing harness.
- Check the claims of an independent review (a person or a model) against the data before you accept them. Record what you checked.
- Report failures by kind (no action, turn limit, timeout, wrong answer). Do not report acceptance alone.

## 4. Git rules

### 4.1 Repositories
| Repository | Visibility | Rule |
|---|---|---|
| `YEUNU/Homefield` | Public | All of §4.3–4.6 |
| `YEUNU/Homefield-internal` | Private | Direct commits to `main`. The commit message format (§4.4) is the same. A push needs approval (§4.6). After a change, run `python3 scripts/check_rules.py --internal internal` |

A commit goes to one repository. When public code and an internal record change together, commit to each repository and name the public commit or PR in the internal message.

### 4.2 Identity
- Set `user.name` and `user.email` for each repository on each machine, or pass them for each commit with `git -c`.
- Commits to the public repository use the GitHub no-reply address of the author.
- A commit that an AI agent wrote carries a `Co-authored-by` trailer that names the model.

### 4.3 Branches
- `main`: always in a working state. Direct push is forbidden. Merge only through a PR.
- Work branch: `<type>/<kebab-description>`. Types: `feat`, `fix`, `eval`, `docs`, `chore`, `exp`, `refactor`, `test`.
- `exp/*`: for experiments. You do not have to merge them. Record the results in `internal/EXPERIMENTS.md`.
- One PR holds one purpose. Put related changes in one PR. Put unrelated changes in separate branches.
- Merge: squash merge. Delete the branch after the merge.

### 4.4 Commit messages
- Format: `<type>(<scope>): <summary>`. The summary has at most 72 characters. Write the "why" in the body.
- Scope examples: `core`, `policy`, `state`, `eval`, `evalkit`, `adapter`, `onto`, `p1`…`p5`, `skills`, `docs`, `rules`, `experiments`.
- If a hook blocks a commit, repair the cause. Do not use `--no-verify`.

### 4.5 PR
- Local CI must pass: after you push, run `scripts/ci.sh --report` to set the commit status `local-ci`=success. GitHub Actions is not used (§6.1).
- Fill in the PR template. Give the eval result or "unverified".
- If the PR has a design decision, add a record to `internal/decisions/` and write only its number in the PR (the content is private).
- A PR that changes the protocol says so in its first line (§2.3).

### 4.6 Actions that need human approval
| Action | Repositories |
|---|---|
| push, PR creation, merge | Both |
| tag, release | Public |
| force-push, history rewrite, branch deletion on the remote | Both |
| Change of repository settings or visibility | Both |
| Download of a dataset (after the license check) | — |

A local commit does not need approval. An approval covers one action; it does not cover the next one.

## 5. Release and deployment rules

### 5.1 Version
- Version: SemVer `vMAJOR.MINOR.PATCH`. Before 1.0, a MINOR increase can break compatibility.
- A release is an annotated tag on a `main` commit. The version in `pyproject.toml` equals the tag.

### 5.2 Release gate
A commit can be released when all of these are true:
1. Local CI passes on that commit (`local-ci`=success).
2. The release notes give the changes and an eval summary: protocol document, model ID, tasks, and result. If there is no eval, they say "unverified".
3. The versions of the comparison harnesses in `evalkit/adapters.py` are pinned.
4. The package holds no benchmark data, no result rows, and no secret.
5. No pre-registered run is in progress on that code.

### 5.3 Deliverables
- A standalone CLI package and a Claude Code plugin (skill, hook, MCP).
- Policy, skills, and state have one harness-neutral source. Host formats are generated from it.

### 5.4 Deployment at a customer site
- The default model is on-premises. The address and key come from environment variables. The package holds no address.
- The harness sends data only to the configured model server. It has no telemetry.
- Customer data, schemas, names, and engagement state stay on the customer machine. They do not enter either repository.
- Industry knowledge ships as a domain pack, apart from the core. The core works without a pack.

## 6. Enforcement tools
| Rule | Tool | Location |
|---|---|---|
| Do not commit secrets, key files, or `data/` | pre-commit hook, local CI gitleaks | `.githooks/pre-commit`, `scripts/ci.sh` |
| No private IP addresses (10/8, 172.16/12, 192.168/16) | pre-commit, local CI | `scripts/check_rules.py` |
| Do not track `internal/` | `.gitignore`, local CI | `scripts/check_rules.py` |
| Document front matter and name rules | pre-commit, local CI | `scripts/check_rules.py` |
| No dates in the body of public documents | pre-commit, local CI | `scripts/check_rules.py` |
| References to sections of this document exist | pre-commit, local CI | `scripts/check_rules.py` |
| Commit message format | commit-msg hook | `.githooks/commit-msg` |
| Hooks are installed (`core.hooksPath`) | local CI | `scripts/ci.sh` |
| Lint and format | local CI | `ruff check`, `ruff format --check` |
| Tests | local CI | `pytest` |
| Full check before push | pre-push hook | `.githooks/pre-push` → `scripts/ci.sh` |
| No direct push to `main`, PR and `local-ci` required, no force-push or deletion | GitHub branch protection | Configured. Administrator bypass is for emergencies only |
| Base URL format in `.env` | Connection check | `scripts/check_llm.sh` |
| Style, evidence marks, experiment rules (§3), release gate (§5.2) | Human review | PR review, `internal/EXPERIMENTS.md` |

### 6.1 Local CI
- CI runs on the developer PC, not on GitHub Actions (`scripts/ci.sh`). Checks: hooks, ruff check, ruff format, pytest, rule check, gitleaks.
- The `pre-push` hook runs it automatically before each push. If it fails, the push is blocked.
- To show the result on a PR, run `scripts/ci.sh --report` after the push. This records the GitHub commit status `local-ci`.
- Do not use a self-hosted GitHub runner. In a public repository, code from an external PR can run on this PC.
- Required tools: `uv` (uvx), `gitleaks`, `gh` (logged in).

## 7. First-time setup
```bash
git config core.hooksPath .githooks
# install uv, gitleaks, and gh with the package manager of the machine
git clone https://github.com/YEUNU/Homefield-internal.git internal   # if you have access
cp .env.example .env
scripts/check_llm.sh
```
Then set the Git identity for both repositories (§4.2).
