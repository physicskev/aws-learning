# Learnings

Insights and patterns discovered while building with Claude Code, AWS, and FastAPI experiments.

---

## Claude Code Workflow

- **PRD-driven development is the fastest way to work with Claude Code** — write a PRD first, hand it to Claude Code, it builds the whole thing. At work this produced 4 experiments in one session; here it produced 5. The PRD acts as both documentation and instruction set. (2026-04-15)
- **CLAUDE.md is the quick-reference layer** — Claude reads it at the start of every conversation. PRD has the full spec, CLAUDE.md has the "how to run things" cheat sheet. Both are needed. (2026-04-15)
- **Claude Code can manage remote servers via SSH** — it runs locally on my Mac but executes `ssh -i key ubuntu@ip "command"` to set up servers, install packages, edit files, and deploy. No need to SSH in manually for most things. (2026-04-15)
- **Let Claude build all experiments in one session** — don't context-switch. Give it the full scope, let it build test1 through test5 sequentially, verify each one, then commit everything at the end. Task tracking (`TaskCreate`/`TaskUpdate`) helps it stay organized. (2026-04-15)
- **`gh auth login` must be interactive** — Claude can't run it for you. Use `! gh auth login -p https -w` from the Claude Code prompt so it runs in the same shell session. After that, `gh auth setup-git` makes git push work without further auth issues. (2026-04-15)

## Integration Patterns

- **FastAPI static file mount must be the last line** — `app.mount("/", StaticFiles(...), name="ui")` is a catch-all. Put it before your routes and it swallows `/api/*` paths. `html=True` makes `/` serve `index.html` automatically. No Nginx needed for local dev. (2026-04-15)
- **Lambda local testing via FastAPI wrapper** — keep the Lambda handler as pure Python (no AWS SDK needed). Wrap it in a FastAPI app (`local_server.py`) that converts HTTP requests to API Gateway v2 event format. Pass `context=None` locally. This means zero AWS mocking and the handler is testable anywhere. (2026-04-15)
- **SQLite FTS5 is plenty for small-scale search** — 200 movies with instant results. Create separate virtual tables (`CREATE VIRTUAL TABLE ... USING fts5`), use `snippet()` for highlighted matches. Two gotchas: (1) `snippet()` fails across JOINs with GROUP BY — query FTS first, then join; (2) special characters like `/` and `-` are token separators — always have a LIKE fallback. (2026-04-15)
- **Fake data generation pattern** — put a `seed_data.py` in `db/`, use template-based random generation with `random.choice` and `random.sample`, write to SQLite AND export as CSV/JSON. Run once to create `.db`, re-run to rebuild. Gitignore the `.db` if large. (2026-04-15)
- **GitHub CLI one-liner for new repos** — `gh repo create aws-learning --public --source=. --push` creates the repo and pushes in one command. If `git push` later fails with "could not read Username", run `gh auth setup-git` once to fix the credential helper permanently. (2026-04-15)

## AWS Infrastructure

- **EC2 "running" ≠ SSH ready** — `aws ec2 wait instance-running` returns as soon as the instance state changes, but sshd takes 15-30 more seconds to start. First SSH attempt will get "Connection refused" — just wait and retry. (2026-04-15)
- **t4g.micro is the sweet spot for learning** — ARM/Graviton, free tier eligible (750 hrs/month for 12 months). Cheaper than t2.micro and better performance. (2026-04-15)
- **Always bump EBS to 20 GB** — default 8 GB fills up fast with Python venvs and dependencies. 20 GB gp3 is still free tier. (2026-04-15)
- **AMI selection via CLI** — `aws ec2 describe-images --owners 099720109477 --filters "Name=name,Values=ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-arm64-server-*"` then sort by `CreationDate` and grab the latest. Owner `099720109477` is Canonical (Ubuntu). (2026-04-15)
- **Elastic IP is free while attached to a running instance** — but costs ~$3.65/month when the instance is stopped. If you stop EC2 for a while, consider releasing the EIP and re-allocating later. (2026-04-16)
- **Set up billing alerts immediately on a new account** — Budgets → Create a $10/month budget with email alerts. Haven't done this yet — should be next. (2026-04-15)
- **AWS CLI can do everything the console can** — `aws ec2`, `aws rds`, `aws dynamodb`, `aws lambda` — full control over every service. With Claude Code running CLI commands, you can manage all of AWS without opening a browser. IAM user `kev` has `AdministratorAccess`. (2026-04-16)

## EC2 Deployment

- **Full deploy from local Mac via SSH in under 3 minutes** — `ssh ubuntu@ip 'bash -s' << 'EOF'` with a heredoc lets Claude Code run multi-line scripts on EC2 without interactive SSH. Install uv, clone repo, uv sync all experiments, seed data, configure Nginx — all scripted. (2026-04-15)
- **Nginx config at `/etc/nginx/sites-available/experiments`** — one `location /testN/` block per experiment with `proxy_pass http://127.0.0.1:800N/;`. The trailing `/` on proxy_pass strips the `/testN/` prefix so FastAPI sees clean paths. Root `/` location serves an HTML landing page with links. (2026-04-15)
- **`nohup` keeps processes alive after SSH disconnect, but not reboot** — `nohup uv run uvicorn ... > /tmp/testN.log 2>&1 &` is the pattern. For reboot persistence, need systemd services (not set up yet). (2026-04-15)
- **`pkill -f uvicorn` over SSH can kill the SSH session itself** — if the signal propagates weirdly. Use `killall uvicorn` or `bash -s` heredoc with `killall -q` instead. The `-q` suppresses "no process found" errors. (2026-04-15)
- **Bind to 127.0.0.1 on EC2, not 0.0.0.0** — Nginx handles external traffic. Uvicorn only needs to listen on localhost since Nginx proxies to it. This prevents direct access to ports 8001-8005 bypassing Nginx. (2026-04-15)

