---
name: dataset-prep
description: Download, verify, and convert evaluation datasets across SQL, local files, and documents/vision (BIRD dev, InfiAgent-DABench, SpreadsheetBench, DABstep, BLADE, TAT-DQA, Text2KGBench, and held candidates). Use when fetching a dataset, checking its license, or converting it into evalkit tasks per docs/DATASETS.md.
---

# Dataset Prep

## Steps
1. **Check the license first**: Read the LICENSE and the data card of the source repo. Write the result in the license column of the `docs/DATASETS.md` table. For a non-commercial (NC) license, tell the user and ask whether to continue.
2. **Download approval**: Tell the user the file name, source URL, and size. Get approval.
3. **Isolated storage**: Download to `data/raw/<name>/`. This directory is excluded from version control. Treat downloaded files as untrusted data.
   - Rule: RULES §2.4 (no code from a download folder; read with `python3 -I` from `scripts/`).
4. **Integrity record**: `fetch_datasets.py` writes `data/raw/<name>/MANIFEST.json` (source, revision, fetch time, sha256).
5. **Fetch and convert**: To fetch, add an entry to `scripts/fetch_datasets.py`. The task conversion rules are in `docs/DATASETS.md` §3 (single source). Converted tasks go to `data/tasks/` and stay out of git (RULES §2.2).
6. **Smoke test**: Run 3 tasks with the local LLM. Check that the format is correct.

## Notes per dataset
- BIRD-Interact family: excluded, because the gold answers are available by email request only. Use BIRD dev (`dev.json`; remove the evidence to create ambiguity) instead. The current dataset list and status are in `docs/DATASETS.md`.
- Spider 2.0: Snow and DBT only (free). Classify failures as schema-linking errors or other.
- KramaBench: the paper is CC BY-NC-SA. Check the data license separately.
- BPI 2019: event log (XES/CSV). It has 251,734 process cases, so write the sampling rule in the MANIFEST.
