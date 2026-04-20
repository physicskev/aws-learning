# test7-solr

Local Solr 9 (in Docker) + FastAPI + vanilla-JS UI for searching and investigating the personal Claude Code export at `~/Documents/exocortex/export/`. See `prd-test7-solr.md` for full product requirements.

## Layout

```
test7-solr/
├── docker/
│   ├── docker-compose.yml         # Solr 9, standalone, named volume
│   └── README.md                  # up/down/reset commands
├── ingest/
│   ├── setup_schema.py            # idempotent: applies schema via Solr Schema API
│   ├── ingest.py                  # full re-ingestion (wipe + reload)
│   ├── timeline.py                # per-session timeline analyzer (user/agent/idle split)
│   ├── pyproject.toml
│   └── uv.lock
├── api/
│   ├── main.py                    # FastAPI on :8007, Solr proxy
│   ├── pyproject.toml
│   └── uv.lock
├── ui/
│   ├── index.html
│   ├── app.js                     # state, fetch, render — no framework
│   └── styles.css
├── CLAUDE.md
└── prd-test7-solr.md
```

## Quickstart

```bash
# 1. Bring up Solr (~15-20s first boot while core is precreated)
cd test7-solr/docker
docker compose up -d
# admin UI: http://localhost:8983/solr/
# core:     http://localhost:8983/solr/exocortex

# 2. Apply the schema (idempotent; safe to re-run)
cd ../ingest
uv sync
uv run python setup_schema.py

# 3. Full re-ingestion of ~/Documents/exocortex/export/
uv run python ingest.py            # ~2s end-to-end for ~933 docs

# 4. Run the API + UI
cd ../api
uv sync
uv run uvicorn main:app --port 8007 --reload
# open http://localhost:8007
```

## Common ops

```bash
# stop Solr (keeps data)
docker compose down

# wipe index + start fresh (destroys the named volume)
docker compose down -v && docker compose up -d
uv run python setup_schema.py
uv run python ingest.py

# tail Solr logs
docker compose logs -f solr

# Timeline of a single session (debug)
cd test7-solr/ingest
uv run python timeline.py /path/to/session.jsonl
```

## Port convention

- Solr container: `8983` (Solr default)
- FastAPI: `8007` (per workspace test<n> convention)

## Architecture

```
Browser (UI on :8007)
  ↓ /api/* fetch
FastAPI (api/main.py)
  ↓ Solr HTTP API
Solr 9 (Docker, core: exocortex)
```

### Ingest pipeline

```
~/Documents/exocortex/export/
  ├── <source>/summary.csv     ──┐
  ├── <source>/insights/*.html   │
  └── <source>/projects/         │── ingest.py walks, builds Solr docs
      └── <project>/             │     (+ timeline.py on each .jsonl)
          ├── docs/*.md          │
          └── sessions/          │
              ├── *.md           │
              └── *.jsonl      ──┘
                                 ↓
                              Solr core "exocortex"  (~933 docs, 4 doc_types)
```

`history.jsonl` is intentionally NOT indexed — too noisy.

### Timeline module (`ingest/timeline.py`)

Every session has a companion `.jsonl` with one event per line, each with a `timestamp`. For each gap between consecutive events, `compute_timeline()` classifies it into one of three buckets:

| Gap size | Next event | Bucket |
|---|---|---|
| ≤ 10 min | real user message | `user_seconds` |
| ≤ 10 min | assistant / tool_result / system / snapshot | `assistant_seconds` |
| > 10 min | anything | `idle_seconds` |

A "real user message" has `type=user` and non-empty text content (string or a list with at least one non-`tool_result` block). Synthetic user events (tool_result echoes) count as assistant time.

Threshold lives in `ingest/timeline.py` as `IDLE_THRESHOLD_SECONDS = 600`. Change it and re-run `uv run python ingest.py`.

### Stats cap (API-side)

