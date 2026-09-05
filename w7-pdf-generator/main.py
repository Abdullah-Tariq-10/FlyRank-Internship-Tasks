from datetime import datetime
import os
import sqlite3
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse

from render_pdf import REPORTS_DIR, generate_html
from report_data import DB_FILE, get_report_data
from playwright.sync_api import sync_playwright


app = FastAPI(title="PDF Report Generator")

def init_reports_table():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_reports_table()


@app.get("/health")
def health_check():
    return {"status": "ok"}

#1. POST /reports: Runs the full pipeline synchronously
@app.post("/reports", status_code=status.HTTP_201_CREATED)
def create_report():
    os.makedirs(REPORTS_DIR, exist_ok=True)
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Reserve the DB record to get an auto-incremented ID
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO reports (path, created_at) VALUES (?, ?)", ("", created_at))
    report_id = cursor.lastrowid
    conn.commit()

    file_path = os.path.join(REPORTS_DIR, f"{report_id}.pdf")

    try:
        #sql aggregation and generating html
        data = get_report_data()
        html_content = generate_html(data)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_content(html_content, wait_until="networkidle")
            page.pdf(
                path=file_path,
                format="A4",
                print_background=True,
                margin={"top": "20mm", "bottom": "20mm", "left": "15mm", "right": "15mm"},
            )
            browser.close()

        cursor.execute("UPDATE reports SET path = ? WHERE id = ?", (file_path, report_id))
        conn.commit()
    except Exception as exc:
        cursor.execute("DELETE FROM reports WHERE id = ?", (report_id,))
        conn.commit()
        raise HTTPException(status_code=500, detail=f"Failed to render report: {exc}")
    finally:
        conn.close()

    return {
        "id" : report_id,
        "file" : f"/reports/{report_id}/file"
    }

#2. GET /reports/{id}: Returns metadata and download link
@app.get("/reports/{report_id}")
def get_report_record(report_id: int):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, path, created_at FROM reports WHERE id = ?", (report_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    return {
        "id": row["id"],
        "created_at": row["created_at"],
        "file": f"/reports/{row['id']}/file"
    }

#3. GET /reports/{id}/file: Moves the megabytes
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

    return FileResponse(
        path=row["path"],
        media_type="application/pdf",
        filename=f"report_{report_id}.pdf"
    )