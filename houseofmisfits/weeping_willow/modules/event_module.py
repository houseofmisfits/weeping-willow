import asyncio
import os
import pytz
from typing import AsyncIterable

import discord

from houseofmisfits.weeping_willow.modules import Module
from houseofmisfits.weeping_willow.triggers import Trigger, ChannelTrigger

from datetime import date, time, datetime, timedelta, timezone
import logging

logger = logging.getLogger(__name__)


weekdays = {
    0: 'mon',
    1: 'tue',
    2: 'wed',
    3: 'thu',
    4: 'fri',
    5: 'sat',
    6: 'sun'
}


class EventModule(Module):
    def __init__(self, client):
        self.client = client
        self.trigger = None
        self.reset_ts = None
        self.is_open = True

    async def get_triggers(self) -> AsyncIterable[Trigger]:
        await self.reset_trigger()
        yield self.trigger
        asyncio.get_running_loop().create_task(self.loop_daily())

    async def reset_trigger(self):
        if self.trigger is not None:
            logger.debug("Removing old channel trigger")
            self.client.triggers.remove(self.trigger)
            self.trigger = None
        self.trigger = await self.create_trigger()
        self.schedule_next_day()

    async def create_trigger(self):
        day_of_week = weekdays[date.today().weekday()]
        participant_channel = await self.client.get_config('participant_channel_{}'.format(day_of_week))
        if participant_channel is None:
            logger.info("No event set for participant_channel_{}, not adding a trigger.".format(day_of_week))
            return None
        logger.info("Setting event channel to channel {}".format(participant_channel))
        return ChannelTrigger(participant_channel, self.process_participant)

    async def clear_participant_role(self):
        logger.info("Clearing participant role")
        participant_role = await self.get_participant_role()
        for user in participant_role.members:
            await user.remove_roles(participant_role)

    def schedule_next_day(self):
        today = date.today() + timedelta(days=1)
        reset_time = time(2, 0, 0)  # 2:00 AM
        self.reset_ts = datetime.combine(today, reset_time)
        logger.info("Will reset event stuff at {}".format(self.reset_ts))

    async def process_participant(self, message):
        if str(message.channel.id) != self.trigger.trigger_value:
            return False
        if EventModule.get_est_time(message) < time(6) or EventModule.get_est_time(message) > time(18):
            return False
        await self.add_participant_role(message.author)
        return True

    async def add_participant_role(self, user):
        await user.add_roles(await self.get_participant_role())

    async def get_participant_role(self):
        guild_id = int(os.getenv('BOT_GUILD_ID'))
        guild = self.client.get_guild(guild_id)
        role_id = await self.client.get_config('participant_role')
        logger.debug("Participant role ID: " + role_id)
        return guild.get_role(int(role_id))

    async def loop_daily(self):
        while self.is_open:
            if datetime.now() > self.reset_ts:
                await self.reset_trigger()
                await self.clear_participant_role()
                self.client.add_trigger(self.trigger)
                self.schedule_next_day()
            await asyncio.sleep(10)

    @staticmethod
    def get_est_time(message: discord.Message) -> time:
        utc = pytz.utc
        est = pytz.timezone('America/New_York')
        ts = utc.localize(message.created_at)
        return ts.astimezone(est).time()