`api/main.py` runs a **second** Solr query just for the aggregate stats. That query:
- Is scoped to `doc_type:session` (only sessions have duration/user/agent/idle fields — running the function over non-sessions would let `min()` return the cap value for missing fields and inflate sums dramatically).
- Caps each time metric per session via function queries: `{!func}min(duration_seconds, 28800)`. So a 180h session-left-open contributes at most 8h to every time sum.

Cap is `stats_cap_seconds` on `/api/search`, default 28800 (8h). Pass `stats_cap_seconds=0` to disable.

## Solr schema

Added via Schema API by `setup_schema.py`. Starts from the Solr `_default` configset (no configset in git).

### Common fields

| Field | Type | Notes |
|---|---|---|
| `id` | string | unique key |
| `doc_type` | string | `session` \| `project_doc` \| `summary_row` \| `insight` |
| `source` | string | `macbook-work` / `macbook-personal` / `atpoc-sandbox` / `atpoc-secureapi` |
| `project` | string | matches folder name under `projects/` |
| `title`, `body`, `topic` | text_en | indexed, stored; `body` has termVectors for unified highlighter |
| `path` | string | original filesystem path for click-through |
| `started`, `ended`, `updated` | pdate | |

### Session-only fields

| Field | Type | Notes |
|---|---|---|
| `session_id` | string | |
| `is_agent` | boolean | from summary.csv |
| `user_turns`, `assistant_turns` | pint | |
| `total_turns` | pint | = user_turns + assistant_turns |
| `duration` | string | raw from csv, e.g. `"2h 6m"` |
| `duration_seconds` | pint | parsed wall-clock |
| `user_seconds` | pint | timeline output — active user time |
| `assistant_seconds` | pint | timeline output — active agent time |
| `idle_seconds` | pint | timeline output — sum of gaps > 10 min |
| `active_seconds` | pint | = user_seconds + assistant_seconds |
| `size_kb` | pfloat | |

### Copy field

`title`, `topic`, `body` → `text` (default catch-all for bare keyword queries).

### ID scheme

- `session`    → `{source}:session:{project}:{session_id}`
  (project IS included — the same session_id can appear under multiple project folders for worktree orphans)
- `project_doc` → `{source}:project_doc:{project}:{relative_path}`
- `summary_row` → `{source}:summary:{session_id}`
- `insight`    → `{source}:insight:{filename}`

## API (`api/main.py`) — FastAPI on :8007

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/search` | Main query: hits + facets + histogram + stats + highlighting |
| GET | `/api/mlt/{id}` | More Like This (via MLT query parser, not `/mlt` handler) |
| GET | `/api/suggest` | Prefix match on title |
| GET | `/api/doc/{id}` | Fetch full doc incl. body |
| GET | `/api/health` | `{solr, core, numDocs}` |
| GET | `/docs`, `/redoc`, `/openapi.json` | FastAPI built-in docs |
| GET | `/` + static files | UI |

### Key `/api/search` params

| Param | Default | Notes |
|---|---|---|
| `q` | `*:*` | edismax parses it |
| `start`, `rows` | 0, 20 | |
| `sort` | `relevance` | `relevance` \| `started_desc` \| `started_asc` \| `turns_desc` \| `duration_desc` \| `size_desc` |
| `source[]`, `project[]`, `doc_type[]` | — | multi-valued; OR within, AND across |
| `is_agent` | — | `"true"` / `"false"` |
| `date_from`, `date_to` | — | ISO-8601 or Solr date math (`NOW-30DAYS`) |
| `min_turns` | — | filters on `total_turns:[min_turns TO *]` |
| `min_duration_seconds` | — | filters on `duration_seconds` |
| `stats_cap_seconds` | 28800 | per-session cap on time stats; pass 0 to disable |

## UI (`ui/`)

Single-page vanilla HTML + JS. No framework, no build.

### Key behaviors

- **Monotonic sequence number** on every `search()` call. Only the latest response's render wins. Eliminates "out-of-order response" UI corruption.
- **Event-delegated facet clicks.** Each facet row has `data-facet-key` / `data-facet-value` / `data-facet-kind` attributes. A single click listener on `#facets` reads them and updates `state`. No per-render handlers.
- **Visual checkbox** — not a real `<input type="checkbox">`. Just a styled `<span class="facet-mark">` controlled by state. Sidesteps label-wrapping and preventDefault weirdness.
- **URL ↔ state sync.** Every filter / sort / query / pagination state lives in the URL via `history.replaceState`. `popstate` re-hydrates on back/forward. No client storage.
- **Debug line** near the top shows the last fetched URL and hit count. Lives in `#debug` div. Useful for triaging UI-vs-server bugs.
- **`cache: 'no-store'`** on every `/api/*` fetch to rule out browser caching.
- **Markdown rendering** in doc modal via `marked` + `DOMPurify` from CDN. Raw/Rendered toggle for markdown-capable doc types (`session`, `project_doc`, `summary_row`).

