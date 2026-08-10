from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
import os
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv


load_dotenv()


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:dev@localhost:5432/tasks"
)

def get_db_connection():
    """Helper function to open a connection to PostgreSQL using DATABASE_URL."""
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)

def init_db():
    """Create tasks table if it doesn't exist and seed default tasks if empty."""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # Create table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    done BOOLEAN NOT NULL DEFAULT FALSE
                )
            """)

            # Check if empty
            cursor.execute("SELECT COUNT(*) FROM tasks")
            count = cursor.fetchone()["count"]

            # Seed example tasks only on first run
            if count == 0:
                sample_tasks = [
                    ("Buy milk", False),
                    ("Learn SQL", False),
                    ("Celebrate Week 3", True)
                ]
                cursor.executemany(
                    "INSERT INTO tasks (title, done) VALUES (%s, %s)",
                    sample_tasks
                )
            conn.commit()


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

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING id",
                (title_clean, False)
            )
            new_id = cursor.fetchone()["id"]
            conn.commit()

    return {"id" : new_id, "title": title_clean, "done": False}

   
@app.put("/tasks/{id}")
def update_task(id: int, task_data: TaskUpdate):
    """Update an existing task's title and/or status in SQLite."""

    # 1. validation that one field is provided atleast
    if task_data.title is None and task_data.done is None:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = {"error": "No update fields provided"}
        )

    # 2. ensure title isnt empty if provided
    if task_data.title is not None and not task_data.title.strip():
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = {"error" : "Title cannot be empty"}
        )
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM tasks WHERE id = %s", (id,))
            existing_task = cursor.fetchone()

            if existing_task is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"error": f"Task {id} not found"}
                )

            new_title = task_data.title.strip() if task_data.title is not None else existing_task["title"]
            new_done = task_data.done if task_data.done is not None else existing_task["done"]

            cursor.execute(
                "UPDATE tasks SET title = %s, done = %s WHERE id = %s",
                (new_title, new_done, id)
            )
            conn.commit()

    return {"id": id, "title": new_title, "done": new_done}



@app.delete("/tasks/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(id : int):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM tasks WHERE id = %s", (id,))
            conn.commit()
            deleted_count = cursor.rowcount

    if deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": f"Task {id} not found"}
        )

    return
    

@app.get("/")
def read_root():
    """Verify API and DB connection health."""
    return {
        "name" : "Task API",
        "version" : "1.0",
        "endpoints" : ["/tasks"]
    }


@app.get("/health")
def check_status():
    """Verify API and DB connection health."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
        return {"status": "ok", "db": "ok"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "error", "db": "unreachable", "error": str(e)}
        )



@app.get("/tasks")
def get_tasks(search: str | None = None, done: bool | None = None):
    """Retrieve tasks with optional search filtering, done status, and alphabetical sorting."""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            query = "SELECT * FROM tasks WHERE 1=1"
            params = []

            if search:
                query += " AND title ILIKE %s"
                params.append(f"%{search.strip()}%")

            if done is not None:
                query += " AND done = %s"
                params.append(done)

            query += " ORDER BY title ASC"

            cursor.execute(query, params)
            return cursor.fetchall()



@app.get("/stats")
def get_stats():
    """Return database-calculated statistics using SQL COUNT functions."""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM tasks")
            total_tasks = cursor.fetchone()["count"]

            cursor.execute("SELECT COUNT(*) FROM tasks WHERE done = TRUE")
            completed_tasks = cursor.fetchone()["count"]

            return {
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "pending_tasks": total_tasks - completed_tasks
            }


@app.get("/tasks/{id}")
def get_task(id: int):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM tasks WHERE id = %s", (id,))
            task = cursor.fetchone()

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail = {"error" : f"Task {id} not found"}
        )

    return task

