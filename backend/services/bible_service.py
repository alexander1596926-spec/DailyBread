import os
from urllib.parse import quote_plus
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv
import requests

from backend.services.supabase_service import get_bible_cache, store_bible_cache

BASE_DIR = Path(__file__).resolve().parent.parent
for env_path in (BASE_DIR / ".env", BASE_DIR.parent / ".env"):
    if env_path.exists():
        load_dotenv(env_path, override=False)

BIBLE_API_KEY = os.getenv("BIBLE_API_KEY") or os.getenv("bible_api_key")
BIBLE_API_URL = os.getenv("BIBLE_API_URL") or "https://bible-api.com"


def _normalize_bible_response(data: Dict[str, Any], reference: str) -> Dict[str, Optional[str]]:
    text = data.get("text")
    if not text:
        verses = data.get("verses")
        if isinstance(verses, list):
            text = "\n".join([str(item.get("text", "")) for item in verses]).strip()

    translation = data.get("translation") or data.get("version") or data.get("version_name")
    actual_reference = data.get("reference") or reference

    if not text:
        raise ValueError("Invalid Bible API response; verse text is missing.")

    return {
        "reference": actual_reference,
        "text": str(text).strip(),
        "translation": str(translation).strip() if translation else None,
    }


def resolve_verse_reference(reference: str) -> Optional[Dict[str, Any]]:
    reference = reference.strip()
    if not reference:
        return None

    cached = get_bible_cache(reference)
    if cached and cached.get("text"):
        return {
            "reference": cached.get("reference", reference),
            "text": cached.get("text"),
            "translation": cached.get("translation"),
        }

    url = f"{BIBLE_API_URL}/{quote_plus(reference)}"
    headers = {}
    if BIBLE_API_KEY:
        headers["X-API-Key"] = BIBLE_API_KEY

    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    data = response.json()
    bible_data = _normalize_bible_response(data, reference)
    store_bible_cache(
        bible_data["reference"],
        bible_data["text"],
        bible_data.get("translation"),
    )
    return bible_data
