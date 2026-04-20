"""
Full re-ingestion of the exocortex export into Solr.

Steps:
  1. DELETE */*   (wipe the core)
  2. Walk each source folder (macbook-work, macbook-personal, atpoc-sandbox, atpoc-secureapi)
  3. Emit docs for each: sessions (.md), project docs (.md), summary rows, insights (.html)
  4. Batched POST to /update, final commit

    uv run python ingest.py                       # full re-ingestion
    uv run python ingest.py --dry-run             # build docs but don't post
    uv run python ingest.py --source macbook-work # limit to one source
    uv run python ingest.py --no-delete           # skip the initial wipe
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import requests
from selectolax.parser import HTMLParser

SOLR_URL = os.environ.get("SOLR_URL", "http://localhost:8983/solr/exocortex")
EXPORT_ROOT = Path(os.environ.get("EXPORT_ROOT", "~/Documents/exocortex/export")).expanduser()

SOURCES = ["macbook-work", "macbook-personal", "atpoc-sandbox", "atpoc-secureapi"]
BATCH_SIZE = 500


# ---------- helpers ----------

def iso(dt_str: str | None) -> str | None:
    """'2026-04-15 20:33' -> '2026-04-15T20:33:00Z'. None/'' -> None."""
    if not dt_str:
        return None
    s = dt_str.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            continue
    return None


def duration_to_seconds(d: str | None) -> int | None:
    """'2h 6m' -> 7560, '4m' -> 240, '30s' -> 30. None/'' -> None."""
    if not d:
        return None
    total = 0
    matched = False
    for num, unit in re.findall(r"(\d+)\s*([hms])", d):
        matched = True
        n = int(num)
        total += n * {"h": 3600, "m": 60, "s": 1}[unit]
    return total if matched else None


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        print(f"  ! skip {path}: {e}", file=sys.stderr)
        return ""


def strip_html(html: str) -> str:
    try:
        return HTMLParser(html).text(separator=" ", strip=True)
    except Exception:
        return html


def parse_session_md(text: str) -> tuple[dict, str]:
    """Extract header fields ('**Key**: value') and return (header_dict, body)."""
    lines = text.splitlines()
    header: dict[str, str] = {}
    body_start = 0
    for i, line in enumerate(lines):
        if line.strip() == "---":
            body_start = i + 1
            break
        m = re.match(r"\*\*([^*]+)\*\*:\s*(.*)", line)
        if m:
            header[m.group(1).strip().lower()] = m.group(2).strip()
    body = "\n".join(lines[body_start:]).strip() if body_start else text
    return header, body


# ---------- doc builders ----------

def build_session_doc(source: str, md_path: Path, project: str, session_id: str, summary_row: dict | None) -> dict:
    text = read_text(md_path)
    header, body = parse_session_md(text)

    # Prefer summary.csv fields when available; fall back to header parsed from md.
    s = summary_row or {}
    topic = s.get("topic") or header.get("topic") or ""
    started = iso(s.get("started")) or iso(header.get("started"))
    ended = iso(s.get("ended"))
    duration = s.get("duration") or header.get("duration")
    u = int(s["user_turns"]) if s.get("user_turns") else None
    a = int(s["assistant_turns"]) if s.get("assistant_turns") else None
    total = (u or 0) + (a or 0) if (u is not None or a is not None) else None
    return {
        "id": f"{source}:session:{project}:{session_id}",
        "doc_type": "session",
        "source": source,
        "project": project,
        "path": str(md_path),
        "title": (topic[:200] if topic else f"Session {session_id[:8]}"),
        "topic": topic,
        "body": body,
        "session_id": session_id,
        "is_agent": (s.get("is_agent", "").lower() == "true") if s.get("is_agent") is not None else None,
        "user_turns": u,
        "assistant_turns": a,
        "total_turns": total,
        "duration": duration,
        "duration_seconds": duration_to_seconds(duration),
        "size_kb": float(s["size_kb"]) if s.get("size_kb") else None,
        "started": started,
        "ended": ended,
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def build_project_doc(source: str, doc_path: Path, project: str) -> dict:
    text = read_text(doc_path)
    rel = doc_path.relative_to(EXPORT_ROOT / source / "projects" / project / "docs")
    first_line = next((l for l in text.splitlines() if l.strip()), doc_path.name)
    title = first_line.lstrip("# ").strip()[:200] or str(rel)
    mtime = datetime.fromtimestamp(doc_path.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "id": f"{source}:project_doc:{project}:{rel}",
        "doc_type": "project_doc",
        "source": source,
        "project": project,
        "path": str(doc_path),
        "title": title,
        "body": text,
        "started": mtime,
        "updated": mtime,
    }


def build_summary_doc(source: str, row: dict) -> dict:
    sid = row.get("session_id", "")
    duration = row.get("duration")
    u = int(row["user_turns"]) if row.get("user_turns") else None
    a = int(row["assistant_turns"]) if row.get("assistant_turns") else None
    total = (u or 0) + (a or 0) if (u is not None or a is not None) else None
    return {
        "id": f"{source}:summary:{sid}",
        "doc_type": "summary_row",
        "source": source,
        "project": row.get("project") or "",
        "title": (row.get("topic") or "")[:200],
        "topic": row.get("topic") or "",
        "body": row.get("topic") or "",
        "session_id": sid,
        "is_agent": row.get("is_agent", "").lower() == "true",
        "user_turns": u,
        "assistant_turns": a,
        "total_turns": total,
        "duration": duration,
        "duration_seconds": duration_to_seconds(duration),
        "size_kb": float(row["size_kb"]) if row.get("size_kb") else None,
        "started": iso(row.get("started")),
        "ended": iso(row.get("ended")),
        "path": row.get("source_file") or "",
    }


def build_insight_doc(source: str, html_path: Path) -> dict:
    raw = read_text(html_path)
    body = strip_html(raw)
    mtime = datetime.fromtimestamp(html_path.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "id": f"{source}:insight:{html_path.name}",
        "doc_type": "insight",
        "source": source,
        "path": str(html_path),
        "title": html_path.stem,
        "body": body,
        "started": mtime,
        "updated": mtime,
    }


# ---------- walkers ----------

def load_summary(source_dir: Path) -> dict[str, dict]:
    csv_path = source_dir / "summary.csv"
    if not csv_path.exists():
        return {}
    with csv_path.open(newline="", encoding="utf-8") as f:
        return {row["session_id"]: row for row in csv.DictReader(f) if row.get("session_id")}


def walk_source(source: str) -> Iterator[dict]:
    src_dir = EXPORT_ROOT / source
    if not src_dir.exists():
        print(f"  ! source missing: {src_dir}", file=sys.stderr)
        return

    summary_by_sid = load_summary(src_dir)
    covered_sids: set[str] = set()

    # 1. session markdown + matching summary row
    projects_dir = src_dir / "projects"
    if projects_dir.exists():
        for project_dir in sorted(projects_dir.iterdir()):
            if not project_dir.is_dir():
                continue
            project = project_dir.name
            sessions_dir = project_dir / "sessions"
            if sessions_dir.exists():
                for md in sorted(sessions_dir.glob("*.md")):
                    sid = md.stem
                    covered_sids.add(sid)
                    yield build_session_doc(source, md, project, sid, summary_by_sid.get(sid))
            docs_dir = project_dir / "docs"
            if docs_dir.exists():
                for doc in sorted(docs_dir.rglob("*.md")):
                    yield build_project_doc(source, doc, project)

    # 2. summary rows without a session markdown
    for sid, row in summary_by_sid.items():
        if sid not in covered_sids:
            yield build_summary_doc(source, row)

    # 3. insight HTMLs
    insights_dir = src_dir / "insights"
    if insights_dir.exists():
        for html in sorted(insights_dir.glob("*.html")):
            yield build_insight_doc(source, html)


# ---------- solr I/O ----------

def solr_delete_all() -> None:
    r = requests.post(
        f"{SOLR_URL}/update?commit=true",
        json={"delete": {"query": "*:*"}},
        timeout=30,
    )
    r.raise_for_status()
    print("  - deleted all docs")


def solr_post(batch: list[dict]) -> None:
    # Strip None values so Solr doesn't choke on typed fields
    cleaned = [{k: v for k, v in d.items() if v is not None and v != ""} for d in batch]
    r = requests.post(f"{SOLR_URL}/update?commit=false", json=cleaned, timeout=60)
    if not r.ok:
        print(r.text[:2000], file=sys.stderr)
        r.raise_for_status()


def solr_commit() -> None:
    r = requests.get(f"{SOLR_URL}/update?commit=true", timeout=30)
    r.raise_for_status()


def solr_numdocs_by_type() -> dict[str, int]:
    r = requests.get(
        f"{SOLR_URL}/select",
        params={"q": "*:*", "rows": 0, "facet": "true", "facet.field": "doc_type"},
        timeout=10,
    )
    r.raise_for_status()
    counts = r.json()["facet_counts"]["facet_fields"]["doc_type"]
    return dict(zip(counts[::2], counts[1::2]))


# ---------- main ----------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="build docs but don't post to Solr")
    ap.add_argument("--no-delete", action="store_true", help="skip the initial wipe")
    ap.add_argument("--source", choices=SOURCES, help="limit to one source")
    args = ap.parse_args()

    sources = [args.source] if args.source else SOURCES
    print(f"Ingesting from {EXPORT_ROOT} -> {SOLR_URL}")
    print(f"Sources: {', '.join(sources)}")

    if not args.dry_run and not args.no_delete:
        solr_delete_all()

    batch: list[dict] = []
    total = 0
    by_type: dict[str, int] = {}

    for source in sources:
        print(f"[{source}]")
        for doc in walk_source(source):
            by_type[doc["doc_type"]] = by_type.get(doc["doc_type"], 0) + 1
            total += 1
            if args.dry_run:
                continue
            batch.append(doc)
            if len(batch) >= BATCH_SIZE:
                solr_post(batch)
                batch.clear()

    if not args.dry_run and batch:
        solr_post(batch)
    if not args.dry_run:
        solr_commit()

    print(f"\nDone. {total} docs.")
    for dt, n in sorted(by_type.items()):
        print(f"  {dt}: {n}")

    if not args.dry_run:
        print("\nSolr reports:")
        for dt, n in sorted(solr_numdocs_by_type().items()):
            print(f"  {dt}: {n}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
