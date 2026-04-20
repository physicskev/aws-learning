# test7-solr

Local Solr 9 instance (in Docker) indexing the personal Claude Code export at `~/Documents/exocortex/export/`. See `prd-test7-solr.md` for full requirements.

## Layout

```
test7-solr/
├── docker/              # docker-compose + Solr configset (in git)
│   ├── docker-compose.yml
│   ├── README.md
│   └── solr-config/exocortex/conf/   # mounted as the core's configset
├── ingest/              # python ingest script (uv)
│   └── ingest.py        # full re-ingestion: DELETE */*, then reload all docs
├── api/                 # FastAPI on :8007 (uv)
│   └── main.py          # thin proxy over Solr /select, /mlt, /suggest
├── ui/                  # vanilla HTML + JS search UI
└── prd-test7-solr.md
```

## Quickstart

```bash
# 1. Bring up Solr (persists data in a named volume)
cd test7-solr/docker
docker compose up -d
# admin UI: http://localhost:8983/solr/
# core:     http://localhost:8983/solr/exocortex

# 2. Apply schema (idempotent; safe to re-run)
cd ../ingest
uv sync
uv run python setup_schema.py

# 3. Full re-ingestion of ~/Documents/exocortex/export/
uv run python ingest.py

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

# wipe index + start fresh
docker compose down -v && docker compose up -d
uv run python setup_schema.py
uv run python ingest.py

# tail Solr logs
docker compose logs -f solr
```

## Port convention

- Solr container: `8983` (Solr default)
- FastAPI: `8007` (per workspace test<n> convention)

## Repointing at a hosted Solr later

Only one env var changes — everything else is Solr HTTP API, so it's portable:

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

- `docker/docker-compose.yml` and `docker/solr-config/**` — yes
- `ingest/`, `api/`, `ui/` source — yes
- Solr data volume (`/var/solr` in container) — no, managed by Docker
- `.venv/`, `__pycache__/` — gitignored

## Gotchas

- Solr's bind-mount needs the right UID. The official `solr:9` image runs as UID 8983. `docker-compose.yml` either uses a named volume (easy) or chowns the host dir.
- `solr-precreate` only runs on first boot when the core doesn't yet exist. To re-apply a changed configset, either `docker compose down -v` (destructive) or use the Schema API.
- Schema changes to `text_en` analyzer chains require re-indexing, not just a reload.
