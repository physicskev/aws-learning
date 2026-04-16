"""Postgres (RDS) database layer."""

import psycopg2
import psycopg2.extras
import os

def get_conn():
    return psycopg2.connect(
        host=os.environ.get("PG_HOST", ""),
        port=int(os.environ.get("PG_PORT", "5432")),
        dbname=os.environ.get("PG_DB", "learning"),
        user=os.environ.get("PG_USER", "kev"),
        password=os.environ.get("PG_PASSWORD", ""),
    )


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT,
            company TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)
    conn.commit()
    cur.close()
    conn.close()


def list_contacts(search: str | None = None):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if search:
        cur.execute(
            "SELECT * FROM contacts WHERE name ILIKE %s OR email ILIKE %s OR company ILIKE %s ORDER BY created_at DESC",
            (f"%{search}%", f"%{search}%", f"%{search}%"),
        )
    else:
        cur.execute("SELECT * FROM contacts ORDER BY created_at DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]


def get_contact(contact_id: int):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM contacts WHERE id = %s", (contact_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return dict(row) if row else None


def create_contact(name: str, email: str | None, company: str | None, notes: str | None):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "INSERT INTO contacts (name, email, company, notes) VALUES (%s, %s, %s, %s) RETURNING *",
        (name, email, company, notes),
    )
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return dict(row)


def update_contact(contact_id: int, **fields):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    sets = []
    params = []
    for k, v in fields.items():
        if v is not None:
            sets.append(f"{k} = %s")
            params.append(v)
    if not sets:
        cur.close()
        conn.close()
        return get_contact(contact_id)
    sets.append("updated_at = NOW()")
    params.append(contact_id)
    cur.execute(f"UPDATE contacts SET {', '.join(sets)} WHERE id = %s RETURNING *", params)
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return dict(row) if row else None


def delete_contact(contact_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM contacts WHERE id = %s", (contact_id,))
    conn.commit()
    cur.close()
    conn.close()
