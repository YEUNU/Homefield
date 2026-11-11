---
status: draft
updated: 2026-11-10
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
- Count rework in two classes: **interpretation error** (the result is different) and **execution error** (SQL error, no answer file, no `@key[value]` pair).
- **No action**: an episode that ends with no question and no submission (early exit, a question in chat text instead of the protocol, and so on). Count it as a failure. Also show the number of such episodes separately for diagnosis.
- Secondary metrics: number of questions, number of "I don't know" answers, run time.
- **Guess baseline**: the acceptance probability and CFC when the agent guesses uniformly among the interpretations and asks no question. Put it in the result table.
- The default is 10 or more repeats for each cell (task × harness × variant).

- **Anchor tasks** (`anchor_k` in `task.json`) also get diagnostics from the episode logs: candidate-set hit rate (submitted results that match the customer's number), duplicate submissions, first-submission gold rate, timeouts, and keyword counts of "unknown" answers and of customer answers that approve the agent's proposal.
- **Chance level** of an anchor task = min(1, submit budget / k). It is the expected acceptance of uniform guessing among the k candidates left after the anchor. It is not an upper bound: a model's prior can push the acceptance above or below it.

## 2. Task format (`tasks/<id>/task.json`)
| Field | Meaning |
|---|---|
| `request` | The ambiguous customer request |
| `db`, `db_sql` | The SQLite DB name in the work folder and the SQL that creates it |
| `db_file` | Instead of `db_sql`: the path of an existing SQLite file |
| `files` | Other source files (CSV, documents) copied to the work folder. No DB is needed |
| `answer_file` | The file where the agent writes the answer |
| `check.type` | `sql_result` or `exact_answer` |
| `check.gold_sql` | `sql_result`: the gold SQL. evalkit compares the result sets (order ignored, numeric tolerance 1e-6) |
| `check.answers` | `exact_answer`: gold `[key, value]` pairs. The answer file holds `@key[value]` pairs. Every gold key must be present. A number is equal if it is within half a unit of the last decimal of the gold value. Other values are compared after strip and lower case |
| `condition` | Optional. `O` (facts in the request, no questions), `N` (no facts, no questions), `D` (facts known only to the customer) |
| `hidden.facts` | Facts that only the customer simulator knows |
| `budget.ask`, `budget.submit` | Question budget and submission budget |
| `n_interpretations` | Number of interpretation combinations that change the result (for the guess baseline) |

## 3. Common protocol for the agent
The protocol is the same in every harness that has a shell.

- Answer: write the answer in the answer file in the work folder (`sql_result`: one SQL statement; `exact_answer`: `@key[value]` pairs in the format that the request gives).
- Question: `<bin>/ask_user "question"` prints the answer of the customer simulator.
- Submission: `<bin>/submit_answer` prints `ACCEPTED` or `REJECTED`.
  - A rejection message gives only the information that a real customer gives. It does not give the remaining count or the content of an SQL error.
  - Scoring time is limited so that the agent always gets a reply. The gold result is computed once, before the agent starts. An answer SQL that runs longer than 60 s is rejected as an SQL error (`error_kind` = `sql_error`, result `timeout after 60s` in the episode log). The limit is below the 120 s tool timeout of `bare`.
  - If the agent's process leaves before a reply arrives, the question or submission still counts. The episode log gets an event of kind `client_gone`.

The customer simulator knows only `hidden.facts`. For a question outside the facts, it answers `I don't know.` It does not know the gold SQL. It answers only about the term or condition that the question names, with the fact line of that term (the facts are split into lines at `;`). A question that names no specific term or condition ("What should I know?") gets no fact; the answer is `Please ask about a specific term or condition.` Reason: without this rule one broad question returns all facts, and the hidden form of a task equals the form with the facts in the request.

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
- Episode records: `$HF_RUNS_DIR` (default: the temporary folder/homefield-runs). When an episode ends, evalkit deletes the copied source files (DB and its SQLite side files, CSVs, documents). It keeps `events.jsonl`, `stdout.txt`, the answer file, and the other files that the agent wrote.
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
| | `bare-fs` | `bare` with a forced final delivery: when the turn cap (40) or a 13-minute deadline is reached, the loop tells the model to stop exploring and deliver, and allows 3 more turns | Isolates termination failures from the rest of the procedure | Connected |
| | `hf` | `bare-fs` inside gates (`homefield/gate.py`): the ask and submit commands of the prompt are replaced by gate commands. A gate keeps the budgets, refuses a result that was already rejected, refuses a submission without a stated assumption list, runs the answer read-only before it goes out, and delivers an answer that the agent wrote but did not submit. A refusal does not use the budget. It adds one line on assumptions to the prompt. Events: `<episode>/hf/events.jsonl` | Step B1 of our harness: plumbing, not a claim | Connected |
| | `hf-steps` | `hf` with the 4 steps for query tasks (`homefield/procedure.py`, `run_steps`): the code profiles the columns that the model names, runs at most 4 candidate queries and groups equal results, asks the customer about the terms that the data does not settle and about the points where the groups differ, generates the candidates once more with the answers, and delivers one group with its assumption list. After a rejection it delivers another group or generates once more. The worker loop of `hf` is the fallback when the steps give nothing usable | Step B3 of our harness: the procedure for one request | Connected |
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
| E5 | A procedure for tasks where the customer knows definitions: look at the schema and sample values → list every term or condition that changes the result and that the data does not settle → ask about each one before the first submission → write and check the query → submit. It names no kind of ambiguity |
