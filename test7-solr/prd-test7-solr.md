# PRD — test7-solr: Solr-powered search over the exocortex export

## Vision

A local, single-user search and investigation tool over a personal archive of Claude Code conversation history (the "exocortex" export). The product should let the user surface patterns, find specific conversations, quantify time and effort spent, and investigate how their use of Claude Code has evolved across machines, projects, and time.

Primary purpose is twofold:
1. **Experimentation.** Relearn Apache Solr and exercise its features (faceting, highlighting, MLT, stats, date ranges, spell-check).
2. **Utility.** Be genuinely useful for answering questions about the user's own past work — not just a toy.

The deployment target today is local Docker. The product should be portable to a hosted Solr (EC2, SolrCloud, etc.) by changing a single environment variable.

## Goals

- Index the entire export — no content is dropped.
- Support periodic full re-ingestion (the export is regenerated periodically).
- Offer both keyword search AND investigation/analytics (aggregate stats, time series, faceted drilldowns).
- Keep the stack simple: one Solr node, one FastAPI service, one vanilla HTML/JS UI.
- Be bookmarkable — any view must be reproducible from a URL.

## Source data

Root: `~/Documents/exocortex/export/` (override via `EXPORT_ROOT`).

Four top-level **source** folders, each representing a machine or context:

- `macbook-work/`
- `macbook-personal/`
- `atpoc-sandbox/`
- `atpoc-secureapi/`

Each source contains:

| Path | Shape |
|------|-------|
| `history.jsonl` | Per-command raw log. **Not indexed** — too noisy (short `/help`, `/login` commands dominate). Kept in the export for reference. |
| `summary.csv` | Header row + one per session: `session_id, project, is_agent, topic, user_turns, assistant_turns, duration, size_kb, started, ended, source_file` |
| `insights/*.html` | Generated HTML reports (small count, one or a few per source) |
| `projects/<project>/docs/**/*.md` | Project-level docs such as `CLAUDE.md`, `learnings.md` |
| `projects/<project>/sessions/<session_id>.md` | Per-session markdown transcripts |
| `projects/<project>/sessions/<session_id>.jsonl` | Occasional raw session jsonl (not indexed separately) |

Observed totals at time of writing: 933 indexable items split as 635 session markdowns, 167 orphan summary rows (no matching .md), 125 project docs, 6 insights.

## User Stories

1. **Recall**: "When did I first work on Solr?" → keyword search, oldest-first.
2. **Time budgeting**: "How many hours did I sink into project X?" → facet on project, read total hours from the stats card.
3. **Pattern discovery**: "When was my activity highest?" → view the monthly histogram.
4. **Deep dive retrieval**: "Show me only long AWS sessions" → search `aws`, min turns 30, sort by most turns.
5. **Cross-machine comparison**: "Did I use Claude differently at work vs personally?" → facet on source.
6. **Related conversation lookup**: "What other sessions are like this one?" → More Like This from any hit.
7. **Agent vs interactive**: "How much time is the agent doing things unattended?" → facet on is_agent.
8. **Bookmarkable investigation**: "Save and revisit a specific query + filter combination" → URL state sync.
9. **Readable review**: "Open a session and actually read it" → modal with rendered markdown.
10. **Me vs bot effort split**: "How much of my Claude time was ME engaged vs the model working unattended?" → read the Active / User / Agent / Idle breakdown on the stats card.

## Features

### F1 — Full re-ingestion from the export

**Description:** A script walks the export root and pushes every item to Solr, wiping the core first. Idempotent — same input always produces the same document IDs.

**Acceptance Criteria:**
- [ ] Running the ingest wipes the core (`delete *:*`) then reloads.
- [ ] Produces exactly 4 `doc_type` values: `session`, `project_doc`, `summary_row`, `insight`.
- [ ] `history.jsonl` is **not** indexed (too noisy — dominated by short slash-commands).
- [ ] Supports CLI flags: `--dry-run`, `--no-delete`, `--source <name>`.
- [ ] All four sources are walked by default.
- [ ] Session markdown files are joined with their matching `summary.csv` row (when present) for metadata enrichment.
- [ ] `summary_row` docs are created only for session IDs not already covered by a markdown file — no double counting.
- [ ] Re-running the ingest twice yields the same `numDocs` (no duplicates, no drift).

