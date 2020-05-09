from typing import AsyncIterable

from houseofmisfits.weeping_willow.modules import Module
from houseofmisfits.weeping_willow.triggers import Trigger, Command

import discord


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
            await self.open_session(args, message)
        elif args[1] == 'close':
            await self.close_session(args, message)
        elif args[1] == 'clear':
            await self.clear_channel(args, message)
        else:
            await self.send_error(
                message.channel,
                "Unknown subcommand, `{}`. Try running `.private` to see subcommands.".format(args[1])
            )
        return True

    async def test_authorization(self, message):
        pass

    async def open_session(self, args, message):
        pass

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
