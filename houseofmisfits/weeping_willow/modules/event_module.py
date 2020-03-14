import asyncio
import os
import pytz
from typing import AsyncIterable

import discord

from houseofmisfits.weeping_willow.modules import Module
from houseofmisfits.weeping_willow.triggers import Trigger, ChannelTrigger, Command

from datetime import date, time, datetime, timedelta
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
        self.command = Command(self.client, 'events', self.events_command)

    async def get_triggers(self) -> AsyncIterable[Trigger]:
        await self.reset_trigger()
        yield self.trigger
        yield self.command.get_trigger()
        asyncio.get_running_loop().create_task(self.loop_daily())

    async def events_command(self, message):
        if not await self.test_authorization(message):
            return True
        args = message.content.split(' ')
        args = [arg for arg in args if arg]
        if len(args) == 1:
            await message.channel.send(
                embed=discord.Embed(
                    color=discord.Color.greyple(),
                    description="""Subcommands:
`set {day} {channel}` - Sets the event channel for `day` to `channel` 
`clear {day}` - Removes the event for `day`
`role {role ID}` - Sets the role given to event participants to `role ID`
`getparticipants {day}` - Sets the participant role to people who participated on `day`
`resetparticipants` - Resets the participant role to people who participated today
"""
                )
            )
        elif args[1] == 'set':
            await self.set_command(args, message)
        elif args[1] == 'clear':
            await self.clear_command(args, message)
        elif args[1] == 'role':
            await self.role_command(args, message)
        elif args[1] == 'getparticipants':
            await self.get_participants_command(args, message)
        elif args[1] == 'resetparticipants':
            await self.reset_participants_command(args, message)
        else:
            await self.send_error(
                message.channel,
                "Unknown subcommand, `{}`. Try running `.events` to see subcommands.".format(args[1])
            )
        return True

    async def set_command(self, args, message):
        if len(args) < 4:
            await self.send_error(
                message.channel,
                "Improper syntax. "
                "Syntax should be `{} {} {{day_of_week}} {{channel}}`".format(*args[0:2])
            )
        try:
            day_of_week = self.get_day_of_week(args[2])
        except ValueError:
            await self.send_error(
                message.channel,
                "Couldn't understand {} as day of week".format(args[2])
            )
            return
        try:
            channel_id = self.get_channel_id(args[3])
        except ValueError:
            await self.send_error(
                message.channel,
                "Couldn't understand {} as a channel. Try copying the channel ID.".format(args[3])
            )
            return
        if date.today().weekday() == day_of_week and \
                not await self.confirm_change_today(message.channel, message.author):
            return
        await self.set_event(day_of_week, channel_id)
        await message.add_reaction('✅')

    async def clear_command(self, args, message):
        if len(args) < 3:
            await self.send_error(
                message.channel,
                "Improper syntax. "
                "Syntax should be `{} {} {{day_of_week}}`".format(*args[0:2])
            )
        try:
            day_of_week = self.get_day_of_week(args[2])
        except ValueError:
            await self.send_error(
                message.channel,
                "Couldn't understand {} as day of week".format(args[2])
            )
            return
        if date.today().weekday() == day_of_week and \
                not await self.confirm_change_today(message.channel, message.author):
            return
        await self.set_event(day_of_week, None)
        await message.add_reaction('✅')

    async def confirm_change_today(self, channel, user):
        msg = await channel.send("You're changing today's event. That can have unexpected consequences. "
                                 "Do you want to continue?")
        await msg.add_reaction('✅')
        await msg.add_reaction('❌')
        try:
            reaction, user = await self.client.wait_for(
                'reaction_add',
                timeout=30,
                check=lambda r, u: r.message.id == msg.id and u.id == user.id
            )
        except asyncio.TimeoutError:
            await msg.delete()
            return False
        await msg.delete()
        return str(reaction.emoji) == '✅'

    async def set_event(self, day_of_week, channel_id):
        async with self.client.data_connection.pool.acquire() as conn:
            await conn.execute(
                "UPDATE event_channels SET channel_id = $2 WHERE day_of_week = $1",
                day_of_week, channel_id
            )
        if date.today().weekday() == day_of_week:
            await self.reset_trigger()

    async def role_command(self, args):
        pass

    async def get_participants_command(self, args):
        pass

    async def reset_participants_command(self, args):
        pass

    async def test_authorization(self, message):
        admin_users = await self.client.get_admin_users()
        if message.author not in admin_users:
            await message.channel.send(
                embed=discord.Embed(
                    description="You're not authorized to use that command",
                    color=discord.Color.red()
                )
            )
            return False
        return True

    def get_channel_id(self, channel_str):
        if channel_str.startswith('<#'):
            channel_str = channel_str[2:-1]
        if channel_str.isnumeric():
            for channel in self.client.get_all_channels():
                if int(channel_str) == channel.id:
                    return channel.id
            raise ValueError()
        for channel in self.client.get_all_channels():
            if channel_str == channel.name:
                return channel.id
        raise ValueError()

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

    @staticmethod
    async def send_error(channel, message):
        await channel.send(
            embed=discord.Embed(
                description=message,
                color=discord.Color.red()
            )
        )

    @staticmethod
    def get_day_of_week(day):
        days = {
            'su': 6, 'sun': 6, 'sunday': 6, 'sund': 6, 'sundae': 6, 'thelordsday': 6,
            'm': 0, 'mo': 0, 'mon': 0, 'monday': 0, 'garfield': 0,
            'tu': 1, 'tue': 1, 'tuesday': 1, 'twosday': 1,
            'w': 2, 'we': 2, 'wed': 2, 'wednesday': 2, 'wendys': 2, 'humpday': 2, 'wensday': 2,
            'th': 3, 'thu': 3, 'thur': 3, 'thurs': 3, 'thursday': 3,
            'f': 4, 'fr': 4, 'fri': 4, 'friday': 4,
            'sa': 5, 'sat': 5, 'saturday': 5
        }
        if day.isnumeric() and int(day) in range(7):
            return int(day)
        elif day.lower() in days.keys():
            return days[day.lower()]
        else:
            raise ValueError()


