# AWS Learning Workspace

Personal AWS experimentation workspace. Same architecture pattern as the work experiments (FastAPI + vanilla HTML/JS + databases) but running on a personal EC2 instance instead of on-prem servers.

## Server

- **Domain**: `physicskev.com` (registered on Namecheap)
- **EC2 instance**: `i-09b4f3e3492583c2c` (aws-learning)
- **Type**: t4g.micro (ARM/Graviton), Ubuntu 24.04
- **Elastic IP**: `32.194.2.97` (permanent, won't change on stop/start)
- **SSH**: `ssh -i ~/.ssh/kev-aws-learning.pem ubuntu@32.194.2.97`
- **AWS region**: us-east-1
- **Security group**: `sg-094fb41fbad9b266a` (ports 22, 80, 443)
- **SSL**: Let's Encrypt via Certbot, auto-renews. Cert at `/etc/letsencrypt/live/physicskev.com/`

## Experiment pattern

Each experiment lives in its own folder with this structure:

```
test<n>-name/
├── api/
│   ├── main.py           # FastAPI app
│   ├── pyproject.toml    # uv-managed dependencies
│   └── .venv/            # gitignored
├── ui/
│   ├── index.html
│   └── app.js
├── db/                   # if needed
│   ├── *.db              # SQLite database (gitignore if >10MB)
│   └── ingest.py         # data loader
└── prd-test<n>-*.md      # requirements doc
```

## Running experiments locally

```bash
cd test<n>-name/api
uv sync
uv run uvicorn main:app --port 800<n> --reload
# Open http://localhost:800<n>
```

## Running experiments on EC2

```bash
ssh -i ~/.ssh/kev-aws-learning.pem ubuntu@3.95.0.131
export PATH="$HOME/.local/bin:$PATH"
cd /home/ubuntu/aws-learning/test<n>-name/api
uv sync
nohup uv run uvicorn main:app --host 127.0.0.1 --port 800<n> > /tmp/test<n>.log 2>&1 &
```

Nginx reverse proxies each experiment. Config at `/etc/nginx/sites-available/experiments`.
HTTP auto-redirects to HTTPS.
- `https://physicskev.com/` → Landing page with links to all experiments
- `https://physicskev.com/test1/` → `localhost:8001`
- `https://physicskev.com/test2/` → `localhost:8002`
- `https://physicskev.com/test3/` → `localhost:8003`
- `https://physicskev.com/test4/` → `localhost:8004`
- `https://physicskev.com/test5/` → `localhost:8005`

To stop all experiments: `pkill -f uvicorn` (or `killall uvicorn`)
Processes use `nohup` so they survive SSH disconnect, but NOT instance reboot.

## Port convention

| Experiment | Port | Description |
|-----------|------|-------------|
| test1-tasks | 8001 | Task manager CRUD |
| test2-research | 8002 | Claude-powered research viewer |
| test3-search | 8003 | FTS5 movie search |
| test4-board | 8004 | Kanban board / ticket tracker |
| test5-lambda | 8005 | Lambda handler (local wrapper) |
| test6-databases | 8006 | RDS Postgres + DynamoDB CRUD |
| test7-solr | 8007 | Solr 9 + FastAPI proxy over personal Claude Code export |

test7 is the first experiment that needs Docker (Solr runs in a local `solr:9` container). See `test7-solr/CLAUDE.md` for its own quickstart. Not yet wired into Nginx on EC2.

## Seed data

test3 and test4 need generated data before first run:
```bash
cd test3-search/db && python3 seed_data.py   # generates movies.db (200 movies)
cd test4-board/db && python3 seed_data.py     # generates board.db (150 tickets)
```

## Key differences from work setup

| Work (atpoc) | Personal (AWS) |
|-------------|----------------|
| Apache + .htaccess | Nginx + sites-available config |
| On-prem servers | EC2 t4g.micro |
| Postgres (RDS Proxy) | SQLite first, RDS later |
| Bitbucket | GitHub |
| secret.py at workspace root | .env files (gitignored) |
| app_factory.py shared module | Direct FastAPI() — no proxy path complexity needed |

## What to commit

- All code, HTML, JS — yes
- Small .db files (<10MB) — yes
- Large .db files — gitignore, regenerate with ingest.py
- .env, credentials — never
- .venv/, __pycache__/ — always gitignored

## Package management

Use `uv` for everything. Each experiment has its own venv.

```bash
cd test<n>-name/api
uv init
uv add fastapi 'uvicorn[standard]'
uv sync
```
