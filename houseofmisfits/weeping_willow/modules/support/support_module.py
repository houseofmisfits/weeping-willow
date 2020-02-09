import asyncio
import logging

from typing import AsyncIterable

from houseofmisfits.weeping_willow.modules import Module
from houseofmisfits.weeping_willow.modules.support.support_session import SupportSession
from houseofmisfits.weeping_willow.triggers import Trigger, Command

from houseofmisfits.weeping_willow.modules.support import SupportChannel, SupportNotAllowedException

import discord

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class SupportModule(Module):

    def __init__(self, client):
        self.client = client

    async def get_triggers(self) -> AsyncIterable[Trigger]:
        yield Command(self.client, 'support', self.on_support).get_trigger()

    async def on_support(self, message: discord.Message):
        loop = asyncio.get_running_loop()
        loop.create_task(message.delete())
        loop.create_task(self.start_support_session(message))
        return True

    async def start_support_session(self, message):
        try:
            session = await SupportSession.for_user(message.author, self.client)
            if session.brand_new:
                await session.channel.send(
                    "Hey there, <@{author.id}>, I see you need some support...".format(author=message.author)
                )
            else:
                await session.channel.send(
                    "Oops, looks like you already have a session open here, <@{author.id}>!".format(
                        author=message.author
                    )
                )
        except SupportNotAllowedException:
            # TODO: figure out what to do when someone can't initiate a support session
            message.author.ban()

    async def get_support_channel(self, user):
        pass
