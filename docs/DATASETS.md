---
status: draft
updated: 2026-11-08
audience: public
---
# Datasets

This document lists the datasets for evaluation. It gives the status of each dataset, how to download it, and the rules to convert it to the task format.
FDE field data has three types: **relational databases**, **local files** (CSV, Excel, JSON, manuals), and **documents and vision** (PDF, scans, table images). The ontology pack takes all three as input. The datasets also cover all three.

Sources and licenses come from official pages (papers, official repositories, Hugging Face cards). An item that is not checked is marked `(unverified)`.

## 1. List and status
Status: **Downloaded** = in `data/raw/`. **On hold** = usable, but a condition blocks it. **Excluded** = not used.

### 1.1 Downloaded
| Type | Dataset | Use | Data license | Source | Downloaded size | Gold answer | Ambiguity material |
|---|---|---|---|---|---|---|---|
| SQL | BIRD dev | Resolve knowledge ambiguity | CC BY-SA 4.0 | `dev.zip` (dev set `dev.json`, 1,534 questions, and the dev DBs) + HF `birdsql/bird_mini_dev` | 342MB | Public SQL | 1,386 `evidence` items in `dev.json` (without them, the question is ambiguous). The Mini-Dev file states its output contracts inside the questions, so evidence removal leaves little ambiguity there |
| SQL | AmbiQT | Queries with two interpretations | MIT | GitHub `testzer0/AmbiQT` | 247MB (with DB) | 2 SQL queries, one for each interpretation | Column and table synonyms, joins, pre-aggregation. The DBs are the original Spider DBs, so both interpretations give the same result: not usable for hidden-intent tasks |
| Local file (CSV) | InfiAgent-DABench | CSV analysis | Apache-2.0 | HF `infiagent/DABench` | 61MB | Closed-format answer (dev 257) | `constraints` (without them, the question is ambiguous) |
| Local file (Excel) | SpreadsheetBench verified 400 | Excel operations | CC BY-SA 4.0 (HF card) | HF `KAKA22/SpreadsheetBench` | 14MB | Gold Excel file | None |
| Local file (mixed) | DABstep dev | Document rules + payment CSV | CC BY 4.0 | HF `adyen/DABstep` | 23MB | Dev 10 only | None |
| Local file (CSV) | BLADE | Justification of analysis decisions | ODC-By 1.0 | GitHub `behavioral-data/BLADE` | 55MB | Gold analysis decisions | Analysis decisions with more than one valid answer |
| Document and vision (PDF) | TAT-DQA dev + test answers | Financial report document QA | CC BY 4.0 | HF `next-tat/TAT-DQA` | 163MB (training data of 1.2GB excluded) | Public (dev 1,644 questions) | Unit (scale) and formula (derivation) |
| Ontology | Text2KGBench | KG generation that obeys ontology constraints | Apache-2.0 | GitHub `cenguix/Text2KGBench` | 36MB | Gold triples | Not applicable |

### 1.2 On hold
| Dataset | Reason |
|---|---|
| AMBROSIA | License conflict (repository CC BY 4.0, website "All rights reserved"). The owners ask that nobody redistributes it |
| BEAVER | The user must accept the HF terms (human approval) |
| FDABench | The public part (Lite, MIT) has only multiple-choice and report-type items with fixed search results. The real PDFs and images are in `FDABench-File` (terms acceptance, license "other") |
| MMLongBench-Doc | The documents have an open license. The license of the question annotations is unverified |
| SpreadsheetBench 2 | The GitHub repository has no license file (unverified) |
| LakeQuest | The repository has no license (unverified) |
| Spider 2.0-DBT, BPI Challenge 2019 | Usable, but not necessary for the current experiments |
| KramaBench, Wide World Importers | The license is not clear |

### 1.3 Excluded
| Dataset | Reason |
|---|---|
| BIRD-Interact (Lite, Full), Mini-Interact | The gold SQL is available only by email request. You cannot download it automatically |
| Ambig-DS | Non-commercial license. The official distribution site is unverified |
| EnterpriseMem-Bench, PRACTIQ | No public distribution found |

### 1.4 Own tasks (`tasks/`)
| Task | Fact type | Number of interpretations | Use |
|---|---|---|---|
| `smoke-revenue` | Definition type | 4 | Protocol smoke test, E0 versus E1 |
| `anchor-revenue` | Anchor type (exact number, k=1) | 16 | Question strategy when the customer does not know the definition |
| `anchor-revenue-k2`, `-k4` | anchor type (number range, k=2 and k=4; k4 has submit budget 4) | 16 | candidates remain after the anchor |
| `anchor-revenue-noise` | Anchor type (report error) | 16 | When the customer number differs a little from the gold answer |

k = the number of interpretations that match the number that the customer knows. `scripts/make_anchor_variants.py` makes the variants.

## 2. How to download
```bash
python3 -I scripts/fetch_datasets.py              # all "Downloaded" datasets (about 940MB)
python3 -I scripts/fetch_datasets.py tat-dqa      # one dataset only
```
- Storage location: `data/raw/<name>/` (excluded from git). Each folder has a `MANIFEST.json` (source, revision, download time, sha256 of each file).
- Archive files stay packed. The conversion script unpacks them safely (it checks for path escape).
- Downloaded files are untrusted data. Do not run code in them (example: the `*.py` files of AmbiQT). Put the scripts that read them in `scripts/` and run them with `python3 -I`.

