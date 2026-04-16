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

## Future Experiments (not yet started)

These mirror the work experiments but with personal/fake data:

### Experiment 2: Data Explorer (test2-explorer)
Browse and search a dataset. Equivalent to test1-status + test3-activities from work. Use a public dataset (e.g., movies, books, recipes) instead of medical data. Practice SQLite FTS5 full-text search.

### Experiment 3: Board/Tracker (test3-board)
Kanban board with CRUD. Equivalent to test4-jira from work. Fake project tickets. Practice inline editing, swimlane views, Excel/CSV import.

### Experiment 4: Lambda Function (test4-lambda)
Serverless endpoint. Equivalent to test5-lambda from work. Practice Lambda, API Gateway, IAM roles, VPC if connecting to RDS.

### Experiment 5: Full AWS Stack (test5-full)
Combine everything: RDS Postgres, S3 for file storage, SES for email, CloudFront for CDN. The "graduation" experiment.

---

## Out of scope (for now)

- Domain name / HTTPS (use raw IP + HTTP for learning)
- Docker / containers
- CI/CD pipelines
- Production concerns (logging, monitoring, error tracking)
- CSS frameworks (keep it ugly and functional)

---

## How to start

Give this PRD to Claude Code and say: "Set up the EC2 server (install uv, nginx, git) and build experiment 1."
