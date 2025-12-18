# api/server.py

import os
import time
import threading
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from ingestion.onedrive_watcher import run_once
from ingestion.auth import get_app_token
from core.memory import get_conn
from core.scoring import score_resume_with_llm

# --------------------------------------------------
# ENV
# --------------------------------------------------
if os.getenv("ENV") != "production":
    load_dotenv()

DRIVE_ID = os.getenv("ONEDRIVE_DRIVE_ID")
FOLDER_ID = os.getenv("ONEDRIVE_FOLDER_ID")

if not DRIVE_ID or not FOLDER_ID:
    print("⚠️ Missing OneDrive config — ingestion disabled")

GRAPH = "https://graph.microsoft.com/v1.0"

# --------------------------------------------------
# APP
# --------------------------------------------------
app = FastAPI(title="Resume Intelligence Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Azure + frontend safe
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------
# BACKGROUND INGESTION
# --------------------------------------------------
def onedrive_worker():
    if not DRIVE_ID or not FOLDER_ID:
        return

    while True:
        try:
            run_once(DRIVE_ID, FOLDER_ID)
        except Exception as e:
            print("❌ OneDrive ingestion error:", e)
        time.sleep(300)


_ingestion_started = False

@app.on_event("startup")
def startup():
    global _ingestion_started
    if _ingestion_started:
        return
    _ingestion_started = True
    threading.Thread(target=onedrive_worker, daemon=True).start()
    print("✅ OneDrive background ingestion started")


# --------------------------------------------------
# MODELS
# --------------------------------------------------
class JDRequest(BaseModel):
    jd_text: str
    min_exp: float
    max_exp: float
    category: str = "Sales"


# --------------------------------------------------
# ROUTES
# --------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/shortlist")
def shortlist(req: JDRequest):
    conn = get_conn()

    rows = conn.execute(
        """
        SELECT resume_id, drive_id, item_id,
               name, email, experience_years, skills, raw_text
        FROM resumes
        WHERE category = ?
        AND experience_years BETWEEN ? AND ?
        """,
        [req.category, req.min_exp, req.max_exp],
    ).fetchall()

    results = []
    for r in rows:
        score = score_resume_with_llm(r[7], req.jd_text, req.category)
        results.append({
            "resume_id": r[0],
            "name": r[3],
            "email": r[4],
            "experience": r[5],
            "skills": r[6],
            "score": score["ai_fit_score"],
            "fit": score["best_fit"],
        })

    return sorted(results, key=lambda x: x["score"], reverse=True)[:3]


@app.get("/resumes/{resume_id}/download")
def download_resume(resume_id: str):
    conn = get_conn()

    row = conn.execute(
        "SELECT drive_id, item_id, name FROM resumes WHERE resume_id = ?",
        [resume_id],
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Resume not found")

    drive_id, item_id, name = row
    token = get_app_token()

    headers = {"Authorization": f"Bearer {token}"}
    url = f"{GRAPH}/drives/{drive_id}/items/{item_id}/content"

    resp = requests.get(url, headers=headers, stream=True)
    resp.raise_for_status()

    return StreamingResponse(
        resp.iter_content(chunk_size=8192),
        media_type=resp.headers.get("Content-Type", "application/octet-stream"),
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )
