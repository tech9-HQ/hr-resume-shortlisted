# core/parsing.py
from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path
from datetime import datetime
from typing import List, Tuple

from docx import Document
from PyPDF2 import PdfReader
import dateparser
import phonenumbers

# ============================================================
# CONFIG: Cloud + Sales skill dictionary (no noisy dev skills)
# ============================================================

TECH_DICTIONARY: List[str] = [
    # Cloud Platforms
    "aws", "amazon web services",
    "azure", "microsoft azure",
    "gcp", "google cloud",

    # Cloud & infra concepts
    "cloud consulting", "cloud sales",
    "infrastructure as a service", "iaas",
    "platform as a service", "paas",
    "software as a service", "saas",
    "virtual machines", "vm", "virtualization",
    "backup", "disaster recovery",
    "cloud security", "cybersecurity",

    # Sales & GTM
    "enterprise sales", "b2b sales",
    "inside sales", "channel sales",
    "account management", "key account management",
    "territory management",
    "business development",
    "demand generation", "lead generation",
    "pipeline management",
    "solution selling", "consultative selling",
    "presales",

    # Tools
    "linkedin sales navigator", "lusha",
    "salesforce", "hubspot", "crm",
]

EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_RE = re.compile(r"(\+?\d[\d\-\s\(\)]{7,}\d)")

DATE_RANGE_RE = re.compile(
    r"(?P<from>(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|\w{3,9}|\d{4})[\.]?\s*\d{4}|\d{4})"
    r"\s*(?:-|to|—|–)\s*"
    r"(?P<to>(?:Present|present|Current|Now|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|\w{3,9}|\d{4})[\.]?\s*\d{4}|\d{4}))",
    re.I,
)

EDU_PRIORITY = [
    "phd", "doctorate", "mba", "m.tech", "mtech", "msc", "master", "masters",
    "b.tech", "btech", "b.e", "be", "bsc", "bachelor", "diploma",
]

EDU_CANON = {
    "phd": "PhD",
    "mba": "MBA",
    "m.tech": "M.Tech",
    "msc": "M.Sc",
    "b.tech": "B.Tech",
    "b.e": "B.E.",
    "bsc": "B.Sc",
    "diploma": "Diploma",
}

# ============================================================
# FILE → TEXT
# ============================================================

def extract_text_from_pdf_bytes(b: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(b))
        return "\n".join((p.extract_text() or "") for p in reader.pages)
    except Exception:
        return ""


def extract_text_from_docx_bytes(b: bytes) -> str:
    try:
        doc = Document(BytesIO(b))
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception:
        return ""


def extract_text_from_bytes(filename: str, b: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        return extract_text_from_pdf_bytes(b)
    if suffix in (".docx", ".doc"):
        return extract_text_from_docx_bytes(b)
    try:
        return b.decode("utf-8", errors="ignore")
    except Exception:
        return ""

# ============================================================
# CONTACTS
# ============================================================

def extract_contacts(text: str) -> Tuple[List[str], List[str]]:
    emails = EMAIL_RE.findall(text or "")
    phones_raw = PHONE_RE.findall(text or "")

    phones: List[str] = []
    for p in phones_raw:
        digits = re.sub(r"\D", "", p)
        if not digits:
            continue
        try:
            num = phonenumbers.parse(p, None)
            phones.append(
                phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164)
            )
        except Exception:
            phones.append(digits)

    def dedupe(seq: List[str]) -> List[str]:
        seen = set()
        out: List[str] = []
        for x in seq:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out

    return dedupe(emails), dedupe(phones)

# ============================================================
# NAME (ultra-strict, avoids "Duration ...", "Role Sr ...", etc.)
# ============================================================

