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

## Solr (test7-solr)

- **Bootstrap Solr cores from `_default` + apply schema via the Schema API** — way cleaner than maintaining a custom configset in git. `solr-precreate exocortex` uses the built-in `_default` on first boot; a separate `setup_schema.py` then POSTs field definitions to `/schema`. Idempotent: it lists existing fields and adds only what's missing. Schema lives in Python code, not XML. (2026-04-19)
- **`facet.mincount=1` is GLOBAL in Solr** — applies to both field facets AND range facets. If you set it globally, your monthly date histogram silently loses its empty months, which breaks visual continuity. Fix: scope per field with `f.<field>.facet.mincount=1` on just the categorical facets, leave range facets alone. (2026-04-19)
- **The `/mlt` request handler isn't in Solr's `_default` configset** — calling it 404s. Use the **MLT query parser** via `/select` instead: `q={!mlt qf="body title" mintf=2 mindf=2}<doc_id>`. Same functionality, works against the default configset, no solrconfig.xml edits needed. (2026-04-19)
- **Session IDs are not globally unique when exported** — Claude Code exports can include the same `session_id` under multiple project folders (e.g. git worktree orphans). Solr silently overwrites docs with matching `id` at ingest. Fix: qualify the unique key with project (`{source}:session:{project}:{session_id}`) so each path gets its own doc. Lost 99 sessions to this before I caught it. (2026-04-19)
- **`history.jsonl` is too noisy to index as-is** — dominated by short slash-commands like `/help` and `/login` that drown out substantive content in search results. Dropped it entirely; kept sessions, project docs, summary rows, and insights. 2317 docs → 933 docs, dramatically better signal. (2026-04-19)
- **Solr Stats component gives you free aggregate analytics** — `stats=true&stats.field=duration_seconds&stats.field=started` returns sum/count/mean/min/max in the same response as your search hits. Powers a "Total time: 333 hours" stat card without a second query. (2026-04-19)
- **Solr is portable by env var** — the whole stack (ingest script + FastAPI) reads `SOLR_URL`. Local Docker, EC2, or SolrCloud — change one variable, done. Don't bake "localhost" into app code. (2026-04-19)
- **Solr `min()` function returns the cap value for missing fields, NOT 0 or null** — `stats.field={!func}min(duration_seconds, 28800)` run over docs that don't have `duration_seconds` inflates the sum by (missing_count × 28800) silently. Burned 30× inflation before catching. Fix: scope the stats sub-query with `fq=doc_type:session` (or whatever subset actually has the field). Always scope function-based stats queries. (2026-04-19)
- **Prefer "include + cap per doc" over "exclude" for outlier-tolerant stats** — Early approach was `fq=duration_seconds:[* TO 28800]` to drop long sessions. Better approach: include all docs, but cap each one's contribution via `{!func}min(field, cap)`. Reads as: "no single document can distort the aggregate." Makes stats more truthful (every session counts) without letting a 180h abandoned session dominate. (2026-04-19)
- **Per-metric caps are independent — don't expect additivity** — When you cap `user_seconds`, `assistant_seconds`, and `active_seconds` each at 8h per session, `user + agent` can exceed `active` after aggregation (if many sessions cap on different axes). This is correct behavior; design the UI copy so the three numbers read as independent views, not as components that must sum. (2026-04-19)
- **Parse per-message timestamps to reconstruct real effort time** — Wall-clock session duration (last_msg − first_msg) conflates idle time, user-active time, and model-generating time. Walking the raw `.jsonl` and classifying each gap by "who wrote the next message" gives you `user_seconds` vs `assistant_seconds` vs `idle_seconds`. Three-bucket pattern: gap ≤ threshold AND next event is real user → user; gap ≤ threshold AND next is assistant/tool/system → agent; gap > threshold → idle. The gap threshold matters a lot — started at 5 min, bumped to 10 min when realistic "user thinking about response" gaps got mis-classified as idle. (2026-04-19)
- **"Real user message" ≠ "`type:user` event"** — In Claude Code session jsonl, `type:user` can mean either a genuine user input OR a synthetic event echoing tool_result back to the model. When measuring user engagement time, only genuine user messages (content is a string, or content list has ≥1 non-`tool_result` text block) should count as user-driven events. Synthetic user events are model-driven and should count as agent time. (2026-04-19)

## Docker for local infra

- **Named volume > bind mount for Solr data** — `solr_data:/var/solr` in docker-compose avoids host UID/permission issues (the `solr:9` image runs as UID 8983). Bind mounts need `chown` on the host. Named volumes just work. (2026-04-19)
- **`solr-precreate <core>` only runs on first boot** — if you change config and restart, the pre-create is skipped because the core already exists. To apply new settings, either tear down the volume (`docker compose down -v`) or use the Schema/Config API. (2026-04-19)
- **Healthcheck with `wget -qO-` beats `curl`** — the official `solr:9` image ships `wget` but not `curl`. `wget -qO- http://localhost:8983/solr/<core>/admin/ping?wt=json | grep -q '"status":"OK"'` gives you a proper healthy/unhealthy gate in compose. (2026-04-19)

## Frontend: async races + event handling

