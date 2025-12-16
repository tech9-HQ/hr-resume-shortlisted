# ingestion/onedrive_watcher.py

import requests
from ingestion.auth import get_app_token

from core.parsing import (
    extract_text_from_bytes,
    extract_contacts,
    extract_name,
    extract_skills,
    compute_experience_years,
)
from core.categorization import categorize_resume
from core.memory import resume_exists, insert_resume

GRAPH = "https://graph.microsoft.com/v1.0"


def fetch_folder_items(drive_id: str, folder_id: str):
    token = get_app_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp = requests.get(
        f"{GRAPH}/drives/{drive_id}/items/{folder_id}/children",
        headers=headers,
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json().get("value", [])


def download_file(drive_id: str, item_id: str) -> bytes:
    token = get_app_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp = requests.get(
        f"{GRAPH}/drives/{drive_id}/items/{item_id}/content",
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.content


def process_item(item: dict, drive_id: str):
    if "file" not in item:
        return

    item_id = item["id"]

    if resume_exists(item_id):
        return

    content = download_file(drive_id, item_id)
    text = extract_text_from_bytes(item["name"], content)

    if not text or len(text.strip()) < 50:
        return

    emails, phones = extract_contacts(text)
    skills = extract_skills(text)
    category = categorize_resume(text)

    insert_resume(
        resume_id=item_id,
        name=extract_name(text, emails),
        email=emails[0] if emails else "",
        phone=phones[0] if phones else "",
        category=category,
        experience_years=compute_experience_years(text),
        skills=skills,
        raw_text=text,
        drive_id=drive_id,
        item_id=item_id,
    )

    print(f"✅ Ingested: {item['name']} → {category}")


def run_once(drive_id: str, folder_id: str):
    items = fetch_folder_items(drive_id, folder_id)
    for item in items:
        process_item(item, drive_id)
