import asyncio
import os
from contextlib import suppress

import uvicorn

from bot.bot import create_bot
from bot.utils.config import configure_logging, get_discord_token, load_environment_variables
from backend.main import app as web_app


def _get_port() -> int:
    return int(os.getenv("PORT", "8000"))


async def start_services() -> None:
    load_environment_variables()
    configure_logging()

    token = get_discord_token()
    bot = create_bot()

    bot_task = asyncio.create_task(bot.start(token))

    server_config = uvicorn.Config(
        web_app,
        host="0.0.0.0",
        port=_get_port(),
        log_level=os.getenv("LOG_LEVEL", "info"),
        proxy_headers=True,
        forwarded_allow_ips="*",
    )

    web_server = uvicorn.Server(server_config)
    web_task = asyncio.create_task(web_server.serve())

    tasks = {bot_task, web_task}

    try:
        done, pending = await asyncio.wait(
            tasks,
            return_when=asyncio.FIRST_EXCEPTION,
        )

        for task in done:
            if task.exception():
                raise task.exception()

    except asyncio.CancelledError:
        # Expected during shutdown
        pass

    finally:
        for task in tasks:
            if not task.done():
                task.cancel()

        await asyncio.gather(
            *tasks,
            return_exceptions=True,
        )

        if not bot.is_closed():
            await bot.close()


def run_main() -> None:
    asyncio.run(start_services())


if __name__ == "__main__":
    run_main()
