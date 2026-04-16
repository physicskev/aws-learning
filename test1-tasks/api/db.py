import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "db" / "tasks.db"
MIGRATION_PATH = Path(__file__).parent.parent / "db" / "001_create_tasks.sql"


def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript(MIGRATION_PATH.read_text())
    conn.close()


def get_all_tasks(status: str | None = None, priority: str | None = None, search: str | None = None):
    conn = get_conn()
    query = "SELECT * FROM tasks WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if priority:
        query += " AND priority = ?"
        params.append(priority)
    if search:
        query += " AND (title LIKE ? OR description LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    query += " ORDER BY created_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_task(task_id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_task(title: str, description: str | None, status: str, priority: str):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO tasks (title, description, status, priority) VALUES (?, ?, ?, ?)",
        (title, description, status, priority),
    )
    conn.commit()
    task = conn.execute("SELECT * FROM tasks WHERE id = ?", (cur.lastrowid,)).fetchone()
    conn.close()
    return dict(task)


def update_task(task_id: int, **fields):
    conn = get_conn()
    sets = []
    params = []
    for key, val in fields.items():
        if val is not None:
            sets.append(f"{key} = ?")
            params.append(val)
    if not sets:
        conn.close()
        return get_task(task_id)
    params.append(task_id)
    conn.execute(f"UPDATE tasks SET {', '.join(sets)} WHERE id = ?", params)
    conn.commit()
    task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    return dict(task) if task else None


def delete_task(task_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
