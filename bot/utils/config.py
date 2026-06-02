import logging
import os

from dotenv import load_dotenv


ENVIRONMENT_LOCAL = "local"
ENVIRONMENT_RENDER = "render"
ENVIRONMENT_VARIABLE = "DAILYBREAD_ENV"


def get_runtime_environment() -> str:
    """Return whether the bot should run with local or Render behavior."""

    configured_environment = os.getenv(ENVIRONMENT_VARIABLE, "").strip().lower()
    if configured_environment in {ENVIRONMENT_LOCAL, ENVIRONMENT_RENDER}:
        return configured_environment

    if os.getenv("RENDER"):
        return ENVIRONMENT_RENDER

    return ENVIRONMENT_LOCAL


def is_render_environment() -> bool:
    """Check whether Render-only startup helpers should run."""

    return get_runtime_environment() == ENVIRONMENT_RENDER


def load_environment_variables() -> None:
    """Load the right environment source for local development or Render."""

    if os.getenv("RENDER"):
        return

    load_dotenv()


def configure_logging() -> None:
    """Configure clean console logs for local development and Render."""

    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def get_discord_token() -> str:
    """Read the Discord bot token from environment variables."""

    token = os.getenv("DISCORD_TOKEN") or os.getenv("discord_token")
    if token:
        return token.strip().strip('"').strip("'")

    raise RuntimeError("DISCORD_TOKEN is missing. Add it to the Render environment or .env file.")
