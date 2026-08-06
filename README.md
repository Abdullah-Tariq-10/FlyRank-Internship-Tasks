# W3-A2: Task CRUD API with SQLite Persistence

This is a lightweight CRUD (Create, Read, Update, Delete) API built using FastAPI as part of the FlyRank Backend Internship. In this version, storage has been migrated from an in-memory array to a persistent SQLite database (`tasks.db`).

## 🗄️ Database Architecture & Design Choices

* **Why SQLite Was Chosen:**
* **Zero Setup:** Requires no external database server or complex configuration.
* **Single File Storage:** The entire database lives in a local file (`tasks.db`), making it easy to manage.
* **Data Persistence:** Ensures that all task data survives server restarts while maintaining the exact same REST API behavior.


* **Database File Location:**
* The database file is located at the root of the project: `tasks.db`.
* It is created automatically upon launching the application along with the `tasks` table.
* `tasks.db` is `.gitignore`d so every clean clone starts fresh with 3 seeded tasks on first run.



---

## 🚀 How to Install & Run

1. **Clone the repository**:
```bash
git clone https://github.com/Abdullah-Tariq-10/FlyRank-Internship-Tasks
cd FlyRank-Internship-Tasks

```


2. **Install dependencies**:
```bash
pip install fastapi uvicorn

```


3. **Start the server** (Creates `tasks.db` and seeds initial data automatically):
```bash
uvicorn main:app --reload

```



*The server will run locally at `http://localhost:8000/`.*

---

## 📊 Database Verification & Manual SQL Query

**Example SQL Query Executed (Stage 4)**

```sql
SELECT * FROM tasks WHERE done = 1;

```

* **Result:** Returns all completed tasks stored in the `tasks` table where the `done` column equals `1`.

---

## API Endpoints

| HTTP Method | Path | Description | Expected Status Codes |
| --- | --- | --- | --- |
| **GET** | `/` | Get basic API metadata and available resource paths. | `200 OK` |
| **GET** | `/health` | Verify the API server is healthy and operational. | `200 OK` |
| **GET** | `/tasks` | Retrieve tasks with optional search, status filtering, and alphabetical sorting. | `200 OK` |
| **GET** | `/tasks/{id}` | Retrieve a single task by its unique ID from SQLite. | `200 OK`, `404 Not Found` |
| **POST** | `/tasks` | Create a brand new task and insert it into SQLite. | `201 Created`, `400 Bad Request` |
| **PUT** | `/tasks/{id}` | Update an existing task's title and/or status in SQLite. | `200 OK`, `400 Bad Request`, `404 Not Found` |
| **DELETE** | `/tasks/{id}` | Remove a task from SQLite by its unique ID. | `204 No Content`, `404 Not Found` |
| **GET** | `/stats` | Compute real-time database metrics using SQL `COUNT()` aggregations. | `200 OK` |

---

##  Optional Extras (SQL Enhancements)

This project includes advanced database-level operations for enhanced performance and security:

1. **Search with SQL (`GET /tasks?search=milk`)**: Filters task titles directly inside SQLite using the SQL `LIKE` operator (`%search%`) with safe parameterized query bindings.
2. **Filter by Completion Status (`GET /tasks?done=true`)**: Queries specific completion statuses using a dynamic SQL `WHERE done = ?` clause.
3. **Alphabetical Sorting**: Automatically returns queried tasks ordered alphabetically using SQL's `ORDER BY title ASC`.
4. **Database Statistics (`GET /stats`)**: Offloads calculations to the database using `SELECT COUNT(*)` queries instead of computing metrics in Python application memory.

---

## Sample curl Outputs

### 1. Get All Tasks (GET `/tasks`)

```bash
PS D:\flyrank-internship> curl.exe -i http://localhost:8000/tasks
HTTP/1.1 200 OK
date: Thu, 06 Aug 2026 11:45:00 GMT
server: uvicorn
content-length: 180
content-type: application/json

[{"id":1,"title":"Buy milk","done":false},{"id":2,"title":"Learn SQL","done":false},{"id":3,"title":"Celebrate Week 3","done":true}]

```

### 2. Triggering a 404 Error (GET `/tasks/99`)

```bash
PS D:\flyrank-internship> curl.exe -i http://localhost:8000/tasks/99
HTTP/1.1 404 Not Found
date: Thu, 06 Aug 2026 11:45:10 GMT
server: uvicorn
content-length: 37
content-type: application/json

{"detail":{"error":"Task 99 not found"}}

```

### 3. Database Statistics (GET `/stats`)

```bash
PS D:\flyrank-internship> curl.exe -i http://localhost:8000/stats
HTTP/1.1 200 OK
date: Thu, 06 Aug 2026 12:30:00 GMT
server: uvicorn
content-length: 61
content-type: application/json

{"total_tasks":3,"completed_tasks":1,"pending_tasks":2}

```

---

## Interactive OpenAPI Documentation

FastAPI automatically serves interactive API documentation at `http://localhost:8000/docs`. You can view, test, and run the full CRUD lifecycle directly from your browser.
