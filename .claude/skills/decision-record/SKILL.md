---
name: decision-record
description: Record a design decision or an unconfirmed assumption for the FDE harness as a short ADR in internal/decisions/. Use when the user and Claude settle a design choice, reject an alternative, or proceed on an assumption that was not confirmed.
---

# Decision Record

Record decisions and assumptions as `internal/decisions/NNNN-<slug>.md`. The number is the current maximum + 1.

## Format
```markdown
---
status: accepted | assumed | deprecated | superseded
updated: YYYY-MM-DD
audience: internal
---
# NNNN. <title>
- Scope: core | adapter | domain pack | eval | P1–P5

## Context
<Why the decision was needed. 2-4 sentences.>

## Candidates
| Candidate | Basis | Confidence |
|---|---|---|

## Decision
<One sentence.>

## Consequences and review conditions
<What change makes us look at this again.>
```

## Rules
- Name and front matter: `docs/RULES.md` §1.2, §1.3.
- Set the status to `assumed` for a choice the user did not confirm. (Same principle as the uncertainty ledger.)
- Add a source (paper or doc link) to each basis. Mark numbers that nobody reproduced as "(unreproduced)".
- If you reverse an existing decision, create a new document and set the old document's status to `superseded`.
