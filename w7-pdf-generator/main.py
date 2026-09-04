from fastapi import FastAPI

app = FastAPI(title="PDF Report Generator")


@app.get("/health")
def health_check():
    return {"status": "ok"}