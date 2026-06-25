# api/server.py

import os
import json
import time
import uuid
import threading
import requests
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from ingestion.onedrive_watcher import run_once
from ingestion.auth import get_app_token
from core.memory import (
    get_conn,
    insert_resume,
    create_session,
    add_session_candidate,
    save_questions,
    get_questions,
    save_interview_result,
    get_interview_result,
    get_session_with_candidates,
    list_all_sessions,
    delete_session as _delete_session,
    update_resume_fields,
)
from core.scoring import score_resume_with_llm
from core.interview import generate_interview_questions, score_interview_answers, ALLOWED_TYPES
from core.parsing import (
    extract_text_from_bytes,
    extract_contacts,
    extract_name,
    extract_skills,
    compute_experience_years,
    extract_position_from_jd,
)
from core.categorization import categorize_resume

# --------------------------------------------------
# ENV
# --------------------------------------------------
if os.getenv("ENV") != "production":
    load_dotenv()

DRIVE_ID = os.getenv("ONEDRIVE_DRIVE_ID")
FOLDER_ID = os.getenv("ONEDRIVE_FOLDER_ID")

if not DRIVE_ID or not FOLDER_ID:
    print("WARNING: Missing OneDrive config - ingestion disabled")

GRAPH = "https://graph.microsoft.com/v1.0"

