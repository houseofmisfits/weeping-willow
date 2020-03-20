import asyncio
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
        from houseofmisfits.weeping_willow import WeepingWillowClient
        self.client: WeepingWillowClient = client
        self.trigger = None
        self.reset_ts = None
        self.scan_ts = datetime.now()
        self.is_open = True
        self.command = Command(self.client, 'events', self.events_command)
        self.backdated = False

    async def get_triggers(self) -> AsyncIterable[Trigger]:
        await self.reset_trigger()
        yield self.trigger
        yield self.command.get_trigger()
        asyncio.get_running_loop().create_task(self.loop_daily())
        asyncio.get_running_loop().create_task(self.scan_for_messages())

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
                "Couldn't understand `{}` as day of week".format(args[2])
            )
            return
        try:
            channel_id = self.get_channel_id(args[3])
        except ValueError:
            await self.send_error(
                message.channel,
                "Couldn't understand `{}` as a channel. Try copying the channel ID.".format(args[3])
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
                "Couldn't understand `{}` as day of week".format(args[2])
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
            self.client.add_trigger(self.trigger)

    async def role_command(self, args, message):
        if len(args) < 3:
            await self.send_error(
                message.channel,
                "Improper syntax. "
                "Syntax should be `{} {} {{role}}`".format(*args[0:2])
            )
            return
        try:
            role = self.get_role_id(args[2])
            await self.client.set_config('participant_role', str(role))
            await message.add_reaction('✅')
        except ValueError:
            await self.send_error(
                message.channel,
                "Couldn't understand `{}` as a role".format(
                    args[2]
                )
            )

    async def get_participants_command(self, args, message):
        if len(args) < 3:
            await self.send_error(
                message.channel,
                "Improper syntax. "
                "Syntax should be `{} {} {{day/date}}`".format(*args[0:2])
            )
            return
        try:
            weekday = self.get_day_of_week(args[2])
            test_date = date.today() - timedelta(days=1)
            while test_date.weekday() != weekday:
                test_date = test_date - timedelta(days=1)
            event_date = test_date
        except ValueError:
            try:
                event_date = date.fromisoformat(args[2])
            except ValueError:
                await self.send_error(
                    message.channel,
                    "Could not understand {} as date or day of week."
                    "If using a date, please use the format `YYYY-MM-DD`.".format(args[2])
                )
                return
        await self.set_participants_role_to_day(event_date)
        await message.add_reaction('✅')

    async def reset_participants_command(self, args, message):
        await self.reset_participant_role()
        await message.add_reaction('✅')

    async def set_participants_role_to_day(self, event_date):
        self.backdated = True
        await self.clear_participant_role()
        participants = await self.get_participants_for_day(event_date)
        for user_id in participants:
            participant = self.client.get_user(user_id)
            await self.add_participant_role(participant)

    async def reset_participant_role(self):
        await self.clear_participant_role()
        todays_participants = await self.get_participants_for_day(date.today())
        for user_id in todays_participants:
            participant = self.client.get_user(user_id)
            await self.add_participant_role(participant)
        self.backdated = False

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
            if channel_str.lower() == channel.name.lower():
                return channel.id
        raise ValueError()

    def get_role_id(self, role_str):
        if role_str.startswith('<@&'):
            role_str = role_str[3:-1]
        if role_str.isnumeric():
            role = self.client.guild.get_role(int(role_str))
            if role is None:
                raise ValueError()
            return role.id
        for role in self.client.guild.roles:
            if role.name.lower() == role_str.lower():
                return role.id
        raise ValueError()

    async def reset_trigger(self):
        if self.trigger is not None:
            logger.debug("Removing old channel trigger")
            self.client.triggers.remove(self.trigger)
            self.trigger = None
        self.trigger = await self.create_trigger()
        await self.reset_participant_role()
        self.schedule_next_day()

    async def create_trigger(self):
        async with self.client.data_connection.pool.acquire() as conn:
            participant_channel = await conn.fetchrow(
                "SELECT channel_id FROM event_channels WHERE day_of_week = $1", date.today().weekday())
        if participant_channel['channel_id'] is None:
            logger.info("No event set for today, not adding a trigger.")
            return None
        logger.info("Setting event channel to channel {}".format(participant_channel['channel_id']))
        trigger = ChannelTrigger(str(participant_channel['channel_id']), self.process_participant)
        self.client.add_trigger(trigger)
        return trigger

    async def clear_participant_role(self):
        logger.debug("Clearing participant role")
        participant_role = await self.get_participant_role()
        for user in participant_role.members:
            await user.remove_roles(participant_role)

    def schedule_next_day(self):
        if datetime.now().time() > time(2, 0, 0):
            today = date.today() + timedelta(days=1)
        else:
            today = date.today()
        reset_time = time(2, 0, 0)  # 2:00 AM
        self.reset_ts = datetime.combine(today, reset_time)
        logger.info("Will reset event stuff at {}".format(self.reset_ts))

    async def process_participant(self, message):
        if str(message.channel.id) != self.trigger.trigger_value:
            return False
        if EventModule.get_est_time(message).time() < time(6) or EventModule.get_est_time(message).time() > time(18):
            return False
        if message.author.bot:
            return False
        self.client.loop.create_task(self.update_participant_database(message))
        if not self.backdated:
            await self.add_participant_role(message.author)
        return True

    async def update_participant_database(self, message):
        async with self.client.data_connection.pool.acquire() as conn:
            result = await conn.fetchrow(
                'SELECT message_id FROM event_participants WHERE participation_dt = $1 AND member_id = $2',
                date.today(), message.author.id
            )
            if result is not None:
                return
            await conn.execute(
                "INSERT INTO event_participants VALUES ($1, $2, $3);",
                date.today(), message.author.id, message.id
            )

    async def add_participant_role(self, user):
        member = self.client.guild.get_member(user.id)
        if member is None:
            logger.debug("User {} is not a valid member - skipping".format(user.id))
            return
        logger.debug("Giving user {} the participant role".format(member.id))
        await member.add_roles(await self.get_participant_role())

    async def get_participant_role(self):
        role_id = await self.client.get_config('participant_role')
        logger.debug("Participant role ID: " + role_id)
        return self.client.guild.get_role(int(role_id))

    async def loop_daily(self):
        while self.is_open:
            if datetime.now() > self.reset_ts:
                await self.reset_trigger()
                await self.clear_participant_role()
                self.client.add_trigger(self.trigger)
                self.schedule_next_day()
            await asyncio.sleep(10)

    async def scan_for_messages(self):
        while self.is_open:
            if datetime.now() > self.scan_ts and self.trigger:
                logger.info("Scanning for missed event participants")
                participant_users = await self.get_participants_for_day(date.today())
                event_channel = await self.get_event_channel(date.today().weekday())
                channel: discord.TextChannel = self.client.get_channel(event_channel)
                async for message in channel.history(limit=200):
                    if EventModule.get_est_time(message).date() != date.today():
                        continue
                    if message.author.id not in participant_users:
                        logger.debug("Found message {} for user not in participants list, adding participant".format(
                            message.id
                        ))
                        await self.process_participant(message)
                self.scan_ts = datetime.now() + timedelta(hours=2)
            await asyncio.sleep(5)

    async def get_participants_for_day(self, event_date):
        async with self.client.data_connection.pool.acquire() as conn:
            results = await conn.fetch(
                "SELECT member_id FROM event_participants WHERE participation_dt = $1", event_date)
            return [int(result['member_id']) for result in results] if results is not None else []

    async def get_event_channel(self, weekday):
        async with self.client.data_connection.pool.acquire() as conn:
            result = await conn.fetchrow('SELECT channel_id FROM event_channels WHERE day_of_week = $1', weekday)
            return int(result['channel_id'])

    @staticmethod
    def get_est_time(message: discord.Message) -> datetime:
        utc = pytz.utc
        est = pytz.timezone('America/New_York')
        ts = utc.localize(message.created_at)
        return ts.astimezone(est)

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
