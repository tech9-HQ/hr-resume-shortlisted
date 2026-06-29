"""
Unit tests for core/interview.py.

Question generation calls OpenAI and falls back to PRESCREENING_QUESTIONS.
Scoring also calls OpenAI; both are patched so no API key is needed.
"""

from unittest.mock import patch, MagicMock
from core.interview import (
    generate_interview_questions,
    score_interview_answers,
    PRESCREENING_QUESTIONS,
    MANDATORY_TYPES,
)


# ---------------------------------------------------------------------------
# PRESCREENING_QUESTIONS fallback constant
# ---------------------------------------------------------------------------

def test_prescreening_has_8_questions():
    assert len(PRESCREENING_QUESTIONS) == 8


def test_prescreening_covers_all_required_types():
    types = {q["type"] for q in PRESCREENING_QUESTIONS}
    assert MANDATORY_TYPES.issubset(types)


def test_prescreening_questions_have_required_keys():
    for q in PRESCREENING_QUESTIONS:
        assert "question" in q and "type" in q and "focus_area" in q


# ---------------------------------------------------------------------------
# generate_interview_questions — AI success path
# ---------------------------------------------------------------------------

def _mock_ai_questions(n=8):
    """Build a mock OpenAI client that returns n valid pre-screening questions with dynamic types."""
    import json
    # Mandatory types first, then profile-specific dynamic types
    types = ["Introduction", "Compensation", "Logistics",
             "Quota & Targets", "Client Acquisition", "Sales Methodology",
             "Pipeline Management", "Career Motivation"]
    fake_qs = [
        {"question": f"Personalised question {i}?", "type": types[i % len(types)], "focus_area": f"Area {i}"}
        for i in range(n)
    ]
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = json.dumps(fake_qs)
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_resp
    return mock_client


def test_generate_questions_returns_8_on_success():
    with patch("core.interview._get_client", return_value=_mock_ai_questions()):
        qs = generate_interview_questions("resume text", "jd text", "Sales Manager")
    assert len(qs) == 8


def test_generate_questions_have_required_keys_on_success():
    with patch("core.interview._get_client", return_value=_mock_ai_questions()):
        qs = generate_interview_questions("resume", "jd", "HR Role")
    for q in qs:
        assert "question" in q and "type" in q and "focus_area" in q


def test_generate_questions_mandatory_types_present_on_success():
    with patch("core.interview._get_client", return_value=_mock_ai_questions()):
        qs = generate_interview_questions("resume", "jd", "HR Role")
    present_types = {q["type"] for q in qs}
    assert MANDATORY_TYPES.issubset(present_types), f"Missing mandatory types in: {present_types}"


# ---------------------------------------------------------------------------
# generate_interview_questions — fallback when AI fails
# ---------------------------------------------------------------------------

def test_generate_questions_falls_back_on_exception():
    with patch("core.interview._get_client", side_effect=Exception("no key")):
        qs = generate_interview_questions("resume", "jd", "Sales Manager")
    assert qs == PRESCREENING_QUESTIONS


def test_generate_questions_falls_back_on_invalid_json():
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = "not valid json {{{"
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_resp
    with patch("core.interview._get_client", return_value=mock_client):
        qs = generate_interview_questions("resume", "jd", "Sales Manager")
    assert qs == PRESCREENING_QUESTIONS


def test_generate_questions_falls_back_when_wrong_count():
    """If AI returns fewer than 8 questions, use the safe fallback."""
    import json
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = json.dumps(
        [{"question": "Q?", "type": "Behavioral", "focus_area": "General"}]
    )
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_resp
    with patch("core.interview._get_client", return_value=mock_client):
        qs = generate_interview_questions("resume", "jd", "Sales Manager")
    assert qs == PRESCREENING_QUESTIONS


def test_generate_questions_falls_back_on_non_list_json():
    import json
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = json.dumps({"error": "oops"})
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_resp
    with patch("core.interview._get_client", return_value=mock_client):
        qs = generate_interview_questions("resume", "jd", "Sales Manager")
    assert qs == PRESCREENING_QUESTIONS


# ---------------------------------------------------------------------------
# score_interview_answers — OpenAI success path
# ---------------------------------------------------------------------------

