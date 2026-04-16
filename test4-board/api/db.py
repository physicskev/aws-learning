import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / "db" / "board.db"


def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


# --- Tickets ---

def get_tickets(status=None, ticket_type=None, priority=None, assignee=None, label=None, search=None):
    conn = get_conn()
    query = "SELECT * FROM tickets WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if ticket_type:
        query += " AND type = ?"
        params.append(ticket_type)
    if priority:
        query += " AND priority = ?"
        params.append(priority)
    if assignee:
        query += " AND assignee = ?"
        params.append(assignee)
    if label:
        query += " AND labels LIKE ?"
        params.append(f"%{label}%")
    if search:
        query += " AND (summary LIKE ? OR key LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    query += " ORDER BY created_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_ticket(ticket_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if not row:
        conn.close()
        return None
    ticket = dict(row)
    comments = conn.execute(
        "SELECT * FROM comments WHERE ticket_id = ? ORDER BY created_at DESC", (ticket_id,)
    ).fetchall()
    ticket["comments"] = [dict(c) for c in comments]
    conn.close()
    return ticket


def create_ticket(summary, description=None, ticket_type="Task", priority="Medium", assignee="", labels=""):
    conn = get_conn()
    row = conn.execute("SELECT next_num FROM key_counter").fetchone()
    next_num = row[0]
    key = f"AWS-{next_num}"
    conn.execute("UPDATE key_counter SET next_num = ?", (next_num + 1,))
    conn.execute(
        "INSERT INTO tickets (key, summary, description, type, status, priority, assignee, labels) VALUES (?, ?, ?, ?, 'Backlog', ?, ?, ?)",
        (key, summary, description, ticket_type, priority, assignee, labels),
    )
    conn.commit()
    ticket = conn.execute("SELECT * FROM tickets WHERE key = ?", (key,)).fetchone()
    conn.close()
    return dict(ticket)


def update_ticket(ticket_id, **fields):
    conn = get_conn()
    sets = []
    params = []
    for k, v in fields.items():
        if v is not None:
            sets.append(f"{k} = ?")
            params.append(v)
    if not sets:
        conn.close()
        return get_ticket(ticket_id)
    sets.append("updated_at = ?")
    params.append(datetime.now().isoformat())
    params.append(ticket_id)
    conn.execute(f"UPDATE tickets SET {', '.join(sets)} WHERE id = ?", params)
    conn.commit()
    ticket = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    conn.close()
    return dict(ticket) if ticket else None


def delete_ticket(ticket_id):
    conn = get_conn()
    conn.execute("DELETE FROM comments WHERE ticket_id = ?", (ticket_id,))
    conn.execute("DELETE FROM tickets WHERE id = ?", (ticket_id,))
    conn.commit()
    conn.close()


# --- Comments ---

def add_comment(ticket_id, author, text):
    conn = get_conn()
    conn.execute("INSERT INTO comments (ticket_id, author, text) VALUES (?, ?, ?)", (ticket_id, author, text))
    conn.commit()
    comment = conn.execute("SELECT * FROM comments WHERE ticket_id = ? ORDER BY id DESC LIMIT 1", (ticket_id,)).fetchone()
    conn.close()
    return dict(comment)


def delete_comment(comment_id):
    conn = get_conn()
    conn.execute("DELETE FROM comments WHERE id = ?", (comment_id,))
    conn.commit()
    conn.close()


# --- Filters ---

def get_filter_options():
    conn = get_conn()
    statuses = [r[0] for r in conn.execute("SELECT DISTINCT status FROM tickets ORDER BY status").fetchall()]
    types = [r[0] for r in conn.execute("SELECT DISTINCT type FROM tickets ORDER BY type").fetchall()]
    priorities = [r[0] for r in conn.execute("SELECT DISTINCT priority FROM tickets ORDER BY priority").fetchall()]
    assignees = [r[0] for r in conn.execute("SELECT DISTINCT assignee FROM tickets WHERE assignee != '' ORDER BY assignee").fetchall()]
    # Parse labels (comma-separated)
    label_rows = conn.execute("SELECT DISTINCT labels FROM tickets WHERE labels != ''").fetchall()
    label_set = set()
    for r in label_rows:
        for l in r[0].split(","):
            label_set.add(l.strip())
    conn.close()
    return {
        "statuses": statuses,
        "types": types,
        "priorities": priorities,
        "assignees": assignees,
        "labels": sorted(label_set),
    }


# --- Board data ---

def get_board_data():
    """Return tickets grouped by status for the board view."""
    conn = get_conn()
    rows = conn.execute("SELECT * FROM tickets ORDER BY priority, created_at DESC").fetchall()
    conn.close()
    board = {}
    for r in rows:
        ticket = dict(r)
        status = ticket["status"]
        if status not in board:
            board[status] = []
        board[status].append(ticket)
    return board
