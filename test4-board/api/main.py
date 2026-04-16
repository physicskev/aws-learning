from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import db

app = FastAPI(title="Test 4 — Board")


class TicketCreate(BaseModel):
    summary: str
    description: Optional[str] = None
    type: Optional[str] = "Task"
    priority: Optional[str] = "Medium"
    assignee: Optional[str] = ""
    labels: Optional[str] = ""


class TicketUpdate(BaseModel):
    summary: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assignee: Optional[str] = None
    labels: Optional[str] = None


class CommentCreate(BaseModel):
    author: str
    text: str


@app.get("/api/health")
def health():
    return {"status": "ok", "experiment": "test4-board"}


@app.get("/api/filters")
def filters():
    return db.get_filter_options()


@app.get("/api/tickets")
def list_tickets(status: str | None = None, type: str | None = None,
                 priority: str | None = None, assignee: str | None = None,
                 label: str | None = None, search: str | None = None):
    return db.get_tickets(status=status, ticket_type=type, priority=priority,
                          assignee=assignee, label=label, search=search)


@app.get("/api/board")
def board():
    return db.get_board_data()


@app.get("/api/tickets/{ticket_id}")
def get_ticket(ticket_id: int):
    ticket = db.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@app.post("/api/tickets", status_code=201)
def create_ticket(body: TicketCreate):
    return db.create_ticket(
        summary=body.summary,
        description=body.description,
        ticket_type=body.type,
        priority=body.priority,
        assignee=body.assignee,
        labels=body.labels,
    )


@app.patch("/api/tickets/{ticket_id}")
def update_ticket(ticket_id: int, body: TicketUpdate):
    existing = db.get_ticket(ticket_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return db.update_ticket(
        ticket_id,
        summary=body.summary,
        description=body.description,
        type=body.type,
        status=body.status,
        priority=body.priority,
        assignee=body.assignee,
        labels=body.labels,
    )


@app.delete("/api/tickets/{ticket_id}")
def delete_ticket(ticket_id: int):
    existing = db.get_ticket(ticket_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Ticket not found")
    db.delete_ticket(ticket_id)
    return {"deleted": True, "id": ticket_id}


@app.post("/api/tickets/{ticket_id}/comments", status_code=201)
def add_comment(ticket_id: int, body: CommentCreate):
    existing = db.get_ticket(ticket_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return db.add_comment(ticket_id, body.author, body.text)


@app.delete("/api/comments/{comment_id}")
def delete_comment(comment_id: int):
    db.delete_comment(comment_id)
    return {"deleted": True, "id": comment_id}


# Serve UI — must be last
ui_path = Path(__file__).parent.parent / "ui"
app.mount("/", StaticFiles(directory=str(ui_path), html=True), name="ui")