### F2 — Schema bootstrap via Schema API

**Description:** Applying the schema is a separate, idempotent step that uses Solr's Schema API rather than shipping a configset in git. Starts from Solr's built-in `_default` configset.

**Acceptance Criteria:**
- [ ] Running schema setup against a fresh core adds all required fields and copy fields.
- [ ] Running it again is a no-op (detects existing fields and skips them).
- [ ] Works against any Solr 9 `exocortex` core bootstrapped from `_default`.

### F3 — Keyword search with highlighting

**Description:** Full-text search across title, topic, and body with edismax, phrase boosting, and unified highlighter snippets.

**Acceptance Criteria:**
- [ ] Bare-keyword queries match against a catch-all `text` field populated from `title`, `topic`, and `body`.
- [ ] `title` is boosted ~4×, `topic` ~3×, `body` 1×.
- [ ] Phrase proximity bonus applied to body with slop ≤ 2.
- [ ] Response includes up to 3 highlighted snippets per doc, each ~220 chars, wrapped in `<em>`.
- [ ] Empty query (`*:*`) is accepted and returns all docs.

### F4 — Faceted filtering

**Description:** Sidebar facets let the user narrow results by source, doc_type, is_agent, and project. Multiple selections within a facet are OR'd; across facets they are AND'd.

**Acceptance Criteria:**
- [ ] Facets shown: `doc_type`, `source`, `is_agent` (pick-one), `project` (multi-select, up to 20 values).
- [ ] Each facet value shows its count for the current query+filter set.
- [ ] `facet.mincount=1` applied per field so empty values don't appear.
- [ ] The histogram (F8) is NOT filtered by `facet.mincount` — it retains empty months for visual continuity.
- [ ] Selecting a facet filter reloads results and updates the URL.

### F5 — Sort options

**Description:** Result ordering is user-controlled.

**Acceptance Criteria:**
- [ ] Sort choices: Relevance (default when q is non-empty), Newest, Oldest, Most turns, Longest duration, Largest size (KB).
- [ ] Default sort auto-switches: empty query → Newest; non-empty query → Relevance (unless user overrides).
- [ ] Sort choice round-trips via URL.

### F6 — Date range filtering

**Description:** Restrict results by `started` timestamp.

**Acceptance Criteria:**
- [ ] Preset buttons: All, 7d, 30d, 90d, Custom.
- [ ] Presets use Solr date math (`NOW-7DAYS`, etc.) so ranges are always relative to query time.
- [ ] Custom opens two native `<input type="date">` fields plus an Apply button.
- [ ] Custom range is inclusive: `from T00:00:00Z TO to T23:59:59Z`.
- [ ] Selected preset/custom range reflected in the URL.

### F7 — Session-size filters

**Description:** Preset-dropdown minimum filters to hide short/trivial sessions and focus on substantial work.

**Acceptance Criteria:**
- [ ] `Min turns` is a dropdown with presets: `any`, `1+`, `5+`, `10+`, `25+`, `50+`, `100+`, `250+`. Filters on `total_turns` (= user_turns + assistant_turns), so 1 message = 1 turn.
- [ ] `Min duration` is a dropdown with presets: `any`, `1 min`, `5 min`, `15 min`, `30 min`, `1 h`, `2 h`, `4 h`. Filters on `duration_seconds` (converted from minutes × 60).
- [ ] Empty selection = no filter.
- [ ] Non-session doc types (no numeric field) are naturally excluded when either filter is active.
- [ ] Active filter shows as a chip (F10) with a human label (`50+ turns`, `2h+ duration`).

### F8 — Monthly activity histogram

**Description:** Bar chart showing result counts bucketed by month. Click to drill into a month.

**Acceptance Criteria:**
- [ ] Buckets span `NOW/YEAR-3YEARS` to `NOW/MONTH+1MONTH`, one month per bar.
- [ ] Leading and trailing empty months are trimmed from the visible chart for a tight view.
- [ ] Each bar shows a tooltip `YYYY-MM: N`.
- [ ] Clicking a non-empty bar sets the date filter to that exact month (Custom preset, [first → first-of-next-month]).
- [ ] Updates live as filters and query change.
- [ ] Hidden when there are zero total hits.