# --------------------------------------------------
# APP
# --------------------------------------------------
app = FastAPI(title="Resume Intelligence Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
            print("ERROR: OneDrive ingestion error:", e)
        time.sleep(300)


_ingestion_started = False


@app.on_event("startup")
def startup():
    global _ingestion_started
    if _ingestion_started:
        return
    _ingestion_started = True
    threading.Thread(target=onedrive_worker, daemon=True).start()
    print("OK: OneDrive background ingestion started")


# --------------------------------------------------
# MODELS
# --------------------------------------------------
class JDRequest(BaseModel):
    jd_text: str
    min_exp: float
    max_exp: float
    category: str = "Sales"


class EvaluateRequest(BaseModel):
    session_id: str
    answers: List[dict]


# --------------------------------------------------
# HEALTH
# --------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok"}


# --------------------------------------------------
# SESSION: single-candidate interview setup (HR provides name + position)
# --------------------------------------------------
@app.post("/sessions/start")
async def start_interview(
    candidate_name: str = Form(...),
    position: str = Form(...),
    jd_text: str = Form(...),
    resume: UploadFile = File(...),
):
    if not candidate_name.strip():
        raise HTTPException(400, "Candidate name is required.")
    if not position.strip():
        raise HTTPException(400, "Position is required.")
    if not jd_text.strip():
        raise HTTPException(400, "Job description is required.")

    raw = await resume.read()
    text = extract_text_from_bytes(resume.filename, raw)
    if not text or len(text.strip()) < 20:
        raise HTTPException(400, "Could not extract text from the resume. Please upload a PDF, DOCX, or TXT file.")

    emails, phones = extract_contacts(text)
    skills = extract_skills(text)
    exp = compute_experience_years(text)
    category = categorize_resume(text)

    rid = str(uuid.uuid4())
    insert_resume(
        resume_id=rid,
        name=candidate_name.strip(),
        email=emails[0] if emails else "",
        phone=phones[0] if phones else "",
        category=category,
        experience_years=exp,
        skills=skills,
        raw_text=text,
        drive_id="local",
        item_id=rid,
    )

    session_id = str(uuid.uuid4())
    create_session(session_id, jd_text.strip(), position.strip())
    add_session_candidate(str(uuid.uuid4()), session_id, rid)

    return {
        "session_id": session_id,
        "position_title": position.strip(),
        "candidate": {
            "candidate_id": rid,
            "name": candidate_name.strip(),
            "email": emails[0] if emails else "",
            "experience": exp,
            "category": category,
            "skills": ", ".join(skills) if isinstance(skills, list) else skills,
            "status": "pending",
        },
    }


# --------------------------------------------------
# SESSIONS: list all (history)
# --------------------------------------------------
@app.get("/sessions")
def get_all_sessions():
    return list_all_sessions()


# --------------------------------------------------
# SESSION: delete
# --------------------------------------------------
@app.delete("/sessions/{session_id}")
def delete_session_endpoint(session_id: str):
    _delete_session(session_id)
    return {"ok": True}


# --------------------------------------------------
# CANDIDATE: update category / experience
# --------------------------------------------------
class UpdateCandidateRequest(BaseModel):
    category: Optional[str] = None
    experience_years: Optional[float] = None


@app.patch("/candidates/{candidate_id}")
def update_candidate(candidate_id: str, body: UpdateCandidateRequest):
    update_resume_fields(candidate_id, body.category, body.experience_years)
    return {"ok": True}


# --------------------------------------------------
# SESSION: upload JD + resumes, parse all, return candidates
# --------------------------------------------------
@app.post("/sessions/upload")
async def upload_session(
    jd_text: str = Form(...),
    resumes: List[UploadFile] = File(...),
):
    if not jd_text.strip():
        raise HTTPException(400, "JD text is required.")

    session_id = str(uuid.uuid4())
    position_title = extract_position_from_jd(jd_text) or "Open Position"

    create_session(session_id, jd_text, position_title)

    candidates = []
    for f in resumes:
        raw = await f.read()
        text = extract_text_from_bytes(f.filename, raw)
        if not text or len(text.strip()) < 20:
            continue

        emails, phones = extract_contacts(text)
        name = extract_name(text, emails)
        skills = extract_skills(text)
        exp = compute_experience_years(text)
        category = categorize_resume(text)
        rid = str(uuid.uuid4())

        insert_resume(
            resume_id=rid,
            name=name or f.filename,
            email=emails[0] if emails else "",
            phone=phones[0] if phones else "",
            category=category,
            experience_years=exp,
            skills=skills,
            raw_text=text,
            drive_id="local",
            item_id=rid,
        )

        add_session_candidate(str(uuid.uuid4()), session_id, rid)

        candidates.append({
            "candidate_id": rid,
            "name": name or f.filename,
            "email": emails[0] if emails else "",
            "experience": exp,
            "category": category,
            "skills": ", ".join(skills) if isinstance(skills, list) else skills,
            "status": "pending",
            "overall_score": None,
            "recommendation": None,
        })

    if not candidates:
        raise HTTPException(400, "No valid resumes could be parsed.")

    return {
        "session_id": session_id,
        "position_title": position_title,
        "candidates": candidates,
    }


# --------------------------------------------------
# SESSION: fetch session + candidates (with status)
# --------------------------------------------------
@app.get("/sessions/{session_id}")
def get_session(session_id: str):
    session = get_session_with_candidates(session_id)
    if not session:
        raise HTTPException(404, "Session not found.")
    return session


# --------------------------------------------------
# QUESTIONS: generate (or return cached) per candidate
# --------------------------------------------------
@app.get("/candidates/{candidate_id}/questions")
def get_candidate_questions(candidate_id: str, session_id: str):
    cached = get_questions(session_id, candidate_id)
    # Discard cache if it contains questions from the old type system
    if cached and all(q.get("type") in ALLOWED_TYPES for q in cached):
        questions = cached
    else:
        conn = get_conn()
        candidate = conn.execute(
            "SELECT name, email, experience_years, category, raw_text FROM resumes WHERE resume_id = ?",
            [candidate_id],
        ).fetchone()
        session = conn.execute(
            "SELECT jd_text, position_title FROM sessions WHERE session_id = ?",
            [session_id],
        ).fetchone()
        if not candidate or not session:
            raise HTTPException(404, "Candidate or session not found.")

        questions = generate_interview_questions(candidate[4], session[0], session[1])
        save_questions(session_id, candidate_id, questions)

    conn = get_conn()
    c = conn.execute(
        "SELECT name, email, experience_years, category, skills FROM resumes WHERE resume_id = ?",
        [candidate_id],
    ).fetchone()

    return {
        "questions": questions,
        "candidate": {
            "candidate_id": candidate_id,
            "name": c[0] if c else "",
            "email": c[1] if c else "",
            "experience": c[2] if c else 0,
            "category": c[3] if c else "",
            "skills": c[4] if c else "",
        },
    }


# --------------------------------------------------
# EVALUATE: score submitted answers
# --------------------------------------------------
@app.post("/candidates/{candidate_id}/evaluate")
def evaluate_candidate(candidate_id: str, body: EvaluateRequest):
    conn = get_conn()

    candidate = conn.execute(
        "SELECT name, email, experience_years, category, raw_text FROM resumes WHERE resume_id = ?",
        [candidate_id],
    ).fetchone()
    session = conn.execute(
        "SELECT jd_text, position_title FROM sessions WHERE session_id = ?",
        [body.session_id],
    ).fetchone()

    if not candidate or not session:
        raise HTTPException(404, "Candidate or session not found.")

    result = score_interview_answers(
        body.answers, candidate[4], session[0], session[1]
    )

    save_interview_result(
        candidate_id=candidate_id,
        session_id=body.session_id,
        scored_answers=result.get("scored_answers", []),
        overall_score=result.get("overall_score", 0),
        recommendation=result.get("recommendation", "Maybe"),
        summary=result.get("summary", ""),
        strengths=result.get("strengths", []),
        concerns=result.get("concerns", []),
    )

    return result


# --------------------------------------------------
# REPORT: full report card data
# --------------------------------------------------
@app.get("/candidates/{candidate_id}/report")
def get_report(candidate_id: str, session_id: str):
    conn = get_conn()

    candidate = conn.execute(
        "SELECT name, email, experience_years, category, skills FROM resumes WHERE resume_id = ?",
        [candidate_id],
    ).fetchone()
    session = conn.execute(
        "SELECT position_title FROM sessions WHERE session_id = ?",
        [session_id],
    ).fetchone()

    if not candidate or not session:
        raise HTTPException(404, "Not found.")

    result = get_interview_result(candidate_id, session_id)
    if not result:
        raise HTTPException(404, "Interview not yet completed for this candidate.")

    return {
        "candidate": {
            "candidate_id": candidate_id,
            "name": candidate[0],
            "email": candidate[1],
            "experience": candidate[2],
            "category": candidate[3],
            "skills": candidate[4],
        },
        "session": {"session_id": session_id, "position_title": session[0]},
        **result,
    }


# --------------------------------------------------
# LEGACY: OneDrive-based shortlist
# --------------------------------------------------
@app.get("/resumes")
def list_resumes(limit: int = 50):
    conn = get_conn()
    rows = conn.execute(
        "SELECT resume_id, name, email, category, experience_years, skills FROM resumes ORDER BY created_at DESC LIMIT ?",
        [limit],
    ).fetchall()
    return [
        {"resume_id": r[0], "name": r[1], "email": r[2], "category": r[3], "experience": r[4], "skills": r[5]}
        for r in rows
    ]


@app.post("/shortlist")
def shortlist(req: JDRequest):
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT resume_id, drive_id, item_id, name, email, experience_years, skills, raw_text
        FROM resumes
        WHERE category = ? AND experience_years BETWEEN ? AND ?
        """,
        [req.category, req.min_exp, req.max_exp],
    ).fetchall()

    results = []
    for r in rows:
        score = score_resume_with_llm(r[7], req.jd_text, req.category)
        results.append({
            "resume_id": r[0], "name": r[3], "email": r[4],
            "experience": r[5], "skills": r[6],
            "score": score["ai_fit_score"], "fit": score["best_fit"],
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
        raise HTTPException(404, "Resume not found.")
    drive_id, item_id, name = row
    if drive_id == "local":
        raise HTTPException(404, "Locally ingested resume is not available for download.")
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