## Domain & SSL

- **Let's Encrypt + Certbot = free SSL in one command** — `sudo certbot --nginx -d physicskev.com -d www.physicskev.com --non-interactive --agree-tos -m email --redirect` does everything: gets the cert, edits Nginx config for SSL, sets up HTTP→HTTPS redirect, and schedules auto-renewal. (2026-04-15)
- **Need a domain for SSL — can't cert a bare IP** — Let's Encrypt won't issue certs for IP addresses. Cheapest path: buy a domain (~$10/year on Namecheap), point A records at the Elastic IP. (2026-04-15)
- **Attach Elastic IP before setting up DNS** — otherwise DNS points at an ephemeral IP that changes on stop/start. Elastic IP is free while associated with a running instance. Allocated `eipalloc-0132e4fd0a6c21d41` → `32.194.2.97`. (2026-04-15)
- **Namecheap DNS propagates fast** — root domain A record resolved within a minute. `www` CNAME took slightly longer. Use `dig +short physicskev.com` to check. (2026-04-15)
- **Update Nginx `server_name` before running Certbot** — Certbot uses the server_name directive to know which server block to modify. Change `server_name _;` to `server_name physicskev.com www.physicskev.com;` first. (2026-04-15)

## Cloud Databases

- **RDS Postgres free tier: `db.t4g.micro`, 750 hrs/month, 20 GB** — same managed Postgres as production workloads. Creates in ~5 minutes via CLI. Must create a security group that allows port 5432 from your IP. Key gotcha: the instance runs 24/7 and eats free tier hours even when idle. You can stop it, but it auto-restarts after 7 days. (2026-04-16)
- **DynamoDB is always free at low usage** — 25 GB storage + 25 read/write capacity units, permanently free (not just 12 months). Use `PAY_PER_REQUEST` billing mode so you never worry about provisioned capacity. (2026-04-16)
- **DynamoDB partition key design matters** — use `pk` (partition key) + `sk` (sort key) pattern. Group related items under the same partition: `BOOKMARK#aws`, `BOOKMARK#python`. Query by partition is fast; scan across all partitions is slow and expensive. This is the biggest mental shift from SQL. (2026-04-16)
- **Postgres vs DynamoDB in practice** — Postgres: SQL, schemas, JOINs, ILIKE search, familiar. DynamoDB: NoSQL, key-value, no JOINs, design your keys around your access patterns. Use Postgres when you need relational queries; use DynamoDB when you need cheap, always-on, simple lookups. (2026-04-16)
- **RDS security group for local dev** — create a separate security group (`rds-learning-sg`) that allows port 5432 from your current IP (`curl -s https://api.ipify.org`). Also allow from the EC2 security group so the instance can connect later. Your IP may change — update the rule if you can't connect. (2026-04-16)
- **Environment variables for database credentials** — use a `.env` file (gitignored) with `PG_HOST`, `PG_PASSWORD`, etc. Load with `set -a && source .env && set +a` before running uvicorn. Cleaner than work's `secret.py` pattern and more standard. (2026-04-16)
- **`psycopg2.extras.RealDictCursor` returns real dicts** — without it, `psycopg2` returns tuples. Use `cursor_factory=psycopg2.extras.RealDictCursor` to get dict rows that serialize directly to JSON. (2026-04-16)
- **boto3 uses your `~/.aws/credentials` automatically** — no need to pass access keys in code. The `aws configure` setup from earlier works for both CLI and boto3. Just set the region via env var or boto3 resource constructor. (2026-04-16)
- **Develop locally, deploy selectively** — build and test on your Mac (fast iteration), use cloud databases for persistence (data survives restarts), deploy individual features as Lambda functions when you want to share them. EC2 stays stopped most of the time. (2026-04-16)

## Gotchas & Pitfalls

- **uv + hatchling "Unable to determine which files to ship"** — `uv init` creates a pyproject.toml with hatchling as the build backend, which expects a Python package directory matching the project name. For FastAPI apps that aren't installable packages, add `[tool.hatch.build.targets.wheel] packages = ["."]` to fix it. (2026-04-15)
- **Python `global` declaration must come before any use** — putting `global _items` after reading `_items` in the same function causes `SyntaxError: name '_items' is used prior to global declaration`. Move the `global` to the top of the function. (2026-04-15)
- **Port per experiment matters for parallel local dev** — each experiment on its own port (8001-8005) means you can run multiple simultaneously. If a port is already in use, `lsof -ti:8001` finds the PID to kill. (2026-04-15)
