from __future__ import annotations

import logging
import os
import threading
import time
from typing import Optional

import requests
from flask import Flask

from bot.utils.config import is_render_environment


LOGGER = logging.getLogger("dailybread.bot")
DEFAULT_KEEPALIVE_INTERVAL_SECONDS = 10 * 60

app = Flask(__name__)


@app.route("/")
def home():
    """Simple health route Render can hit to confirm the bot process is alive."""

    return "Bot is alive!"


@app.route("/health")
def health():
    """Health check route for Render or external uptime monitors."""

    return {"status": "ok"}


def run_health_server() -> None:
    """Start the tiny Flask server required by Render web services."""

    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, use_reloader=False)


def get_keepalive_url() -> Optional[str]:
    """Return the URL this process should ping to keep the Render service warm."""

    raw_url = os.getenv("KEEPALIVE_URL") or os.getenv("FLASK_URL") or os.getenv("RENDER_EXTERNAL_URL")
    if not raw_url:
        return None

    url = raw_url.rstrip("/")
    if url.endswith("/health"):
        return url

    return url + "/health"


def ping_self() -> None:
    """Ping the Render URL every 10 minutes to keep the service warm."""

    url = get_keepalive_url()
    if not url:
        LOGGER.info("KEEPALIVE_URL/FLASK_URL is not set; skipping Render self-ping")
        return

    interval_seconds = int(os.getenv("KEEPALIVE_INTERVAL_SECONDS", DEFAULT_KEEPALIVE_INTERVAL_SECONDS))
    LOGGER.info("Render self-ping enabled url=%s interval_seconds=%s", url, interval_seconds)

    session = requests.Session()
    while True:
        try:
            response = session.get(url, timeout=10)
            response.raise_for_status()
            LOGGER.debug("Render self-ping succeeded status=%s", response.status_code)
        except requests.RequestException:
            LOGGER.exception("Render self-ping failed")
        time.sleep(interval_seconds)


def start_render_helpers() -> None:
    """Start Render-only helper threads when DAILYBREAD_ENV=render."""

    if not is_render_environment():
        LOGGER.info("Running in local mode; Render health server is disabled")
        return

    LOGGER.info("Running in Render mode; starting health server")
    threading.Thread(target=run_health_server, daemon=True, name="render-health-server").start()
    threading.Thread(target=ping_self, daemon=True, name="render-self-ping").start()
