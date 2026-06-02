from __future__ import annotations

from typing import Optional

import discord

from bot.utils.permissions import ensure_management_access
from bot.utils.webhooks import create_webhook, list_accessible_text_channels


async def handle_dailybread(interaction: discord.Interaction) -> None:
    """Handle the /dailybread status command."""

    if not interaction.guild:
        await interaction.response.send_message(
            "DailyBread is online. Use this command inside a server for guild status.",
            ephemeral=True,
        )
        return

    channels = list_accessible_text_channels(interaction.guild)
    await interaction.response.send_message(
        f"DailyBread is online for **{interaction.guild.name}**. Accessible webhook channels: **{len(channels)}**.",
        ephemeral=True,
    )


async def handle_setup(
    interaction: discord.Interaction,
    channel: Optional[discord.TextChannel] = None,
) -> None:
    """Handle the /setup command."""

    if not await ensure_management_access(interaction):
        return

    target_channel = channel
    if target_channel is None and isinstance(interaction.channel, discord.TextChannel):
        target_channel = interaction.channel

    if target_channel is None:
        await interaction.response.send_message("Please choose a text channel for DailyBread setup.", ephemeral=True)
        return

    if not interaction.guild or target_channel.guild.id != interaction.guild.id:
        await interaction.response.send_message("Please choose a channel from this server.", ephemeral=True)
        return

    bot_member = interaction.guild.me
    if bot_member is None:
        await interaction.response.send_message(
            "DailyBread could not verify its server permissions yet. Please try again.",
            ephemeral=True,
        )
        return

    permissions = target_channel.permissions_for(bot_member)
    if not permissions.view_channel or not permissions.manage_webhooks:
        await interaction.response.send_message(
            "DailyBread needs View Channel and Manage Webhooks permission in that channel.",
            ephemeral=True,
        )
        return

    webhook = await create_webhook(target_channel)
    await interaction.response.send_message(
        f"DailyBread setup is ready in {target_channel.mention}. Webhook ID: `{webhook.id}`.",
        ephemeral=True,
    )


async def handle_help(interaction: discord.Interaction) -> None:
    """Handle the /help command."""

    await interaction.response.send_message(
        "DailyBread connects this server to the website. Use `/setup` to create a webhook in a text channel, "
        "and `/dailybread` to check bot status.",
        ephemeral=True,
    )
