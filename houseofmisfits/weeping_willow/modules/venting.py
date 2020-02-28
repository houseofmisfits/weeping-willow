import discord

from datetime import datetime, timedelta

import logging

from asyncio import sleep

from discord import TextChannel

from houseofmisfits.weeping_willow.modules import Module
from houseofmisfits.weeping_willow.triggers import ChannelTrigger

logger = logging.getLogger(__name__)


class VentingModule(Module):
    def __init__(self, client):
        from houseofmisfits.weeping_willow import WeepingWillowClient
        self.client: WeepingWillowClient = client
        self.deletion_schedules = {}
        self.messages = {}
        self.is_open = True
        self.scan_time = datetime.now()
        self.client.loop.create_task(self.run_loop())
        self.trigger = None

    async def get_triggers(self):
        data_connection = self.client.data_connection
        await data_connection.on_config_change('venting_channel', self.reset_module)
        await data_connection.on_config_change('venting_deletion_seconds', self.reset_module)

        venting_channel = await self.client.get_config('venting_channel')
        if venting_channel is None:
            logger.warning("Venting channel is not set, venting module will not work.")
            self.is_open = False
        else:
            self.trigger = ChannelTrigger(venting_channel, self.process)
            yield self.trigger

    async def reset_module(self, key, value):
        if value is not None:
            self.client.modules.remove(self)
            self.client.triggers.remove(self.trigger)
            self.is_open = False
            await self.client.add_module(VentingModule(self.client))

    async def process(self, message: discord.Message):
        deletion_seconds = int(await self.client.get_config('venting_deletion_seconds', '300'))
        deletion_time = message.created_at + timedelta(seconds=deletion_seconds)
        self.messages[message.id] = message
        self.deletion_schedules[message.id] = deletion_time
        logger.debug("Message will be deleted at {}".format(deletion_time.isoformat()))
        return False

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
        venting_channel = await self.client.get_config('venting_channel')
        if venting_channel is None:
            return
        channel: TextChannel = await self.client.fetch_channel(int(venting_channel))
        async for message in channel.history(limit=200):
            if message.id not in self.deletion_schedules:
                logger.debug("Found message {} not scheduled for deletion, adding to queue".format(
                    message.id
                ))
                await self.process(message)
