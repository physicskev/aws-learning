# Learnings

Everything I learn from building on AWS with Claude Code. Not just what worked — why it worked, what broke first, and what I'd do differently.

---

## AWS Account Setup (2026-04-15)

### Getting back into an old AWS account
- Signed in as root user, had to reset password since it had been years
- Account was clean — no surprise resources running, no accumulated charges
- First thing to do: check Billing dashboard across all regions for zombie resources

### IAM user for CLI
- Created IAM user `kev` with AdministratorAccess — fine for personal learning, would never do this at work
- Created access key, ran `aws configure` locally
- Default region: us-east-1 (most services available, cheapest)
- AWS CLI was already installed via homebrew (`aws-cli/2.21.3`)
- Verified with `aws sts get-caller-identity` — shows account ID, user ARN

### EC2 instance launch (all via CLI)
- **Key pair**: `aws ec2 create-key-pair` — saves the .pem file locally at `~/.ssh/kev-aws-learning.pem`, must `chmod 400` immediately
- **Security group**: Created `aws-learning-sg`, opened ports 22 (SSH), 80 (HTTP), 443 (HTTPS) to 0.0.0.0/0
- **AMI selection**: Used `aws ec2 describe-images` with filters for Ubuntu 24.04 ARM64 — sort by CreationDate and grab the latest
- **Instance type**: `t4g.micro` — ARM/Graviton processor, free tier eligible for 750 hrs/month in first 12 months
- **Storage**: 20 GB gp3 (default is 8 GB which fills up fast with Python venvs)
- **SSH worked on second try** — first attempt got "Connection refused" because sshd hadn't started yet. EC2 "running" state doesn't mean SSH is ready. Wait ~15-30 seconds after instance enters "running" state.

### What I'd do differently
- Could attach an Elastic IP so the address doesn't change on stop/start — haven't done this yet, will add when it becomes annoying
- Should set up a billing alarm/budget immediately (haven't done this yet either)

---

## Claude Code Workflow Learnings

### Using Claude Code to manage remote servers
- Claude Code runs locally on my Mac but can SSH into the EC2 instance to run commands
- Pattern: Claude runs `ssh -i key ubuntu@ip "command"` to execute things on the server
- This means Claude Code can set up the server, install packages, edit files, and deploy — all from my local terminal

### PRD-driven development
- Write a PRD first, then hand it to Claude Code
- At work this produced 4 experiments in a single session
- The PRD acts as both documentation and instruction set
- CLAUDE.md is the quick-reference version that Claude reads on every conversation start

### Building 5 experiments in one session
- Same pattern as work: each experiment gets its own folder with `api/`, `ui/`, and optionally `db/`
- Each has its own `pyproject.toml` and `uv sync` — fully independent Python environments
- Port convention: test1=8001, test2=8002, etc.
- All verified working locally before committing

### uv pyproject.toml gotcha with hatchling
- `uv init` creates a `pyproject.toml` with `[build-system] requires = ["hatchling"]`
- Hatchling expects a Python package directory matching the project name (e.g., `test1_tasks/`)
- Since our projects aren't installable packages, we need to add `[tool.hatch.build.targets.wheel] packages = ["."]` to avoid build failures on `uv sync`
- Without this, `uv sync` fails with "Unable to determine which files to ship inside the wheel"

### SQLite FTS5 for search
- Works great at small scale (200 movies, instant searches)
- Need separate FTS tables: `CREATE VIRTUAL TABLE movies_fts USING fts5(title, director, ...)`
- FTS5 `snippet()` function highlights matches: `snippet(movies_fts, 0, '<mark>', '</mark>', '...', 40)`
- FTS5 doesn't match special characters (slashes, hyphens are token separators) — always have a LIKE fallback
- FTS5 `snippet()` can't be used across JOINs with GROUP BY — query FTS first, then fetch details

### Fake data generation pattern
- Python script in `db/seed_data.py` generates realistic fake data
- Randomized but deterministic enough to be useful (template-based summaries, weighted random choices)
- Run once to create `.db` file, re-run to rebuild from scratch
- Also save as CSV/JSON for reference and alternate import paths

### Lambda local testing pattern
- Lambda handler is pure Python — no AWS dependencies needed for the core logic
- Wrap in a FastAPI app (`local_server.py`) that converts HTTP requests to API Gateway v2 event format
- Test locally at `localhost:8005`, deploy to AWS when ready
- `context=None` for local, Lambda provides a real context object in AWS
- This separation means the handler itself is testable without any AWS mocking

### Git + GitHub CLI
- `gh auth login` must be run interactively (browser-based OAuth)
- `gh repo create --source=. --push` creates the repo AND pushes in one command
- If `git push` fails with "could not read Username", run `gh auth setup-git` to configure the credential helper
- `gh auth setup-git` only needs to run once — after that, git uses the gh token automatically

### FastAPI static file serving
- `app.mount("/", StaticFiles(directory=str(ui_path), html=True), name="ui")` serves the UI
- **Must be the last line** — it's a catch-all that intercepts all routes not matched by API endpoints
- `html=True` means `/` serves `index.html` automatically
- No need for Nginx locally — FastAPI serves both API and static files

### SSH to new EC2 instance
- EC2 "running" state doesn't mean SSH is ready — sshd takes 15-30 seconds to start after the instance enters "running"
- First `ssh` attempt will get "Connection refused" — this is normal, just wait and retry
- `aws ec2 wait instance-running` only waits for the instance state, not for SSH

(More learnings will be added as experiments are built...)
