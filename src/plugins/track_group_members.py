import asyncio
import logging
from discord.errors import NotFound
from discord.utils import get

from .base import MyClientPlugin
from src.settings import BOT_CALL, SLEEP_TIME

logger = logging.getLogger(__name__)


class TrackGroupMembers(MyClientPlugin):
    name = 'track-group-members'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # initialize table for this plugin
        with self.client.db.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS track_group_members (
                    id SERIAL PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT now(),
                    message_id TEXT NOT NULL, -- bot message to edit
                    role_id TEXT NOT NULL, -- tracked role
                    channel_id TEXT NOT NULL, -- channel where bot msg was posted
                    guild_id TEXT NOT NULL -- guild/server owning channel
                );
            """)
        self.client.db.commit()


    async def process_message(self, msg):
        if msg.content.startswith(f"{BOT_CALL} {self.name}"):
            logger.info(f"TrackGroupMembers called >process_message<\n{msg}")

            bot_msg = await msg.channel.send("Magiczny BOT sees this, working...")
            guild = msg.guild
            role_target = msg.content.replace(f"{BOT_CALL} {self.name} ", "")

            for role_check in guild.roles:
                if role_check.name == role_target:
                    role = role_check
                    break
            else:
                await bot_msg.edit(content=f"Magiczny BOT couldn't find role `{role_target}`")
                return

            with self.client.db.cursor() as cur:
                cur.execute(
                    "INSERT INTO track_group_members (message_id, role_id, channel_id, guild_id) VALUES (%s::TEXT, %s::TEXT, %s::TEXT, %s::TEXT);",
                    (bot_msg.id, role.id, bot_msg.channel.id, guild.id),
                )
            self.client.db.commit()

            await self.client.loop.create_task(
                self._setup_async_bot_task(bot_msg.id, role.id, bot_msg.channel.id, guild.id),
            )

    async def process_reaction(self, reaction):
        print(f"got reaction: {reaction}")
        if reaction.emoji.name == '🍆':
            channel = self.client.get_channel(reaction.channel_id)
            msg = await channel.fetch_message(reaction.message_id)
            await msg.delete()

            with self.client.db.cursor() as cur:
                cur.execute(
                    "DELETE FROM track_group_members WHERE message_id=%s::TEXT;",
                    (reaction.message_id,),
                )
            self.client.db.commit()

    async def initialize_after_restart(self):
        with self.client.db.cursor() as cur:
            cur.execute("SELECT message_id, role_id, channel_id, guild_id FROM track_group_members;")
            messages = cur.fetchall()

        for msg in messages:
            print(msg)
            await self._setup_async_bot_task(
                int(msg[0]), int(msg[1]), int(msg[2]), int(msg[3]),
            )

    async def _setup_async_bot_task(self, message_id, role_id, channel_id, guild_id):
        await self.client.wait_until_ready()

        guild = self.client.get_guild(guild_id)
        role = get(guild.roles, id=role_id)
        channel = self.client.get_channel(channel_id)

        try:
            msg = await channel.fetch_message(message_id)
        except NotFound:
            logger.error("Meggage_ID: `%s::TEXT` was removed, deleting from database.", message_id)
            with self.client.db.cursor() as cur:
                cur.execute(
                    "DELETE FROM track_group_members WHERE message_id=%s::TEXT;",
                    (message_id,),
                )
            self.client.db.commit()
            return

        last_msg = ''
        safety_counter = 1

        while not self.client.is_closed():
            online_members = 0

            msg_head_1 = f"__Members of **{role.name}**:__\n"
            msg_body = ''

            for m in role.members:
                if str(m.status) != 'offline':
                    emoji = '🟢'
                    online_members += 1
                else:
                    emoji = '⚪'
                msg_body += f"{emoji} {m.mention}\n"

            msg_head_2 = f"__Online__: {online_members} / {len(role.members)}\n\n"
            new_msg = msg_head_1 + msg_head_2 + msg_body

            if new_msg != last_msg:
                try:
                    await msg.edit(content=new_msg)
                except NotFound:
                    logger.error("Meggage_ID: `%s::TEXT` was removed, deleting from database.", message_id)
                    with self.client.db.cursor() as cur:
                        cur.execute(
                            "DELETE FROM track_group_members WHERE message_id=%s::TEXT;",
                            (message_id,),
                        )
                    self.client.db.commit()
                    break

                last_msg = new_msg

            # safety check: once every 100 runs check if message still exists
            if safety_counter % 100 == 0:
                try:
                    await channel.fetch_message(message_id)
                except NotFound:
                    logger.error("Meggage_ID: `%s::TEXT` was removed, deleting from database.", message_id)
                    with self.client.db.cursor() as cur:
                        cur.execute(
                            "DELETE FROM track_group_members WHERE message_id=%s::TEXT;",
                            (message_id,),
                        )
                    self.client.db.commit()
                break
            else:
                safety_counter += 1

            await asyncio.sleep(SLEEP_TIME)

