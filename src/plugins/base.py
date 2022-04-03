from abc import ABC, abstractmethod


class MyClientPlugin(ABC):
    def __init__(self, client):
        self.client = client

    @abstractmethod
    async def process_message(self, msg):
        ...

    @abstractmethod
    async def process_reaction(self, reaction):
        ...

    @abstractmethod
    async def initialize_after_restart(self):
        ...
