from fastapi import FastAPI
from fastapi import HTTPException, status
app = FastAPI()

tasks = [
    {"id" : 1, "title" : "Buy Groceries", "done" : False},
    {"id": 2, "title": "Clean the car", "done": True},
    {"id": 3, "title": "Study Backend AI", "done": False}   
]


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

