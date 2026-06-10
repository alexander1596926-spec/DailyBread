import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from supabase import create_client

BASE_DIR = Path(__file__).resolve().parent.parent
for env_path in (BASE_DIR / ".env", BASE_DIR.parent / ".env"):
    if env_path.exists():
        load_dotenv(env_path, override=False)

SUPABASE_URL = os.getenv("SUPABASE_URL") or os.getenv("supabase_url")
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_SERVICE_KEY")
)
SUPABASE_KEY_SOURCE = (
    "SERVICE_ROLE"
    if os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    else "SERVICE_KEY"
    if os.getenv("SUPABASE_SERVICE_KEY")
    else "NONE"
)

print("SUPABASE INIT", {"url": SUPABASE_URL, "key_source": SUPABASE_KEY_SOURCE})

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_SERVICE_KEY) are required for Supabase access. Do not use anon keys for backend sync."
    )

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


class SupabaseError(Exception):
    pass


def _execute(query: Any) -> Any:
    result = query.execute()
    if getattr(result, "error", None):
        raise SupabaseError(str(result.error))
    return getattr(result, "data", None)


def get_user_by_discord_id(discord_id: str) -> Optional[Dict[str, Any]]:
    rows = _execute(
        supabase.table("users").select("*").eq("discord_id", discord_id).limit(1)
    )
    return rows[0] if rows else None


def get_user_id_by_discord_id(discord_id: str) -> Optional[Any]:
    user = get_user_by_discord_id(discord_id)
    return user.get("id") if user else None


def get_guild_by_guild_id(guild_id: str) -> Optional[Dict[str, Any]]:
    rows = _execute(
        supabase.table("guilds").select("*").eq("guild_id", guild_id).limit(1)
    )
    return rows[0] if rows else None


def get_user_guilds(user_id: Any) -> List[Dict[str, Any]]:
    rows = _execute(
        supabase.table("user_guilds").select("*").eq("user_id", user_id)
    )
    guilds: List[Dict[str, Any]] = []
    for row in rows or []:
        guild = get_guild_by_guild_id(str(row.get("guild_id")))
        if not guild:
            continue
        guilds.append(
            {
                "id": guild.get("guild_id"),
                "guild_id": guild.get("guild_id"),
                "name": guild.get("name"),
                "icon": guild.get("icon"),
                "owner": bool(row.get("is_owner")),
                "permissions": int(row.get("permissions", 0)),
                "has_bot": bool(guild.get("has_bot")),
                "owner_id": guild.get("owner_id"),
            }
        )
    return guilds


def get_user_guild(user_id: Any, guild_id: str) -> Optional[Dict[str, Any]]:
    rows = _execute(
        supabase.table("user_guilds")
        .select("*")
        .eq("user_id", user_id)
        .eq("guild_id", guild_id)
        .limit(1)
    )
    return rows[0] if rows else None


def user_has_guild_access(user_id: Any, guild_id: str) -> bool:
    guild = get_user_guild(user_id, guild_id)
    return bool(guild and (guild.get("is_owner") or guild.get("is_admin")))


def upsert_user_by_discord_id(
    discord_id: str,
    username: str = "",
    avatar: str = "",
    global_name: str = "",
) -> Dict[str, Any]:
    record: Dict[str, Any] = {
        "discord_id": discord_id,
        "updated_at": datetime.utcnow().isoformat(),
    }
    if username:
        record["username"] = username
    if avatar:
        record["avatar"] = avatar
    if global_name:
        record["global_name"] = global_name

    print("UPSERT USER", record)
    rows = _execute(
        supabase.table("users").upsert(record, on_conflict="discord_id").select("*")
    )
    print("SUPABASE USER RESPONSE", rows)
    return rows[0]


