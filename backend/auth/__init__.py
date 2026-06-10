import os
import time
from pathlib import Path
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv
from fastapi import HTTPException, Request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent

backend_env_path = BASE_DIR / ".env"
root_env_path = ROOT_DIR / ".env"

for env_path in (backend_env_path, root_env_path):
    if env_path.exists():
        load_dotenv(env_path, override=False)


def _get_env(*keys: str) -> str | None:
    for key in keys:
        value = os.getenv(key)
        if value:
            return value
    return None

DISCORD_CLIENT_ID = _get_env("DISCORD_CLIENT_ID", "discord_client_id")
DISCORD_CLIENT_SECRET = _get_env("DISCORD_CLIENT_SECRET", "discord_client_secret")
DISCORD_REDIRECT_URI = _get_env("DISCORD_REDIRECT_URI", "discord_redirect_uri")
SESSION_SECRET = _get_env("SESSION_SECRET", "session_secret")

if not DISCORD_CLIENT_ID or not DISCORD_CLIENT_SECRET or not DISCORD_REDIRECT_URI or not SESSION_SECRET:
    raise RuntimeError(
        "Missing one or more required environment variables: DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET, "
        "DISCORD_REDIRECT_URI, SESSION_SECRET. Set these in Render or a local .env file."
    )

DISCORD_AUTHORIZE_URL = "https://discord.com/api/oauth2/authorize"
DISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token"
DISCORD_USER_URL = "https://discord.com/api/users/@me"
DISCORD_GUILDS_URL = "https://discord.com/api/users/@me/guilds"
SESSION_COOKIE_NAME = "dailybread_session"
STATE_COOKIE_NAME = "dailybread_oauth_state"
SESSION_MAX_AGE = 60 * 60 * 24 * 7
STATE_MAX_AGE = 600

serializer = URLSafeTimedSerializer(SESSION_SECRET, salt="dailybread-session")


def build_avatar_url(user: dict[str, str]) -> str:
    if user.get("avatar"):
        return f"https://cdn.discordapp.com/avatars/{user['id']}/{user['avatar']}.png?size=256"

    discriminator = user.get("discriminator", "0")
    fallback = int(discriminator) % 5 if discriminator.isdigit() else 0
    return f"https://cdn.discordapp.com/embed/avatars/{fallback}.png"


def build_guild_icon_url(guild: dict[str, str]) -> str | None:
    if guild.get("icon"):
        return f"https://cdn.discordapp.com/icons/{guild['id']}/{guild['icon']}.png?size=96"
    return None


def create_session_cookie_value(user: dict, guilds: list[dict]) -> str:
    payload = {
        "user": user,
        "guilds": guilds,
        "created_at": int(time.time()),
    }
    return serializer.dumps(payload)


def parse_session_cookie(cookie_value: str) -> dict | None:
    try:
        return serializer.loads(cookie_value, max_age=SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None


def get_session(request: Request) -> dict | None:
    raw_session = request.cookies.get(SESSION_COOKIE_NAME)
    if not raw_session:
        return None
    return parse_session_cookie(raw_session)


def get_login_redirect_url(state: str) -> str:
    params = {
        "client_id": DISCORD_CLIENT_ID,
        "redirect_uri": DISCORD_REDIRECT_URI,
        "response_type": "code",
        "scope": "identify guilds",
        "state": state,
        "prompt": "consent",
    }
    return f"{DISCORD_AUTHORIZE_URL}?{urlencode(params)}"


def exchange_code_for_token(code: str) -> dict:
    response = requests.post(
        DISCORD_TOKEN_URL,
        data={
            "client_id": DISCORD_CLIENT_ID,
            "client_secret": DISCORD_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": DISCORD_REDIRECT_URI,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15,
    )
    response_data = response.json()
    if response.status_code != 200 or "access_token" not in response_data:
        raise HTTPException(
            status_code=400,
            detail="Unable to complete Discord authorization. Please try again.",
        )
    return response_data


def fetch_discord_user(access_token: str) -> dict:
    response = requests.get(
        DISCORD_USER_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def fetch_discord_guilds(access_token: str) -> list[dict]:
    response = requests.get(
        DISCORD_GUILDS_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()
