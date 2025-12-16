# core/memory.py

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


def resume_exists(item_id: str) -> bool:
    conn = get_conn()
    return conn.execute(
        "SELECT 1 FROM resumes WHERE item_id = ?",
        [item_id]
    ).fetchone() is not None


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
