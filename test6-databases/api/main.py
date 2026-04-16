from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import pg_db
import dynamo_db

app = FastAPI(title="Test 6 — Cloud Databases")


# --- Models ---

class ContactCreate(BaseModel):
    name: str
    email: Optional[str] = None
    company: Optional[str] = None
    notes: Optional[str] = None

class ContactUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    notes: Optional[str] = None

class BookmarkCreate(BaseModel):
    category: str
    title: str
    url: str
    notes: Optional[str] = None

class BookmarkUpdate(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    notes: Optional[str] = None


# --- Health ---

@app.get("/api/health")
def health():
    status = {"experiment": "test6-databases", "postgres": "unknown", "dynamodb": "unknown"}
    try:
        pg_db.get_conn().close()
        status["postgres"] = "connected"
    except Exception as e:
        status["postgres"] = f"error: {e}"
    try:
        dynamo_db.get_table().table_status
        status["dynamodb"] = "connected"
    except Exception as e:
        status["dynamodb"] = f"error: {e}"
    return status


@app.post("/api/pg/init")
def init_postgres():
    """Create the contacts table if it doesn't exist."""
    pg_db.init_db()
    return {"status": "initialized"}


# --- Postgres: Contacts ---

@app.get("/api/pg/contacts")
def list_contacts(search: str | None = None):
    return pg_db.list_contacts(search=search)


@app.get("/api/pg/contacts/{contact_id}")
def get_contact(contact_id: int):
    contact = pg_db.get_contact(contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@app.post("/api/pg/contacts", status_code=201)
def create_contact(body: ContactCreate):
    return pg_db.create_contact(name=body.name, email=body.email, company=body.company, notes=body.notes)


@app.patch("/api/pg/contacts/{contact_id}")
def update_contact(contact_id: int, body: ContactUpdate):
    existing = pg_db.get_contact(contact_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Contact not found")
    return pg_db.update_contact(contact_id, name=body.name, email=body.email, company=body.company, notes=body.notes)


@app.delete("/api/pg/contacts/{contact_id}")
def delete_contact(contact_id: int):
    existing = pg_db.get_contact(contact_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Contact not found")
    pg_db.delete_contact(contact_id)
    return {"deleted": True, "id": contact_id}


# --- DynamoDB: Bookmarks ---

@app.get("/api/dynamo/categories")
def list_categories():
    return dynamo_db.get_categories()


@app.get("/api/dynamo/bookmarks")
def list_bookmarks(category: str | None = None):
    return dynamo_db.list_bookmarks(category=category)


@app.get("/api/dynamo/bookmarks/{category}/{bookmark_id}")
def get_bookmark(category: str, bookmark_id: str):
    item = dynamo_db.get_bookmark(category, bookmark_id)
    if not item:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    return item


@app.post("/api/dynamo/bookmarks", status_code=201)
def create_bookmark(body: BookmarkCreate):
    return dynamo_db.create_bookmark(category=body.category, title=body.title, url=body.url, notes=body.notes)


@app.patch("/api/dynamo/bookmarks/{category}/{bookmark_id}")
def update_bookmark(category: str, bookmark_id: str, body: BookmarkUpdate):
    existing = dynamo_db.get_bookmark(category, bookmark_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    return dynamo_db.update_bookmark(category, bookmark_id, title=body.title, url=body.url, notes=body.notes)


@app.delete("/api/dynamo/bookmarks/{category}/{bookmark_id}")
def delete_bookmark(category: str, bookmark_id: str):
    existing = dynamo_db.get_bookmark(category, bookmark_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    dynamo_db.delete_bookmark(category, bookmark_id)
    return {"deleted": True, "category": category, "id": bookmark_id}


# Serve UI — must be last
ui_path = Path(__file__).parent.parent / "ui"
app.mount("/", StaticFiles(directory=str(ui_path), html=True), name="ui")
