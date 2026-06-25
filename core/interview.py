# core/interview.py
from __future__ import annotations

import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

MODEL = "gpt-4.1-mini"
_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


PRESCREENING_QUESTIONS = [
    {
        "question": "Please introduce yourself and walk us through your professional background.",
        "type": "Introduction",
        "focus_area": "Communication",
    },
    {
        "question": "What is your current role and what are your key day-to-day responsibilities?",
        "type": "Background",
        "focus_area": "Current Role",
    },
    {
        "question": "Walk us through your key achievements and notable projects from your previous roles.",
        "type": "Background",
        "focus_area": "Previous Work",
    },
    {
        "question": "Why are you looking to move from your current company? What is driving this change?",
        "type": "Behavioral",
        "focus_area": "Motivation",
    },
    {
        "question": "Tell me about a challenging situation you faced at work and how you handled it.",
        "type": "Behavioral",
        "focus_area": "Problem Solving",
    },
    {
        "question": "What is your current CTC (fixed + variable)? What is your expected CTC for this role?",
        "type": "Compensation",
        "focus_area": "Current vs Expected CTC",
    },
    {
        "question": "What is your current notice period? Is there any possibility of an early release if required?",
        "type": "Logistics",
        "focus_area": "Notice Period & Joining",
    },
    {
        "question": "Where do you see yourself in the next 2–3 years, and how does this role fit into that plan?",
        "type": "Behavioral",
        "focus_area": "Career Goals",
    },
]


ALLOWED_TYPES = {"Introduction", "Background", "Behavioral", "Compensation", "Logistics"}


def _valid_questions(data: object) -> bool:
    """Return True only if data is exactly 8 well-formed questions with allowed types."""
    if not isinstance(data, list) or len(data) != 8:
        return False
    return all(
        isinstance(q, dict)
        and isinstance(q.get("question"), str) and q["question"].strip()
        and q.get("type") in ALLOWED_TYPES
        and isinstance(q.get("focus_area"), str) and q["focus_area"].strip()
        for q in data
    )


