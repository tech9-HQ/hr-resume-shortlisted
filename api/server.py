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
load_dotenv()

DRIVE_ID = os.getenv("ONEDRIVE_DRIVE_ID")
FOLDER_ID = os.getenv("ONEDRIVE_FOLDER_ID")

if not DRIVE_ID or not FOLDER_ID:
    raise RuntimeError("Missing ONEDRIVE_DRIVE_ID / ONEDRIVE_FOLDER_ID")

GRAPH = "https://graph.microsoft.com/v1.0"

# --------------------------------------------------
# APP
# --------------------------------------------------
app = FastAPI(title="Resume Intelligence Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------
# BACKGROUND INGESTION
# --------------------------------------------------
def onedrive_worker():
    while True:
        try:
            run_once(DRIVE_ID, FOLDER_ID)
        except Exception as e:
            print("❌ OneDrive ingestion error:", e)
        time.sleep(300)


@app.on_event("startup")
def startup():
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
    print(f"🔍 Download requested for resume_id: {resume_id}")
    
    conn = get_conn()

    row = conn.execute(
        """
        SELECT drive_id, item_id, name
        FROM resumes
        WHERE resume_id = ?
        """,
        [resume_id],
    ).fetchone()

    if not row:
        print(f"❌ No resume found with resume_id: {resume_id}")
        
        # Debug: Show what's actually in the database
        all_resumes = conn.execute("SELECT resume_id, name FROM resumes LIMIT 5").fetchall()
        print(f"📊 Sample resumes in DB: {all_resumes}")
        
        raise HTTPException(status_code=404, detail=f"Resume not found: {resume_id}")

    drive_id, item_id, name = row
    print(f"✅ Found resume: drive_id={drive_id}, item_id={item_id}, name={name}")

    token = get_app_token()
    
    if not token:
        raise HTTPException(status_code=500, detail="Failed to get access token")

    headers = {
        "Authorization": f"Bearer {token}"
    }

    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}/content"
    print(f"📥 Fetching from OneDrive: {url}")

    try:
        resp = requests.get(url, headers=headers, stream=True)
        resp.raise_for_status()
        
        print(f"✅ OneDrive responded with status: {resp.status_code}")
        
        return StreamingResponse(
            resp.iter_content(chunk_size=8192),
            media_type=resp.headers.get("Content-Type", "application/octet-stream"),
            headers={
                "Content-Disposition": f'attachment; filename="{name}"'
            },
        )
    except requests.exceptions.HTTPError as e:
        print(f"❌ OneDrive API error: {e}")
        raise HTTPException(status_code=502, detail=f"OneDrive error: {str(e)}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")