def extract_name(text: str, emails: List[str]) -> str:
    """
    Ultra-strict name extractor:
    - Look only at the first ~12 non-empty lines
    - Skip lines that look like:
      * addresses, roles, durations, profiles, resumes, etc.
      * contain email/phone/contact symbols
    - Accept only lines that:
      * have 1–4 words
      * all words start with uppercase (proper name style)
    - If nothing passes → fallback to email username (if available)
    """
    BAD_STARTS = (
        "of", "duration", "role", "address", "profile", "curriculum",
        "objective", "summary", "experience", "responsibilities", "company",
        "skills", "career", "professional", "work", "employment"
    )

    BAD_KEYWORDS = (
        "delhi", "nagar", "india", "road", "sector", "floor",
        "street", "lane", "repute", "till date", "till", "date"
    )

    lines = [l.strip() for l in (text or "").splitlines() if l.strip()]
    candidates: List[str] = []

    for line in lines[:12]:
        low = line.lower()

        # Skip obvious non-name lines
        if any(low.startswith(b) for b in BAD_STARTS):
            continue
        if any(k in low for k in BAD_KEYWORDS):
            continue
        if any(x in low for x in ["@", "email", "e-mail", "phone", "mobile", "contact"]):
            continue

        # Remove non-letter characters
        cleaned = re.sub(r"[^A-Za-z\s\-']", " ", line).strip()
        cleaned = re.sub(r"\s{2,}", " ", cleaned)
        if not cleaned:
            continue

        words = cleaned.split()

        # Only accept 1–4 word lines
        if not (1 <= len(words) <= 4):
            continue

        # All words should start with uppercase (likely proper name)
        if not all(w[0].isupper() for w in words if w):
            continue

        candidates.append(cleaned)

    if candidates:
        return candidates[0]

    # Fallback: derive from email
    if emails:
        local = emails[0].split("@")[0]
        local = re.sub(r"[._\d]+", " ", local).strip()
        return local.title()

    # If no decent candidate and no email → return empty, not garbage
    return ""

# ============================================================
# SKILLS (clean, exact match — no fuzzy noise)
# ============================================================

def extract_skills(text: str, skills_master: List[str] | None = None) -> List[str]:
    """
    Extract relevant cloud-sales skills using exact phrase matching only.
    This avoids noisy detections like 'ai', 'react', 'ansible', etc.
    """
    if skills_master is None:
        skills_master = TECH_DICTIONARY

    t = (text or "").lower()
    found: set[str] = set()

    for s in skills_master:
        if s.lower() in t:
            found.add(s)

    # Normalize platform variants
    normalized: List[str] = []
    for s in found:
        if s == "amazon web services":
            normalized.append("aws")
        elif s == "microsoft azure":
            normalized.append("azure")
        elif s == "google cloud":
            normalized.append("gcp")
        else:
            normalized.append(s)

    return sorted(set(normalized))

# ============================================================
# EXPERIENCE & EDUCATION
# ============================================================

def compute_experience_years(text: str) -> float:
    total_months = 0

    for m in DATE_RANGE_RE.finditer(text or ""):
        seg = m.group(0).lower()
        if "intern" in seg:
            continue

        try:
            start = dateparser.parse(m.group("from"))
            to_raw = m.group("to")
            end = (
                datetime.now()
                if re.search(r"present|current|now", to_raw, re.I)
                else dateparser.parse(to_raw)
            )
            if start and end and end > start:
                total_months += (end.year - start.year) * 12 + (end.month - start.month)
        except Exception:
            continue

    # fallback: "X years" pattern
    if total_months == 0:
        ym = re.search(r"(\d+)\s+years?", text or "", re.I)
        if ym:
            total_months = int(ym.group(1)) * 12

    return round(total_months / 12.0, 1)


def extract_education(text: str) -> str:
    tl = (text or "").lower()
    for k in EDU_PRIORITY:
        if k in tl:
            return EDU_CANON.get(k, k.title())
    return ""

# ============================================================
# JD PARSING
# ============================================================

def extract_position_from_jd(jd_text: str) -> str:
    if not jd_text:
        return ""
    lines = [l.strip() for l in jd_text.splitlines() if l.strip()]
    if not lines:
        return ""
    top = lines[0]
    m = re.search(r"(?i)(job\s*title[:\-\s]+)(.+)", top)
    if m:
        return m.group(2).strip()
    return top[:120]
