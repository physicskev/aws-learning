# PRD: AWS Learning Experiments

## Overview

A series of small, focused experiments that replicate the architecture patterns from work (FastAPI + vanilla HTML/JS + databases) but on a personal AWS EC2 instance with fake data. The goal is learning — both AWS infrastructure and the Claude Code workflow. Each experiment builds on the last, adding one new concept.

---

## Infrastructure (one-time setup)

An Ubuntu 24.04 EC2 instance (t4g.micro) serves as the base. Nginx replaces Apache as the reverse proxy. Each experiment gets its own port, its own uv-managed Python venv, and its own Nginx location block. No Docker, no frameworks, no build tools.

```
Browser
  ↓ HTTP
Nginx (port 80)
  ↓ proxy_pass per location
FastAPI (port 800N)
  ↓
SQLite / Postgres / External API
```

### Nginx setup

One config file at `/etc/nginx/sites-available/experiments` with a location block per experiment:

```nginx
server {
    listen 80;
    server_name _;

    location /test1/ {
        proxy_pass http://127.0.0.1:8001/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # location /test2/ { ... }
}
```

Each experiment's FastAPI app serves both the API (`/api/*`) and the UI (`/` serves static files). No separate static file serving from Nginx needed.

---

## Experiment 1: Task Manager (test1-tasks)

**Purpose:** Prove the full stack works end to end — EC2, Nginx, FastAPI, SQLite, vanilla JS. This is the "hello world" that validates the infrastructure.

**Based on:** prd-v1.md from work (the foundational three-tier task manager), adapted with no auth and no proxy path complexity.

### Folder structure

```
test1-tasks/
├── api/
│   ├── main.py           # FastAPI app — routes only
│   ├── db.py             # All SQLite queries
│   ├── models.py         # Pydantic request/response models
│   └── pyproject.toml    # fastapi, uvicorn
├── ui/
│   ├── index.html        # Single page
│   └── app.js            # All JS, fetch-based
└── db/
    └── 001_create_tasks.sql  # Migration
```

### Database

SQLite file at `db/tasks.db`. One table:

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | Primary key, autoincrement |
| title | TEXT | Not null |
| description | TEXT | Nullable |
| status | TEXT | "pending", "in_progress", "complete" — default "pending" |
| priority | TEXT | "low", "medium", "high" — default "medium" |
| created_at | TIMESTAMP | Default current time |
| updated_at | TIMESTAMP | Updates on change |

### API endpoints

| Method | Path | What it does |
|--------|------|-------------|
| GET | /api/health | Server status check |
| GET | /api/tasks | List all tasks, optional ?status= filter |
| GET | /api/tasks/{id} | Single task or 404 |
| POST | /api/tasks | Create task (title required, rest optional) |
| PATCH | /api/tasks/{id} | Update any field (partial update) |
| DELETE | /api/tasks/{id} | Delete task |

### UI

Single page with:
- Text input + "Add Task" button at top
- Task list below, each card shows title, status badge, priority badge, created date
- Click a task to expand inline: edit title, description, change status/priority via dropdowns, delete button
- Filter bar: status dropdown, priority dropdown, search text
- No login, no auth — this is a personal learning tool

### What this teaches

- Full request lifecycle: browser → Nginx → FastAPI → SQLite → JSON → browser render
- uv project setup on a remote server
- Nginx reverse proxy configuration
- SQLite CRUD with proper Pydantic validation
- Static file serving from FastAPI
- The same three-layer separation used at work, but stripped to essentials

---

## Experiment 2: Research Viewer (test2-research) — DONE

**Purpose:** Call Claude CLI from a web UI, display markdown results. Based on work's test2-fda but without SendGrid.

**How it works:**
- User enters topics (one per line) and optional extra instructions
- "Run Research" calls `claude -p "prompt" --allowedTools "WebSearch,WebFetch"` via `asyncio.create_subprocess_exec`
- Results rendered as markdown with a raw/rendered toggle
- No email sending — just research + preview

**Note:** Claude CLI not installed on EC2 yet. Works locally on Mac where Claude Code is installed.

---

## Experiment 3: Movie Search (test3-search) — DONE

**Purpose:** FTS5 full-text search over a fake dataset. Based on work's test3-activities but with 200 generated movies instead of medical activities.

**Data:** `db/seed_data.py` generates 200 movies with titles, genres, directors, cast, synopses, ratings, and reviews. Stored in SQLite with FTS5 indexes on both movies and reviews.

**Features:**
- Browse tab: filter by genre, director, sort by rating/year/title
- Search tab: FTS5 search with title/cast/synopsis mode and review mode
- Highlighted snippets via FTS5 `snippet()`, LIKE fallback for special chars
- Expandable movie cards with full details

---

## Experiment 4: Board (test4-board) — DONE

**Purpose:** Kanban board with fake project tickets. Based on work's test4-jira.

**Data:** `db/seed_data.py` generates 150 tickets (AWS-1 through AWS-150) with types, statuses, priorities, assignees, labels, and comments.

**Features:**
- List view: filterable by status, type, priority, assignee, label, search text
- Board view: columns by status (Backlog → Done), toggle Done/Cancelled visibility
- Ticket detail modal: inline editing of all fields, comments
- Create new tickets with auto-incrementing AWS-N keys
- Full CRUD on tickets and comments

---

## Experiment 5: Lambda (test5-lambda) — DONE

**Purpose:** AWS Lambda handler with local testing. Based on work's test5-lambda.

**Architecture:**
- `function/lambda_handler.py` — pure Python handler, no AWS SDK dependencies
- `test/local_server.py` — FastAPI wrapper that converts HTTP → API Gateway v2 event format
- `deploy.sh` — builds zip and uploads to AWS Lambda (not yet deployed)

**Endpoints:** GET/POST/DELETE on `/api/items` plus `/api/health`. In-memory store for local testing.

**Next step:** Actually deploy to AWS Lambda + API Gateway.

---

## Future Work

- **Systemd services** — so experiments survive EC2 reboot
- **RDS Postgres** — replace SQLite with managed Postgres for test1 or test3
- **Deploy test5 to real Lambda** — create the function, API Gateway, IAM role
- **S3 + CloudFront** — serve static files from CDN
- **SES** — add email sending to test2 (replace work's SendGrid)
- **Domain + HTTPS** — Route53 + ACM certificate
- **CI/CD** — GitHub Actions to auto-deploy on push

---

## Out of scope (for now)

- Docker / containers
- Production concerns (logging, monitoring, error tracking)
- CSS frameworks (keep it ugly and functional)
