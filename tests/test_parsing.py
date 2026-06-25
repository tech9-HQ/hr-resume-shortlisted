"""
Unit tests for core/parsing.py — no DB, no network, no AI.
"""

from core.parsing import (
    extract_contacts,
    extract_name,
    extract_skills,
    compute_experience_years,
    extract_education,
    extract_position_from_jd,
    extract_text_from_bytes,
)

RESUME = """
John Smith
john.smith@example.com
+91 9876543210

Senior Sales Manager with 6 years experience.

Work History:
Jan 2019 - Present: Senior Sales Manager at CloudCorp
Jan 2017 - Dec 2018: Account Executive at TechSales

Skills: salesforce, crm, enterprise sales, aws, hubspot, pipeline management

Education: MBA from Mumbai University
"""


# ---------------------------------------------------------------------------
# extract_contacts
# ---------------------------------------------------------------------------

def test_extract_contacts_email():
    emails, _ = extract_contacts(RESUME)
    assert "john.smith@example.com" in emails


def test_extract_contacts_phone():
    _, phones = extract_contacts(RESUME)
    assert len(phones) > 0


def test_extract_contacts_deduplicates_emails():
    text = "a@b.com a@b.com c@d.com"
    emails, _ = extract_contacts(text)
    assert emails.count("a@b.com") == 1


def test_extract_contacts_empty_text():
    emails, phones = extract_contacts("")
    assert emails == []
    assert phones == []


# ---------------------------------------------------------------------------
# extract_name
# ---------------------------------------------------------------------------

def test_extract_name_picks_first_proper_name():
    emails, _ = extract_contacts(RESUME)
    name = extract_name(RESUME, emails)
    assert "John" in name or "Smith" in name


def test_extract_name_falls_back_to_email():
    text = "john.doe@example.com\nSome random content without a clear name."
    emails, _ = extract_contacts(text)
    name = extract_name(text, emails)
    assert name != ""


def test_extract_name_empty_text():
    name = extract_name("", [])
    assert name == ""


def test_extract_name_skips_all_caps_section_headers():
    # "TECHNICAL SKILLS" starts with "technical" (BAD_STARTS) — must be rejected
    text = "TECHNICAL SKILLS\nJohn Smith\njohn@example.com"
    emails, _ = extract_contacts(text)
    name = extract_name(text, emails)
    assert name != "TECHNICAL SKILLS"
    assert "John" in name or "Smith" in name


def test_extract_name_skips_section_header_keyword():
    text = "Technical Skills: Python, AWS\nJane Doe\njane@example.com"
    emails, _ = extract_contacts(text)
    name = extract_name(text, emails)
    assert "Technical Skills" not in name


def test_extract_name_skips_work_experience_header():
    text = "WORK EXPERIENCE\nRaj Kumar\nraj@example.com"
    emails, _ = extract_contacts(text)
    name = extract_name(text, emails)
    assert name != "WORK EXPERIENCE"


def test_extract_name_handles_all_caps_indian_style():
    # Many Indian résumés write the name in all-caps — should be title-cased
    text = "PRIYA SHARMA\npriya.sharma@gmail.com\n+91 9876543210"
    emails, _ = extract_contacts(text)
    name = extract_name(text, emails)
    assert name == "Priya Sharma"


def test_extract_name_explicit_name_label():
    # "Name: ..." pattern anywhere in the text
    text = "TECHNICAL SKILLS\nPython, AWS\nName: Rahul Verma\nrahul@example.com"
    emails, _ = extract_contacts(text)
    name = extract_name(text, emails)
    assert "Rahul" in name or "Verma" in name


def test_extract_name_does_not_pick_long_all_caps_line():
    # 4-word all-caps lines should be rejected (too long for a name)
    text = "SENIOR SOFTWARE ENGINEER RESUME\nAkash Mehta\nakash@example.com"
    emails, _ = extract_contacts(text)
    name = extract_name(text, emails)
    assert name != "Senior Software Engineer Resume"
    assert "Akash" in name or "Mehta" in name


# ---------------------------------------------------------------------------
# extract_skills
# ---------------------------------------------------------------------------

def test_extract_skills_detects_salesforce():
    skills = extract_skills(RESUME)
    assert "salesforce" in skills


def test_extract_skills_detects_aws():
    skills = extract_skills(RESUME)
    assert "aws" in skills


def test_extract_skills_detects_crm():
    skills = extract_skills(RESUME)
    assert "crm" in skills


def test_extract_skills_returns_sorted_unique():
    skills = extract_skills(RESUME)
    assert skills == sorted(set(skills))


def test_extract_skills_empty_text():
    assert extract_skills("") == []


# ---------------------------------------------------------------------------
# compute_experience_years
# ---------------------------------------------------------------------------

def test_compute_experience_years_positive():
    exp = compute_experience_years(RESUME)
    assert exp > 0


def test_compute_experience_years_fallback_pattern():
    text = "I have 7 years of sales experience."
    exp = compute_experience_years(text)
    assert exp == 7.0


def test_compute_experience_years_empty():
    exp = compute_experience_years("")
    assert exp == 0.0


# ---------------------------------------------------------------------------
# extract_education
# ---------------------------------------------------------------------------

def test_extract_education_mba():
    assert extract_education(RESUME) == "MBA"


def test_extract_education_btech():
    text = "Education: B.Tech in Computer Science"
    assert extract_education(text) == "B.Tech"


def test_extract_education_unknown():
    text = "Worked hard and learned on the job."
    assert extract_education(text) == ""


# ---------------------------------------------------------------------------
# extract_position_from_jd
# ---------------------------------------------------------------------------

def test_extract_position_explicit_label():
    jd = "Job Title: Senior Sales Manager\nWe are looking for..."
    assert "Senior Sales Manager" in extract_position_from_jd(jd)


def test_extract_position_falls_back_to_first_line():
    jd = "Cloud Solutions Architect\nResponsible for designing..."
    assert "Cloud Solutions Architect" in extract_position_from_jd(jd)


def test_extract_position_empty_jd():
    assert extract_position_from_jd("") == ""


# ---------------------------------------------------------------------------
# extract_text_from_bytes
# ---------------------------------------------------------------------------

def test_extract_text_from_txt_bytes():
    content = b"Hello world, this is a resume."
    text = extract_text_from_bytes("resume.txt", content)
    assert "Hello world" in text


def test_extract_text_unknown_extension_treated_as_text():
    content = b"Plain text content"
    text = extract_text_from_bytes("file.xyz", content)
    assert "Plain text content" in text
