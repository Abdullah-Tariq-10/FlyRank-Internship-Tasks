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
    # 1. Operator Kill Switch Check (LLM_ENABLED=false)
    if os.environ.get("LLM_ENABLED", "true").lower() == "false":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Triage AI processing is currently disabled by operator kill switch.",
        )

    # 2. Stub Mode Check
    if os.environ.get("LLM_STUB", "0") == "1":
        return TriageResponse(
            category=TriageCategory.BILLING,
            urgency=TriageUrgency.NORMAL,
            confidence=0.95,
            reason="Stub mode active: hard-coded classification response.",
        )

    # 3. Production Triage Execution with Mapped Exceptions
    try:
        return execute_triage(payload.text)
    except PermissionError as perm_err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication/configuration error with AI provider: {str(perm_err)}",
        )
    except TimeoutError as time_err:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"AI model provider timed out: {str(time_err)}",
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Model output failed schema validation: {str(val_err)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Upstream provider failure: {str(e)}",
        )


    