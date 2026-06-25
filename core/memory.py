# core/memory.py

import json
import os
from contextlib import contextmanager
from datetime import datetime

import psycopg2
import psycopg2.pool

DATABASE_URL = os.getenv("DATABASE_URL", "")

_pool = None


def _get_pool():
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.ThreadedConnectionPool(1, 10, DATABASE_URL)
        _init_tables()
    return _pool


@contextmanager
def _db():
    """Acquire a connection from the pool, commit on success, rollback on error."""
    pool = _get_pool()
    conn = pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


def _q(sql):
    """Convert DuckDB ? placeholders to psycopg2 %s."""
    return sql.replace("?", "%s")


def _exec(sql, params=None, fetch=None):
    with _db() as conn:
        cur = conn.cursor()
        cur.execute(_q(sql), params or [])
        if fetch == "one":
            return cur.fetchone()
        if fetch == "all":
            return cur.fetchall()
        return None


def _init_tables():
    with _db() as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS resumes (
                resume_id TEXT PRIMARY KEY,
                name TEXT,
                email TEXT,
                phone TEXT,
                category TEXT,
                experience_years FLOAT,
                skills TEXT,
                raw_text TEXT,
                drive_id TEXT,
                item_id TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                jd_text TEXT,
                position_title TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS session_candidates (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                candidate_id TEXT,
                questions TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("""
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
                completed_at TIMESTAMP DEFAULT NOW()
            )
        """)


# ── Public helpers used by server.py ─────────────────────────────────────────

def resume_exists(item_id: str) -> bool:
    row = _exec("SELECT 1 FROM resumes WHERE item_id = ?", [item_id], fetch="one")
    return row is not None


def insert_resume(**r):
    _exec(
        """
        INSERT INTO resumes
            (resume_id, name, email, phone, category, experience_years,
             skills, raw_text, drive_id, item_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (resume_id) DO UPDATE SET
            name = EXCLUDED.name,
            email = EXCLUDED.email,
            phone = EXCLUDED.phone,
            category = EXCLUDED.category,
            experience_years = EXCLUDED.experience_years,
            skills = EXCLUDED.skills,
            raw_text = EXCLUDED.raw_text
        """,
        [
            r["resume_id"], r["name"], r["email"], r["phone"],
            r["category"], r["experience_years"],
            ", ".join(r["skills"]) if isinstance(r["skills"], list) else r["skills"],
            r["raw_text"], r["drive_id"], r["item_id"],
            datetime.utcnow(),
        ],
    )


def create_session(session_id: str, jd_text: str, position_title: str):
    _exec(
        "INSERT INTO sessions (session_id, jd_text, position_title, created_at) VALUES (?, ?, ?, ?)",
        [session_id, jd_text, position_title, datetime.utcnow()],
    )


def add_session_candidate(sc_id: str, session_id: str, candidate_id: str):
    _exec(
        "INSERT INTO session_candidates (id, session_id, candidate_id, created_at) VALUES (?, ?, ?, ?)",
        [sc_id, session_id, candidate_id, datetime.utcnow()],
    )


def save_questions(session_id: str, candidate_id: str, questions: list):
    _exec(
        "UPDATE session_candidates SET questions = ? WHERE session_id = ? AND candidate_id = ?",
        [json.dumps(questions), session_id, candidate_id],
    )


def get_questions(session_id: str, candidate_id: str):
    row = _exec(
        "SELECT questions FROM session_candidates WHERE session_id = ? AND candidate_id = ?",
        [session_id, candidate_id],
        fetch="one",
    )
    if row and row[0]:
        return json.loads(row[0])
    return None


def save_interview_result(
    candidate_id, session_id, scored_answers, overall_score,
    recommendation, summary, strengths, concerns,
):
    result_id = f"{candidate_id}_{session_id}"
    _exec(
        """
        INSERT INTO interview_results
            (result_id, candidate_id, session_id, scored_answers, overall_score,
             recommendation, summary, strengths, concerns, completed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (result_id) DO UPDATE SET
            scored_answers  = EXCLUDED.scored_answers,
            overall_score   = EXCLUDED.overall_score,
            recommendation  = EXCLUDED.recommendation,
            summary         = EXCLUDED.summary,
            strengths       = EXCLUDED.strengths,
            concerns        = EXCLUDED.concerns,
            completed_at    = EXCLUDED.completed_at
        """,
        [
            result_id, candidate_id, session_id,
            json.dumps(scored_answers), overall_score, recommendation,
            summary, json.dumps(strengths), json.dumps(concerns),
            datetime.utcnow(),
        ],
    )


def get_interview_result(candidate_id: str, session_id: str):
    row = _exec(
        """
        SELECT scored_answers, overall_score, recommendation, summary, strengths, concerns
        FROM interview_results
        WHERE candidate_id = ? AND session_id = ?
        ORDER BY completed_at DESC LIMIT 1
        """,
        [candidate_id, session_id],
        fetch="one",
    )
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


def get_session_with_candidates(session_id: str):
    sess = _exec(
        "SELECT session_id, jd_text, position_title FROM sessions WHERE session_id = ?",
        [session_id],
        fetch="one",
    )
    if not sess:
        return None

    rows = _exec(
        """
        SELECT r.resume_id, r.name, r.email, r.experience_years, r.category, r.skills
        FROM session_candidates sc
        JOIN resumes r ON r.resume_id = sc.candidate_id
        WHERE sc.session_id = ?
        ORDER BY sc.created_at
        """,
        [session_id],
        fetch="all",
    )

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

    return {"session_id": sess[0], "position_title": sess[2], "candidates": candidates}


def list_all_sessions() -> list:
    rows = _exec(
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
        """,
        fetch="all",
    )
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
        for r in (rows or [])
    ]


def delete_session(session_id: str):
    _exec("DELETE FROM interview_results WHERE session_id = ?", [session_id])
    _exec("DELETE FROM session_candidates WHERE session_id = ?", [session_id])
    _exec("DELETE FROM sessions WHERE session_id = ?", [session_id])


def update_resume_fields(resume_id: str, category=None, experience_years=None):
    if category is not None:
        _exec("UPDATE resumes SET category = ? WHERE resume_id = ?", [category, resume_id])
    if experience_years is not None:
        _exec("UPDATE resumes SET experience_years = ? WHERE resume_id = ?", [experience_years, resume_id])


# ── Helpers for server.py (replaces direct get_conn() calls) ─────────────────

def fetch_resume(resume_id: str):
    """Returns (name, email, experience_years, category, raw_text) or None."""
    return _exec(
        "SELECT name, email, experience_years, category, raw_text FROM resumes WHERE resume_id = ?",
        [resume_id],
        fetch="one",
    )


def fetch_resume_summary(resume_id: str):
    """Returns (name, email, experience_years, category, skills) or None."""
    return _exec(
        "SELECT name, email, experience_years, category, skills FROM resumes WHERE resume_id = ?",
        [resume_id],
        fetch="one",
    )


def fetch_session(session_id: str):
    """Returns (jd_text, position_title) or None."""
    return _exec(
        "SELECT jd_text, position_title FROM sessions WHERE session_id = ?",
        [session_id],
        fetch="one",
    )


def fetch_session_title(session_id: str):
    """Returns (position_title,) or None."""
    return _exec(
        "SELECT position_title FROM sessions WHERE session_id = ?",
        [session_id],
        fetch="one",
    )


def list_resumes_db(limit: int = 50):
    return _exec(
        "SELECT resume_id, name, email, category, experience_years, skills FROM resumes ORDER BY created_at DESC LIMIT ?",
        [limit],
        fetch="all",
    ) or []


def get_resumes_for_shortlist(category: str, min_exp: float, max_exp: float):
    return _exec(
        """
        SELECT resume_id, drive_id, item_id, name, email, experience_years, skills, raw_text
        FROM resumes
        WHERE category = ? AND experience_years BETWEEN ? AND ?
        """,
        [category, min_exp, max_exp],
        fetch="all",
    ) or []
