import sqlite3
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

DB_FILE = "tasks.db"

# stage 4: Verified manual SQL execution 

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
    """Insert a new task into the SQL database."""
    title_clean = task_data.title.strip()
    
    if not title_clean:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = {"error" : "Title Cannot Be  Empty"}
        )

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO tasks (title, done) VALUES (?, ?)",
        (title_clean, 0)
    )
    conn.commit()

    new_id = cursor.lastrowid
    conn.close()

    return {"id": new_id, "title": title_clean, "done": False}

   
@app.put("/tasks/{id}")
def update_task(id: int, task_data: TaskUpdate):
    """Update an existing task's title and/or status in SQLite."""

    # 1. validation that one field is provided atleast
    if task_data.title is None and task_data.done is None:
        raise HTTPException(
            status_code = status.HTTP_404_BAD_REQUEST,
            detail = {"error": "No update fields provided"}
        )

    # 2. ensure title isnt empty if provided
    if task_data.title is not None and not task_data.title.strip():
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = {"error" : "Title cannot be empty"}
        )

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 3. check if task exists first
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (id,))
    existing_task = cursor.fetchone()

    if existing_task is None:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": f"Task {id} not found"}
        )

    # 4. determine new values (keep current value if field was not passed in request)
    new_title = task_data.title.strip() if task_data.title is not None else existing_task["title"]
    new_done = int(task_data.done) if task_data.done is not None else existing_task["done"]

    # 5. execute the SQL UPDATE
    cursor.execute(
        "UPDATE tasks SET title = ?, done = ? WHERE id = ?",
        (new_title, new_done, id)
    )
    conn.commit()
    conn.close()

    return {"id": id, "title": new_title, "done": bool(new_done)}


@app.delete("/tasks/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(id : int):
    """Remove a task from SQLite by its unique ID."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM tasks WHERE id = ?", (id,))
    conn.commit()

    deleted_count = cursor.rowcount
    conn.close()

    if deleted_count == 0:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail = {"error": f"Task {id} not found"}
        )
    
    return
    

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
def get_tasks(search: str | None = None, done: bool | None = None):
    """Retrieve tasks with optional search filtering, done status, and alphabetical sorting."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = "SELECT * FROM tasks WHERE 1=1"
    params = []

    if search:
        query += " AND title LIKE ?"
        params.append(f"%{search.strip()}%")

    if done is not None:
        query += " AND done = ?"
        params.append(1 if done else 0)

    query += " ORDER BY title ASC"

    cursor.execute(query, tuple(params))
    db_tasks = cursor.fetchall()
    conn.close()

    return [
        {"id": row["id"], "title": row["title"], "done": bool(row["done"])}
        for row in db_tasks
    ]

@app.get("/stats")
def get_stats():
    """Return database-calculated statistics using SQL COUNT functions."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Total tasks count
    cursor.execute("SELECT COUNT(*) FROM tasks")
    total_tasks = cursor.fetchone()[0]

    # Completed tasks count
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE done = 1")
    completed_tasks = cursor.fetchone()[0]

    # Pending tasks count
    pending_tasks = total_tasks - completed_tasks
    conn.close()

    return {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "pending_tasks": pending_tasks
    }


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

