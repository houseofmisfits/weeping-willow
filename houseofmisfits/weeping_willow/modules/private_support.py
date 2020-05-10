import os
from typing import AsyncIterable

from houseofmisfits.weeping_willow.modules import Module
from houseofmisfits.weeping_willow.triggers import Trigger, Command

import discord
import logging
import re

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class PrivateSupport(Module):
    def __init__(self, client):
        from houseofmisfits.weeping_willow import WeepingWillowClient
        self.client: WeepingWillowClient = client

    async def get_triggers(self) -> AsyncIterable[Trigger]:
        yield Command(self.client, 'private', self.handle_command).get_trigger()

    async def handle_command(self, message):
        """
        Handles whenever someone types a `.private` command
        :param message: The message the command was typed in
        :return: Always True
        """
        if not await self.test_authorization(message):
            return True
        args = [arg for arg in message.content.split(' ') if arg]
        if len(args) == 1:
            await message.channel.send(
                embed=discord.Embed(
                    color=discord.Color.greyple(),
                    description="""Subcommands:
`open {user}` - Adds `{user}` to the channel and sends a message opening the session
`close` - Makes the channel read-only for users that have been added to the channel and sends a close message
`clear` - Clears the channel and removes added users to open the channel up for new private sessions
        """
                )
            )
        elif args[1] == 'open':
            return await self.open_session(args, message)
        elif args[1] == 'close':
            return await self.close_session(args, message)
        elif args[1] == 'clear':
            return await self.clear_channel(args, message)
        else:
            await self.send_error(
                message.channel,
                "Unknown subcommand, `{}`. Try running `.private` to see subcommands.".format(args[1])
            )
        return True

    async def test_authorization(self, message: discord.Message):
        support_role = await self.client.get_config('support_role_id')
        for role in message.author.roles:
            if str(role.id) == support_role:
                if not message.channel.name.startswith('private-support'):
                    logger.info("`.private` issued in channel that is not `private-support` {}".format(
                        message.jump_url)
                    )
                    return False
                return True
        logger.info("`.private` issued by non-support member. {}".format(message.jump_url))
        return False

    async def open_session(self, args, message):
        if len(args) < 3:
            await self.send_error(
                message.channel,
                "Please let me know who you want to open a session with. `{} {} {{user}}`".format(
                    *args[0:2]
                )
            )
            return True
        try:
            user = self.get_user(args[2])
            support_role = await self.client.get_config('support_role_id')
            await message.channel.set_permissions(user, send_messages=True, read_messages=True)
            await message.channel.send("Hi <@!{}>, I see you need support right now. Our <@&{}> "
                                       "team will try to get to you soon, but in the meantime please state as much "
                                       "information as you can so that a suitable support member can assist you. "
                                       "Remember, "
                                       "we are volunteers, not professionals. Note please do not double ping it will "
                                       "not get "
                                       "anyone there faster.".format(user.id, support_role))
        except ValueError:
            await self.send_error(
                message.channel,
                "I couldn't recognize `{}` as a user. Try copying their user ID.".format(
                    args[2]
                )
            )

    def get_user(self, user_str):
        match = re.search("^(?:<@!?)?(\\d+)>?$", user_str)
        if match:
            return self.client.get_user(int(match.group(1)))
        guild_id = os.getenv('BOT_GUILD_ID')
        guild = self.client.get_guild(int(guild_id))
        for member in guild.members:
            if user_str in [member.name, member.name + '#' + member.discriminator, member.nick]:
                return member
        raise ValueError()

    async def close_session(self, args, message):
        pass

    async def clear_channel(self, args, message):
        pass

    @staticmethod
    async def send_error(channel, message):
        await channel.send(
            embed=discord.Embed(
                description=message,
                color=discord.Color.red()
            )
        )
