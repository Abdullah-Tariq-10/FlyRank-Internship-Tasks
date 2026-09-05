from datetime import datetime
import os
import sqlite3
from typing import Optional
from fastapi import FastAPI, HTTPException, Response, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from render_pdf import REPORTS_DIR, render_pdf
from report_data import DB_FILE, get_report_data

app = FastAPI(title="PDF Report Generator")


class ReportRequest(BaseModel):
    force: Optional[bool] = False
    days: Optional[int] = Field(default=30, ge=1, le=365)


def init_reports_table():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL,
            days INTEGER DEFAULT 30,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


init_reports_table()


@app.get("/health")
def health_check():
    return {"status": "ok"}


# Control Panel: List all generated reports
@app.get("/reports")
def list_reports():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, path, days, created_at FROM reports ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": row["id"],
            "days": row["days"],
            "created_at": row["created_at"],
            "file": f"/reports/{row['id']}/file",
            "exists_on_disk": os.path.exists(row["path"]) if row["path"] else False
        }
        for row in rows
    ]


# POST /reports: Parameterized + Idempotent generation
@app.post("/reports")
def create_report(response: Response, payload: Optional[ReportRequest] = None):
    force = payload.force if payload else False
    days = payload.days if payload else 30
    today_str = datetime.now().strftime("%Y-%m-%d")

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Idempotency check: same day + same parameter configuration
    if not force:
        cursor.execute(
            """
            SELECT id, path FROM reports 
            WHERE DATE(created_at) = ? AND days = ?
            ORDER BY id DESC LIMIT 1
            """,
            (today_str, days),
        )
        existing = cursor.fetchone()
        if existing and os.path.exists(existing["path"]):
            conn.close()
            response.status_code = status.HTTP_200_OK
            return {
                "id": existing["id"],
                "file": f"/reports/{existing['id']}/file"
            }

    # Generate new report
    os.makedirs(REPORTS_DIR, exist_ok=True)
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        "INSERT INTO reports (path, days, created_at) VALUES (?, ?, ?)",
        ("", days, created_at)
    )
    report_id = cursor.lastrowid
    conn.commit()

    # Professional clean filename
    date_stamp = datetime.now().strftime("%Y-%m-%d")
    file_path = os.path.join(REPORTS_DIR, f"sales-report-{date_stamp}-id{report_id}.pdf")

    try:
        data = get_report_data(days=days)
        render_pdf(data=data, output_path=file_path)

        cursor.execute("UPDATE reports SET path = ? WHERE id = ?", (file_path, report_id))
        conn.commit()
    except Exception as exc:
        cursor.execute("DELETE FROM reports WHERE id = ?", (report_id,))
        conn.commit()
        raise HTTPException(status_code=500, detail=f"Failed to render report: {exc}")
    finally:
        conn.close()

    response.status_code = status.HTTP_201_CREATED
    return {
        "id": report_id,
        "file": f"/reports/{report_id}/file"
    }


# GET /reports/{id}: Metadata lookup
@app.get("/reports/{report_id}")
def get_report_record(report_id: int):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, path, days, created_at FROM reports WHERE id = ?", (report_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    return {
        "id": row["id"],
        "days": row["days"],
        "created_at": row["created_at"],
        "file": f"/reports/{row['id']}/file"
    }


# GET /reports/{id}/file: Streams PDF
@app.get("/reports/{report_id}/file")
def download_report_file(report_id: int):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT path FROM reports WHERE id = ?", (report_id,))
    row = cursor.fetchone()
    conn.close()

    if not row or not os.path.exists(row["path"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF artifact not found on disk")

    filename = os.path.basename(row["path"])
    return FileResponse(
        path=row["path"],
        media_type="application/pdf",
        filename=filename,
        headers={"Content-Disposition": f"inline; filename={filename}"}
    )