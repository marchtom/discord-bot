import asyncio
import logging
from cachetools.func import ttl_cache
from collections import defaultdict
from discord.errors import NotFound
from discord.utils import get

from .base import MyClientPlugin
from src.settings import BOT_CALL, SLEEP_TIME

logger = logging.getLogger(__name__)


FEAT_CACHE_TTL = 30*SLEEP_TIME

class TrackGroupMembers(MyClientPlugin):
    name = 'track-group-members'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tasks = []

        # initialize table for this plugin
        with self.client.db.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS track_group_members (
                    id SERIAL PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT now(),
                    message_id BIGINT NOT NULL, -- bot message to edit
                    role_id BIGINT NOT NULL, -- tracked role
                    channel_id BIGINT NOT NULL, -- channel where bot msg was posted
                    guild_id BIGINT NOT NULL -- guild/server owning channel
                );

                CREATE TABLE IF NOT EXISTS track_group_members_feats (
                    id SERIAL PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT now(),
                    role_id BIGINT NOT NULL, -- role enhanced with feat
                    feat_role_id BIGINT NOT NULL, -- feat role
                    feat_description TEXT NOT NULL -- symbolic description of feat
                );
            """)
        self.client.db.commit()

        self.HELP_MSG = f"""
To start tracking role members:
`{BOT_CALL} {self.name} init @<tracked-role-name>`
Refresh time for members status: {BOT_CALL}s
Refresh time for feats: {FEAT_CACHE_TTL}s

Add Feat to tracked role:
`{BOT_CALL} {self.name} add-feat @<tracked-role-name> @<feat-role-name> <text or emoji depicting feat>`

Remove Feat from tracked role:
`{BOT_CALL} {self.name} remove-feat @<tracked-role-name> @<feat-role-name>`

