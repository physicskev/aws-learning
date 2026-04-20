"""
Apply the exocortex schema to the Solr `exocortex` core.

Idempotent: re-running only adds missing fields, never duplicates.
Run after `docker compose up -d` and before `ingest.py`.

    uv run python setup_schema.py
"""
from __future__ import annotations

import os
import sys

import requests

SOLR_URL = os.environ.get("SOLR_URL", "http://localhost:8983/solr/exocortex")

# Field definitions. Each entry becomes a managed-schema field.
# text_en = stemming + english stopwords, good for natural-language body
# string  = exact match, for facets/filters
# pdate, pint, pfloat, boolean = typed, docValues on by default
FIELDS: list[dict] = [
    # identity / routing
    {"name": "doc_type",        "type": "string",  "indexed": True, "stored": True, "docValues": True},
    {"name": "source",          "type": "string",  "indexed": True, "stored": True, "docValues": True},
    {"name": "project",         "type": "string",  "indexed": True, "stored": True, "docValues": True},
    {"name": "path",            "type": "string",  "indexed": False, "stored": True},

    # content
    {"name": "title",           "type": "text_en", "indexed": True, "stored": True},
    {"name": "body",            "type": "text_en", "indexed": True, "stored": True, "termVectors": True, "termPositions": True, "termOffsets": True},

    # timestamps
    {"name": "started",         "type": "pdate",   "indexed": True, "stored": True, "docValues": True},
    {"name": "ended",           "type": "pdate",   "indexed": True, "stored": True, "docValues": True},
    {"name": "updated",         "type": "pdate",   "indexed": True, "stored": True, "docValues": True},

    # session-specific
    {"name": "session_id",      "type": "string",  "indexed": True, "stored": True, "docValues": True},
    {"name": "is_agent",        "type": "boolean", "indexed": True, "stored": True, "docValues": True},
    {"name": "topic",           "type": "text_en", "indexed": True, "stored": True},
    {"name": "user_turns",      "type": "pint",    "indexed": True, "stored": True, "docValues": True},
    {"name": "assistant_turns", "type": "pint",    "indexed": True, "stored": True, "docValues": True},
    # total_turns = user_turns + assistant_turns. Each individual message is 1 "turn".
    # Filtering on this matches the user's mental model better than user_turns alone.
    {"name": "total_turns",     "type": "pint",    "indexed": True, "stored": True, "docValues": True},

    # Per-session timeline breakdown computed from the raw session jsonl.
    # See ingest/timeline.py. Gaps > 5 min = idle. Real user msgs drive user_seconds.
    {"name": "user_seconds",      "type": "pint", "indexed": True, "stored": True, "docValues": True},
    {"name": "assistant_seconds", "type": "pint", "indexed": True, "stored": True, "docValues": True},
    {"name": "idle_seconds",      "type": "pint", "indexed": True, "stored": True, "docValues": True},
    {"name": "active_seconds",    "type": "pint", "indexed": True, "stored": True, "docValues": True},
    {"name": "duration",        "type": "string",  "indexed": False, "stored": True},
    {"name": "duration_seconds","type": "pint",    "indexed": True, "stored": True, "docValues": True},
    {"name": "size_kb",         "type": "pfloat",  "indexed": True, "stored": True, "docValues": True},
]

# Everything searchable flows into `text` as the catch-all default field.
COPY_FIELDS: list[dict] = [
    {"source": "title", "dest": "text"},
    {"source": "topic", "dest": "text"},
    {"source": "body",  "dest": "text"},
]


def get_existing_fields() -> set[str]:
    r = requests.get(f"{SOLR_URL}/schema/fields", timeout=10)
    r.raise_for_status()
    return {f["name"] for f in r.json()["fields"]}


def get_existing_copyfields() -> set[tuple[str, str]]:
    r = requests.get(f"{SOLR_URL}/schema/copyfields", timeout=10)
    r.raise_for_status()
    return {(c["source"], c["dest"]) for c in r.json()["copyFields"]}


def ensure_text_field() -> None:
    """`text` is the catch-all search field. Default _default configset already has
    a `_text_` field; we define our own `text` for clarity and to avoid the
    schemaless `_text_` defaults."""
    fields = get_existing_fields()
    if "text" in fields:
        return
    payload = {"add-field": {"name": "text", "type": "text_en", "indexed": True, "stored": False, "multiValued": True}}
    r = requests.post(f"{SOLR_URL}/schema", json=payload, timeout=10)
    r.raise_for_status()
    print("  + added catch-all field: text")


def ensure_fields() -> None:
    existing = get_existing_fields()
    to_add = [f for f in FIELDS if f["name"] not in existing]
    if not to_add:
        print("  = all fields already present")
        return
    payload = {"add-field": to_add}
    r = requests.post(f"{SOLR_URL}/schema", json=payload, timeout=15)
    r.raise_for_status()
    for f in to_add:
        print(f"  + added field: {f['name']} ({f['type']})")


def ensure_copyfields() -> None:
    existing = get_existing_copyfields()
    to_add = [c for c in COPY_FIELDS if (c["source"], c["dest"]) not in existing]
    if not to_add:
        print("  = all copyFields already present")
        return
    payload = {"add-copy-field": to_add}
    r = requests.post(f"{SOLR_URL}/schema", json=payload, timeout=10)
    r.raise_for_status()
    for c in to_add:
        print(f"  + added copyField: {c['source']} -> {c['dest']}")


def main() -> int:
    print(f"Applying schema to {SOLR_URL}")
    try:
        r = requests.get(f"{SOLR_URL}/admin/ping", timeout=5)
        r.raise_for_status()
    except Exception as e:
        print(f"Solr not reachable at {SOLR_URL}: {e}", file=sys.stderr)
        return 1

    ensure_text_field()
    ensure_fields()
    ensure_copyfields()
    print("Schema applied.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
