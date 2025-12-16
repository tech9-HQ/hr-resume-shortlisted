# core/scoring.py
from __future__ import annotations

import json
from datetime import datetime
from typing import Dict, Any, List

from dotenv import load_dotenv
from openai import OpenAI

from .parsing import extract_skills, TECH_DICTIONARY

load_dotenv()

AUDIT_LOG = "audit_parsed.jsonl"
MODEL_NAME = "gpt-4.1-mini"

_client: OpenAI | None = None


def _client_instance() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


def _log_audit(entry: Dict[str, Any]) -> None:
    try:
        with open(AUDIT_LOG, "a", encoding="utf-8") as f:
            entry["ts"] = datetime.utcnow().isoformat()
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _heuristic_score(resume_text: str, jd_text: str) -> Dict[str, Any]:
    """Fallback if OpenAI fails."""
    skills = extract_skills(resume_text, TECH_DICTIONARY)
    jd_skills = extract_skills(jd_text, TECH_DICTIONARY)
    overlap = [s for s in skills if s in jd_skills]

    if jd_skills:
        score = int(round((len(overlap) / max(1, len(jd_skills))) * 100))
    else:
        score = min(100, len(skills) * 10)

    ai_summary = (
        f"{len(skills)} technical skills identified; "
        f"key: {', '.join(skills[:6])}."
    )

    strengths = [f"Experienced in {x}" for x in (overlap[:3] or skills[:3])]
    gaps_base = list(set(jd_skills) - set(skills))[:3]
    weaknesses = [f"Missing or weak in {x}" for x in gaps_base]

    best_fit = "Yes" if score >= 70 else "No"

    return {
        "ai_summary": ai_summary,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "ai_fit_score": score,
        "best_fit": best_fit,
    }


def score_resume_with_llm(
    resume_text: str,
    jd_text: str,
    position: str,
) -> Dict[str, Any]:
    """
    Use OpenAI gpt-4.1-mini to score a resume against a JD.
    Returns dict with keys:
      ai_summary, strengths, weaknesses, ai_fit_score, best_fit
    """
    prompt_system = (
        "You are an expert technical recruiter.\n"
        "You must respond ONLY with a valid JSON object.\n"
        "Keys:\n"
        '  "ai_summary": string (2-3 sentence professional summary of candidate suitability),\n'
        '  "strengths": array of short strings,\n'
        '  "weaknesses": array of short strings,\n'
        '  "ai_fit_score": integer 0-100,\n'
        '  "best_fit": string "Yes" or "No".\n'
    )

    prompt_user = (
        f"JOB ROLE/TITLE: {position}\n\n"
        f"JOB DESCRIPTION:\n{jd_text[:4000]}\n\n"
        f"RESUME:\n{resume_text[:8000]}\n"
    )

    try:
        client = _client_instance()
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": prompt_system},
                {"role": "user", "content": prompt_user},
            ],
        )
        content = resp.choices[0].message.content or "{}"
        _log_audit(
            {
                "model": MODEL_NAME,
                "prompt_system": prompt_system,
                "prompt_user": prompt_user[:1000],
                "response": content[:4000],
            }
        )

        data = json.loads(content)
        out = {
            "ai_summary": str(data.get("ai_summary", "")).strip(),
            "strengths": (
                data.get("strengths")
                if isinstance(data.get("strengths"), list)
                else (
                    [data.get("strengths")]
                    if data.get("strengths") is not None
                    else []
                )
            ),
            "weaknesses": (
                data.get("weaknesses")
                if isinstance(data.get("weaknesses"), list)
                else (
                    [data.get("weaknesses")]
                    if data.get("weaknesses") is not None
                    else []
                )
            ),
            "ai_fit_score": int(data.get("ai_fit_score") or 0),
            "best_fit": "Yes"
            if str(data.get("best_fit", "")).strip().lower().startswith("y")
            or int(data.get("ai_fit_score") or 0) >= 70
            else "No",
        }
        return out
    except Exception as e:
        _log_audit({"error": str(e), "fallback": True})
        return _heuristic_score(resume_text, jd_text)
