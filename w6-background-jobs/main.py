import datetime
import inspect
import os
import uuid
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import inngest
import inngest.fast_api
from pydantic import BaseModel, Field

# Enable local dev mode bypass
os.environ["INNGEST_DEV"] = "1"

# 1. In-memory storage for reports
reports: dict[str, dict] = {}

# 2. Inngest client
inngest_client = inngest.Inngest(
    app_id="report-api",
    is_production=False
)


#3. Request schema
class ReportCreate(BaseModel):
    topic : str = Field(..., min_length=1)

# func 1: say hello
@inngest_client.create_function(
    fn_id="say-hello",
    trigger=inngest.TriggerEvent(event="test/hello")
)
async def say_hello(*args, **kwargs):
    ctx = args[0] if len(args) > 0 else kwargs.get("ctx")
    step = args[1] if len(args) > 1 else getattr(ctx, "step", None)
    if step:
        await step.sleep("sleep-5-seconds", datetime.timedelta(seconds=5))
    return "Hello from the background!"

# func 2: make-report
@inngest_client.create_function(
    fn_id = "make-report",
    trigger=inngest.TriggerEvent(event="report/requested"),
    retries=2
)

async def make_report(*args, **kwargs):
    ctx = args[0] if len(args) > 0 else kwargs.get("ctx")
    step = args[1] if len(args) > 1 else getattr(ctx, "step", None)

    #Extract even data safely
    event_data = ctx.event.data if hasattr(ctx, "event") and hasattr(ctx.event, "data") else {}
    report_id = event_data.get("id")
    topic = event_data.get("topic", "general")

    if step:
        #step 1: simulate heavy work
        await step.sleep("do-the-slow-work", datetime.timedelta(seconds=8))

        #step 2: build the final report and update the in-memory store
        def build_report():
            if topic == "fail":
                raise RuntimeError("The report oven is broken!")
            
            if report_id in reports:
                reports[report_id]["status"] = "done"
                reports[report_id]["result"] = f"Execute summary on {topic}: Market trends are positive."
            return reports.get(report_id)

        await step.run("build-report", build_report)

    return {"status" : "done", "report_id": report_id}

app = FastAPI(title="Background Job Service")

#custom handler to ensure missing/invalid field return HTTP 400
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error" : "Field 'topic' is required and cannot be empty"}
    )

@app.get("/health")
def health():
    return {"status": "ok"}

# endpoint: POST /reports
@app.post("/reports", status_code=status.HTTP_202_ACCEPTED)
async def create_report(payload: ReportCreate):
    # Reject whitespace-only topic
    if not payload.topic.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Field 'topic' cannot be whitespace"}
        )

    report_id = str(uuid.uuid4())[:8]
    
    # save initial pending state
    reports[report_id] = {
        "id": report_id,
        "topic": payload.topic,
        "status": "pending"
    }

    # dispatch event to Inngest asynchronously
    event = inngest.Event(
        name="report/requested",
        data={"id": report_id, "topic": payload.topic}
    )
    res = inngest_client.send(event)
    if inspect.isawaitable(res):
        await res

    # return 202 Accepted immediately
    return {"id": report_id, "status": "pending"}


#endpoint: GET /reports/{id}
@app.get("/reports/{report_id}")
def get_report_status(report_id: str):
    if report_id not in reports:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": f"Report {report_id} not found"}
        )
    return reports[report_id]

# 4. serve both functions at /api/inngest
inngest.fast_api.serve(
    app,
    inngest_client,
    [say_hello, make_report]
)



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)