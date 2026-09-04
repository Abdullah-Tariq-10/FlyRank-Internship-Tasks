# Background Job Service (FastAPI + Inngest)

An asynchronous background job system built with **FastAPI** and **Inngest**. The API decouples slow processing from HTTP request-response loops by issuing immediate `202 Accepted` responses, while background work is executed through durable, checkpointed steps with exponential-backoff retries.

The service also includes scheduled heartbeat jobs using Inngest cron triggers.

---

## Running the Application

This service requires **two concurrently running processes**:

1. FastAPI web application
2. Inngest Dev Server

### Terminal 1: Start the API Server

```bash
python main.py
````

### Terminal 2: Start the Inngest Dev Server

```bash
npx inngest-cli@latest dev -u http://127.0.0.1:8000/api/inngest
```

Once both services are running, the local Inngest dashboard is available at:

```text
http://localhost:8288
```

---

## API Endpoints

| Method | Endpoint        | Status                             | Description                                                                 |
| ------ | --------------- | ---------------------------------- | --------------------------------------------------------------------------- |
| `GET`  | `/health`       | `200 OK`                           | Returns the service health status.                                          |
| `POST` | `/reports`      | `202 Accepted` / `400 Bad Request` | Validates input, creates a pending job, and dispatches the background task. |
| `GET`  | `/reports/{id}` | `200 OK` / `404 Not Found`         | Returns the current status and result of a report job.                      |
| `GET`  | `/reports`      | `200 OK`                           | Lists all tracked jobs and their current statuses.                          |

---

## Inngest Background Functions

| Function      | Trigger            | Type  | Execution Behavior                                                                     |
| ------------- | ------------------ | ----- | -------------------------------------------------------------------------------------- |
| `say-hello`   | `test/hello`       | Event | Sleeps durably for 5 seconds and returns a confirmation message.                       |
| `make-report` | `report/requested` | Event | Sleeps for 8 seconds, builds the report, and retries up to 2 times if execution fails. |
| `heartbeat`   | `* * * * *`        | Cron  | Runs every minute and logs the number of pending, completed, and failed jobs.          |

---

## Execution Proof

The system demonstrates the **Fast Door + Eventual Consistency** pattern:

1. The API immediately accepts the request.
2. The job is stored as `pending`.
3. Background processing happens asynchronously.
4. The client can poll the job status.
5. Once processing finishes, the status changes to `done` and the result becomes available.

### 1. Fast Door: `202 Accepted`

A report request returns immediately instead of waiting for the slow background task:

```http
POST /reports HTTP/1.1
Host: 127.0.0.1:8000
Content-Type: application/json

{"topic": "cats"}

HTTP/1.1 202 Accepted
date: Thu, 03 Sep 2026 05:32:42 GMT
server: uvicorn
content-length: 36
content-type: application/json

{"id": "127fd0e6", "status": "pending"}
```

The API does not wait for the report to be generated.

---

### 2. Immediate Poll

Approximately 2 seconds later:

```http
GET /reports/127fd0e6 HTTP/1.1
Host: 127.0.0.1:8000

HTTP/1.1 200 OK
content-type: application/json

{"id": "127fd0e6", "topic": "cats", "status": "pending"}
```

The job is still being processed in the background.

---

### 3. Final Poll After Completion

After approximately 10 seconds:

```http
GET /reports/127fd0e6 HTTP/1.1
Host: 127.0.0.1:8000

HTTP/1.1 200 OK
date: Thu, 03 Sep 2026 05:34:51 GMT
server: uvicorn
content-length: 112
content-type: application/json

{
  "id": "127fd0e6",
  "topic": "cats",
  "status": "done",
  "result": "Execute summary on cats: Market trends are positive."
}
```

The background job has completed successfully and the generated result is now available through the polling endpoint.

---

## Concept Questions & Explanations

### Retries vs. Input Validation

Invalid input should be rejected immediately with a `400 Bad Request`.

A deterministic failure will not be fixed by retrying the same request. Automatic retries are intended for **transient failures**, where the operation may succeed if attempted again later.

In short:

* **Invalid input → `400 Bad Request`**
* **Transient processing failure → Retry with backoff**

---

## Cron Heartbeat Schedules

### Daily at 08:00

```text
0 8 * * *
```

Runs every day at **08:00 UTC**.

### Weekly on Sunday at 22:00

```text
0 22 * * 0
```

Runs every Sunday at **22:00 UTC**.

---

## Restart Experiment

The durability of Inngest was tested by stopping the FastAPI process while a background job was executing its 8-second sleep step.

The FastAPI process was restarted approximately three seconds later.

The job did not need to be manually restarted or duplicated. Because the work is executed through Inngest's durable steps, the execution state survives the temporary API outage and the workflow can continue once the application reconnects.

This demonstrates the benefit of separating background execution from the HTTP request lifecycle.

---

## Dashboard Proof

The Inngest dashboard shows the registered functions and their execution history.

![Inngest Dashboard](dashboard.png)