### F9 — Aggregate stats card

**Description:** Summary statistics for the current result set, arranged in two logically-grouped sections. All time aggregates are per-session-capped (F19) so a single abandoned session can't dominate the sums.

**Acceptance Criteria:**
- [ ] **Documents section** (left): Hits, Date span.
- [ ] **Activity section** (right, 3×2 grid): Total turns, Total time, Active time, User time, Agent time, Idle time.
- [ ] Activity boxes use color variants to distinguish user vs bot at a glance: Active (light blue), User (stronger blue), Agent (dark slate / white text), Idle (muted grey).
- [ ] Each Activity time box shows its percentage of Active time as subtext where meaningful (User, Agent).
- [ ] Subtext under Total time shows `longest Nh · capped at 8h per session`.
- [ ] Every stat box has a descriptive hover tooltip (CSS `data-tip` bubble, not native `title`) explaining what it measures and noting the cap.
- [ ] Card hidden entirely when no session-like data is present.
- [ ] Updates live as filters and query change.
- [ ] Responsive: sections stack vertically below 1100px viewport; Activity grid becomes 2-col below 700px.

### F10 — Active filter chips

**Description:** Chips above the results visually summarize every applied filter. Each chip has an × button to remove it.

**Acceptance Criteria:**
- [ ] One chip per: query text, date range, min turns, min minutes, source, project, doc_type, is_agent.
- [ ] × removes that single filter and re-searches.
- [ ] Chip strip is empty (no padding) when no filters are active.

### F11 — Pagination

**Description:** Standard page-based pagination.

**Acceptance Criteria:**
- [ ] Page size: 20.
- [ ] Shows up to 7 numbered page buttons centered around the current page.
- [ ] Prev/Next disabled at boundaries.
- [ ] Current page reflected in URL via `start` param.

### F12 — Open doc modal with rendered markdown

**Description:** Clicking "open" shows the full doc. Markdown-like doc types are rendered; others are shown raw.

**Acceptance Criteria:**
- [ ] Modal shows title, path, metadata (doc_type, source, project, started).
- [ ] For `session`, `project_doc`, and `summary_row`: rendered markdown via `marked`, HTML sanitized via `DOMPurify`.
- [ ] Rendered/Raw toggle present for markdown-capable types.
- [ ] Other doc types show raw `<pre>` only (no toggle).
- [ ] Modal closes on backdrop click, × button, or Escape.

### F13 — More Like This

**Description:** From any result or in-modal context, find similar docs by content.

**Acceptance Criteria:**
- [ ] Uses Solr's MLT **query parser** (via `/select`), not the `/mlt` request handler (which isn't enabled in `_default`).
- [ ] Fields used: `body`, `title`. `mintf=2`, `mindf=2`.
- [ ] Seed doc is filtered out of similar results.
- [ ] Opens in the same modal; clicking a result opens that doc.

### F14 — URL state sync

**Description:** The current search state is always reflected in the URL, and the URL can be pasted to reproduce the view.

**Acceptance Criteria:**
- [ ] All of: `q`, `sort`, `date` preset, custom `from`/`to`, `min_turns`, `min_dur`, `source[]`, `project[]`, `doc_type[]`, `is_agent`, `start` round-trip via URL.
- [ ] Browser Back / Forward re-hydrates the state (popstate handler).
- [ ] Reset button clears all state, restoring default empty-query view.

### F15 — Empty-query default view

**Description:** When the page loads with no query, show something immediately useful.

**Acceptance Criteria:**
- [ ] Default sort = Newest first.
- [ ] Stats card + histogram visible from first paint (as long as there are any docs).
- [ ] User can browse recent activity without typing anything.

### F16 — Health endpoint

**Description:** A simple liveness + fact endpoint for the UI status badge.

