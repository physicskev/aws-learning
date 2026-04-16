from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from models import TaskCreate, TaskUpdate, TaskResponse
import db

app = FastAPI(title="Test 1 — Task Manager")

# Initialize database on startup
db.init_db()


@app.get("/api/health")
def health():
    return {"status": "ok", "experiment": "test1-tasks"}


@app.get("/api/tasks", response_model=list[TaskResponse])
def list_tasks(status: str | None = None, priority: str | None = None, search: str | None = None):
    return db.get_all_tasks(status=status, priority=priority, search=search)


@app.get("/api/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: int):
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.post("/api/tasks", response_model=TaskResponse, status_code=201)
def create_task(body: TaskCreate):
    return db.create_task(
        title=body.title,
        description=body.description,
        status=body.status,
        priority=body.priority,
    )


@app.patch("/api/tasks/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, body: TaskUpdate):
    existing = db.get_task(task_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Task not found")
    updated = db.update_task(
        task_id,
        title=body.title,
        description=body.description,
        status=body.status,
        priority=body.priority,
    )
    return updated


@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: int):
    existing = db.get_task(task_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete_task(task_id)
    return {"deleted": True, "id": task_id}


# Serve UI — must be last
ui_path = Path(__file__).parent.parent / "ui"
app.mount("/", StaticFiles(directory=str(ui_path), html=True), name="ui")
