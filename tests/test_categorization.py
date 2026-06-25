"""
Unit tests for core/categorization.py
"""

from core.categorization import categorize_resume


def test_sales_default():
    text = "I have 5 years of enterprise sales experience managing accounts and closing deals."
    assert categorize_resume(text) == "Sales"


def test_presales_keyword_presales():
    text = "I work in pre-sales supporting the technical evaluation process."
    assert categorize_resume(text) == "Pre-Sales"


def test_presales_keyword_solution_consultant():
    text = "As a solution consultant I run demos and respond to RFPs."
    assert categorize_resume(text) == "Pre-Sales"


def test_presales_keyword_rfp():
    text = "I manage rfp responses and build proof of concept environments."
    assert categorize_resume(text) == "Pre-Sales"


def test_presales_keyword_demo():
    text = "I conduct technical demos for enterprise clients."
    assert categorize_resume(text) == "Pre-Sales"


def test_presales_keyword_poc():
    text = "I lead POC projects to validate solutions before purchase."
    assert categorize_resume(text) == "Pre-Sales"


def test_presales_keyword_architecture():
    text = "I design cloud architecture and support sales teams."
    assert categorize_resume(text) == "Pre-Sales"


def test_empty_text_defaults_to_sales():
    assert categorize_resume("") == "Sales"


def test_generic_text_defaults_to_sales():
    text = "I am a professional with many years of business experience."
    assert categorize_resume(text) == "Sales"
