import os
import logging
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
    or os.getenv("supabase_service_key")
)
SUPABASE_KEY_SOURCE = (
    "SERVICE_ROLE"
    if SUPABASE_KEY
    else "NONE"
)

LOGGER = logging.getLogger(__name__)
LOGGER.info("Supabase init url=%s key_source=%s", SUPABASE_URL, SUPABASE_KEY_SOURCE)

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_SERVICE_KEY) are required for Supabase access. Do not use anon keys for backend sync."
    )

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# Supabase Error
class SupabaseError(Exception):
    pass


def _execute(query: Any) -> Any:
    result = query.execute()
    if getattr(result, "error", None):
        raise SupabaseError(str(result.error))
    return getattr(result, "data", None)



# Retrieves a user by their Discord ID. Returns the user data if found, or None otherwise.
def get_user_by_discord_id(discord_id: str) -> Optional[Dict[str, Any]]:
    rows = _execute(
        supabase.table("users").select("*").eq("discord_id", discord_id).limit(1)
    )
    return rows[0] if rows else None


# Retrieves a user ID by their Discord ID. Returns the user ID if found, or None otherwise.
def get_user_id_by_discord_id(discord_id: str) -> Optional[Any]:
    user = get_user_by_discord_id(discord_id)
    return user.get("id") if user else None


# Retrieves a guild by its Discord guild ID. Returns the guild data if found, or None otherwise.
def get_guild_by_guild_id(guild_id: str) -> Optional[Dict[str, Any]]:
    rows = _execute(
        supabase.table("guilds").select("*").eq("guild_id", guild_id).limit(1)
    )
    return rows[0] if rows else None


def get_guilds_by_guild_ids(guild_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    if not guild_ids:
        return {}

    rows = _execute(supabase.table("guilds").select("*").in_("guild_id", guild_ids))
    return {str(row.get("guild_id")): row for row in rows or []}


# Lists all guilds that the specified user is a member of, along with their permissions and whether they are the owner. Returns a list of guild data dictionaries.
def get_user_guilds(user_id: Any) -> List[Dict[str, Any]]:
    rows = _execute(
        supabase.table("user_guilds").select("*").eq("user_id", user_id)
    )
    guild_map = get_guilds_by_guild_ids([str(row.get("guild_id")) for row in rows or []])
    guilds: List[Dict[str, Any]] = []
    for row in rows or []:
        guild = guild_map.get(str(row.get("guild_id")))
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
                "is_owner": bool(row.get("is_owner")),
                "is_admin": bool(row.get("is_admin")),
                "owner_id": guild.get("owner_id"),
            }
        )
    return guilds


# Retrieves a user's membership information for a specific guild, including their permissions and whether they are the owner. Returns the membership data if found, or None otherwise.
def get_user_guild(user_id: Any, guild_id: str) -> Optional[Dict[str, Any]]:
    rows = _execute(
        supabase.table("user_guilds")
        .select("*")
        .eq("user_id", user_id)
        .eq("guild_id", guild_id)
        .limit(1)
    )
    return rows[0] if rows else None


# Checks if the user has access to the specified guild by verifying their membership and permissions. Returns True if the user is the owner or has admin permissions, False otherwise.
def user_has_guild_access(user_id: Any, guild_id: str) -> bool:
    guild = get_user_guild(user_id, guild_id)
    return bool(guild and (guild.get("is_owner") or guild.get("is_admin")))


# Upserts a user by their Discord ID. Returns the upserted user data. If the user already exists, their information will be updated with the provided data. If the user does not exist, a new record will be created.
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

    rows = _execute(
        supabase.table("users").upsert(record, on_conflict="discord_id").select("*")
    )
    return rows[0]


