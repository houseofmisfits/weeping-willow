import asyncio
from typing import List

import discord

from houseofmisfits.weeping_willow.modules import Module
from houseofmisfits.weeping_willow.triggers import Trigger
from houseofmisfits.weeping_willow.triggers.dm_trigger import DMTrigger

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class DMHandlerModule(Module):
    def __init__(self, client):
        from houseofmisfits.weeping_willow import WeepingWillowClient
        self.client: WeepingWillowClient = client
        self.dm_channels = None
        self.client.loop.create_task(self.ensure_dms())

    def get_triggers(self) -> List[Trigger]:
        return [DMTrigger(self.handle_dm)]

    async def ensure_dms(self):
        """
        Makes sure DM channels exist
        """
        users = await self.client.get_admin_users()
        dm_channels = []
        for user in users:
            dm_channel = user.dm_channel
            if dm_channel is None:
                dm_channel = await user.create_dm()
            dm_channels.append(dm_channel)
        self.dm_channels = dm_channels
        logger.debug(str(len(self.dm_channels)) + " users will be notified if the bot is DMed.")

    def handle_dm(self, message) -> bool:
        loop = asyncio.get_running_loop()
        loop.create_task(
            message.channel.send("Hello, there! Please do not DM this bot. If you have any questions about House of "
                                 "Misfits, you can ask them in <#453174946806497280>.")
        )
        message_embed = discord.Embed(
            title="Direct Message from {} ({})".format(
                message.author.name + "#" + message.author.discriminator,
                message.author.id
            ),
            description=message.content
        )
        for channel in self.dm_channels:
            loop.create_task(
                channel.send(embed=message_embed)
            )
        return True




