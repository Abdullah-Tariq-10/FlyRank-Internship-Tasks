from fastapi import FastAPI
from fastapi import HTTPException, status
from pydantic import BaseModel, Field


app = FastAPI()

class TaskCreate(BaseModel):
    title : str = Field(..., min_length=1)

class TaskUpdate(BaseModel):
    title : str | None = None
    done : bool | None = None

tasks = [
    {"id" : 1, "title" : "Buy Groceries", "done" : False},
    {"id": 2, "title": "Clean the car", "done": True},
    {"id": 3, "title": "Study Backend AI", "done": False}   
]

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
    """Retrieve all tasks currently in the list."""
    return tasks

@app.get("/tasks/{id}")
def get_task(id: int):
    """Retrieve a single task by its unique ID."""
    for task in tasks:
        if task["id"] == id:
            return task
    raise HTTPException(
        status_code = status.HTTP_404_NOT_FOUND,
        detail= {"error" : f"Task {id} not found"}
    )    