**Acceptance Criteria:**
- [ ] `GET /api/health` returns `{solr: "up"|"down", core, numDocs}` on success.
- [ ] Returns 503 with `{solr: "down", error}` when Solr is unreachable.
- [ ] UI header shows "solr up · N docs" in green or "down" in red.

### F17 — Spell-check "did you mean"

**Description:** If Solr returns a spellcheck collation, surface it to the user as a clickable "Did you mean …" link.

**Acceptance Criteria:**
- [ ] When a collation is returned, the UI shows `Did you mean: <suggestion>` with the suggestion as a link.
- [ ] Clicking the suggestion replaces the query and re-searches.
- [ ] When no collation, nothing is shown.
- [ ] Known gap (deferred): the `_default` configset's spellchecker indexes `_text_` not our custom `text` field, so suggestions are often absent. Fixing this requires configset tuning.

### F18 — Autocomplete suggest

**Description:** Prefix-match suggestions from indexed titles.

**Acceptance Criteria:**
- [ ] `GET /api/suggest?q=pre` returns titles whose first term starts with `pre`.
- [ ] Endpoint exists; UI integration deferred (no live autocomplete in the search box yet).

### F19 — Per-session timeline analysis (user / agent / idle)

**Description:** For every indexed session, compute how much wall-clock time was you actively engaged vs. the model (and tools) working vs. idle — by parsing per-message timestamps from the raw session `.jsonl`.

**Acceptance Criteria:**
- [ ] For each gap between consecutive events, classify into one of three buckets and credit it accordingly:
  - Gap ≤ 10 min AND next event is a real user message → `user_seconds`.
  - Gap ≤ 10 min AND next event is assistant / tool_result / system / file-snapshot → `assistant_seconds`.
  - Gap > 10 min → `idle_seconds` (regardless of next-event type).
- [ ] A "real user message" has `type=user` and non-empty text content (plain string, or a list with at least one non-`tool_result` block). Synthetic user events whose content is only tool_result echoes are treated as assistant time.
- [ ] `active_seconds` = `user_seconds` + `assistant_seconds`, stored as its own field.
- [ ] Idle threshold is a single constant (`IDLE_THRESHOLD_SECONDS = 600` in `ingest/timeline.py`), changeable without schema changes but requiring full re-ingest to take effect.
- [ ] Timeline module is standalone-runnable for debugging: `uv run python timeline.py <path-to-session.jsonl>`.
- [ ] If a session has no matching `.jsonl`, timeline fields are absent (not zero) on that doc.
- [ ] Per-hit meta line in the UI shows `N turns (Xu+Ya) · Mm user + Km agent` alongside the raw duration.

### F20 — Per-session stats cap (include but limit)

**Description:** Outlier sessions (e.g. a session left open overnight for 180h) used to be **excluded** from aggregate stats. They are now **included but capped** — each session contributes at most `stats_cap_seconds` (default 28800 = 8h) to every time-based stat.

**Acceptance Criteria:**
- [ ] All sessions matching the query+filters count in the stats (no session is silently dropped).
- [ ] Each session's contribution to `duration_seconds`, `user_seconds`, `assistant_seconds`, `idle_seconds`, `active_seconds` is capped at `stats_cap_seconds` via a Solr function query: `{!func}min(<field>, cap)`.
- [ ] The stats sub-query is scoped with `fq=doc_type:session` to avoid `min()` returning the cap value for docs missing those fields (which would inflate sums by a large multiple).
- [ ] `stats_cap_seconds=0` disables the cap (raw sums).
- [ ] Default cap is 8h.
- [ ] Response includes `stats._capped_at_seconds` so the UI can render a transparent "capped at Nh per session" note.
- [ ] Non-time stats (user_turns, assistant_turns, total_turns, size_kb, started) are not capped.

## Data Models

### Solr document — common fields

