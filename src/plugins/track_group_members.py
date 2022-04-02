import asyncio
import logging

from .base import MyClientPlugin
from settings import BOT_CALL

logger = logging.getLogger(__name__)


class TrackGroupMembers(MyClientPlugin):
    name = 'track-group-members'

    async def process_message(self, msg):
        if msg.content.startswith(f"{BOT_CALL} {self.name}"):
            logger.info(f"TrackGroupMembers called >process_message<\n{msg}")
            await self.client.loop.create_task(self.async_bot_task(msg))

    async def process_reaction(self, *args, **kwargs):
        pass

    async def update_members(self, bot_msg, msg):
        guild = bot_msg.guild
        for role in guild.roles:
            if role.name == msg.content.replace(f"{BOT_CALL} {self.name} ", ""):
                online_cnt = 0
                msg_body = f"__Members of **{role.name}**:__\n\n"

                for m in role.members:
                    if str(m.status) != 'offline':
                        emoji = '🟢'
                        online_cnt += 1
                    else:
                        emoji = '⚪'
                    msg_body += f"{emoji} {m.mention}\n"
                msg_body += f"\n__Online__: {online_cnt} / {len(role.members)}"

                await bot_msg.edit(content=msg_body)

    async def async_bot_task(self, msg):
        logger.info("start async_bot_task")
        await self.client.wait_until_ready()
        bot_msg = await msg.channel.send("Magiczny BOT sees this, working...")
        while not self.client.is_closed():
            await self.update_members(bot_msg, msg)
            await asyncio.sleep(60)

