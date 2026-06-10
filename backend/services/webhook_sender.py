import httpx
from datetime import datetime
from typing import Any, Dict, Optional


class WebhookSenderError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None, response_text: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


def _normalize_color(color: Optional[int]) -> int:
    if color is None:
        return 0
    if isinstance(color, int):
        return color
    try:
        return int(str(color).strip().lstrip("#"), 16)
    except (ValueError, TypeError):
        return 0


def build_payload_from_embed(embed: Dict[str, Any], bible_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    embed_payload: Dict[str, Any] = {
        "title": embed.get("title", ""),
        "description": embed.get("description", ""),
        "color": _normalize_color(embed.get("color")),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    footer_text = embed.get("footer")
    if footer_text:
        embed_payload["footer"] = {"text": footer_text}

    if bible_data and bible_data.get("reference") and bible_data.get("text"):
        embed_payload["fields"] = [
            {
                "name": bible_data["reference"],
                "value": bible_data["text"],
                "inline": False,
            }
        ]

    return {"embeds": [embed_payload]}


def _build_webhook_url(webhook: Dict[str, Any]) -> str:
    webhook_id = webhook.get("discord_id")
    token = webhook.get("token")
    if not webhook_id or not token:
        raise WebhookSenderError("Invalid webhook record: missing webhook ID or token.")
    return f"https://discord.com/api/webhooks/{webhook_id}/{token}"


def _mask_webhook_url(url: str) -> str:
    try:
        parts = url.split("/")
        if len(parts) >= 2:
            return "/".join(parts[:-1]) + "/<masked>"
    except Exception:
        pass
    return "<masked_webhook_url>"


def _discord_error_message(status_code: int, response_text: str) -> str:
    if status_code == 404:
        return "Discord webhook not found or invalid."
    if status_code == 429:
        return "Discord rate limit exceeded. Please wait and try again."
    if status_code >= 500:
        return "Discord is currently unavailable. Please try again later."
    return f"Discord webhook failed with status {status_code}."


async def send_webhook(webhook: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        url = _build_webhook_url(webhook)
    except WebhookSenderError as exc:
        return {
            "webhook_id": webhook.get("discord_id"),
            "success": False,
            "status_code": exc.status_code,
            "response_text": exc.response_text,
            "error": str(exc),
        }

    masked_url = _mask_webhook_url(url)
    print("WEBHOOK DELIVERY ATTEMPT", {
        "webhook_id": webhook.get("discord_id"),
        "masked_url": masked_url,
        "payload": payload,
    })

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.post(url, json=payload)
        except httpx.RequestError as exc:
            return {
                "webhook_id": webhook.get("discord_id"),
                "success": False,
                "status_code": None,
                "response_text": str(exc),
                "error": "Unable to reach Discord webhook endpoint.",
            }

    response_text = response.text or ""
    status_code = response.status_code

    print("WEBHOOK DELIVERY RESPONSE", {
        "webhook_id": webhook.get("discord_id"),
        "masked_url": masked_url,
        "status_code": status_code,
        "response_text": response_text[:300],
    })

    if status_code == 204:
        return {
            "webhook_id": webhook.get("discord_id"),
            "success": True,
            "status_code": status_code,
            "response_text": response_text,
        }

    return {
        "webhook_id": webhook.get("discord_id"),
        "success": False,
        "status_code": status_code,
        "response_text": response_text,
        "error": _discord_error_message(status_code, response_text),
    }
