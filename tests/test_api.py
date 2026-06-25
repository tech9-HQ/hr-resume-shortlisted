"""
Integration tests for api/server.py endpoints.

Uses FastAPI TestClient + in-memory DuckDB (from conftest.py).
OpenAI calls are patched so no API key is needed.
"""

import io
from unittest.mock import patch

from tests.conftest import (
    SAMPLE_JD,
    SAMPLE_RESUME_BYTES,
    MOCK_QUESTIONS,
    MOCK_SCORE_RESULT,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resume_file(name="resume.txt", content=None):
    return ("resumes", (name, io.BytesIO(content or SAMPLE_RESUME_BYTES), "text/plain"))


def _upload(client, jd=SAMPLE_JD, resumes=None):
    files = resumes or [_resume_file()]
    return client.post("/sessions/upload", data={"jd_text": jd}, files=files)


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# POST /sessions/start  (new single-candidate flow)
# ---------------------------------------------------------------------------

def test_start_interview_success(client):
    r = client.post(
        "/sessions/start",
        data={"candidate_name": "Priya Sharma", "position": "Backend Engineer", "jd_text": SAMPLE_JD},
        files=[("resume", ("r.txt", io.BytesIO(SAMPLE_RESUME_BYTES), "text/plain"))],
    )
    assert r.status_code == 200
    body = r.json()
    assert body["candidate"]["name"] == "Priya Sharma"
    assert body["position_title"] == "Backend Engineer"
    assert "session_id" in body


def test_start_interview_uses_provided_name_not_extracted(client):
    """Name must come from the form field, not from resume text."""
    r = client.post(
        "/sessions/start",
        data={"candidate_name": "Override Name", "position": "Engineer", "jd_text": SAMPLE_JD},
        files=[("resume", ("r.txt", io.BytesIO(SAMPLE_RESUME_BYTES), "text/plain"))],
    )
    assert r.json()["candidate"]["name"] == "Override Name"


def test_start_interview_missing_name_returns_400(client):
    r = client.post(
        "/sessions/start",
        data={"candidate_name": "  ", "position": "Engineer", "jd_text": SAMPLE_JD},
        files=[("resume", ("r.txt", io.BytesIO(SAMPLE_RESUME_BYTES), "text/plain"))],
    )
    assert r.status_code == 400


def test_start_interview_missing_position_returns_400(client):
    r = client.post(
        "/sessions/start",
        data={"candidate_name": "Jane", "position": "", "jd_text": SAMPLE_JD},
        files=[("resume", ("r.txt", io.BytesIO(SAMPLE_RESUME_BYTES), "text/plain"))],
    )
    assert r.status_code == 400


def test_start_interview_missing_jd_returns_400(client):
    r = client.post(
        "/sessions/start",
        data={"candidate_name": "Jane", "position": "Engineer", "jd_text": "  "},
        files=[("resume", ("r.txt", io.BytesIO(SAMPLE_RESUME_BYTES), "text/plain"))],
    )
    assert r.status_code == 400


def test_start_interview_bad_resume_returns_400(client):
    r = client.post(
        "/sessions/start",
        data={"candidate_name": "Jane", "position": "Engineer", "jd_text": SAMPLE_JD},
        files=[("resume", ("r.txt", io.BytesIO(b"hi"), "text/plain"))],
    )
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# GET /sessions  (history list)
# ---------------------------------------------------------------------------

def test_list_sessions_empty(client):
    r = client.get("/sessions")
    assert r.status_code == 200
    assert r.json() == []


def test_list_sessions_after_start(client):
    client.post(
        "/sessions/start",
        data={"candidate_name": "Test User", "position": "Engineer", "jd_text": SAMPLE_JD},
        files=[("resume", ("r.txt", io.BytesIO(SAMPLE_RESUME_BYTES), "text/plain"))],
    )
    r = client.get("/sessions")
    assert r.status_code == 200
    sessions = r.json()
    assert len(sessions) == 1
    assert sessions[0]["candidate_name"] == "Test User"
    assert sessions[0]["position_title"] == "Engineer"
    assert sessions[0]["status"] == "pending"


@patch("api.server.score_interview_answers", return_value=MOCK_SCORE_RESULT)
def test_list_sessions_shows_interviewed_status(mock_score, client):
    start = client.post(
        "/sessions/start",
        data={"candidate_name": "Scored User", "position": "Manager", "jd_text": SAMPLE_JD},
        files=[("resume", ("r.txt", io.BytesIO(SAMPLE_RESUME_BYTES), "text/plain"))],
    ).json()
    sid = start["session_id"]
    cid = start["candidate"]["candidate_id"]
    answers = [{**q, "notes": "Good response.", "stars": 4} for q in MOCK_QUESTIONS]
    client.post(f"/candidates/{cid}/evaluate", json={"session_id": sid, "answers": answers})

    sessions = client.get("/sessions").json()
    assert sessions[0]["status"] == "interviewed"
    assert sessions[0]["overall_score"] == 78
    assert sessions[0]["recommendation"] == "Hire"


# ---------------------------------------------------------------------------
# POST /sessions/upload
# ---------------------------------------------------------------------------

def test_upload_session_returns_session_id(client):
    r = _upload(client)
    assert r.status_code == 200
    assert "session_id" in r.json()


def test_upload_session_returns_position_title(client):
    r = _upload(client)
    assert r.json()["position_title"]


def test_upload_session_returns_candidates(client):
    r = _upload(client)
    candidates = r.json()["candidates"]
    assert len(candidates) == 1


def test_upload_session_candidate_has_required_fields(client):
    r = _upload(client)
    c = r.json()["candidates"][0]
    for field in ("candidate_id", "name", "email", "experience", "category", "status"):
        assert field in c, f"Missing field: {field}"


def test_upload_session_candidate_status_is_pending(client):
    r = _upload(client)
    assert r.json()["candidates"][0]["status"] == "pending"


def test_upload_session_multiple_resumes(client):
    files = [_resume_file("r1.txt"), _resume_file("r2.txt"), _resume_file("r3.txt")]
    r = _upload(client, resumes=files)
    assert r.status_code == 200
    assert len(r.json()["candidates"]) == 3


def test_upload_session_empty_jd_returns_400(client):
    r = _upload(client, jd="   ")
    assert r.status_code == 400


def test_upload_session_empty_resume_content_skipped(client):
    tiny = b"hi"  # too short — will be skipped
    files = [
        _resume_file("tiny.txt", tiny),
        _resume_file("good.txt"),
    ]
    r = _upload(client, resumes=files)
    assert r.status_code == 200
    assert len(r.json()["candidates"]) == 1  # only the good one


def test_upload_session_all_empty_resumes_returns_400(client):
    files = [_resume_file("tiny.txt", b"hi")]
    r = _upload(client, resumes=files)
    assert r.status_code == 400


def test_upload_session_detects_category(client):
    presales_resume = SAMPLE_RESUME_BYTES + b"\npre-sales solution consultant demo rfp"
    files = [_resume_file("ps.txt", presales_resume)]
    r = _upload(client, resumes=files)
    c = r.json()["candidates"][0]
    assert c["category"] in ("Sales", "Pre-Sales")


# ---------------------------------------------------------------------------
# GET /sessions/{session_id}
# ---------------------------------------------------------------------------

def test_get_session_returns_session(client, uploaded_session):
    sid = uploaded_session["session_id"]
    r = client.get(f"/sessions/{sid}")
    assert r.status_code == 200
    assert r.json()["session_id"] == sid


def test_get_session_has_candidates(client, uploaded_session):
    sid = uploaded_session["session_id"]
    r = client.get(f"/sessions/{sid}")
    assert len(r.json()["candidates"]) == 1


def test_get_session_not_found(client):
    r = client.get("/sessions/does-not-exist")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# GET /candidates/{id}/questions
# ---------------------------------------------------------------------------

@patch("api.server.generate_interview_questions", return_value=MOCK_QUESTIONS)
def test_get_questions_returns_8(mock_gen, client, uploaded_session):
    sid = uploaded_session["session_id"]
    cid = uploaded_session["candidates"][0]["candidate_id"]
    r = client.get(f"/candidates/{cid}/questions?session_id={sid}")
    assert r.status_code == 200
    assert len(r.json()["questions"]) == 8


@patch("api.server.generate_interview_questions", return_value=MOCK_QUESTIONS)
def test_get_questions_includes_candidate_info(mock_gen, client, uploaded_session):
    sid = uploaded_session["session_id"]
    cid = uploaded_session["candidates"][0]["candidate_id"]
    r = client.get(f"/candidates/{cid}/questions?session_id={sid}")
    body = r.json()
    assert "candidate" in body
    assert body["candidate"]["candidate_id"] == cid


@patch("api.server.generate_interview_questions", return_value=MOCK_QUESTIONS)
def test_get_questions_caches_on_second_call(mock_gen, client, uploaded_session):
    sid = uploaded_session["session_id"]
    cid = uploaded_session["candidates"][0]["candidate_id"]
    url = f"/candidates/{cid}/questions?session_id={sid}"
    client.get(url)
    client.get(url)
    # generate_interview_questions should only be called once; second hit is cached
    assert mock_gen.call_count == 1


def test_get_questions_unknown_candidate_returns_404(client, uploaded_session):
    sid = uploaded_session["session_id"]
    r = client.get(f"/candidates/bad-id/questions?session_id={sid}")
    assert r.status_code == 404


def test_get_questions_unknown_session_returns_404(client, uploaded_session):
    cid = uploaded_session["candidates"][0]["candidate_id"]
    r = client.get(f"/candidates/{cid}/questions?session_id=bad-session")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# POST /candidates/{id}/evaluate
# ---------------------------------------------------------------------------

def _evaluate(client, uploaded_session):
    sid = uploaded_session["session_id"]
    cid = uploaded_session["candidates"][0]["candidate_id"]
    answers = [
        {**q, "notes": "Candidate gave a clear response.", "stars": 4}
        for q in MOCK_QUESTIONS
    ]
    return client.post(
        f"/candidates/{cid}/evaluate",
        json={"session_id": sid, "answers": answers},
    )


@patch("api.server.score_interview_answers", return_value=MOCK_SCORE_RESULT)
def test_evaluate_returns_200(mock_score, client, uploaded_session):
    r = _evaluate(client, uploaded_session)
    assert r.status_code == 200


@patch("api.server.score_interview_answers", return_value=MOCK_SCORE_RESULT)
def test_evaluate_returns_overall_score(mock_score, client, uploaded_session):
    r = _evaluate(client, uploaded_session)
    assert r.json()["overall_score"] == 78


@patch("api.server.score_interview_answers", return_value=MOCK_SCORE_RESULT)
def test_evaluate_returns_recommendation(mock_score, client, uploaded_session):
    r = _evaluate(client, uploaded_session)
    assert r.json()["recommendation"] == "Hire"


@patch("api.server.score_interview_answers", return_value=MOCK_SCORE_RESULT)
def test_evaluate_returns_scored_answers(mock_score, client, uploaded_session):
    r = _evaluate(client, uploaded_session)
    assert len(r.json()["scored_answers"]) == len(MOCK_QUESTIONS)


@patch("api.server.score_interview_answers", return_value=MOCK_SCORE_RESULT)
def test_evaluate_stores_result_in_db(mock_score, client, uploaded_session):
    sid = uploaded_session["session_id"]
    cid = uploaded_session["candidates"][0]["candidate_id"]
    _evaluate(client, uploaded_session)
    from core.memory import get_interview_result
    result = get_interview_result(cid, sid)
    assert result is not None
    assert result["overall_score"] == 78


def test_evaluate_unknown_candidate_returns_404(client, uploaded_session):
    sid = uploaded_session["session_id"]
    r = client.post(
        "/candidates/bad-id/evaluate",
        json={"session_id": sid, "answers": []},
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# GET /candidates/{id}/report
# ---------------------------------------------------------------------------

@patch("api.server.score_interview_answers", return_value=MOCK_SCORE_RESULT)
def test_report_after_evaluate_returns_200(mock_score, client, uploaded_session):
    _evaluate(client, uploaded_session)
    sid = uploaded_session["session_id"]
    cid = uploaded_session["candidates"][0]["candidate_id"]
    r = client.get(f"/candidates/{cid}/report?session_id={sid}")
    assert r.status_code == 200


@patch("api.server.score_interview_answers", return_value=MOCK_SCORE_RESULT)
def test_report_contains_candidate_info(mock_score, client, uploaded_session):
    _evaluate(client, uploaded_session)
    sid = uploaded_session["session_id"]
    cid = uploaded_session["candidates"][0]["candidate_id"]
    body = client.get(f"/candidates/{cid}/report?session_id={sid}").json()
    assert body["candidate"]["candidate_id"] == cid
    assert body["candidate"]["name"]


@patch("api.server.score_interview_answers", return_value=MOCK_SCORE_RESULT)
def test_report_contains_session_info(mock_score, client, uploaded_session):
    _evaluate(client, uploaded_session)
    sid = uploaded_session["session_id"]
    cid = uploaded_session["candidates"][0]["candidate_id"]
    body = client.get(f"/candidates/{cid}/report?session_id={sid}").json()
    assert body["session"]["position_title"]


@patch("api.server.score_interview_answers", return_value=MOCK_SCORE_RESULT)
def test_report_overall_score_matches_evaluate(mock_score, client, uploaded_session):
    _evaluate(client, uploaded_session)
    sid = uploaded_session["session_id"]
    cid = uploaded_session["candidates"][0]["candidate_id"]
    body = client.get(f"/candidates/{cid}/report?session_id={sid}").json()
    assert body["overall_score"] == 78


def test_report_before_evaluate_returns_404(client, uploaded_session):
    sid = uploaded_session["session_id"]
    cid = uploaded_session["candidates"][0]["candidate_id"]
    r = client.get(f"/candidates/{cid}/report?session_id={sid}")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Session candidate status updates after evaluate
# ---------------------------------------------------------------------------

@patch("api.server.score_interview_answers", return_value=MOCK_SCORE_RESULT)
def test_session_candidate_status_is_interviewed_after_evaluate(mock_score, client, uploaded_session):
    _evaluate(client, uploaded_session)
    sid = uploaded_session["session_id"]
    session = client.get(f"/sessions/{sid}").json()
    c = session["candidates"][0]
    assert c["status"] == "interviewed"
    assert c["overall_score"] == 78
    assert c["recommendation"] == "Hire"
