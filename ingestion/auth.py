import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

TOKEN_URL = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
SCOPE = "https://graph.microsoft.com/.default"

_cached_token = None
_token_expiry = 0


def get_app_token() -> str:
    global _cached_token, _token_expiry

    # Reuse token if still valid (55 mins)
    if _cached_token and time.time() < _token_expiry:
        return _cached_token

    resp = requests.post(
        TOKEN_URL,
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "client_credentials",
            "scope": SCOPE,
        },
        timeout=15,
    )

    resp.raise_for_status()
    data = resp.json()

    _cached_token = data["access_token"]
    _token_expiry = time.time() + int(data.get("expires_in", 3600)) - 300

    return _cached_token
