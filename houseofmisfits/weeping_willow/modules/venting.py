import discord

from datetime import datetime, timedelta

import logging

from asyncio import sleep

from discord import TextChannel

from houseofmisfits.weeping_willow.modules import Module
from houseofmisfits.weeping_willow.triggers import ChannelTrigger

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class VentingModule(Module):
    def __init__(self, client):
        from houseofmisfits.weeping_willow import WeepingWillowClient
        self.client: WeepingWillowClient = client
        self.config = client.config['venting']
        self.deletion_schedules = {}
        self.messages = {}
        self.is_open = True
        self.scan_time = datetime.now()
        self.client.loop.create_task(self.run_loop())

    def get_triggers(self):
        return [ChannelTrigger(self.config['channel_id'], self.process)]

    def process(self, message: discord.Message):
        deletion_time = message.created_at + timedelta(seconds=self.config['deletion_seconds'])
        self.messages[message.id] = message
        self.deletion_schedules[message.id] = deletion_time
        logger.debug("Message will be deleted at {}".format(deletion_time.isoformat()))
        return True

    async def run_loop(self):
        while self.is_open:
            await sleep(1)
            await self.execute_scheduled_deletions()
            if self.scan_time <= datetime.now():
                await self.scan_messages()
                self.scan_time = datetime.now() + timedelta(minutes=10)

    async def execute_scheduled_deletions(self):
        for message_id in self.deletion_schedules.copy():
            if datetime.utcnow() >= self.deletion_schedules[message_id]:
                message = self.messages[message_id]
                logger.debug("Deleting message {}".format(message.id))
                try:
                    await message.delete()
                except discord.errors.DiscordException as e:
                    logger.debug("Unable to delete message {}. Got exception {}".format(message_id, str(e)))
                finally:
                    del self.deletion_schedules[message_id]
                    del self.messages[message_id]

    async def scan_messages(self):
        logger.debug("Scanning for missed messages")
        channel: TextChannel = await self.client.fetch_channel(self.config['channel_id'])
        async for message in channel.history(limit=200):
            if message.id not in self.deletion_schedules:
                logger.debug("Found message {} not scheduled for deletion, adding to queue".format(
                    message.id
                ))
                self.process(message)
