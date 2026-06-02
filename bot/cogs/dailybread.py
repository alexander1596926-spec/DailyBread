from __future__ import annotations

from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from bot.commands.dailybread import handle_dailybread, handle_help, handle_setup


class DailyBreadCog(commands.Cog):
    """Slash commands for the DailyBread Discord integration."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="dailybread", description="Show DailyBread bot status.")
    async def dailybread(self, interaction: discord.Interaction) -> None:
        """Lightweight health/status command for server admins."""

        await handle_dailybread(interaction)

    @app_commands.command(name="setup", description="Prepare a channel for DailyBread webhooks.")
    @app_commands.describe(channel="Text channel to prepare")
    async def setup(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.TextChannel] = None,
    ) -> None:
        """Create a webhook in the selected channel for future website sends."""

        await handle_setup(interaction, channel)

    @app_commands.command(name="help", description="Show DailyBread bot help.")
    async def help_command(self, interaction: discord.Interaction) -> None:
        """Short help command that explains the bot's limited integration role."""

        await handle_help(interaction)
