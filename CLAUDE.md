# AWS Learning Workspace

Personal AWS experimentation workspace. Same architecture pattern as the work experiments (FastAPI + vanilla HTML/JS + databases) but running on a personal EC2 instance instead of on-prem servers.

## Server

- **EC2 instance**: `i-09b4f3e3492583c2c` (aws-learning)
- **Type**: t4g.micro (ARM/Graviton), Ubuntu 24.04
- **Public IP**: `3.95.0.131` (will change on stop/start — no Elastic IP yet)
- **SSH**: `ssh -i ~/.ssh/kev-aws-learning.pem ubuntu@3.95.0.131`
- **AWS region**: us-east-1
- **Security group**: `sg-094fb41fbad9b266a` (ports 22, 80, 443)

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

## Running experiments on EC2

```bash
cd /home/ubuntu/aws-learning/test<n>-name/api
uv sync
uv run uvicorn main:app --host 0.0.0.0 --port 800<n> --reload
```

Nginx reverse proxies each experiment:
- `http://<ip>/test1/` → `localhost:8001`
- `http://<ip>/test2/` → `localhost:8002`
- etc.

## Port convention

| Experiment | Port |
|-----------|------|
| test1-tasks | 8001 |
| (future) | 8002+ |

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