### Stats card sections

Two panels side-by-side (stacks vertically below 1100px):

- **Documents** (left, 2-col): Hits, Date span
- **Activity** (right, 3×2 grid): Total turns, Total time, Active time, User time, Agent time, Idle time

Activity boxes have color variants for instant "me vs bot" reading:
- `variant-active` — light blue
- `variant-user` — stronger blue
- `variant-agent` — dark slate with white text
- `variant-idle` — muted grey

Every box has a `data-tip` attribute; CSS `:hover::after` renders a dark tooltip bubble.

## Repointing at a hosted Solr later

Only one env var changes — everything else speaks Solr HTTP API, so it's portable:

```bash
export SOLR_URL=https://my-hosted-solr.example.com/solr/exocortex
```

Used by both `ingest/ingest.py` and `api/main.py`.

## Env vars

| Var | Default | Used by |
|-----|---------|---------|
| `SOLR_URL` | `http://localhost:8983/solr/exocortex` | ingest, api |
| `EXPORT_ROOT` | `~/Documents/exocortex/export` | ingest |

## What to commit

- `docker/docker-compose.yml`, `docker/README.md` — yes
- `ingest/`, `api/`, `ui/` source + `pyproject.toml` + `uv.lock` — yes
- Solr data volume (named Docker volume `docker_solr_data`) — no, not in git
- `.venv/`, `__pycache__/`, `.DS_Store` — gitignored at workspace root

## Gotchas

- **Solr function queries over missing fields.** `{!func}min(duration_seconds, 28800)` run on a doc that doesn't have `duration_seconds` returns the cap value (28800), not 0. Always scope such queries with `fq=doc_type:session` or similar. Failing to do so inflated our Total time by 30× before it was caught.
- **`solr-precreate` only runs on first boot.** To apply a changed schema, either `docker compose down -v` (destructive — wipes the volume) or use the Schema API (what `setup_schema.py` does).
- **`_default` configset spellcheck targets `_text_`, not our `text` field.** So `spellcheck.collate` rarely returns a suggestion for real queries. Noted; not fixed.
- **MLT `/mlt` handler isn't enabled in `_default`.** Use the MLT query parser via `/select`: `q={!mlt qf="body title" mintf=2 mindf=2}<doc_id>`.
- **Session IDs can collide across project folders.** The export may expose the same `session_id` under multiple project folders (worktree orphans). Sessions use a project-qualified ID to avoid silent overwrites.
- **`history.jsonl` is NOT indexed.** Too noisy — dominated by `/help`, `/login` slash commands. Sessions, project docs, summary rows, and insights are the indexed doc types.
- **Changing `IDLE_THRESHOLD_SECONDS` requires a full re-ingest.** Timeline values are computed once at ingest, not at query time.
- **Docker bind-mount UIDs.** The `solr:9` image runs as UID 8983. The compose file uses a named volume to avoid host UID issues. Bind mounts would need `chown 8983:8983`.
