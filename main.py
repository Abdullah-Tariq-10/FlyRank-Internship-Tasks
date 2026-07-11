from fastapi import FastAPI

app = FastAPI()

# Endpoint 1: The root endpoint
@app.get("/")
def read_root():
    return {"message": "Hello World! This is my first API."}

# Endpoint 2: A simple status check
@app.get("/status")
def check_status():
    return {"status": "active", "track": "Backend AI Engineering"}