- **Prefer a monotonic sequence number over AbortController for "only render the latest response"** — `let seq = 0; const mine = ++seq; ... if (mine !== seq) return;` is 3 lines, works across any async chain, and doesn't rely on fetch honoring the signal between `await fetch()` and `await r.json()`. AbortController is fine but more moving parts. (2026-04-19)
- **`<label><input type="checkbox">` synthesizes clicks you can't always see** — clicking anywhere in the label fires a click on the child input; the input toggles; the change event fires. Combined with rebuilding the DOM on every search response, this produced a phantom "stale render" bug that looked like the filter wasn't applying. Fix: ditch the input entirely. Use a plain `<div>` with a styled `<span>` as the visual checkbox, plus **event delegation on the container** that reads `data-*` attributes. One handler attached once, zero closures over re-rendered DOM nodes. (2026-04-19)
- **Always CLEAR the DOM before deciding to hide it** — `renderStats()` had `if (!hasData) { card.classList.add('hidden'); return; }` BEFORE `card.innerHTML = ''`. When a new filter produced an empty stats shape, the card hid but kept its prior content, so the "hidden" content was still in the DOM and became visible the next time `classList.remove('hidden')` ran. Always clear first, then decide to hide. (2026-04-19)
- **Add a visible debug line, not just console.log** — when investigation-heavy UI misbehaves, a tiny `<div id="debug">` that shows "fetched #3: /api/search?... → 125 hits" lets the user diagnose without opening DevTools. Huge for remote debugging over screenshots. (2026-04-19)
- **`fetch(..., { cache: 'no-store' })` eliminates browser-cache as a suspect** — by default, `fetch` may serve cached responses for same-URL GETs. When debugging "the server returned the right thing but the UI shows wrong data", rule this out explicitly. (2026-04-19)
- **URL state sync is the bookmarkability feature** — `history.replaceState` on every state change + `urlToState` on load + a `popstate` handler for back/forward. No client storage, no server sessions — the URL is the single source of truth. Investigation tools live and die by this: "send me the view you're looking at" has to be copy-paste-URL simple. (2026-04-19)
- **Don't cram too many stat boxes on one row — readability beats density** — Tried to force 6 activity boxes onto a single row with `minmax(0, 1fr)` and text ellipsis. Result: values truncated to "79..." and labels became "AGENT T..." — all data, zero readability. Lesson: pick a reasonable minimum box width and let the grid wrap to multiple rows naturally. Two rows of three beats one row of six when each box has to show a number, a label, and a subtitle. (2026-04-19)
- **Color-code stat variants to convey meaning at a glance** — Active time in light blue, User time in stronger blue, Agent time in dark slate with white text, Idle in muted grey. The user reads "who's doing what" without parsing labels. Works far better than uniformly-styled boxes with different labels. (2026-04-19)
- **CSS `:hover::after` + `data-tip` attribute beats native `title`** — Native `title` tooltips have a ~1s delay, can't be styled, and look bad. A small CSS tooltip using `[data-tip]:hover::after { content: attr(data-tip); ... }` appears instantly, looks consistent with the UI, and supports multi-line with `white-space: normal`. Watch out: don't put `overflow: hidden` on the element that hosts the tooltip — it'll clip the `::after`. (2026-04-19)
- **Change thresholds require a full re-ingest, not just a config reload** — The 5→10 minute idle threshold lives in `timeline.py` as a constant. Bumping it didn't magically update existing docs — had to re-run `ingest.py`. Design: decide early whether a knob is query-time (always live) or ingest-time (needs re-ingest). Compute-on-ingest is faster per query but less flexible. (2026-04-19)

## Claude Code — end-of-session workflow

- **`/update-all` wrapper skill** — composes `/update-claude`, `/update-prd`, `/update-learnings`, then commits and pushes. Originally the sub-skills carried `disable-model-invocation: true` (user-invocable only), so the wrapper had to re-execute their instructions inline. After removing that flag from all four, the wrapper became a clean 3-line orchestrator (`Skill(update-claude)` + `Skill(update-prd)` + `Skill(update-learnings)` + commit). Tradeoff: removing the flag means Claude *can* auto-invoke these skills mid-session without being asked. Worth it for the DRY win when skills are idempotent and only write to three well-known files. (2026-04-19)
- **`disable-model-invocation: true` on a skill makes it slash-command-only, NOT programmatic-only** — Can't call such skills via the Skill tool from another skill. If you want composability across skills, leave the flag off. If you want "user types this or nothing", set it. Don't set it by default. (2026-04-19)

## Gotchas & Pitfalls

- **uv + hatchling "Unable to determine which files to ship"** — `uv init` creates a pyproject.toml with hatchling as the build backend, which expects a Python package directory matching the project name. For FastAPI apps that aren't installable packages, add `[tool.hatch.build.targets.wheel] packages = ["."]` to fix it. (2026-04-15)
- **Python `global` declaration must come before any use** — putting `global _items` after reading `_items` in the same function causes `SyntaxError: name '_items' is used prior to global declaration`. Move the `global` to the top of the function. (2026-04-15)
- **Port per experiment matters for parallel local dev** — each experiment on its own port (8001-8005) means you can run multiple simultaneously. If a port is already in use, `lsof -ti:8001` finds the PID to kill. (2026-04-15)
