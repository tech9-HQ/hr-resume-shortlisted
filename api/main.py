# api/main.py
from __future__ import annotations

from io import BytesIO
from typing import List, Dict, Any

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

import pandas as pd

from core.parsing import (
    extract_text_from_bytes,
    extract_contacts,
    extract_name,
    extract_skills,
    compute_experience_years,
    extract_education,
    extract_position_from_jd,
)
from core.scoring import score_resume_with_llm
from core.storage import (
    create_duckdb_conn,
    init_table,
    insert_row,
    append_to_master_excel,
)


app = FastAPI(
    title="Resume Parser API",
    description="Parse and score resumes against a JD using OpenAI gpt-4.1-mini.",
    version="1.0.0",
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


def build_row_for_resume(
    file_name: str, text: str, jd_text: str, position_title: str
) -> Dict[str, Any]:
    """
    Core logic for parsing + scoring a single resume.
    Reuses all your previous heuristics + LLM scoring.
    """
    emails, phones = extract_contacts(text)
    email = emails[0] if emails else ""
    phone = phones[0] if phones else ""
    name = extract_name(text, emails)
    skills = extract_skills(text)
    exp_years = compute_experience_years(text)
    highest_edu = extract_education(text)

    llm_result = score_resume_with_llm(text, jd_text, position_title)

    row = {
        "Name": name,
        "Gender": None,
        "phone": phone,
        "email": email,
        "Experience": exp_years,
        "Summary": llm_result.get("ai_summary", ""),
        "Strength": llm_result.get("strengths", []),
        "Weakness": llm_result.get("weaknesses", []),
        "Best Fit Position": llm_result.get("best_fit", "No"),
        "Skill Set": skills,
        "Overall Impression and Recommendation by AI": {
            "ai_summary": llm_result.get("ai_summary", ""),
            "ai_fit_score": llm_result.get("ai_fit_score", 0),
            "best_fit": llm_result.get("best_fit", "No"),
        },
        "Position": position_title,
        "highest_education": highest_edu,
        "raw_file_name": file_name,
        "raw_text": text,
    }
    return row


def build_hr_dataframe(rows: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Convert parsed rows into HR-friendly DataFrame format
    (same as you used earlier for Excel).
    """
    df_hr = pd.DataFrame(rows)

    df_hr = df_hr.rename(
        columns={
            "Name": "Name",
            "Gender": "Gender",
            "phone": "Phone",
            "email": "Email",
            "Experience": "Experience (yrs)",
            "Summary": "Summary",
            "Strength": "Strengths",
            "Weakness": "Weaknesses",
            "Best Fit Position": "Best Fit (Yes/No)",
            "Skill Set": "Skill Set",
            "Overall Impression and Recommendation by AI": "Overall Impression (AI)",
            "Position": "Position Applied",
            "highest_education": "Highest Education",
            "raw_file_name": "raw_file_name",
        }
    )

    # list → string
    if "Strengths" in df_hr.columns:
        df_hr["Strengths"] = df_hr["Strengths"].apply(
            lambda v: "; ".join(v) if isinstance(v, list) else v
        )
    if "Weaknesses" in df_hr.columns:
        df_hr["Weaknesses"] = df_hr["Weaknesses"].apply(
            lambda v: "; ".join(v) if isinstance(v, list) else v
        )
    if "Skill Set" in df_hr.columns:
        df_hr["Skill Set"] = df_hr["Skill Set"].apply(
            lambda v: ", ".join(v) if isinstance(v, list) else v
        )

    # overall impression + score
    def oi_to_text(o):
        if isinstance(o, dict):
            return o.get("ai_summary", "")
        return str(o) if o is not None else ""

    def oi_score(o):
        if isinstance(o, dict):
            return o.get("ai_fit_score", None)
        return None

    if "Overall Impression (AI)" in df_hr.columns:
        df_hr["Overall Impression (AI)"] = df_hr["Overall Impression (AI)"].apply(
            oi_to_text
        )

    df_hr["AI Fit Score"] = [
        oi_score(r.get("Overall Impression and Recommendation by AI", {})) for r in rows
    ]

    cols = [
        "Name",
        "Gender",
        "Phone",
        "Email",
        "Experience (yrs)",
        "Summary",
        "Strengths",
        "Weaknesses",
        "Best Fit (Yes/No)",
        "Skill Set",
        "Overall Impression (AI)",
        "AI Fit Score",
        "Position Applied",
        "Highest Education",
        "raw_file_name",
    ]
    cols = [c for c in cols if c in df_hr.columns]
    df_hr = df_hr[cols]

    return df_hr


@app.post("/process-resumes")
async def process_resumes(
    jd_file: UploadFile = File(...),
    resumes: List[UploadFile] = File(...),
):
    """
    Upload:
      - one JD file (pdf/docx/txt)
      - multiple resume files (pdf/docx/txt)

    Returns:
      - position_title
      - processed_count
      - excel_message (status of master Excel write)
      - rows: parsed+scored data (without raw_text)
    """
    # --- JD TEXT ---
    jd_bytes = await jd_file.read()
    jd_text = extract_text_from_bytes(jd_file.filename, jd_bytes)
    if not jd_text or len(jd_text.strip()) < 20:
        raise HTTPException(status_code=400, detail="Could not extract text from JD.")

    position_title = extract_position_from_jd(jd_text) or "default"

    # --- RESUMES ---
    rows: List[Dict[str, Any]] = []
    for up in resumes:
        file_bytes = await up.read()
        text = extract_text_from_bytes(up.filename, file_bytes)
        if not text or len(text.strip()) < 20:
            # skip bad file but do not crash
            continue
        row = build_row_for_resume(up.filename, text, jd_text, position_title)
        rows.append(row)

    if not rows:
        raise HTTPException(status_code=400, detail="No valid resumes processed.")

    # --- Persist to DuckDB + Excel (same logic as before) ---
    conn = create_duckdb_conn()
    init_table(conn)
    for r in rows:
        insert_row(conn, r)

    df_hr = build_hr_dataframe(rows)
    ok, msg = append_to_master_excel(df_hr, position_title)
    excel_message = msg if ok else f"Failed to update Excel: {msg}"

    # --- Prepare lightweight JSON response (no raw_text) ---
    json_rows: List[Dict[str, Any]] = []
    for r in rows:
        r_copy = dict(r)
        r_copy.pop("raw_text", None)  # remove heavy field
        json_rows.append(r_copy)

    return JSONResponse(
        {
            "position_title": position_title,
            "processed_count": len(rows),
            "excel_message": excel_message,
            "rows": json_rows,
        }
    )
