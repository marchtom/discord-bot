import asyncio
import logging

import discord

from settings import MY_ID, BOT_CALL, SECRET
from .plugins.base import MyClientPlugin

logger = logging.getLogger(__name__)
logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)


class MyClient(discord.Client):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message = None
        self.role = None
        self.__plugins = []

        for p in MyClientPlugin.__subclasses__():
            logger.info(f"register: {p.name}")
            self.__plugins.append(p(self))

    async def on_ready(self):
        logger.info('Connected!')
        logger.info('Username: {0.name}\nID: {0.id}'.format(self.user))

    async def on_message(self, message):
        if message.author.id != MY_ID:
            return
        if not message.content.startswith(BOT_CALL):
            return

        await self.broadcast_message(message)

    async def broadcast_message(self, message):
        for p in self.__plugins:
            await p.process_message(message)

    async def on_raw_reaction_add(self, payload):
        if payload.member.id != MY_ID:
            return

        await self.broadcast_reaction_add(payload)

    async def broadcast_reaction_add(self, reaction):
        for p in self.__plugins:
            await p.process_reaction(reaction)


def start():
    intents = discord.Intents.default()
    intents.members = True
    intents.presences = True
    client = MyClient(intents=intents)

    client.run(SECRET)
