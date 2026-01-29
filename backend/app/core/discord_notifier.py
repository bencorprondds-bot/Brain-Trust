"""
Discord Notifier for Brain Trust / Legion

Enables Willow to communicate with the user via Discord.

Features:
- Send notifications (approvals, completions, blockers)
- Receive user responses
- Support for embeds and reactions
- Daily digest delivery
"""

import os
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum

import discord
from discord import Embed, Color
from discord.ext import commands

logger = logging.getLogger(__name__)


class NotificationType(str, Enum):
    """Types of notifications Willow can send."""
    APPROVAL_NEEDED = "approval_needed"
    BLOCKER = "blocker"
    COMPLETION = "completion"
    DAILY_DIGEST = "daily_digest"
    STATUS_UPDATE = "status_update"
    INFO = "info"


@dataclass
class DiscordNotification:
    """A notification to send via Discord."""

    notification_type: NotificationType
    title: str
    message: str

    # Optional fields
    project: Optional[str] = None
    plan_id: Optional[str] = None

    # Interaction
    needs_response: bool = False
    response_options: List[str] = field(default_factory=list)  # Reaction emojis or button labels

    # Styling
    color: Optional[int] = None  # Discord color int
    fields: List[Dict[str, str]] = field(default_factory=list)  # Embed fields

    def to_embed(self) -> Embed:
        """Convert to Discord embed."""
        # Color based on notification type
        colors = {
            NotificationType.APPROVAL_NEEDED: Color.gold(),
            NotificationType.BLOCKER: Color.red(),
            NotificationType.COMPLETION: Color.green(),
            NotificationType.DAILY_DIGEST: Color.blue(),
            NotificationType.STATUS_UPDATE: Color.greyple(),
            NotificationType.INFO: Color.blurple(),
        }

        color = self.color or colors.get(self.notification_type, Color.blurple())

        embed = Embed(
            title=self.title,
            description=self.message,
            color=color,
            timestamp=datetime.now(),
        )

        # Add project field if specified
        if self.project:
            embed.add_field(name="Project", value=self.project, inline=True)

        # Add plan ID if specified
        if self.plan_id:
            embed.add_field(name="Plan ID", value=self.plan_id, inline=True)

        # Add custom fields
        for field_data in self.fields:
            embed.add_field(
                name=field_data.get("name", "Info"),
                value=field_data.get("value", ""),
                inline=field_data.get("inline", True),
            )

        # Footer
        embed.set_footer(text=f"Legion • {self.notification_type.value}")

        return embed


