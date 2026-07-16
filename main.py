from fastapi import FastAPI
from fastapi import HTTPException, status
from pydantic import BaseModel, Field


app = FastAPI()

class TaskCreate(BaseModel):
    title : str = Field(..., min_length=1)

tasks = [
    {"id" : 1, "title" : "Buy Groceries", "done" : False},
    {"id": 2, "title": "Clean the car", "done": True},
    {"id": 3, "title": "Study Backend AI", "done": False}   
]

@app.post("/tasks", status_code=status.HTTP_201_CREATED)
def create_task(task_data : TaskCreate):
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


@app.get("/")
def read_root():
    return {
        "name" : "Task API",
        "version" : "1.0",
        "endpoints" : ["/tasks"]
    }


@app.get("/health")
def check_status():
    return {"status": "ok"}


@app.get("/tasks")
def get_tasks():
    return tasks

@app.get("/tasks/{id}")
def get_task(id: int):
    for task in tasks:
        if task["id"] == id:
            return task
    raise HTTPException(
        status_code = status.HTTP_404_NOT_FOUND,
        detail= {"error" : f"Task {id} not found"}
    )    