| Field | Type | Stored | Indexed | Notes |
|-------|------|--------|---------|-------|
| `id` | string | ✓ | ✓ | Unique key (see ID schemes below) |
| `doc_type` | string | ✓ | ✓ | One of `session`, `project_doc`, `summary_row`, `insight` |
| `source` | string | ✓ | ✓ | `macbook-work` / `macbook-personal` / `atpoc-sandbox` / `atpoc-secureapi` |
| `project` | string | ✓ | ✓ | Normalized project name (matches folder name under `projects/`) |
| `title` | text_en | ✓ | ✓ | Topic, doc filename, or first non-empty line of body |
| `body` | text_en | ✓ | ✓ | termVectors/positions/offsets on, for unified highlighting |
| `path` | string | ✓ | — | Original file path for click-through |
| `started` | pdate | ✓ | ✓ | Session start, history timestamp, or file mtime |
| `ended` | pdate | ✓ | ✓ | Session end (when available) |
| `updated` | pdate | ✓ | ✓ | Indexed-at timestamp |

### Session-specific fields (nullable on other doc types)

| Field | Type | Notes |
|-------|------|-------|
| `session_id` | string | UUID from filename or summary.csv |
| `is_agent` | boolean | From summary.csv |
| `topic` | text_en | From summary.csv or parsed header |
| `user_turns` | pint | |
| `assistant_turns` | pint | |
| `total_turns` | pint | `user_turns + assistant_turns`. The canonical "1 message = 1 turn" field used by the Min turns filter. |
| `duration` | string | Raw form, e.g. `"2h 6m"` |
| `duration_seconds` | pint | Parsed wall-clock duration |
| `user_seconds` | pint | Timeline output (F19). Active user time. |
| `assistant_seconds` | pint | Timeline output. Active agent/tool time. |
| `idle_seconds` | pint | Timeline output. Sum of gaps > 10 min. |
| `active_seconds` | pint | `user_seconds + assistant_seconds`. |
| `size_kb` | pfloat | |

### Copy fields

- `title`, `topic`, `body` → `text` (the default catch-all for bare keyword queries)

### ID schemes

- session → `{source}:session:{project}:{session_id}`
  *(`project` is included because the same `session_id` can appear under multiple project folders, e.g. worktree orphans. Without it, docs would silently overwrite each other.)*
- project_doc → `{source}:project_doc:{project}:{relative_path}`
- summary_row → `{source}:summary:{session_id}`
- insight → `{source}:insight:{filename}`

## API Contracts

Base URL: `http://localhost:8007`. Same-origin from the UI.

### `GET /api/health`

Response 200:
```json
{ "solr": "up", "core": "exocortex", "numDocs": 2317 }
```
Response 503 when Solr is unreachable.

### `GET /api/search`

Query parameters:

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `q` | string | `*:*` | Solr query string; edismax parses it |
| `start` | int | 0 | Pagination offset |
| `rows` | int | 20 | Page size |
| `sort` | enum | `relevance` | `relevance` · `started_desc` · `started_asc` · `turns_desc` · `duration_desc` · `size_desc` |
| `source` | string[] | — | Multi-valued; OR within field |
| `project` | string[] | — | Multi-valued; OR within field |
| `doc_type` | string[] | — | Multi-valued; OR within field |
| `is_agent` | `"true"`/`"false"` | — | Single value |
| `date_from` | string | — | ISO-8601 or Solr date math (e.g. `NOW-30DAYS`) |
| `date_to` | string | — | Same |
| `min_turns` | int | — | Filter: `total_turns:[min_turns TO *]` (1 message = 1 turn) |
| `min_duration_seconds` | int | — | Filter: `duration_seconds:[… TO *]` |
| `stats_cap_seconds` | int | 28800 | Per-session cap applied to time-based stats (F20). Pass 0 to disable. |