## 3. Rules to convert to the task format
Convert every dataset to the evalkit task format (`docs/EVALUATION.md` §2). `scripts/make_tasks.py` makes the tasks from `data/raw/` into `data/tasks/<dataset>-<original ID>-<condition>/` (excluded from git, because the tasks contain licensed data). Unpacked DBs go to `data/processed/`. `tasks/` holds only our own tasks.

```bash
python3 -I scripts/make_tasks.py bird --n 20 --seed 0        # BIRD dev, conditions O, N, D
python3 -I scripts/make_tasks.py infiagent --n 10 --seed 0   # InfiAgent-DABench, conditions O, N, D
```
- Selection is random with a fixed seed. Every task passes a self-check (the gold answer is accepted) before the script writes it. The script writes the selection and the skipped items to `data/tasks/<dataset>-selection.json`.
- BIRD: only `moderate` and `challenging` questions with evidence. 3 of the 11 dev DBs are evaluation-only (drawn with the seed, listed in the selection file). The script does not make tasks from them.
- Conditions: `O` = request + facts, no questions. `N` = request only, no questions. `D` = request only, the customer simulator knows the facts.

### 3.1 Common fields
| Task field | Meaning | Rule |
|---|---|---|
| `request` | The ambiguous customer request | The original query without the ambiguity material (definitions and constraints) |
| `sources` | Input data | One or more of `sqlite`, `csv`, `xlsx`, `pdf_pages` (page images + OCR JSON) |
| `check` | Scoring | One of the scoring types below |
| `hidden.facts` | What the customer knows | Write it as one of the fact types below |
| `hidden.fact_kind` | Fact type | `definition` or `anchor` |
| `n_interpretations` | Number of interpretation combinations that change the result | Count it from the original annotations. If you cannot count it, use `null` |
| `budget` | Question and submission budget | Default: 5 questions, 2 submissions |

### 3.2 Fact types
| Type | What the customer knows | Example | How to make it |
|---|---|---|---|
| `definition` (definition type) | The definition of a term or calculation method | "매출은 세전이다" ("Revenue is before tax") | Convert the definition and constraint fields of the original (`evidence`, `constraints`, synonym map) to natural language |
| `anchor` (anchor type) | A number in an existing report. The customer does not know the definition | "10월 매출 보고서 총액은 1,645이다" ("The total in the October revenue report is 1,645") | Aggregate the gold answer at a **coarser grain than the gold answer**. Do not use a number that exposes the gold value directly |

An anchor fact comes from the gold answer, so it is circular. Fix the aggregation rule for each task and write it in `notes` in `task.json`.

### 3.3 Scoring types
| Type | Comparison | Datasets that use it | evalkit implementation |
|---|---|---|---|
| `sql_result` | Result set of the answer SQL against the gold SQL (SQLite) | BIRD dev, own tasks | Yes |
| `exact_answer` | `@key[value]` pairs: number within half a unit of the last gold decimal, other values after strip and lower case | InfiAgent-DABench. TAT-DQA (value + unit) and DABstep (plain answer) need an adapted format | Yes (`@key[value]` only) |
| `sheet_cells` | Values in a specified cell range | SpreadsheetBench | No |
| `kg_triples` | Precision and recall against the gold triples, number of ontology violations | Text2KGBench | No |

### 3.4 Rules for each dataset
| Dataset | `request` | `sources` | `check` | `hidden.facts` | `n_interpretations` |
|---|---|---|---|---|---|
| BIRD dev | `question` (without evidence) | `sqlite` (dev DB) | `sql_result`, gold `SQL` | Definition type: `evidence`. Anchor type: a coarse aggregate of the gold result | Approximated by the number of `evidence` sentences |
| AmbiQT | Not converted (both interpretations give the same result on the Spider DBs) | | | | |
| InfiAgent-DABench | `question` (without `constraints`), keep `format` | `csv` | `exact_answer` (`common_answers`) | Definition type: `constraints` | Approximated by the number of `constraints` conditions |
| TAT-DQA | `question` | `pdf_pages` (page PNG + OCR JSON) | `exact_answer` (`answer` + `scale`) | Definition type: the unit and calculation range (`scale`, `derivation`) as a business sentence. A question without a unit has no ambiguity | 2 if there is a unit or formula, 1 if not |
| SpreadsheetBench | The instruction text | `xlsx` | `sheet_cells` | None (no ambiguity annotation) | 1 |
| DABstep dev | `question` + `guidelines` | `csv`, documents | `exact_answer` | None | 1 |
| BLADE | The research question | `csv` | The original LLM evaluator | Not applicable | Not applicable |
| Text2KGBench | Ontology + sentence | Text, ontology | `kg_triples` | Not applicable (for ontology pack evaluation, not CFC) | Not applicable |

## 4. Priority
1. `anchor-revenue` (own): the question strategy for the anchor type. It can run now.
2. **BIRD dev**: converted (`scripts/make_tasks.py bird`). Definition type now. The anchor type needs candidate interpretations, which BIRD does not annotate.
3. **InfiAgent-DABench**: local CSV, converted (`scripts/make_tasks.py infiagent`, `exact_answer`).
4. **TAT-DQA**: document and vision. `exact_answer` + page image input.
5. SpreadsheetBench, Text2KGBench: Excel operations and ontology pack evaluation. Do them after you build the scorers.
