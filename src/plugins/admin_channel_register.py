import logging

from src.settings import BOT_CALL
from .base import MyClientPlugin

logger = logging.getLogger(__name__)


class AdminChannel(MyClientPlugin):
    name = 'admin-channel-register'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.channel = None

    async def process_message(self, msg):
        if msg.content.startswith(f"{BOT_CALL} {self.name}"):
            logger.info(f"AdminChannel called >process_message<\n{msg}")
            self.channel = msg.channel

        if self.channel:
            await self.channel.send(f"{msg}\n\n{msg.content}")

    async def process_reaction(self, reaction):
        print(f"got reaction: {reaction}")
        if reaction.emoji.name == '🍆':
            channel = self.client.get_channel(reaction.channel_id)
            msg = await channel.fetch_message(reaction.message_id)
            await msg.delete()