Response 200 shape:
```json
{
  "numFound": 2317,
  "start": 0,
  "rows": 20,
  "qtime": 42,
  "docs": [
    { "id": "...", "doc_type": "session", "source": "...", "project": "...",
      "title": "...", "started": "2026-04-15T20:33:00Z",
      "user_turns": 14, "assistant_turns": 35, "duration": "2h 6m",
      "duration_seconds": 7560, "size_kb": 1347.9,
      "_highlights": ["...<em>match</em>..."] }
  ],
  "facets": {
    "source":   [{"value": "macbook-work", "count": 200}, ...],
    "project":  [...],
    "doc_type": [...],
    "is_agent": [...]
  },
  "date_facets": [
    {"value": "2026-03-01T00:00:00Z", "count": 159},
    {"value": "2026-04-01T00:00:00Z", "count": 2158},
    ...
  ],
  "stats": {
    "user_turns":       {"sum": 1963, "count": 554, "mean": 3.54, "min": 0, "max": 93},
    "assistant_turns":  {...},
    "total_turns":      {...},
    "duration_seconds": {"sum": 543600, "count": 635, "mean": 856, "min": 0, "max": 28800},
    "user_seconds":     {"sum": 138240, "count": 635, "mean": 218, "min": 0, "max": 9720},
    "assistant_seconds":{"sum": 188280, "count": 635, "mean": 296, "min": 0, "max": 26640},
    "idle_seconds":     {"sum": 248400, "count": 635, "mean": 391, "min": 0, "max": 28800},
    "active_seconds":   {"sum": 322560, "count": 635, "mean": 508, "min": 0, "max": 28800},
    "size_kb":          {...},
    "started":          {"min": "2026-03-24T16:22:00Z", "max": "2026-04-19T19:48:00Z"},
    "_capped_at_seconds": 28800
  },
  "suggestion": null
}
```

Note: time-based stat fields (`duration_seconds`, `user_seconds`, `assistant_seconds`, `idle_seconds`, `active_seconds`) are per-session capped at `stats_cap_seconds`. The stats sub-query is scoped to `doc_type:session` (only sessions carry these fields).

### `GET /api/mlt/{doc_id}`

Path param: full Solr `id` (URL-encoded). Query param `rows` (default 10).

Response:
```json
{
  "match":   { /* seed doc */ },
  "similar": [ /* up to `rows` similar docs */ ]
}
```

### `GET /api/suggest?q=...`

Prefix-match against `title`. Response:
```json
{ "suggestions": [ {"id": "...", "title": "..."} ] }
```

### `GET /api/doc/{doc_id}`

Fetches the full document including `body`. 404 if not found.

### FastAPI auto-docs

- Swagger: `/docs`
- ReDoc: `/redoc`
- OpenAPI JSON: `/openapi.json`

## Integrations

- **Solr 9** (official `solr:9` Docker image). Single-node standalone (no SolrCloud).
- **marked** (from jsDelivr CDN) — client-side markdown rendering.
- **DOMPurify** (from jsDelivr CDN) — HTML sanitization of rendered markdown.
- **selectolax** — HTML → text extraction during ingest (for insight files).
- **requests** — Solr HTTP client.

Environment variables:

| Var | Default | Used by |
|-----|---------|---------|
| `SOLR_URL` | `http://localhost:8983/solr/exocortex` | ingest, api |
| `EXPORT_ROOT` | `~/Documents/exocortex/export` | ingest |

## Non-Functional Requirements

- **Portability.** Repointing at a hosted Solr must require nothing more than changing `SOLR_URL`. No app-level assumptions about "localhost".
- **Re-runnability.** Ingestion must be safe to run at any time, end-to-end, without manual cleanup.
- **Response time.** Search p50 under 150ms on a local Solr with ~2k–20k docs. (Current: ~40–60ms QTime plus network.)
- **Bookmark fidelity.** Every meaningful UI state must be reconstructable from the URL alone.
- **Stateless UI.** No server-side sessions, no client storage — URL is the single source of truth.
- **No auth.** Local only; not exposed on public interfaces.

## Non-Goals

