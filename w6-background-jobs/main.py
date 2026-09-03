import datetime
import os
from fastapi import FastAPI
import inngest
import inngest.fast_api

# Enable local dev mode bypass
os.environ["INNGEST_DEV"] = "1"

# 1. Inngest client
inngest_client = inngest.Inngest(
    app_id="report-api",
    is_production=False
)

# 2. say-hello function
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

app = FastAPI(title="Background Job Service")

@app.get("/health")
def health():
    return {"status": "ok"}

# 3. Mount handlers at /api/inngest
inngest.fast_api.serve(
    app,
    inngest_client,
    [say_hello]
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)