class DiscordBot(commands.Bot):
    """Discord bot for Legion notifications."""

    def __init__(self, channel_id: int, on_message_callback: Optional[Callable] = None):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.reactions = True

        super().__init__(command_prefix="!", intents=intents)

        self.notification_channel_id = channel_id
        self.on_message_callback = on_message_callback
        self._notification_channel: Optional[discord.TextChannel] = None
        self._pending_responses: Dict[int, asyncio.Future] = {}  # message_id -> Future

    async def on_ready(self):
        """Called when bot is connected and ready."""
        logger.info(f"Discord bot connected as {self.user}")

        # Get the notification channel
        self._notification_channel = self.get_channel(self.notification_channel_id)
        if self._notification_channel:
            logger.info(f"Notification channel: #{self._notification_channel.name}")
        else:
            logger.error(f"Could not find channel {self.notification_channel_id}")

    async def on_message(self, message: discord.Message):
        """Handle incoming messages."""
        # Ignore bot's own messages
        if message.author == self.user:
            return

        # Only process messages in the notification channel
        if message.channel.id != self.notification_channel_id:
            return

        # Check if this is a reply to a pending notification
        if message.reference and message.reference.message_id in self._pending_responses:
            future = self._pending_responses.pop(message.reference.message_id)
            if not future.done():
                future.set_result(message.content)
            return

        # Otherwise, pass to callback if set
        if self.on_message_callback:
            await self.on_message_callback(message.content, message.author.name)

        # Process commands
        await self.process_commands(message)

    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        """Handle reaction additions."""
        # Ignore bot's own reactions
        if user == self.user:
            return

        message_id = reaction.message.id
        if message_id in self._pending_responses:
            future = self._pending_responses.pop(message_id)
            if not future.done():
                future.set_result(str(reaction.emoji))

    async def send_notification(
        self,
        notification: DiscordNotification,
        wait_for_response: bool = False,
        timeout: float = 300.0,
    ) -> Optional[str]:
        """
        Send a notification to the Discord channel.

        Args:
            notification: The notification to send
            wait_for_response: Whether to wait for a user response
            timeout: How long to wait for response (seconds)

        Returns:
            User's response if wait_for_response=True, else None
        """
        if not self._notification_channel:
            logger.error("Notification channel not available")
            return None

        embed = notification.to_embed()

        # Send the message
        message = await self._notification_channel.send(embed=embed)

        # Add reaction options if specified
        for emoji in notification.response_options:
            try:
                await message.add_reaction(emoji)
            except discord.HTTPException:
                logger.warning(f"Could not add reaction: {emoji}")

        # Wait for response if requested
        if wait_for_response or notification.needs_response:
            future = asyncio.get_event_loop().create_future()
            self._pending_responses[message.id] = future

            try:
                response = await asyncio.wait_for(future, timeout=timeout)
                return response
            except asyncio.TimeoutError:
                logger.warning(f"Notification {message.id} timed out waiting for response")
                self._pending_responses.pop(message.id, None)
                return None

        return None

    async def send_simple_message(self, content: str) -> Optional[discord.Message]:
        """Send a simple text message."""
        if not self._notification_channel:
            return None

        return await self._notification_channel.send(content)