- No authentication or multi-user support.
- No SolrCloud or ZooKeeper.
- No incremental or delta ingest — always full re-ingestion.
- No vector / semantic search.
- No deployment to EC2 (port 8007 is reserved by convention but Nginx isn't wired up).
- No autocomplete integration in the search box (endpoint exists but UI doesn't call it yet).

## Edge Cases & Error Handling

- **Solr down.** `/api/health` returns 503; UI header shows red "down" badge; other endpoints return 502 with a structured error.
- **Duplicate session_ids across project folders** (worktree orphans). Handled via project-qualified IDs so nothing is silently overwritten.
- **Sessions with no markdown file.** Emitted as `summary_row` docs so their metadata is still searchable.
- **Sessions with no summary row.** Fall back to parsing the markdown header for `started`, `topic`, `duration`, `turns`.
- **Numeric filters on non-session docs.** When `min_turns` or `min_duration_seconds` are set, non-session doc types naturally drop out (they have no value for those fields).
- **Empty histogram buckets.** Preserved by per-field `facet.mincount`; leading/trailing empties trimmed client-side for a tight visual.
- **Unknown or missing dates.** Doc is still indexed; stats ignore it.
- **Unparseable history.jsonl lines.** Skipped with a stderr warning; ingest continues.
- **Very long session bodies.** Solr's default limits apply; no chunking in v1.
- **Spellcheck gap.** The `_default` configset spellchecker targets `_text_` (not our `text` field), so "did you mean" suggestions are often empty. Documented as a known deferred issue; not a blocker.
- **MLT via `/mlt` handler.** Not available in `_default`; implementation uses the MLT query parser through `/select` instead.
- **Solr `min()` returns the cap value for missing fields.** If you run `{!func}min(duration_seconds, 28800)` as `stats.field` without scoping to sessions, docs without a `duration_seconds` field silently contribute the cap value to the sum (confirmed experimentally — a 30× sum inflation when `fq=doc_type:session` was missing). Always scope stats queries to the subset of docs that actually have the field.
- **Sessions with no matching `.jsonl`.** Timeline fields are absent (not zero), so the stats `count` for `user_seconds`/`assistant_seconds`/`idle_seconds` may be lower than the session count.
- **User+Agent per session can exceed Active after capping.** Because each metric is capped independently at 8h, a session with 5h user + 5h agent (= 10h active) reports capped values of 5h + 5h + 8h for user/agent/active. The three numbers are useful individually; they are not expected to be additive after capping.
- **Race conditions on rapid facet clicks.** Mitigated by a monotonic sequence number on every search. Only the latest response is rendered; older responses are discarded as they arrive.

## Milestones

Historical record of the build order. M1–M6 complete; M7 partial.

1. **M1 — Solr up.** Docker-compose boots Solr 9; `exocortex` core created from `_default`; admin UI reachable.
2. **M2 — Schema + ingest.** Schema applied via Schema API; full re-ingestion emits 4 `doc_type`s (history entries intentionally excluded); ~933 docs indexed.
3. **M3 — FastAPI proxy on :8007.** Search / MLT / suggest / doc / health all respond; Solr params wrapped with sensible defaults.
4. **M4 — Search UI.** Search box, facet sidebar, highlighted snippets, pagination, open-modal, MLT, Markdown rendering.
5. **M4.5 — Investigation layer.** Date presets + custom picker, sort options, min-turns / min-minutes filters (initially number inputs, later preset dropdowns), monthly histogram, stats card, active filter chips, URL state sync, Reset button, empty-query default view.
6. **M5 — Timeline split (F19).** New `ingest/timeline.py` module reads raw session `.jsonl`, classifies each gap into user/agent/idle, and writes per-session `user_seconds`, `assistant_seconds`, `idle_seconds`, `active_seconds` fields. Idle threshold initially 5 min, later relaxed to 10 min. Stats card gets colored variants to distinguish me vs bot vs idle.
7. **M6 — Stats cap refactor (F20).** Changed from "exclude sessions > 8h" to "include but cap each session's contribution at 8h via Solr function queries". Required scoping the stats sub-query to `doc_type:session` after discovering that `min()` inflates sums when the field is missing on non-session docs.
8. **M7 — Polish (partial).** Did-you-mean and autocomplete endpoints stubbed; meaningful "did you mean" output requires configset tuning (known gap).

## Open Questions (still deferred, not blocking)

- Boost weights (`title^4 topic^3 body^1`) — values chosen by feel, not tuned empirically.
- Whether to strip Markdown syntax from `body` before indexing. Current choice: leave it so code blocks remain searchable.
- Whether to reintroduce `history.jsonl` ingestion with aggressive filtering (skip slash-commands, length ≥ N). Dropped in v1 because it drowned out the substantive content.
- Whether to deploy the app to EC2 behind Nginx at `/test7/` on port 8007 (reserved but not wired).
