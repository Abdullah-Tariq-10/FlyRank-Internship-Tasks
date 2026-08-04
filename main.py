import sqlite3
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

DB_FILE = "tasks.db"


# stage 0: Database setup and seeding
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # create tasks table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            done INTEGER NOT NULL DEFAULT 0
        )
    """)

    # seed 3 example tasks ONLY if the table is empty
    cursor.execute("SELECT COUNT(*) FROM tasks")
    count = cursor.fetchone()[0]

    if count == 0:
        sample_tasks = [
            ("Buy milk", 0),
            ("Learn SQL", 0),
            ("Celebrate Week 3", 1)
        ]
        cursor.executemany("INSERT INTO tasks (title, done) VALUES (?, ?)", sample_tasks)
        conn.commit()

    conn.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(lifespan=lifespan)

# Pydantic schemas

class TaskCreate(BaseModel):
    title : str = Field(..., min_length=1)

class TaskUpdate(BaseModel):
    title : str | None = None
    done : bool | None = None


# endpoints

@app.post("/tasks", status_code=status.HTTP_201_CREATED)
def create_task(task_data : TaskCreate):
    """Create a brand new task in the list."""
    if not task_data.title.strip():
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = {"error" : "Title Cannot Be  Empty"}
        )

    new_id = max(t["id"] for t in tasks) + 1 if tasks else 1

    new_task = {
        "id" : new_id,
        "title" : task_data.title,
        "done" : False
    }

    tasks.append(new_task)

    return new_task

@app.put("/tasks/{id}")
def update_task(id: int, task_data: TaskUpdate):
    """Update an existing task's title and/or status."""
    task_to_update = None
    for task in tasks:
        if task["id"] == id:
            task_to_update = task
            break
    
    if not task_to_update:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail = {"error": f"Task {id} not found"}
        )
    
    if task_data.title is None and task_data.done is None:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = {"error" : "No update fields provided"}
        )
    
    if task_data.title is not None and not task_data.title.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Title cannot be empty"}
        )
    
    if task_data.title is not None:
        task_to_update["title"] = task_data.title
    if task_data.done is not None:
        task_to_update["done"] = task_data.done

    return task_to_update


@app.delete("/tasks/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(id : int):
    """Remove a task from the list by its unique ID."""
    for index,task in enumerate(tasks):
        if task["id"] == id:
            tasks.pop(index)
            return

    raise HTTPException(
        status_code = status.HTTP_404_NOT_FOUND,
        detail={"error": f"Task {id} not found"}
    )


@app.get("/")
def read_root():
    """Get basic API metadata and available resource paths."""
    return {
        "name" : "Task API",
        "version" : "1.0",
        "endpoints" : ["/tasks"]
    }


@app.get("/health")
def check_status():
    """Verify the API server is healthy and operational."""
    return {"status": "ok"}


@app.get("/tasks")
def get_tasks():
    """Retrieve all tasks currently in the database."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM tasks")
    db_tasks = cursor.fetchall()
    conn.close()
    return [
        {"id": row["id"], "title": row["title"], "done": bool(row["done"])}
        for row in db_tasks
    ]

@app.get("/tasks/{id}")
def get_task(id: int):
    """Retrieve a single task by its unique ID from the database."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM tasks WHERE id = ?", (id,))
    task = cursor.fetchone()
    conn.close()

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail = {"error" : f"Task {id} not found"}
        )

    return {"id": task["id"], "title": task["title"], "done": bool(task["done"])}

