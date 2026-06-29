"""
Shared fixtures for all test modules.

Key design decisions:
- Each test gets a fresh in-memory DuckDB so production data is never touched.
- OpenAI calls are never made in tests — patched at the API layer.
- TestClient is function-scoped so startup/shutdown events fire cleanly per test.
"""

import duckdb
import pytest
from fastapi.testclient import TestClient

import core.memory as mem


# ---------------------------------------------------------------------------
# In-memory DB — replaces the file-backed DuckDB for every test
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def fresh_db():
    """Swap the global DuckDB connection for a clean in-memory instance."""
    conn = duckdb.connect(":memory:")
    mem._init_tables(conn)
    old_conn = mem._conn
    mem._conn = conn
    yield conn
    mem._conn = old_conn
    try:
        conn.close()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# FastAPI TestClient
# ---------------------------------------------------------------------------

@pytest.fixture
def client(fresh_db):
    from api.server import app
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


# ---------------------------------------------------------------------------
# Reusable sample data
# ---------------------------------------------------------------------------

SAMPLE_JD = (
    "Job Title: Senior Sales Manager\n"
    "We are looking for an experienced sales professional to lead enterprise accounts. "
    "The ideal candidate has 5+ years in B2B sales, strong CRM experience (Salesforce), "
    "and a proven track record in pipeline management and closing large deals."
)

SAMPLE_RESUME_BYTES = b"""John Smith
john.smith@example.com
+91 9876543210

Senior Sales Manager | 6 Years Experience

Work Experience:
Jan 2019 - Present: Senior Sales Manager at CloudCorp
  - Managed enterprise accounts worth $5M ARR
  - Led a team of 8 sales reps

Jan 2017 - Dec 2018: Account Executive at TechSales Inc

Skills: salesforce, crm, enterprise sales, aws, hubspot, business development, pipeline management

Education: MBA from Mumbai University
"""

MOCK_QUESTIONS = [
    {"question": "Please introduce yourself and walk us through your professional background.", "type": "Introduction", "focus_area": "Communication"},
    {"question": "What is your current role and what are your key day-to-day responsibilities?", "type": "Role Experience", "focus_area": "Current Role"},
    {"question": "Walk us through your key achievements and notable projects from your previous roles.", "type": "Quota & Targets", "focus_area": "Previous Work"},
    {"question": "Why are you looking to move from your current company? What is driving this change?", "type": "Career Motivation", "focus_area": "Reason for Change"},
    {"question": "Tell me about a challenging situation you faced at work and how you handled it.", "type": "Client Acquisition", "focus_area": "Problem Solving"},
    {"question": "What is your current CTC (fixed + variable)? What is your expected CTC for this role?", "type": "Compensation", "focus_area": "Current vs Expected CTC"},
    {"question": "What is your current notice period? Is there any possibility of an early release if required?", "type": "Logistics", "focus_area": "Notice Period & Joining"},
    {"question": "Where do you see yourself in the next 2-3 years, and how does this role fit into that plan?", "type": "Sales Methodology", "focus_area": "Growth & Ambition"},
]

MOCK_SCORE_RESULT = {
    "scored_answers": [
        {**q, "notes": "Candidate gave a clear and confident response.", "stars": 4, "score": 8, "feedback": "Solid response, well-structured."}
        for q in MOCK_QUESTIONS
    ],
    "overall_score": 78,
    "recommendation": "Hire",
    "summary": "Strong candidate with clear communication and relevant background. CTC expectations are reasonable.",
    "strengths": ["Strong communication", "Relevant experience", "Reasonable notice period"],
    "concerns": ["Limited pre-sales exposure"],
}


@pytest.fixture
def uploaded_session(client):
    """Helper: upload one resume and return the session response body."""
    import io
    files = [("resumes", ("resume.txt", io.BytesIO(SAMPLE_RESUME_BYTES), "text/plain"))]
    r = client.post("/sessions/upload", data={"jd_text": SAMPLE_JD}, files=files)
    assert r.status_code == 200, r.text
    return r.json()
