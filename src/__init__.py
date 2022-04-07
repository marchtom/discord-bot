import logging
import psycopg2

import discord
from cachetools.func import ttl_cache

from src.settings import MY_ID, BOT_CALL, SECRET, DB_URL
from .plugins.base import MyClientPlugin

logger = logging.getLogger(__name__)
logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)


class MyClient(discord.Client):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db = psycopg2.connect(DB_URL)
        self.__plugins = []

        # initialize client-wide tables
        with self.db.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS allowed_users (
                    id SERIAL PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT now(),
                    user_id BIGINT NOT NULL
                );
            """)
        self.db.commit()

        for p in MyClientPlugin.__subclasses__():
            logger.info(f"register: {p.name}")
            self.__plugins.append(p(self))

    async def on_ready(self):
        logger.info('Connected!')
        logger.info('Username: {0.name}\nID: {0.id}'.format(self.user))

        # reinitialize plugins
        for plugin in self.__plugins:
            await plugin.initialize_after_restart()

    async def on_message(self, message):
        if not message.content.startswith(BOT_CALL):
            return
        print("author ID:", message.author.id)
        print("allowed users:", self._get_allowed_users())
        if not message.author.id in self._get_allowed_users():
            return

        await self.broadcast_message(message)

    async def broadcast_message(self, message):
        for p in self.__plugins:
            await p.process_message(message)

    async def on_raw_reaction_add(self, payload):
        if payload.member.id in self._get_allowed_users():
            return

        await self.broadcast_reaction_add(payload)

    async def broadcast_reaction_add(self, reaction):
        for p in self.__plugins:
            await p.process_reaction(reaction)

    @ttl_cache(ttl=300)
    def _get_allowed_users(self):
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT user_id
                FROM allowed_users;
            """)
            users = cur.fetchall()
        return [x[0] for x in users]


def start():
    intents = discord.Intents.default()
    intents.members = True
    intents.presences = True
    client = MyClient(intents=intents)

    client.run(SECRET)
