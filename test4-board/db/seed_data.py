"""Generate fake project tickets and ingest into SQLite."""

import sqlite3
import random
import csv
from pathlib import Path
from datetime import datetime, timedelta

DB_PATH = Path(__file__).parent / "board.db"
CSV_PATH = Path(__file__).parent / "tickets.csv"

STATUSES = ["Backlog", "To Do", "In Progress", "In Review", "Done", "Cancelled"]
TYPES = ["Bug", "Feature", "Task", "Improvement", "Epic"]
PRIORITIES = ["Critical", "High", "Medium", "Low"]
LABELS = ["Frontend", "Backend", "API", "Database", "DevOps", "Auth", "UI/UX", "Testing", "Docs"]
ASSIGNEES = [
    "Alice Chen", "Bob Martinez", "Carol Kim", "Dave Singh", "Eve Johnson",
    "Frank Lee", "Grace Park", "Hank Williams", "Iris Tanaka", "Jake Brown",
]

SUMMARIES = {
    "Bug": [
        "Fix login timeout on mobile browsers",
        "Search results not sorted correctly",
        "Memory leak in dashboard component",
        "API returns 500 on empty payload",
        "Date picker shows wrong timezone",
        "Export CSV missing header row",
        "Upload fails for files over 10MB",
        "Notification badge count incorrect",
        "Password reset link expires too quickly",
        "Dark mode breaks table borders",
    ],
    "Feature": [
        "Add bulk import from CSV",
        "Implement real-time notifications",
        "Add two-factor authentication",
        "Create public API documentation",
        "Build analytics dashboard",
        "Add webhook integrations",
        "Implement role-based access control",
        "Create email template editor",
        "Add audit log viewer",
        "Build custom report builder",
    ],
    "Task": [
        "Update dependencies to latest versions",
        "Write integration tests for auth flow",
        "Migrate database to new schema",
        "Set up CI/CD pipeline",
        "Configure monitoring alerts",
        "Document API endpoints",
        "Review and merge pending PRs",
        "Set up staging environment",
        "Create database backup script",
        "Update SSL certificates",
    ],
    "Improvement": [
        "Optimize search query performance",
        "Reduce bundle size by 30%",
        "Add pagination to all list views",
        "Improve error messages for validation",
        "Cache frequently accessed data",
        "Refactor user service layer",
        "Add loading skeletons to UI",
        "Compress API response payloads",
        "Add retry logic for external API calls",
        "Improve accessibility on forms",
    ],
    "Epic": [
        "User management overhaul",
        "Performance optimization sprint",
        "Mobile responsive redesign",
        "API v2 migration",
        "Security audit remediation",
    ],
}

def gen_description(summary, ticket_type):
    templates = [
        f"## Description\n\n{summary}\n\n## Acceptance Criteria\n\n- [ ] Implementation complete\n- [ ] Tests added\n- [ ] Documentation updated",
        f"### Context\n\nThis {ticket_type.lower()} was identified during the latest sprint review.\n\n### Details\n\n{summary}. This needs to be addressed before the next release.",
        f"**Problem:** {summary}\n\n**Expected behavior:** Should work as specified in the requirements.\n\n**Steps to reproduce:**\n1. Navigate to the relevant page\n2. Perform the action\n3. Observe the issue",
    ]
    return random.choice(templates)

def generate_tickets(n=150):
    tickets = []
    base_date = datetime(2026, 1, 1)
    key_counter = 1

    for i in range(n):
        ticket_type = random.choices(TYPES, weights=[25, 30, 25, 15, 5])[0]
        summary = random.choice(SUMMARIES[ticket_type])
        # Add variation
        if random.random() > 0.5:
            summary = summary + f" ({random.choice(['v2', 'mobile', 'admin panel', 'API', 'dashboard'])})"

        status = random.choices(STATUSES, weights=[15, 20, 20, 15, 25, 5])[0]
        priority = random.choices(PRIORITIES, weights=[5, 20, 50, 25])[0]
        labels = random.sample(LABELS, k=random.randint(1, 3))
        assignee = random.choice(ASSIGNEES) if status != "Backlog" or random.random() > 0.5 else ""
        created = base_date + timedelta(days=random.randint(0, 100), hours=random.randint(0, 23))
        updated = created + timedelta(days=random.randint(0, 14), hours=random.randint(0, 23))

        tickets.append({
            "key": f"AWS-{key_counter}",
            "summary": summary,
            "description": gen_description(summary, ticket_type),
            "type": ticket_type,
            "status": status,
            "priority": priority,
            "assignee": assignee,
            "labels": ",".join(labels),
            "created_at": created.isoformat(),
            "updated_at": updated.isoformat(),
        })
        key_counter += 1

    return tickets

def save_csv(tickets):
    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=tickets[0].keys())
        writer.writeheader()
        writer.writerows(tickets)
    print(f"Saved {len(tickets)} tickets to {CSV_PATH}")

def create_db(tickets):
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")

    conn.executescript("""
        CREATE TABLE tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            summary TEXT NOT NULL,
            description TEXT,
            type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Backlog',
            priority TEXT NOT NULL DEFAULT 'Medium',
            assignee TEXT DEFAULT '',
            labels TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER NOT NULL REFERENCES tickets(id),
            author TEXT NOT NULL,
            text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE key_counter (
            next_num INTEGER NOT NULL
        );
    """)

    for t in tickets:
        conn.execute(
            "INSERT INTO tickets (key, summary, description, type, status, priority, assignee, labels, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (t["key"], t["summary"], t["description"], t["type"], t["status"], t["priority"], t["assignee"], t["labels"], t["created_at"], t["updated_at"]),
        )

    # Seed some comments
    for ticket_id in random.sample(range(1, len(tickets) + 1), k=min(50, len(tickets))):
        for _ in range(random.randint(1, 3)):
            author = random.choice(ASSIGNEES)
            texts = [
                "Working on this now, should be ready by end of sprint.",
                "Needs more clarification on the requirements.",
                "Blocked by the API team — waiting on their endpoint.",
                "Fixed in latest commit, please review.",
                "This is a duplicate of AWS-42, should we close?",
                "Updated the priority based on customer feedback.",
                "Added unit tests, ready for review.",
                "Can we split this into smaller tasks?",
            ]
            conn.execute(
                "INSERT INTO comments (ticket_id, author, text) VALUES (?, ?, ?)",
                (ticket_id, author, random.choice(texts)),
            )

    conn.execute("INSERT INTO key_counter (next_num) VALUES (?)", (len(tickets) + 1,))
    conn.commit()

    count = conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
    comment_count = conn.execute("SELECT COUNT(*) FROM comments").fetchone()[0]
    print(f"Created {count} tickets with {comment_count} comments in {DB_PATH}")
    conn.close()

if __name__ == "__main__":
    tickets = generate_tickets(150)
    save_csv(tickets)
    create_db(tickets)
