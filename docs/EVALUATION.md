---
status: draft
updated: 2026-11-08
audience: public
---
# Evaluation protocol (evalkit)

Homefield compares agent harnesses with the same model and the same conditions. This document describes the protocol.

## 1. What we measure
The **interaction cost** to the first correct answer. The request is an ambiguous data-analysis request. The correct answer must match the hidden customer intent.

- **Read two primary metrics together.**
  - **Acceptance rate**: the share of episodes accepted within the budget. Give a Wilson 95% interval.
  - **Cost** (failures included) = for an accepted episode, `question round trips + r × rework count`. For a failed episode, `question budget + r × submission budget`. Report the mean ± a 95% interval.
  - Rework = a rejected submission. It is the same as showing a wrong result in a demo.
  - r is how many times more expensive one rework is than one question. The value is not known, so report all of r ∈ {1, 3, 10}.
- Use CFC (the cost of accepted episodes only) as a reference only. It has no meaning when the acceptance rate is low.
- Count rework in two classes: **interpretation error** (the result is different) and **execution error** (SQL error, no answer file).
- **No action**: an episode that ends with no question and no submission (early exit, a question in chat text instead of the protocol, and so on). Count it as a failure. Also show the number of such episodes separately for diagnosis.
- Secondary metrics: number of questions, number of "I don't know" answers, run time.
- **Guess baseline**: the acceptance probability and CFC when the agent guesses uniformly among the interpretations and asks no question. Put it in the result table.
- The default is 10 or more repeats for each cell (task × harness × variant).

## 2. Task format (`tasks/<id>/task.json`)
| Field | Meaning |
|---|---|
| `request` | The ambiguous customer request |
| `db`, `db_sql` | The SQLite DB and the SQL that creates it |
| `answer_file` | The file where the agent writes the answer SQL |
| `check.gold_sql` | The gold SQL. evalkit compares the result sets (order ignored, numeric tolerance 1e-6) |
| `hidden.facts` | Facts that only the customer simulator knows |
| `budget.ask`, `budget.submit` | Question budget and submission budget |
| `n_interpretations` | Number of interpretation combinations that change the result (for the guess baseline) |

## 3. Common protocol for the agent
The protocol is the same in every harness that has a shell.

- Answer: write one SQL statement in the answer file in the work folder.
- Question: `<bin>/ask_user "question"` prints the answer of the customer simulator.
- Submission: `<bin>/submit_answer` prints `ACCEPTED` or `REJECTED`.
  - A rejection message gives only the information that a real customer gives. It does not give the remaining count or the content of an SQL error.

The customer simulator knows only `hidden.facts`. For a question outside the facts, it answers `I don't know.` It does not know the gold SQL.

## 4. Fairness rules
1. Fix the model. Change only the harness.
2. Give all harnesses the same tool (shell), the same protocol, and the same budget.
3. Do not tune the prompt for a harness. Apply the prompt variants (E0, E1 …) identically to all harnesses.
4. Run episodes outside the repository. Inside the repository, a harness reads the instruction files of this repository and the comparison is contaminated.
5. Score with a copy of the gold DB that is outside the work folder. If the agent changes the DB in the work folder, scoring is not affected.
6. Run repeats. Put the repeats in the outer loop.
7. Pin the harness versions (`VERSIONS` in `evalkit/adapters.py`).
8. For sampling, all harnesses use the server defaults (temperature, thinking). Only the customer simulator is fixed to temperature 0 and thinking off (it is not under evaluation).

Limit: the agent and the simulator run on the same machine. If the agent searches the file system, it can find the original task. Container isolation is the next step.

## 5. Run
```bash
cp .env.example .env    # LOCAL_LLM_BASE_URL, LOCAL_LLM_API_KEY
python3 -m evalkit.run --task tasks/smoke-revenue --harness claude,codex,opencode,mini,openhands --variant E0,E1 --repeat 3
python3 -m evalkit.report evals/results/<date>.jsonl --task tasks/smoke-revenue
```
- Give more than one task with `--task a,b`. `--jobs N` runs N episodes at the same time (on a shared LLM server, adjust it while you watch the run time).
- To continue an interrupted experiment, add `--resume <start time>` to the same command. The run skips the valid episodes that are in the result file after that time.
- `evalkit.report` prints one row for each variant × harness. The columns show the number of episodes (n), the number of no-action episodes, the acceptance rate with its 95% interval, the number of questions, the number of "I don't know" answers, the rework split into interpretation and execution errors, the cost for each r, and the time in seconds. The report prints the column names in Korean.
- Result: `evals/results/<date>.jsonl` (excluded from git)
- Episode records: `$HF_RUNS_DIR` (default: the temporary folder/homefield-runs)
- How to connect a harness: `docs/HARNESSES.md`

