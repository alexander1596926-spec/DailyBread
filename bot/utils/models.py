from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class WebhookMetadata:
    """Database-ready shape for webhook records created or discovered by the bot."""

    id: int
    name: str
    guild_id: int
    channel_id: int
    url: Optional[str]
    created_by_bot: bool


@dataclass(slots=True)
class ChannelMetadata:
    """Database-ready shape for Discord text channels DailyBread can use."""

    id: int
    name: str
    guild_id: int
    position: int
    category_id: Optional[int]
    bot_can_view: bool
    bot_can_manage_webhooks: bool
    bot_can_send_messages: bool