List role's Feats:
`{BOT_CALL} {self.name} list-feat @<tracked-role-name>`
        """


    async def process_message(self, msg):
        if msg.content.startswith(f"{BOT_CALL} {self.name}"):
            logger.info(f"TrackGroupMembers called >process_message<\n{msg}")

            bot_msg = await msg.channel.send("Magiczny BOT sees this, working...")
            msg_content_parts = msg.content.replace(f"{BOT_CALL} {self.name} ", "").split()
            guild = msg.guild

            if msg_content_parts[0] == "help":
                await bot_msg.edit(content=self.HELP_MSG)

            elif msg_content_parts[0] == "init":
                if len(msg.role_mentions) == 1:
                    role = msg.role_mentions[0]
                else:
                    await bot_msg.edit(content="No valid role mentioned, exiting.")
                    return
                with self.client.db.cursor() as cur:
                    cur.execute(
                        "INSERT INTO track_group_members (message_id, role_id, channel_id, guild_id) VALUES (%s, %s, %s, %s);",
                        (bot_msg.id, role.id, bot_msg.channel.id, guild.id),
                    )
                self.client.db.commit()

                task = self._setup_async_bot_task(bot_msg.id, role.id, bot_msg.channel.id, guild.id)
                self._tasks.append(task)

                await self.client.loop.create_task(task)

            elif msg_content_parts[0] == "add-feat":
                if len(msg.role_mentions) == 2:
                    role_tracked = msg.raw_role_mentions[0]
                    role_feat = msg.raw_role_mentions[1]
                else:
                    await bot_msg.edit(content="No valid role mentioned, exiting.")
                    return
                if len(msg_content_parts) == 4:
                    feat_description = msg_content_parts[3]
                else:
                    await bot_msg.edit(content="Invalid message, exiting.")
                    return

                with self.client.db.cursor() as cur:
                    cur.execute(
                        "INSERT INTO track_group_members_feats (role_id, feat_role_id, feat_description) VALUES (%s, %s, %s);",
                        (role_tracked, role_feat, feat_description),
                    )
                self.client.db.commit()
                await bot_msg.edit(
                    content=f"Feat {get(guild.roles, id=role_feat).mention} ({feat_description}) added to role {get(guild.roles, id=role_tracked).mention}",
                )

            elif msg_content_parts[0] == "remove-feat":
                if len(msg.role_mentions) == 2:
                    role_tracked = msg.role_mentions[0]
                    role_feat = msg.role_mentions[1]
                else:
                    await bot_msg.edit(content="No valid role mentioned, exiting.")
                    return

                with self.client.db.cursor() as cur:
                    cur.execute(
                        "DELETE FROM track_group_members_feats WHERE role_id=%s AND feat_role_id=%s;",
                        (role_tracked.id, role_feat.id),
                    )
                self.client.db.commit()
                await bot_msg.edit(content=f"Feat {role_feat.mention} removed from role {role_tracked.mention}")

            elif msg_content_parts[0] == "list-feat":
                if len(msg.role_mentions) == 1:
                    role_tracked = msg.role_mentions[0]
                else:
                    await bot_msg.edit(content="No valid role mentioned, exiting.")
                    return

                with self.client.db.cursor() as cur:
                    cur.execute(
                        """
                        SELECT feat_role_id, feat_description
                        FROM track_group_members_feats
                        WHERE role_id=%s;
                        """,
                        (role_tracked.id,),
                    )
                    feats = cur.fetchall()
                if feats:
                    edited_msg = "\n".join([f"{get(guild.roles, id=x[0]).mention} ({x[1]})" for x in feats])
                    await bot_msg.edit(content=edited_msg)
                else:
                    await bot_msg.edit(content=f"Role {role_tracked.mention} has no feats.")

    async def process_reaction(self, reaction):
        logger.info(f"got reaction: {reaction}")
        if reaction.emoji.name == '🍆':
            channel = self.client.get_channel(reaction.channel_id)
            msg = await channel.fetch_message(reaction.message_id)
            await msg.delete()

            with self.client.db.cursor() as cur:
                cur.execute(
                    "DELETE FROM track_group_members WHERE message_id=%s;",
                    (reaction.message_id,),
                )
            self.client.db.commit()

    async def initialize_after_restart(self):
        with self.client.db.cursor() as cur:
            cur.execute("SELECT message_id, role_id, channel_id, guild_id FROM track_group_members;")
            messages = cur.fetchall()
        
        if not messages:
            return
        async_tasks = []

        for msg in messages:
            logger.info("Reinitializing `%s` message (message_id, role_id, channel_id, guild_id)", msg)
            async_tasks.append(self.client.loop.create_task(
                self._setup_async_bot_task(
                    msg[0], msg[1], msg[2], msg[3],
                )
            ))
            # sleep to avoid rate limitting from Discord API
            await asyncio.sleep(0.2)
        self._tasks.extend(async_tasks)

        await asyncio.wait(async_tasks)

    @ttl_cache(ttl=FEAT_CACHE_TTL)
    def _get_member_feats(self, guild_id, role_id):
        with self.client.db.cursor() as cur:
            cur.execute("""
                SELECT feat_role_id, feat_description
                FROM track_group_members_feats
                WHERE role_id=%s;
            """, (role_id,))
            role_feats = cur.fetchall()

        if not role_feats:
            return {}

        guild = self.client.get_guild(guild_id)

        feats = defaultdict(list)
        for role_feat_raw in role_feats:
            role_feat = get(guild.roles, id=role_feat_raw[0])
            for member in role_feat.members:
                feats[member.id].append(role_feat_raw[1])
        return feats

    async def _refresh_track_message(self, guild, role, msg):
        exit_time = False
        last_msg = ''
        while True and not exit_time:
            if self.client.is_closed():
                logger.info("Got signal: client is closed")
                await asyncio.sleep(5*SLEEP_TIME)
            else:
                while not self.client.is_closed():
                    online_members = 0
                    msg_head_1 = f"__Members of **{role.name}**:__\n"

                    msg_body_people = []
                    for m in role.members:
                        if str(m.status) != 'offline':
                            status_emoji = '🟢'
                            online_members += 1
                        else:
                            status_emoji = '⚪'
                        feats_list = self._get_member_feats(guild.id, role.id).get(m.id) or []
                        feats = ' '.join(feats_list)
                        msg_body_people.append(f"{status_emoji} {m.mention} {feats}")

                    msg_body = "\n".join(sorted(msg_body_people))
                    msg_head_2 = f"__Online__: {online_members} / {len(role.members)}\n\n"
                    new_msg = msg_head_1 + msg_head_2 + msg_body

                    if new_msg != last_msg:
                        try:
                            await msg.edit(content=new_msg)
                        except NotFound:
                            logger.error("Meggage_ID: `%s` was removed, deleting from database.", msg.id)
                            with self.client.db.cursor() as cur:
                                cur.execute(
                                    "DELETE FROM track_group_members WHERE message_id=%s;",
                                    (msg.id,),
                                )
                            self.client.db.commit()
                            exit_time = True
                        last_msg = new_msg

                    await asyncio.sleep(SLEEP_TIME)
                    exit_time = False

    async def _setup_async_bot_task(self, message_id, role_id, channel_id, guild_id):
        await self.client.wait_until_ready()

        guild = self.client.get_guild(guild_id)
        role = get(guild.roles, id=role_id)
        channel = self.client.get_channel(channel_id)

        try:
            msg = await channel.fetch_message(message_id)
        except NotFound:
            logger.error("Meggage_ID: `%s` was removed, deleting from database.", message_id)
            with self.client.db.cursor() as cur:
                cur.execute(
                    "DELETE FROM track_group_members WHERE message_id=%s;",
                    (message_id,),
                )
            self.client.db.commit()
            return

        await self._refresh_track_message(guild, role, msg)

