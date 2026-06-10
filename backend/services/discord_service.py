import os
from typing import Any, Dict, List, Optional

import requests

DISCORD_API_BASE = "https://discord.com/api/v10"
BOT_TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("discord_token") or os.getenv("DISCORD_BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("DISCORD_TOKEN or DISCORD_BOT_TOKEN is required for Discord REST operations.")

_cached_bot_user: Optional[Dict[str, Any]] = None


def _headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bot {BOT_TOKEN}",
        "Content-Type": "application/json",
    }


def _request(method: str, path: str, json: Any = None) -> Dict[str, Any]:
    url = f"{DISCORD_API_BASE}{path}"
    response = requests.request(method, url, json=json, headers=_headers(), timeout=10)
    try:
        body = response.json()
    except ValueError:
        body = {"status_text": response.text}
    if response.status_code >= 400:
        raise RuntimeError(f"Discord API {response.status_code}: {body}")
    return body


def get_bot_user() -> Dict[str, Any]:
    global _cached_bot_user
    if _cached_bot_user is None:
        _cached_bot_user = _request("GET", "/users/@me")
    return _cached_bot_user


def is_bot_in_guild(guild_id: str) -> bool:
    bot_user = get_bot_user()
    bot_id = bot_user.get("id")
    if not bot_id:
        return False
    try:
        _request("GET", f"/guilds/{guild_id}/members/{bot_id}")
        return True
    except RuntimeError:
        return False


def list_guild_channels(guild_id: str) -> List[Dict[str, Any]]:
    return _request("GET", f"/guilds/{guild_id}/channels")


def create_webhook(channel_id: str, name: str = "DailyBread") -> Dict[str, Any]:
    payload = {"name": name}
    return _request("POST", f"/channels/{channel_id}/webhooks", json=payload)


def send_webhook(webhook_id: str, webhook_token: str, embed_payload: Dict[str, Any]) -> Dict[str, Any]:
    url = f"https://discord.com/api/v10/webhooks/{webhook_id}/{webhook_token}"
    response = requests.post(url, json=embed_payload, timeout=10)
    try:
        body = response.json()
    except ValueError:
        body = {"status_text": response.text}
    if response.status_code >= 400:
        raise RuntimeError(f"Discord Webhook {response.status_code}: {body}")
    return body
