# core/memory.py

import json
import duckdb
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "resumes.duckdb"

_conn = None


def get_conn():
    global _conn
    if _conn is None:
        _conn = duckdb.connect(str(DB_PATH))
        _init_tables(_conn)
    return _conn


def _init_tables(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS resumes (
            resume_id TEXT PRIMARY KEY,
            name TEXT,
            email TEXT,
            phone TEXT,
            category TEXT,
            experience_years DOUBLE,
            skills TEXT,
            raw_text TEXT,
            drive_id TEXT,
            item_id TEXT,
            created_at TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            jd_text TEXT,
            position_title TEXT,
            created_at TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS session_candidates (
            id TEXT PRIMARY KEY,
            session_id TEXT,
            candidate_id TEXT,
            questions TEXT,
            created_at TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS interview_results (
            result_id TEXT PRIMARY KEY,
            candidate_id TEXT,
            session_id TEXT,
            scored_answers TEXT,
            overall_score INTEGER,
            recommendation TEXT,
            summary TEXT,
            strengths TEXT,
            concerns TEXT,
            completed_at TIMESTAMP
        )
    """)


def resume_exists(item_id: str) -> bool:
    conn = get_conn()
    return conn.execute(
        "SELECT 1 FROM resumes WHERE item_id = ?",
        [item_id]
    ).fetchone() is not None


def create_session(session_id: str, jd_text: str, position_title: str):
    conn = get_conn()
    conn.execute(
        "INSERT INTO sessions VALUES (?, ?, ?, ?)",
        [session_id, jd_text, position_title, datetime.utcnow()],
    )


def add_session_candidate(sc_id: str, session_id: str, candidate_id: str):
    conn = get_conn()
    conn.execute(
        "INSERT INTO session_candidates VALUES (?, ?, ?, NULL, ?)",
        [sc_id, session_id, candidate_id, datetime.utcnow()],
    )


def save_questions(session_id: str, candidate_id: str, questions: list):
    conn = get_conn()
    conn.execute(
        "UPDATE session_candidates SET questions = ? WHERE session_id = ? AND candidate_id = ?",
        [json.dumps(questions), session_id, candidate_id],
    )


def get_questions(session_id: str, candidate_id: str) -> list | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT questions FROM session_candidates WHERE session_id = ? AND candidate_id = ?",
        [session_id, candidate_id],
    ).fetchone()
    if row and row[0]:
        return json.loads(row[0])
    return None


def save_interview_result(
    candidate_id: str,
    session_id: str,
    scored_answers: list,
    overall_score: int,
    recommendation: str,
    summary: str,
    strengths: list,
    concerns: list,
):
    conn = get_conn()
    result_id = f"{candidate_id}_{session_id}"
    conn.execute(
        "INSERT OR REPLACE INTO interview_results VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            result_id, candidate_id, session_id,
            json.dumps(scored_answers), overall_score, recommendation,
            summary, json.dumps(strengths), json.dumps(concerns),
            datetime.utcnow(),
        ],
    )


def get_interview_result(candidate_id: str, session_id: str) -> dict | None:
    conn = get_conn()
    row = conn.execute(
        """
        SELECT scored_answers, overall_score, recommendation, summary, strengths, concerns
        FROM interview_results
        WHERE candidate_id = ? AND session_id = ?
        ORDER BY completed_at DESC LIMIT 1
        """,
        [candidate_id, session_id],
    ).fetchone()
    if not row:
        return None
    return {
        "scored_answers": json.loads(row[0]),
        "overall_score": row[1],
        "recommendation": row[2],
        "summary": row[3],
        "strengths": json.loads(row[4]),
        "concerns": json.loads(row[5]),
    }


def get_session_with_candidates(session_id: str) -> dict | None:
    conn = get_conn()
    sess = conn.execute(
        "SELECT session_id, jd_text, position_title FROM sessions WHERE session_id = ?",
        [session_id],
    ).fetchone()
    if not sess:
        return None

    rows = conn.execute(
        """
        SELECT r.resume_id, r.name, r.email, r.experience_years, r.category, r.skills
        FROM session_candidates sc
        JOIN resumes r ON r.resume_id = sc.candidate_id
        WHERE sc.session_id = ?
        ORDER BY sc.created_at
        """,
        [session_id],
    ).fetchall()

    candidates = []
    for r in rows:
        result = get_interview_result(r[0], session_id)
        candidates.append({
            "candidate_id": r[0],
            "name": r[1],
            "email": r[2],
            "experience": r[3],
            "category": r[4],
            "skills": r[5],
            "status": "interviewed" if result else "pending",
            "overall_score": result["overall_score"] if result else None,
            "recommendation": result["recommendation"] if result else None,
        })

    return {
        "session_id": sess[0],
        "position_title": sess[2],
        "candidates": candidates,
    }


def list_all_sessions() -> list[dict]:
    """Return all sessions ordered newest-first, with candidate + interview status."""
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT s.session_id, s.position_title, s.created_at,
               r.resume_id, r.name, r.email, r.experience_years, r.category,
               ir.overall_score, ir.recommendation, ir.completed_at
        FROM sessions s
        JOIN session_candidates sc ON sc.session_id = s.session_id
        JOIN resumes r ON r.resume_id = sc.candidate_id
        LEFT JOIN interview_results ir
               ON ir.candidate_id = r.resume_id AND ir.session_id = s.session_id
        ORDER BY s.created_at DESC
        """
    ).fetchall()

    return [
        {
            "session_id": r[0],
            "position_title": r[1],
            "created_at": r[2].isoformat() if r[2] else None,
            "candidate_id": r[3],
            "candidate_name": r[4],
            "candidate_email": r[5],
            "experience": r[6],
            "category": r[7],
            "status": "interviewed" if r[8] is not None else "pending",
            "overall_score": r[8],
            "recommendation": r[9],
            "completed_at": r[10].isoformat() if r[10] else None,
        }
        for r in rows
    ]


def delete_session(session_id: str):
    conn = get_conn()
    conn.execute("DELETE FROM interview_results WHERE session_id = ?", [session_id])
    conn.execute("DELETE FROM session_candidates WHERE session_id = ?", [session_id])
    conn.execute("DELETE FROM sessions WHERE session_id = ?", [session_id])


def update_resume_fields(resume_id: str, category: str | None = None, experience_years: float | None = None):
    conn = get_conn()
    if category is not None:
        conn.execute("UPDATE resumes SET category = ? WHERE resume_id = ?", [category, resume_id])
    if experience_years is not None:
        conn.execute("UPDATE resumes SET experience_years = ? WHERE resume_id = ?", [experience_years, resume_id])


def insert_resume(**r):
    conn = get_conn()
    conn.execute(
        """
        INSERT OR REPLACE INTO resumes
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            r["resume_id"],
            r["name"],
            r["email"],
            r["phone"],
            r["category"],
            r["experience_years"],
            ", ".join(r["skills"]),
            r["raw_text"],
            r["drive_id"],
            r["item_id"],
            datetime.utcnow(),
        ],
    )
