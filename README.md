# Containerized Task CRUD API (FastAPI + PostgreSQL + Docker Compose)

A fully containerized RESTful CRUD API built with **FastAPI** and **PostgreSQL 16**, managed seamlessly using **Docker Compose**.

This repository represents the third architectural iteration of the Task API (In-Memory Array → SQLite → Containerized PostgreSQL).

---

## 🏗️ Stack Architecture & Design Choices

* **Framework:** FastAPI (Python 3.11)
* **Database:** PostgreSQL 16
* **Database Driver:** `psycopg` (v3 with `dict_row` factory)
* **Containerization:** Docker & Docker Compose
* **Configuration:** Environment variables (`.env` with `python-dotenv`)

### Why PostgreSQL & Docker?

1. **Production Parity:** PostgreSQL is an enterprise-grade relational database engine capable of handling high concurrency, ACID transactions, and complex queries.
2. **Containerization:** Running PostgreSQL inside Docker eliminates local installation overhead, driver incompatibilities, and version mismatch issues.
3. **Environment Isolation:** Both the API and Database run as isolated services within a shared Docker network, ensuring the application behaves identically on any machine.
4. **Data Persistence:** Database storage is mounted to a named Docker volume (`taskdata`), guaranteeing that data survives container restarts and tear-downs.

---

## 🚀 Quick Start (One Command Startup)

### Prerequisites

* [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.
* Git

### Setup & Run

1. **Clone the repository:**
```bash
git clone https://github.com/Abdullah-Tariq-10/FlyRank-Internship-Tasks
cd FlyRank-Internship-Tasks

```


2. **Configure Environment Variables:**
Create a `.env` file based on `.env.example`:
```bash
cp .env.example .env

```


*(Ensure `.env` contains: `DATABASE_URL=postgresql://postgres:dev@db:5432/tasks`)*
3. **Launch the entire stack with Docker Compose:**
```bash
docker compose up --build

```


> **Note:** The API service uses Docker healthchecks (`pg_isready`) to wait for PostgreSQL to fully initialize before launching, preventing startup race conditions.


4. **Access the Application:**
* **API Base URL:** `http://localhost:8000`
* **Interactive OpenAPI (Swagger) Docs:** `http://localhost:8000/docs`



---

## 🛠️ API Endpoints

| HTTP Method | Path | Description | Expected Status Codes |
| --- | --- | --- | --- |
| **GET** | `/` | API metadata and root routing information. | `200 OK` |
| **GET** | `/health` | Live database connectivity healthcheck (`SELECT 1`). | `200 OK`, `503 Service Unavailable` |
| **GET** | `/tasks` | Retrieve all tasks (with optional `search` & `done` filters, ordered by title). | `200 OK` |
| **GET** | `/tasks/{id}` | Retrieve a single task by its primary key ID. | `200 OK`, `404 Not Found` |
| **POST** | `/tasks` | Create a new task (uses `%s` parameterized queries & `RETURNING id`). | `201 Created`, `400 Bad Request` |
| **PUT** | `/tasks/{id}` | Update an existing task's title or status. | `200 OK`, `400 Bad Request`, `404 Not Found` |
| **DELETE** | `/tasks/{id}` | Delete a task by ID. | `204 No Content`, `404 Not Found` |
| **GET** | `/stats` | Calculate real-time task metrics using SQL `COUNT()` aggregation. | `200 OK` |

---

## 🛡️ Security & Reliability Features

1. **Parameterized Queries:** All SQL operations use placeholders (`%s`) to pass variables separately from query strings, completely immunizing the application against **SQL Injection** attacks.
2. **Secrets Management:** Sensitive database credentials are stored in `.env` and excluded from Git version control via `.gitignore`. A template `.env.example` is committed for setup guidance.
3. **Database Health Check Endpoint (`GET /health`):** Directly tests PostgreSQL readiness by executing `SELECT 1` queries to ensure active database connectivity.

---

## 📊 Verification & Sample Outputs

### 1. Get All Tasks (GET `/tasks`)

```bash
PS D:\flyrank-internship> curl.exe -i http://localhost:8000/tasks
HTTP/1.1 200 OK
date: Sat, 08 Aug 2026 19:48:12 GMT
server: uvicorn
content-type: application/json

[{"id":1,"title":"Buy milk","done":false},{"id":2,"title":"Learn SQL","done":false},{"id":3,"title":"Celebrate Week 3","done":true}]

```

### 2. Database Healthcheck (GET `/health`)

```bash
PS D:\flyrank-internship> curl.exe -i http://localhost:8000/health
HTTP/1.1 200 OK
content-type: application/json

{"status":"ok","db":"ok"}

```

---

## 🧹 Stopping & Cleaning Up

To stop the container stack while preserving your database volume:

```bash
docker compose down

```

To stop the stack and completely remove persistent database volumes (reset state):

```bash
docker compose down -v

```
