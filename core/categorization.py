# core/categorization.py

PRESALES_KEYWORDS = [
    "pre-sales",
    "presales",
    "solution consultant",
    "solution architect",
    "technical sales",
    "demo",
    "rfp",
    "poc",
    "bid",
    "tender",
    "architecture",
]


def categorize_resume(text: str) -> str:
    """
    Categorize resume into:
      - Sales
      - Pre-Sales

    Default: Sales
    """
    t = (text or "").lower()

    if any(k in t for k in PRESALES_KEYWORDS):
        return "Pre-Sales"

    return "Sales"
