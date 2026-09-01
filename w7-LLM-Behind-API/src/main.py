import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.llm.client import execute_triage
from src.llm.schema import TriageCategory, TriageRequest, TriageResponse, TriageUrgency

load_dotenv(override=True)

app = FastAPI(
    title="Triage Support API",
    description="Classifies customer support messages using structured LLM output",
    version="1.0.0",
)


# Custom handler to ensure validation errors return a clean 400 naming the field
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    first_error = errors[0] if errors else {}
    loc = first_error.get("loc", [])
    field_name = loc[-1] if loc else "body"
    msg = first_error.get("msg", "Invalid input")

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": f"Validation error on field '{field_name}': {msg}"}
    )



@app.get("/health")
def health_check():
    return {"status" : "ok"}


@app.post("/triage", response_model=TriageResponse)
def triage_message(payload: TriageRequest):
    # Stub mode check
    if os.environ.get("LLM_STUB", "0") == "1":
        return TriageResponse(
            category=TriageCategory.BILLING,
            urgency=TriageUrgency.NORMAL,
            confidence=0.95,
            reason="Stub mode active: hard-coded classification response.",
        )

    try:
        # Calls the full Stage 3 pipeline (Validate -> Repair -> Quarantine)
        return execute_triage(payload.text)
    except ValueError as val_err:
        # Step 4: Return 422 Unprocessable Entity when the model fails validation after repair
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Model output failed schema validation after repair attempt: {str(val_err)}",
        )