def generate_interview_questions(
    resume_text: str, jd_text: str, position: str
) -> list[dict]:
    """
    Generate 8 personalised HR pre-screening questions using the candidate's
    resume and the JD. Falls back to the generic template if AI is unavailable
    or returns questions with wrong types.
    """
    system = (
        "You are an HR recruiter doing an initial phone pre-screening — NOT a technical interview.\n"
        "Generate exactly 8 pre-screening questions personalised to this specific candidate.\n\n"
        "MANDATORY QUESTION TYPES — use ONLY these five values for the 'type' field:\n"
        '  "Introduction"  — one question: ask the candidate to introduce themselves\n'
        '  "Compensation"  — one question: ask for current CTC (fixed + variable) AND expected CTC\n'
        '  "Logistics"     — one question: ask about notice period and early-joining possibility\n'
        '  "Background"    — personalised questions about their specific past roles/companies/achievements\n'
        '  "Behavioral"    — questions about motivation, work style, challenges, career goals\n\n'
        "FORBIDDEN types — NEVER use these: Technical, Situational, Skill, Domain, Other.\n"
        "FORBIDDEN content — do NOT ask deep technical or architecture questions. HR cannot evaluate these.\n\n"
        "OUTPUT FORMAT — respond ONLY with a raw JSON array, no markdown fences, no explanation:\n"
        '[{"question": "...", "type": "Introduction|Background|Behavioral|Compensation|Logistics", "focus_area": "3-5 word label"}, ...]\n\n'
        "Exactly 8 elements. Exactly 1 Introduction, 1 Compensation, 1 Logistics. Rest are Background/Behavioral."
    )
    user = (
        f"POSITION APPLIED FOR: {position}\n\n"
        f"JOB DESCRIPTION:\n{jd_text[:2500]}\n\n"
        f"CANDIDATE RESUME:\n{resume_text[:4000]}\n\n"
        "Generate 8 personalised HR pre-screening questions. Remember: HR types only, no technical questions."
    )

    try:
        resp = _get_client().chat.completions.create(
            model=MODEL,
            temperature=0.5,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        content = (resp.choices[0].message.content or "[]").strip()
        if content.startswith("```"):
            parts = content.split("```")
            content = parts[1] if len(parts) > 1 else content
            if content.lstrip().startswith("json"):
                content = content.lstrip()[4:]
        data = json.loads(content.strip())
        if _valid_questions(data):
            return data
        return PRESCREENING_QUESTIONS
    except Exception:
        return PRESCREENING_QUESTIONS


def score_interview_answers(
    qa_pairs: list[dict],
    resume_text: str,
    jd_text: str,
    position: str,
) -> dict:
    """
    Score a phone pre-screening interview from HR notes + star ratings.
    qa_pairs: [{question, type, focus_area, notes, stars}, ...]
    Returns {scored_answers, overall_score, recommendation, summary, strengths, concerns}.
    """
    def _star_bar(stars: int) -> str:
        s = max(0, min(5, stars))
        return f"{'★' * s}{'☆' * (5 - s)} ({s}/5)"

    qa_text = "\n\n".join(
        f"Q{i + 1} [{item.get('type', '')} | {item.get('focus_area', '')}]:\n"
        f"Question: {item.get('question', '')}\n"
        f"HR Rating: {_star_bar(item.get('stars', 0))}\n"
        f"HR Notes: {item.get('notes', '').strip() or '(no notes recorded)'}"
        for i, item in enumerate(qa_pairs)
    )

    system = (
        "You are a senior HR evaluator reviewing a phone pre-screening interview.\n"
        "The HR interviewer captured brief notes and a star rating (1–5) per question during the call.\n\n"
        "Star rating → score guide:\n"
        "  5 ★ Excellent  → score 9–10\n"
        "  4 ★ Good       → score 7–8\n"
        "  3 ★ Average    → score 5–6\n"
        "  2 ★ Below avg  → score 3–4\n"
        "  1 ★ Poor       → score 1–2\n"
        "  0 ★ Not rated  → infer from notes alone\n\n"
        "Respond ONLY with a valid JSON object — no markdown, no explanation.\n"
        "Required keys:\n"
        '  "scored_answers": array — one object per question:\n'
        '    "question" (string), "type" (string), "focus_area" (string),\n'
        '    "notes" (string — HR notes as provided), "stars" (integer 0–5),\n'
        '    "score" (integer 0–10), "feedback" (1–2 sentence AI evaluation)\n'
        '  "overall_score": integer 0–100\n'
        '  "recommendation": one of "Strong Hire", "Hire", "Maybe", "No Hire"\n'
        '  "summary": 3–4 sentence overall candidate assessment based on the notes and ratings\n'
        '  "strengths": array of exactly 3 short strings\n'
        '  "concerns": array of 2–3 short strings\n'
        "Strong hire = 80+, Hire = 65–79, Maybe = 45–64, No Hire = <45."
    )
    user = (
        f"POSITION: {position}\n\n"
        f"JOB DESCRIPTION:\n{jd_text[:2000]}\n\n"
        f"CANDIDATE RESUME:\n{resume_text[:3000]}\n\n"
        f"PHONE SCREENING NOTES:\n{qa_text}\n\n"
        "Score each question and produce the overall evaluation."
    )

    try:
        resp = _get_client().chat.completions.create(
            model=MODEL,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        data = json.loads(resp.choices[0].message.content or "{}")
        if "scored_answers" not in data or not isinstance(data["scored_answers"], list):
            data["scored_answers"] = [
                {**q, "score": _stars_to_score(q.get("stars", 0)), "feedback": "Notes recorded."}
                for q in qa_pairs
            ]
        return data
    except Exception:
        return _fallback_score(qa_pairs)


def _stars_to_score(stars: int) -> int:
    """Convert 1–5 star rating to 0–10 score. Unrated (0) defaults to 5."""
    return {0: 5, 1: 2, 2: 4, 3: 6, 4: 8, 5: 10}.get(max(0, min(5, stars)), 5)


def _fallback_score(qa_pairs: list[dict]) -> dict:
    scored = [
        {**q, "score": _stars_to_score(q.get("stars", 0)), "feedback": "AI scoring unavailable — derived from star rating."}
        for q in qa_pairs
    ]
    raw = sum(s["score"] for s in scored) / len(scored) if scored else 5
    overall = round(raw * 10)
    rec = "Strong Hire" if overall >= 80 else "Hire" if overall >= 65 else "Maybe" if overall >= 45 else "No Hire"
    return {
        "scored_answers": scored,
        "overall_score": overall,
        "recommendation": rec,
        "summary": "AI scoring was unavailable. Score derived from HR star ratings.",
        "strengths": ["Resume matches role requirements", "Candidate completed screening"],
        "concerns": ["AI evaluation failed — manual review recommended"],
    }
