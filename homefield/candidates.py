"""Steps 1 and 2 of the procedure (internal design harness-core, revision 4, step B2).

Step 1, PROFILE: the model names the tables and columns that the request needs; the code reads facts
about them. Step 2, CANDIDATES: the model names the points of the request that have more than one
reading, the terms that the data does not settle, and at most K queries. The code runs every query
and groups the queries that give the same result into one class."""

import sqlite3
from pathlib import Path

from homefield import model, sources
from homefield.events import EventLog

K = 4  # proposal with no basis; set from development data

SELECT = """A customer sent this request about their database:

{request}

Schema:
{schema}

Which tables and columns does a query for this request need? Include the columns for joins and filters.
Reply with one JSON object and nothing else:
{{"columns": {{"<table>": ["<column>", ...], ...}}}}"""

PROPOSE = """A customer sent this request about their SQLite database:

{request}

Schema:
{schema}

Facts about the columns that look relevant:
{profile}

Do three things.
1. Find the points of the request that have more than one reasonable reading. Give each point its readings.
2. List each phrase of the request that the query turns into a filter, a calculation, or an output column,
   when no column name and no stored value in the facts above states it literally (for example a business
   word, a word for a formula such as a percentage or a profit, a word for an output such as "full name").
   Use the exact words of the request, the whole phrase. Do not list column names. Do not guess silently.
3. Write at most {k} SELECT queries that cover the different readings. Each query states which reading it
   uses at each point (the number of the reading, from 1).
If the request has one reading only, give no points and one query.
Reply with one JSON object and nothing else:
{{"points": [{{"id": "p1", "text": "<what is unclear>", "readings": ["<reading 1>", "<reading 2>"]}}],
 "unsettled_terms": [{{"term": "<phrase of the request>", "why": "<what is missing>"}}],
 "queries": [{{"sql": "<one SELECT>", "readings": {{"p1": 1}}}}]}}"""

REPAIR = """This query for the request below fails on the SQLite database.

Request: {request}
Query: {sql}
Error: {error}

Schema:
{schema}

Keep the meaning and repair the query. Reply with one JSON object and nothing else: {{"sql": "<one SELECT>"}}"""


class StepFailed(Exception):
    """Step 1 or step 2 gave nothing that the code can use. The caller falls back (gate G7)."""


def text(value, what: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{what} must be a non-empty string")
    return value.strip()


def check_selection(obj, tables: dict) -> dict[str, list[str]]:
    """Keep the tables and columns that exist (names match without case)."""
    real = {t.lower(): t for t in tables}
    out = {}
    for table, columns in obj["columns"].items():
        if table.lower() not in real or not isinstance(columns, list):
            continue
        table = real[table.lower()]
        names = {c["name"].lower(): c["name"] for c in tables[table]["columns"]}
        found = [names[c.lower()] for c in columns if isinstance(c, str) and c.lower() in names]
        if found:
            out[table] = list(dict.fromkeys(out.get(table, []) + found))
    if not out:
        raise ValueError("no table or column of the schema is named")
    return out


def check_proposal(obj, k: int = K, request: str | None = None) -> dict:
    """With a request, keep only the unsettled terms that occur in it (the customer knows its own words)."""
    points = []
    for p in obj.get("points") or []:
        readings = [text(r, "a reading") for r in p["readings"]]
        if len(readings) < 2:
            raise ValueError(f"point {p.get('id')!r} needs two or more readings")
        points.append(
            {"id": text(p["id"], "a point id"), "text": text(p["text"], "a point text"), "readings": readings}
        )
    sizes = {p["id"]: len(p["readings"]) for p in points}
    if len(sizes) != len(points):
        raise ValueError("point ids must differ")
    terms = {}
    for t in obj.get("unsettled_terms") or []:
        term = text(t["term"], "a term")
        if request is None or term.lower() in request.lower():
            terms.setdefault(term.lower(), {"term": term, "why": str(t.get("why") or "")})
    terms = list(terms.values())
    queries = []
    for q in (obj.get("queries") or [])[:k]:
        chosen = q.get("readings") or {}
        if set(chosen) != set(sizes):
            raise ValueError("each query must give one reading for each point, and only for the points listed")
        for point, n in chosen.items():
            if not isinstance(n, int) or isinstance(n, bool) or not 1 <= n <= sizes[point]:
                raise ValueError(f"reading {n!r} of point {point!r} is not a number from 1 to {sizes[point]}")
        queries.append({"sql": text(q["sql"], "a query"), "readings": dict(chosen)})
    if not queries:
        raise ValueError("no query")
    return {"points": points, "unsettled_terms": terms, "queries": queries}


def execute(db: Path, queries: list[dict], repair=None) -> list[dict]:
    """Run every query. A query with an error goes to repair(query, error) once. Each query gets
    "error" (text or None) and "result_class" (id or None). Returns the classes in order of first
    appearance: [{"result_class", "queries": [index, ...], "rows"}]."""
    classes = {}
    for i, q in enumerate(queries):
        q["error"], q["result_class"] = None, None
        for attempt in (1, 2):
            try:
                rows = sources.run_select(db, q["sql"])
            except (sqlite3.Error, sqlite3.Warning) as e:
                q["error"] = str(e)
                fixed = repair(q, q["error"]) if repair and attempt == 1 else None
                if not fixed:
                    break
                q["sql"] = fixed
                continue
            q["error"], q["result_class"] = None, sources.class_id(rows)
            classes.setdefault(q["result_class"], {"result_class": q["result_class"], "queries": [], "rows": rows})
            classes[q["result_class"]]["queries"].append(i)
            break
    return list(classes.values())


def run(request: str, db: Path, complete=model.complete, events: EventLog | None = None, k: int = K) -> dict:
    """Steps 1 and 2 for one request. Returns {"points", "unsettled_terms", "queries", "classes"}.
    Raises StepFailed when the model gives no usable reply or no query runs."""
    tables = sources.schema(db)
    schema = sources.schema_text(tables)
    try:
        wanted = model.ask_json(
            [{"role": "user", "content": SELECT.format(request=request, schema=schema)}],
            lambda obj: check_selection(obj, tables),
            complete,
        )
    except ValueError as e:
        raise StepFailed(f"profile: {e}") from e
    prof = sources.profile(db, wanted)
    if events:
        events.append("profile.done", columns=wanted)
    try:
        prompt = PROPOSE.format(request=request, schema=schema, profile=sources.profile_text(prof), k=k)
        proposal = model.ask_json(
            [{"role": "user", "content": prompt}], lambda obj: check_proposal(obj, k, request), complete
        )
    except ValueError as e:
        raise StepFailed(f"candidates: {e}") from e

    def repair(query, error):
        prompt = REPAIR.format(request=request, sql=query["sql"], error=error, schema=schema)
        try:
            return model.ask_json(
                [{"role": "user", "content": prompt}], lambda obj: text(obj["sql"], "a query"), complete
            )
        except ValueError:
            return None

    classes = execute(db, proposal["queries"], repair)
    if events:
        events.append(
            "candidates.done",
            points=proposal["points"],
            unsettled_terms=proposal["unsettled_terms"],
            queries=proposal["queries"],
            classes=[
                {"result_class": c["result_class"], "queries": c["queries"], "rows": len(c["rows"])} for c in classes
            ],
        )
    if not classes:
        raise StepFailed("candidates: no query runs")
    return {**proposal, "classes": classes}