# Creates a new embed record and returns the created embed data.
def create_embed(
    creator_id: Any,
    title: str,
    description: str,
    verse_reference: Optional[str] = None,
    verse_text: Optional[str] = None,
    color: Optional[int] = None,
    footer: Optional[str] = None,
    message_content: Optional[str] = None,
    image_url: Optional[str] = None,
) -> Dict[str, Any]:
    record = {
        "creator_id": creator_id,
        "message_content": message_content,
        "title": title,
        "description": description,
        "verse_reference": verse_reference,
        "verse_text": verse_text,
        "color": color,
        "footer": footer,
        "image_url": image_url,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    try:
        rows = _execute(supabase.table("embeds").insert(record).select("*"))
    except Exception:
        legacy_record = {k: v for k, v in record.items() if k not in {"message_content", "image_url"}}
        rows = _execute(supabase.table("embeds").insert(legacy_record).select("*"))
    return rows[0]


# Retrieves an embed by its ID. Returns the embed data if found, or None otherwise.
def get_embed_by_id(embed_id: str) -> Optional[Dict[str, Any]]:
    rows = _execute(supabase.table("embeds").select("*").eq("id", embed_id).limit(1))
    return rows[0] if rows else None



# Upserts a guild by its ID. Returns the upserted guild data. If the guild already exists, its information will be updated with the provided data. If the guild does not exist, a new record will be created.
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

    rows = _execute(
        supabase.table("guilds").upsert(record, on_conflict="guild_id").select("*")
    )
    return rows[0]


# Upserts a user's membership in a guild with their permissions and ownership status. 
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
    rows = _execute(
        supabase.table("user_guilds").upsert(record, on_conflict="user_id,guild_id").select("*")
    )
    return rows[0]

 
# Upserts a list of channels. Each channel should have a unique discord_id. Returns the list of upserted channel data.
def upsert_channels(channels: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not channels:
        return []
    rows = _execute(
        supabase.table("channels").upsert(channels, on_conflict="discord_id").select("*")
    )
    return rows or []


def get_channel_by_discord_id(channel_discord_id: str) -> Optional[Dict[str, Any]]:
    rows = _execute(
        supabase.table("channels").select("*").eq("discord_id", channel_discord_id).limit(1)
    )
    return rows[0] if rows else None


# Creates a new webhook record and returns the created webhook data.
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
    rows = _execute(supabase.table("webhooks").insert(record).select("*"))
    return rows[0]


# Lists all embeds created by the specified user, identified by their Discord ID. Returns a list of embed data dictionaries.
def list_embeds_for_user(user_id: Any) -> List[Dict[str, Any]]:
    rows = _execute(
        supabase.table("embeds").select("*").eq("creator_id", user_id).order("created_at", desc=True)
    )
    return rows or []


# Retrieves a webhook record by its Discord ID. Returns the webhook data if found, or None if not found.
def get_webhook_by_id(webhook_id: str) -> Optional[Dict[str, Any]]:
    rows = _execute(
        supabase.table("webhooks").select("*").eq("discord_id", webhook_id).limit(1)
    )
    return rows[0] if rows else None


# Retrieves all webhooks associated with a specific channel Discord ID. Returns a list of webhook data dictionaries.
def get_webhooks_for_channel(channel_discord_id: str) -> List[Dict[str, Any]]:
    rows = _execute(
        supabase.table("webhooks").select("*").eq("channel_discord_id", channel_discord_id)
    )
    return rows or []


# Retrieves all webhooks associated with a specific guild Discord ID. Returns a list of webhook data dictionaries.
def get_webhooks_for_guild(guild_discord_id: str) -> List[Dict[str, Any]]:
    rows = _execute(
        supabase.table("webhooks").select("*").eq("guild_discord_id", guild_discord_id)
    )
    return rows or []


# Creates a new embed send record and returns the created embed send data. This is used to log each attempt to send an embed, including the target webhook/guild/channel, whether it was successful, and any response or error information.
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


# Retrieves a Bible cache record by its reference. Returns the Bible cache data if found, or None if not found. 
def get_bible_cache(cache_key: str) -> Optional[Dict[str, Any]]:
    rows = _execute(
        supabase
        .table("bible_cache")
        .select("*")
        .eq("cache_key", cache_key)
        .limit(1)
    )

    if not rows:
        return None

    return rows[0]
# Upserts a Bible cache record. Returns the upserted Bible cache data.
def store_bible_cache(
    cache_key: str,
    reference: str,
    text: str,
    translation: Optional[str] = None,
) -> Dict[str, Any]:
    record = {
        "cache_key": cache_key,
        "reference": reference,
        "text": text,
        "translation": translation,
        "updated_at": datetime.utcnow().isoformat(),
    }

    rows = _execute(
        supabase
        .table("bible_cache")
        .upsert(record, on_conflict="cache_key")
        .select("*")
    )

    return rows[0]


# Deletes a webhook record by its Discord ID.
def delete_webhook(webhook_id: Any) -> None:
    _execute(supabase.table("webhooks").delete().eq("discord_id", webhook_id))