class DiscordNotifier:
    """
    High-level Discord notification manager.

    Provides easy methods for Willow to send notifications.
    """

    _instance = None
    _bot: Optional[DiscordBot] = None
    _bot_task: Optional[asyncio.Task] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.token = os.getenv("DISCORD_BOT_TOKEN")
        self.channel_id = os.getenv("DISCORD_CHANNEL_ID")
        self._message_callback: Optional[Callable] = None
        self._initialized = True

    def set_message_callback(self, callback: Callable):
        """Set callback for incoming messages."""
        self._message_callback = callback

    async def start(self):
        """Start the Discord bot."""
        if not self.token:
            logger.error("DISCORD_BOT_TOKEN not set")
            return

        if not self.channel_id:
            logger.error("DISCORD_CHANNEL_ID not set")
            return

        try:
            channel_id_int = int(self.channel_id)
        except ValueError:
            logger.error(f"Invalid DISCORD_CHANNEL_ID: {self.channel_id}")
            return

        self._bot = DiscordBot(
            channel_id=channel_id_int,
            on_message_callback=self._message_callback,
        )

        # Add commands
        self._setup_commands()

        # Start bot in background
        logger.info("Starting Discord bot...")
        self._bot_task = asyncio.create_task(self._bot.start(self.token))

    async def stop(self):
        """Stop the Discord bot."""
        if self._bot:
            await self._bot.close()
        if self._bot_task:
            self._bot_task.cancel()

    def _setup_commands(self):
        """Set up Discord slash commands."""

        @self._bot.command(name="status")
        async def status_command(ctx):
            """Get Legion status."""
            try:
                from app.agents import get_willow
                willow = get_willow()

                if willow.current_plan:
                    await ctx.send(f"📋 **Active Plan:** {willow.current_plan.intent_summary}")
                else:
                    await ctx.send("✅ **Status:** Ready and waiting for commands.")
            except Exception as e:
                await ctx.send(f"❌ Error: {e}")

        @self._bot.command(name="approve")
        async def approve_command(ctx):
            """Approve current plan."""
            try:
                from app.agents import get_willow
                willow = get_willow()

                if willow.current_plan:
                    response = willow.approve_and_execute()
                    await ctx.send(f"✅ {response.message[:500]}")
                else:
                    await ctx.send("❌ No plan to approve.")
            except Exception as e:
                await ctx.send(f"❌ Error: {e}")

        @self._bot.command(name="cancel")
        async def cancel_command(ctx):
            """Cancel current plan."""
            try:
                from app.agents import get_willow
                willow = get_willow()

                if willow.current_plan:
                    willow.current_plan = None
                    await ctx.send("🚫 Plan cancelled.")
                else:
                    await ctx.send("❌ No plan to cancel.")
            except Exception as e:
                await ctx.send(f"❌ Error: {e}")

    # High-level notification methods

    async def notify_approval_needed(
        self,
        title: str,
        description: str,
        project: Optional[str] = None,
        plan_id: Optional[str] = None,
    ) -> Optional[str]:
        """Send an approval request notification."""
        notification = DiscordNotification(
            notification_type=NotificationType.APPROVAL_NEEDED,
            title=f"🔔 {title}",
            message=description,
            project=project,
            plan_id=plan_id,
            needs_response=True,
            response_options=["✅", "❌", "🔄"],  # Approve, Reject, Modify
        )

        return await self._bot.send_notification(notification, wait_for_response=True)

    async def notify_blocker(
        self,
        title: str,
        description: str,
        project: Optional[str] = None,
    ):
        """Send a blocker notification (urgent)."""
        notification = DiscordNotification(
            notification_type=NotificationType.BLOCKER,
            title=f"🚨 {title}",
            message=description,
            project=project,
            needs_response=True,
        )

        return await self._bot.send_notification(notification, wait_for_response=True)

    async def notify_completion(
        self,
        title: str,
        description: str,
        project: Optional[str] = None,
        fields: Optional[List[Dict[str, str]]] = None,
    ):
        """Send a completion notification."""
        notification = DiscordNotification(
            notification_type=NotificationType.COMPLETION,
            title=f"✅ {title}",
            message=description,
            project=project,
            fields=fields or [],
        )

        await self._bot.send_notification(notification)

    async def send_daily_digest(
        self,
        escalations: List[str],
        completions: List[str],
        pending_approvals: List[str],
    ):
        """Send the daily digest."""
        fields = []

        if escalations:
            fields.append({
                "name": "🚨 Escalations",
                "value": "\n".join(f"• {e}" for e in escalations[:5]),
                "inline": False,
            })

        if completions:
            fields.append({
                "name": "✅ Completed",
                "value": "\n".join(f"• {c}" for c in completions[:5]),
                "inline": False,
            })

        if pending_approvals:
            fields.append({
                "name": "⏳ Awaiting Approval",
                "value": "\n".join(f"• {p}" for p in pending_approvals[:5]),
                "inline": False,
            })

        notification = DiscordNotification(
            notification_type=NotificationType.DAILY_DIGEST,
            title="📊 Daily Legion Digest",
            message=f"Here's your summary for {datetime.now().strftime('%B %d, %Y')}",
            fields=fields,
        )

        await self._bot.send_notification(notification)

    async def send_message(self, content: str):
        """Send a simple message."""
        if self._bot:
            await self._bot.send_simple_message(content)


# Singleton accessor
_notifier: Optional[DiscordNotifier] = None


def get_discord_notifier() -> DiscordNotifier:
    """Get the singleton Discord notifier."""
    global _notifier
    if _notifier is None:
        _notifier = DiscordNotifier()
    return _notifier


async def start_discord_bot():
    """Start the Discord bot (call from app startup)."""
    notifier = get_discord_notifier()
    await notifier.start()


async def stop_discord_bot():
    """Stop the Discord bot (call from app shutdown)."""
    notifier = get_discord_notifier()
    await notifier.stop()
