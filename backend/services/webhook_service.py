import requests
from typing import Any, Dict, Optional


# This module provides functionality to send messages to Discord webhooks, including error handling and payload construction. 
class WebhookError(Exception):
    def __init__(self, message: str, status_code: int, response_text: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


# Normalizes color input to an integer. Accepts integers, hex strings (with or without #), or None. Returns 0 for invalid inputs.
def build_payload_from_embed(embed: Dict[str, Any], bible_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    embed_payload: Dict[str, Any] = {
        "title": embed.get("title", ""),
        "description": embed.get("description", ""),
        "color": embed.get("color") or 0,
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


# Builds a Discord webhook URL from the provided webhook dictionary. 
def _build_webhook_url(webhook: Dict[str, Any]) -> str:
    webhook_id = webhook.get("discord_id")
    token = webhook.get("token")
    if not webhook_id or not token:
        raise WebhookError("Stored webhook is missing required id or token.", 0)
    return f"https://discord.com/api/webhooks/{webhook_id}/{token}"


# Masks the webhook URL for logging purposes to avoid exposing sensitive information. Shows only the last 4 characters of the ID and token.
def _response_text(response: requests.Response) -> str:
    try:
        return response.text
    except Exception:
        return ""


# Sends a payload to the specified Discord webhook. Handles errors and returns a structured result indicating success or failure, along with any relevant status codes and messages.
def send_webhook_record(webhook: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        url = _build_webhook_url(webhook)
    except WebhookError as exc:
        return {
            "webhook_id": webhook.get("discord_id"),
            "success": False,
            "status_code": exc.status_code,
            "response_text": exc.response_text,
            "error": str(exc),
        }

    try:
        response = requests.post(url, json=payload, timeout=15)
    except requests.RequestException as exc:
        return {
            "webhook_id": webhook.get("discord_id"),
            "success": False,
            "status_code": None,
            "response_text": str(exc),
            "error": "Unable to reach Discord webhook endpoint.",
        }

    body_text = _response_text(response)
    if response.status_code == 204:
        return {
            "webhook_id": webhook.get("discord_id"),
            "success": True,
            "status_code": 204,
            "response_text": body_text,
        }

    error_message = "Discord webhook returned an error."
    if response.status_code == 429:
        error_message = "Discord rate limit exceeded."
    elif response.status_code >= 400:
        error_message = f"Discord webhook failed with status {response.status_code}."

    return {
        "webhook_id": webhook.get("discord_id"),
        "success": False,
        "status_code": response.status_code,
        "response_text": body_text,
        "error": error_message,
    }