## 6. Harness IDs
We choose the comparison targets by recognition and role. Criteria: (1) use in the field and GitHub stars, (2) appearance on a public leaderboard (Terminal-Bench, SWE-bench), (3) can run headless with an OpenAI-compatible local model.

| Group | ID | Harness | Why we chose it | Connection |
|---|---|---|---|---|
| A. Field leaders | `claude` | Claude Code | The leading commercial coding agent. FDEs use it in real work | Confirmed |
| | `codex` | Codex CLI | An open-source commercial harness, about 126k stars (secondary source) | Confirmed |
| | `opencode` | OpenCode | The open-source project with the most stars, about 209k (secondary source) | Confirmed |
| | `qwen` | Qwen Code | A fork of the Gemini CLI family (about 107k stars) for open models. The Gemini CLI itself may not continue and has no OpenAI-compatible connection | Confirmed |
| B. Open-source general | `openhands` | OpenHands CLI | A general agent. The default baseline of TheAgentCompany | Confirmed |
| | `goose` | Goose | A general open-source agent, about 55k stars (secondary source) | Confirmed |
| C. Research baselines | `mini` | mini-swe-agent | The minimal baseline of the SWE-bench and Terminal-Bench papers | Confirmed |
| | `terminus` | Terminus 2 | The official reference agent of Terminal-Bench | Unconfirmed (needs the Terminal-Bench run framework) |
| | `bare` | Homefield M0 (`homefield/`): a model-independent tool-call loop with one shell tool | The lower bound of the harness effect and the base of our harness | Connected |
| | `bird-official` | The official BIRD-Interact baseline | The baseline of the benchmark that the tasks come from | Not implemented |

Excluded harnesses and reasons:
- Aider (about 49k stars): it focuses on file editing, so it does not fit the shell protocol. It has no recent commits (secondary source).
- Cline, Kilo Code: they are mainly IDE extensions, so they do not fit a headless comparison.
- The Gemini CLI itself: see the `qwen` row above.

The star counts are approximate values from secondary sources (morphllm.com, openalternative.co). Check the real numbers in each repository.

## 7. Result fields (`evals/results/<date>.jsonl`, one line = one episode)
| Field | Meaning |
|---|---|
| `task_id` | Task ID |
| `harness` | Harness ID (§6) |
| `variant` | Prompt variant (§8) |
| `repeat` | Repeat number (from 0) |
| `model` | Model ID |
| `ts` | Record time (ISO 8601) |
| `accepted` | Whether the episode was accepted within the budget |
| `n_questions`, `n_unknown` | Number of questions, and how many of them got an "I don't know" answer |
| `acted` | Whether the episode had at least one question or submission (`false` is also counted as a failure) |
| `n_submissions`, `n_rework` | Number of submissions, and how many of them were rejected |
| `n_rework_interp`, `n_rework_error` | Of the rejections, the interpretation errors and the execution errors |
| `cost` | Cost with failures included `{"1": …, "3": …, "10": …}` |
| `cfc` | Cost of an accepted episode. `null` if the episode is not accepted |
| `tokens_in`, `tokens_out`, `silent_error` | Reserved fields. Always `null` for now |
| `latency_s` | Harness run time |
| `notes` | Exit code or `timeout` |
| `episode_dir` | Episode record folder |

## 8. Prompt variants
| ID | Content |
|---|---|
| E0 | The base protocol only |
| E1 | E0 + "List the interpretations that change the result. Ask about each one before the first submission. State each interpretation that you did not confirm as an assumption" |
| E2 | E1 + "If the customer does not know a definition, ask for a report number that the customer already knows. Keep only the interpretations that match that number" (a control that gives the anchor strategy as a conditional rule) |
| E3 | The anchor strategy as an explicit procedure: list the decisions → ask for the report number once → compute the number for each candidate → keep only the matching candidates → submit (the strongest prompt control) |
