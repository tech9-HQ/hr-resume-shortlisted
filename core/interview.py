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


MANDATORY_TYPES = {"Introduction", "Compensation", "Logistics"}

PRESCREENING_QUESTIONS = [
    {
        "question": "Please introduce yourself and walk us through your professional background.",
        "type": "Introduction",
        "focus_area": "Communication",
    },
    {
        "question": "What is your current role and what are your key day-to-day responsibilities?",
        "type": "Role Experience",
        "focus_area": "Current Role",
    },
    {
        "question": "Walk us through your key achievements and notable projects from your previous roles.",
        "type": "Achievements",
        "focus_area": "Previous Work",
    },
    {
        "question": "Why are you looking to move from your current company? What is driving this change?",
        "type": "Career Motivation",
        "focus_area": "Reason for Change",
    },
    {
        "question": "Tell me about a challenging situation you faced at work and how you handled it.",
        "type": "Problem Solving",
        "focus_area": "Work Challenges",
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
        "type": "Career Goals",
        "focus_area": "Growth & Ambition",
    },
]

# Kept for backward-compat with cached questions from the old type system
_LEGACY_TYPES = {"Introduction", "Background", "Behavioral", "Compensation", "Logistics"}


def _valid_questions(data: object) -> bool:
    """Return True if data is 8 well-formed questions and contains all 3 mandatory types."""
    if not isinstance(data, list) or len(data) != 8:
        return False
    if not all(
        isinstance(q, dict)
        and isinstance(q.get("question"), str) and q["question"].strip()
        and isinstance(q.get("type"), str) and q["type"].strip()
        and isinstance(q.get("focus_area"), str) and q["focus_area"].strip()
        for q in data
    ):
        return False
    present = {q["type"] for q in data}
    return MANDATORY_TYPES.issubset(present)


def generate_interview_questions(
    resume_text: str, jd_text: str, position: str
) -> list[dict]:
    """
    Generate 8 personalised HR pre-screening questions using the candidate's
    resume and the JD. Question category types are chosen dynamically by the AI
    based on the detected role profile (Sales, Pre-Sales, Solutioning, Technical, etc.).
    Falls back to the generic template if AI is unavailable.
    """
    system = (
        "You are an experienced HR recruiter conducting an initial phone pre-screening call — NOT a technical interview.\n\n"
        "STEP 1 — Identify the role profile from the JD and resume. Common profiles include:\n"
        "  Sales, Pre-Sales / Solutions Consultant, Solutioning / Solution Architect,\n"
        "  Technical / Engineering, Product Management, Marketing, Operations,\n"
        "  Finance, HR, Management / Leadership, Customer Success, and others.\n\n"
        "STEP 2 — Generate exactly 8 pre-screening questions personalised to THIS candidate.\n\n"
        "THREE MANDATORY QUESTIONS (must appear exactly once each):\n"
        '  type "Introduction"  — ask the candidate to introduce themselves and walk through their background\n'
        '  type "Compensation"  — ask for current CTC (fixed + variable) AND expected CTC for this role\n'
        '  type "Logistics"     — ask about notice period and possibility of early joining\n\n'
        "FIVE PROFILE-SPECIFIC QUESTIONS — for the remaining 5 questions:\n"
        "  • Invent concise, descriptive type names (2–4 words) that reflect what each question probes.\n"
        "  • Types should be specific to the role profile. Examples by profile:\n"
        "      Sales:           'Quota & Targets', 'Client Acquisition', 'Sales Methodology', 'Pipeline Management', 'Deal Closure'\n"
        "      Pre-Sales:       'Demo Experience', 'Technical Discovery', 'POC & Pilots', 'RFP / Solutioning', 'Customer Objections'\n"
        "      Solutioning:     'Solution Design', 'Client Requirements', 'Architecture Decisions', 'Delivery Experience', 'Stakeholder Management'\n"
        "      Technical:       'Project Delivery', 'Engineering Culture', 'Technical Leadership', 'Cross-team Collaboration', 'Tech Stack Experience'\n"
        "      Product Mgmt:    'Product Ownership', 'Roadmap Prioritization', 'Stakeholder Alignment', 'Metrics & KPIs', 'User Research'\n"
        "      Management:      'Team Leadership', 'P&L Ownership', 'Hiring & Performance', 'Conflict Resolution', 'Strategic Planning'\n"
        "      Customer Success:'Onboarding Experience', 'Escalation Handling', 'Renewal & Expansion', 'Client Health', 'Cross-sell / Upsell'\n"
        "  • Reference specifics from the resume: company names, role titles, numbers, technologies, products.\n"
        "  • Reference requirements from the JD: skills sought, industry, team context.\n"
        "  • Keep all questions at an HR level — no deep technical architecture or code questions.\n\n"
        "OUTPUT FORMAT — respond ONLY with a raw JSON array (no markdown fences, no explanation):\n"
        '[{"question": "...", "type": "short profile-specific type", "focus_area": "3-5 word label"}, ...]\n'
        "Exactly 8 elements. Questions must feel like a natural conversation, not an interrogation."
    )
    user = (
        f"POSITION APPLIED FOR: {position}\n\n"
        f"JOB DESCRIPTION:\n{jd_text[:2500]}\n\n"
        f"CANDIDATE RESUME:\n{resume_text[:4000]}\n\n"
        "Generate 8 personalised pre-screening questions for this specific candidate and role."
    )

    try:
        resp = _get_client().chat.completions.create(
            model=MODEL,
            temperature=0.6,
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
