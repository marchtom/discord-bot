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

    async def process_reaction(self, *args, **kwargs):
        pass

    async def initialize_after_restart(self):
        pass