def _sample_qa():
    return [
        {"question": "Introduce yourself.", "type": "Introduction", "focus_area": "Communication",
         "notes": "Confident intro, 6 years in enterprise sales.", "stars": 4},
        {"question": "Current vs expected CTC?", "type": "Compensation", "focus_area": "Current vs Expected CTC",
         "notes": "Current 12L fixed + 3L variable. Expecting 18L.", "stars": 3},
    ]


def _mock_openai_scoring():
    import json
    result = {
        "scored_answers": [
            {"question": "Introduce yourself.", "type": "Introduction", "focus_area": "Communication",
             "answer": "I have 6 years in sales.", "score": 8, "feedback": "Clear and confident."},
            {"question": "Current vs expected CTC?", "type": "Compensation", "focus_area": "Current vs Expected CTC",
             "answer": "Current 12L, expecting 18L.", "score": 7, "feedback": "Reasonable ask."},
        ],
        "overall_score": 72,
        "recommendation": "Hire",
        "summary": "Strong candidate.",
        "strengths": ["Communication", "Experience", "Clarity"],
        "concerns": ["Salary jump is 50%"],
    }
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = json.dumps(result)
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_resp
    return mock_client


def test_score_answers_returns_required_keys():
    with patch("core.interview._get_client", return_value=_mock_openai_scoring()):
        result = score_interview_answers(_sample_qa(), "resume", "jd", "Sales Manager")
    for key in ("scored_answers", "overall_score", "recommendation", "summary", "strengths", "concerns"):
        assert key in result


def test_score_answers_overall_score_in_range():
    with patch("core.interview._get_client", return_value=_mock_openai_scoring()):
        result = score_interview_answers(_sample_qa(), "resume", "jd", "Sales Manager")
    assert 0 <= result["overall_score"] <= 100


def test_score_answers_recommendation_is_valid():
    with patch("core.interview._get_client", return_value=_mock_openai_scoring()):
        result = score_interview_answers(_sample_qa(), "resume", "jd", "Sales Manager")
    assert result["recommendation"] in {"Strong Hire", "Hire", "Maybe", "No Hire"}


def test_score_answers_count_matches_input():
    with patch("core.interview._get_client", return_value=_mock_openai_scoring()):
        result = score_interview_answers(_sample_qa(), "resume", "jd", "Sales Manager")
    assert len(result["scored_answers"]) == len(_sample_qa())


# ---------------------------------------------------------------------------
# score_interview_answers — fallback on OpenAI failure
# ---------------------------------------------------------------------------

def test_score_answers_falls_back_on_exception():
    # _sample_qa has stars 4 (→8) and 3 (→6), average 7, overall 70 → "Hire"
    with patch("core.interview._get_client", side_effect=Exception("no key")):
        result = score_interview_answers(_sample_qa(), "resume", "jd", "Sales Manager")
    assert result["overall_score"] == 70
    assert result["recommendation"] == "Hire"


def test_score_answers_fallback_preserves_qa_count():
    qa = _sample_qa()
    with patch("core.interview._get_client", side_effect=Exception("no key")):
        result = score_interview_answers(qa, "resume", "jd", "Sales Manager")
    assert len(result["scored_answers"]) == len(qa)


def test_score_answers_handles_no_notes_or_stars():
    qa = [{"question": "Notice period?", "type": "Logistics", "focus_area": "Notice Period & Joining",
           "notes": "", "stars": 0}]
    with patch("core.interview._get_client", side_effect=Exception("no key")):
        result = score_interview_answers(qa, "resume", "jd", "Sales Manager")
    assert result["scored_answers"][0]["score"] == 5  # 0 stars → default 5


def test_score_answers_fallback_uses_star_rating():
    qa = [{"question": "Introduce yourself.", "type": "Introduction", "focus_area": "Communication",
           "notes": "Great communicator", "stars": 5}]
    with patch("core.interview._get_client", side_effect=Exception("no key")):
        result = score_interview_answers(qa, "resume", "jd", "Sales Manager")
    assert result["scored_answers"][0]["score"] == 10  # 5 stars → 10