def create_embed(
    creator_id: Any,
    title: str,
    description: str,
    verse_reference: Optional[str] = None,
    verse_text: Optional[str] = None,
    color: Optional[int] = None,
    footer: Optional[str] = None,
) -> Dict[str, Any]:
    record = {
        "creator_id": creator_id,
        "title": title,
        "description": description,
        "verse_reference": verse_reference,
        "verse_text": verse_text,
        "color": color,
        "footer": footer,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    print("INSERT EMBED", record)
    rows = _execute(supabase.table("embeds").insert(record).select("*"))
    print("SUPABASE EMBED RESPONSE", rows)
    return rows[0]


def get_embed_by_id(embed_id: str) -> Optional[Dict[str, Any]]:
    rows = _execute(supabase.table("embeds").select("*").eq("id", embed_id).limit(1))
    return rows[0] if rows else None


def upsert_guild(
    guild_id: str,
    name: str,
    icon: Optional[str] = None,
    owner_id: Optional[str] = None,
    permissions: int = 0,
    has_bot: bool = False,
) -> Dict[str, Any]:
    record: Dict[str, Any] = {
        "guild_id": guild_id,
        "name": name,
        "permissions": permissions,
        "has_bot": has_bot,
        "updated_at": datetime.utcnow().isoformat(),
    }
    if icon is not None:
        record["icon"] = icon
    if owner_id is not None:
        record["owner_id"] = owner_id

    print("UPSERT GUILD", record)
    rows = _execute(
        supabase.table("guilds").upsert(record, on_conflict="guild_id").select("*")
    )
    print("SUPABASE GUILD RESPONSE", rows)
    return rows[0]


def ensure_user_guild(
    user_id: Any,
    guild_id: str,
    permissions: int,
    is_owner: bool,
    is_admin: bool,
) -> Dict[str, Any]:
    record = {
        "user_id": user_id,
        "guild_id": guild_id,
        "permissions": permissions,
        "is_owner": is_owner,
        "is_admin": is_admin,
        "updated_at": datetime.utcnow().isoformat(),
    }
    print("UPSERT USER_GUILD", record)
    rows = _execute(
        supabase.table("user_guilds").upsert(record, on_conflict="user_id,guild_id").select("*")
    )
    print("SUPABASE USER_GUILD RESPONSE", rows)
    return rows[0]


def upsert_channels(channels: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not channels:
        return []
    print("UPSERT CHANNELS", channels)
    rows = _execute(
        supabase.table("channels").upsert(channels, on_conflict="discord_id").select("*")
    )
    print("SUPABASE CHANNELS RESPONSE", rows)
    return rows or []


def create_webhook_record(webhook: Dict[str, Any]) -> Dict[str, Any]:
    record = {
        "discord_id": str(webhook.get("id") or webhook.get("discord_id")),
        "name": webhook.get("name"),
        "channel_discord_id": str(webhook.get("channel_id") or webhook.get("channel_discord_id")),
        "guild_discord_id": str(webhook.get("guild_id") or webhook.get("guild_discord_id")),
        "token": webhook.get("token"),
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    print("INSERT WEBHOOK", record)
    rows = _execute(supabase.table("webhooks").insert(record).select("*"))
    print("SUPABASE WEBHOOK RESPONSE", rows)
    return rows[0]


def list_embeds_for_user(user_id: Any) -> List[Dict[str, Any]]:
    rows = _execute(
        supabase.table("embeds").select("*").eq("creator_id", user_id).order("created_at", desc=True)
    )
    return rows or []


def get_webhook_by_id(webhook_id: str) -> Optional[Dict[str, Any]]:
    rows = _execute(
        supabase.table("webhooks").select("*").eq("discord_id", webhook_id).limit(1)
    )
    return rows[0] if rows else None


def get_webhooks_for_channel(channel_discord_id: str) -> List[Dict[str, Any]]:
    rows = _execute(
        supabase.table("webhooks").select("*").eq("channel_discord_id", channel_discord_id)
    )
    return rows or []


def get_webhooks_for_guild(guild_discord_id: str) -> List[Dict[str, Any]]:
    rows = _execute(
        supabase.table("webhooks").select("*").eq("guild_discord_id", guild_discord_id)
    )
    return rows or []


def log_embed_send(
    embed_id: Any,
    webhook_discord_id: Any,
    guild_discord_id: Any,
    channel_discord_id: Any,
    success: bool,
    status_code: Optional[int] = None,
    response_text: Optional[str] = None,
    error: Optional[str] = None,
) -> Dict[str, Any]:
    record = {
        "embed_id": embed_id,
        "webhook_discord_id": webhook_discord_id,
        "guild_discord_id": guild_discord_id,
        "channel_discord_id": channel_discord_id,
        "success": success,
        "status_code": status_code,
        "response_text": response_text,
        "error": error,
        "created_at": datetime.utcnow().isoformat(),
    }
    rows = _execute(supabase.table("embed_sends").insert(record).select("*"))
    return rows[0]


def get_bible_cache(reference: str) -> Optional[Dict[str, Any]]:
    rows = _execute(
        supabase.table("bible_cache").select("*").eq("reference", reference).limit(1)
    )
    return rows[0] if rows else None


def store_bible_cache(reference: str, text: str, translation: Optional[str] = None) -> Dict[str, Any]:
    record = {
        "reference": reference,
        "text": text,
        "translation": translation,
        "updated_at": datetime.utcnow().isoformat(),
    }
    print("UPSERT BIBLE_CACHE", record)
    rows = _execute(
        supabase.table("bible_cache").upsert(record, on_conflict="reference,translation").select("*")
    )
    print("SUPABASE BIBLE_CACHE RESPONSE", rows)
    return rows[0]


def delete_webhook(webhook_id: Any) -> None:
    _execute(supabase.table("webhooks").delete().eq("discord_id", webhook_id))
