---
name: eval-first
description: Build the eval before the feature for any harness component (loop, policy engine, uncertainty ledger, ontology pack, P1–P5 stage). Use when starting a new component, changing harness behavior, running a benchmark (BIRD-Interact, Spider 2.0, DABstep, KramaBench, BPI 2019, WWI), or comparing variants with ablation.
---

# Eval First

Build the way to measure before you change harness behavior.

## Order
1. **Define the question**: Which metric must this change move? (Pick it from the metric list in `docs/DATASETS.md`.)
2. **Write eval tasks**: Put inputs and expected results under `evals/<component>/`. Write at least 5. Include failing tasks.
3. **Run the baseline**: Run evalkit on the state before the change. Results accumulate in `evals/results/<date>.jsonl`.
4. **Implement**.
5. **Run the comparison**: Same tasks, same model, same number of repeats. Use `python3 -m evalkit.report` to view it next to the baseline.
6. **Ablation**: Turn off one component at a time and run again. Record a component with no effect as a removal candidate.

## Fields to record on each result line
The field definitions are in `docs/EVALUATION.md` (single source). The evalkit runner writes this format.

## Rules
- Experiment rules (pre-registration, runs, records, task pools, claims): `docs/RULES.md` §3 (single source).
- Use the local LLM as the default model (`local-llm` skill). Always record the model ID in the results.
- If the sample is small (<30), write "observation" instead of a conclusion.
- When you cite a benchmark number, also write the source paper and the setting (c-Interact / a-Interact, etc.).
- Mark a PR with no eval as "unverified".
