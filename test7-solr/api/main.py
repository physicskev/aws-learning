"""
FastAPI proxy over the local Solr `exocortex` core.

Endpoints:
    GET /api/search     — query with facets + highlighting
    GET /api/mlt/{id}   — more like this
    GET /api/suggest    — autocomplete
    GET /api/doc/{id}   — fetch full doc
    GET /api/health     — solr up? numDocs?
    GET /               — serves ui/index.html
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

SOLR_URL = os.environ.get("SOLR_URL", "http://localhost:8983/solr/exocortex")
UI_DIR = Path(__file__).resolve().parent.parent / "ui"

app = FastAPI(title="test7-solr")


# ---------- solr helpers ----------

def solr_get(path: str, params: dict[str, Any]) -> dict:
    try:
        r = requests.get(f"{SOLR_URL}{path}", params=params, timeout=15)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Solr error: {e}") from e


# ---------- endpoints ----------

@app.get("/api/health")
def health() -> dict:
    try:
        ping = requests.get(f"{SOLR_URL}/admin/ping", timeout=3).json()
        count = requests.get(
            f"{SOLR_URL}/select", params={"q": "*:*", "rows": 0}, timeout=5
        ).json()
        return {
            "solr": "up" if ping.get("status") == "OK" else "down",
            "core": SOLR_URL.rsplit("/", 1)[-1],
            "numDocs": count["response"]["numFound"],
        }
    except requests.RequestException as e:
        return JSONResponse({"solr": "down", "error": str(e)}, status_code=503)


SORT_OPTIONS = {
    "relevance": "score desc",
    "started_desc": "started desc",
    "started_asc": "started asc",
    "turns_desc": "user_turns desc",
    "duration_desc": "duration_seconds desc",
    "size_desc": "size_kb desc",
}


@app.get("/api/search")
def search(
    q: str = Query("*:*"),
    start: int = 0,
    rows: int = 20,
    sort: str = "relevance",
    source: list[str] = Query(default=[]),
    project: list[str] = Query(default=[]),
    doc_type: list[str] = Query(default=[]),
    is_agent: str | None = None,       # "true" | "false" | None
    date_from: str | None = None,      # ISO-8601 or Solr date math (NOW-30DAYS)
    date_to: str | None = None,
    min_turns: int | None = None,
    min_duration_seconds: int | None = None,
) -> dict:
    # Build filter queries
    fqs: list[str] = []
    if source:
        fqs.append(" OR ".join(f'source:"{s}"' for s in source))
    if project:
        fqs.append(" OR ".join(f'project:"{p}"' for p in project))
    if doc_type:
        fqs.append(" OR ".join(f'doc_type:"{d}"' for d in doc_type))
    if is_agent in ("true", "false"):
        fqs.append(f"is_agent:{is_agent}")
    if date_from or date_to:
        f = date_from or "*"
        t = date_to or "*"
        fqs.append(f"started:[{f} TO {t}]")
    if min_turns is not None:
        # 1 message = 1 turn (user OR assistant). total_turns is user+assistant.
        fqs.append(f"total_turns:[{min_turns} TO *]")
    if min_duration_seconds is not None:
        fqs.append(f"duration_seconds:[{min_duration_seconds} TO *]")

    # sort: score requires edismax; Solr expects "score desc" not just "score"
    sort_clause = SORT_OPTIONS.get(sort, SORT_OPTIONS["relevance"])

    # Title/topic boost + phrase boost via edismax
    params: dict[str, Any] = {
        "q": q,
        "defType": "edismax",
        "qf": "title^4 topic^3 body^1",
        "pf": "body^2",
        "ps": 2,
        "sort": sort_clause,
        "start": start,
        "rows": rows,
        "fl": "id,doc_type,source,project,title,topic,session_id,started,ended,duration,is_agent,user_turns,assistant_turns,total_turns,duration_seconds,size_kb,path,score",
        "hl": "true",
        "hl.fl": "body",
        "hl.fragsize": 220,
        "hl.snippets": 3,
        "hl.method": "unified",
        "facet": "true",
        "facet.field": ["source", "project", "doc_type", "is_agent"],
        "facet.limit": 40,
        # mincount scoped per-field so the histogram keeps empty months for visual continuity
        "f.source.facet.mincount": 1,
        "f.project.facet.mincount": 1,
        "f.doc_type.facet.mincount": 1,
        "f.is_agent.facet.mincount": 1,
        "facet.range": "started",
        "facet.range.start": "NOW/YEAR-3YEARS",
        "facet.range.end": "NOW/MONTH+1MONTH",
        "facet.range.gap": "+1MONTH",
        "stats": "true",
        "stats.field": ["user_turns", "assistant_turns", "total_turns", "duration_seconds", "size_kb", "started"],
        "spellcheck": "true",
        "spellcheck.collate": "true",
    }
    if fqs:
        params["fq"] = fqs

    data = solr_get("/select", params)
    resp = data.get("response", {})
    highlighting = data.get("highlighting", {})

    # Merge highlights into each doc for UI convenience
    docs = []
    for d in resp.get("docs", []):
        d["_highlights"] = highlighting.get(d["id"], {}).get("body", [])
        docs.append(d)

    # Shape facets to something easier for the UI
    ff = data.get("facet_counts", {}).get("facet_fields", {})
    facets = {
        name: [{"value": pairs[i], "count": pairs[i + 1]} for i in range(0, len(pairs), 2)]
        for name, pairs in ff.items()
    }
    fr = data.get("facet_counts", {}).get("facet_ranges", {}).get("started", {})
    date_buckets = [
        {"value": fr["counts"][i], "count": fr["counts"][i + 1]}
        for i in range(0, len(fr.get("counts", [])), 2)
    ]

    # Spellcheck — extract collation if any
    suggestion = None
    sc = data.get("spellcheck", {})
    if sc:
        collations = sc.get("collations") or []
        for i in range(1, len(collations), 2):
            entry = collations[i]
            if isinstance(entry, dict) and entry.get("collationQuery"):
                suggestion = entry["collationQuery"]
                break

    # Stats — sums and min/max for the current result set (post-filter)
    stats_raw = data.get("stats", {}).get("stats_fields", {}) or {}
    stats = {
        field: {
            "sum": stats_raw.get(field, {}).get("sum"),
            "count": stats_raw.get(field, {}).get("count"),
            "mean": stats_raw.get(field, {}).get("mean"),
            "min": stats_raw.get(field, {}).get("min"),
            "max": stats_raw.get(field, {}).get("max"),
        }
        for field in ("user_turns", "assistant_turns", "total_turns", "duration_seconds", "size_kb", "started")
    }

    return {
        "numFound": resp.get("numFound", 0),
        "start": resp.get("start", 0),
        "rows": rows,
        "qtime": data.get("responseHeader", {}).get("QTime"),
        "docs": docs,
        "facets": facets,
        "date_facets": date_buckets,
        "stats": stats,
        "suggestion": suggestion,
    }


@app.get("/api/mlt/{doc_id:path}")
def mlt(doc_id: str, rows: int = 10) -> dict:
    # Fetch the seed doc for "Based on" display
    seed = solr_get("/select", {"q": f'id:"{doc_id}"', "rows": 1})
    match_docs = seed.get("response", {}).get("docs", [])
    # Use the MLT query parser — works with the default configset (no /mlt handler needed)
    data = solr_get(
        "/select",
        {
            "q": f'{{!mlt qf="body title" mintf=2 mindf=2}}{doc_id}',
            "rows": rows,
            "fl": "id,doc_type,source,project,title,started",
        },
    )
    # The seed doc itself is returned first by the MLT parser — filter it out.
    similar = [d for d in data.get("response", {}).get("docs", []) if d.get("id") != doc_id]
    return {"match": match_docs[0] if match_docs else None, "similar": similar}


@app.get("/api/suggest")
def suggest(q: str, rows: int = 8) -> dict:
    # No custom suggester configured; use terms-style prefix query on title.
    data = solr_get(
        "/select",
        {
            "q": f'title:{q}*',
            "rows": rows,
            "fl": "id,title",
        },
    )
    return {
        "suggestions": [
            {"id": d["id"], "title": d.get("title", "")}
            for d in data.get("response", {}).get("docs", [])
        ]
    }


@app.get("/api/doc/{doc_id:path}")
def get_doc(doc_id: str) -> dict:
    data = solr_get("/select", {"q": f'id:"{doc_id}"', "rows": 1})
    docs = data.get("response", {}).get("docs", [])
    if not docs:
        raise HTTPException(status_code=404, detail="not found")
    return docs[0]


# ---------- static UI ----------

if UI_DIR.exists():
    @app.get("/")
    def root() -> FileResponse:
        return FileResponse(UI_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=str(UI_DIR)), name="static")

    @app.get("/{filename}")
    def ui_file(filename: str) -> FileResponse:
        p = UI_DIR / filename
        if p.is_file():
            return FileResponse(p)
        raise HTTPException(status_code=404)
