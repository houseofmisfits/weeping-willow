import discord
from typing import Callable, Awaitable, Union

from houseofmisfits.weeping_willow.triggers import Trigger

import asyncio


class Command:
    def __init__(self, client, command, action):
        self.client = client
        if isinstance(command, list):
            self.command = command
        else:
            self.command = [command]
        self.action = action
        self.prefix = None
        asyncio.get_event_loop().create_task(self.get_prefix())

    async def get_prefix(self):
        self.prefix = await self.client.get_config("command_prefix", '.')

    async def check_command(self, message: discord.Message) -> bool:
        if not message.content.startswith(self.prefix):
            return False
        args = message.content.split(' ')
        args = [arg for arg in args if arg]
        command = args[0][len(self.prefix):]
        return command in self.command

    def get_trigger(self):
        return CommandTrigger(self, self.action)


class CommandTrigger(Trigger):
    def __init__(self, command: Command, action: Callable[[discord.Message], Awaitable[bool]]):
        Trigger.__init__(self, command, action)

    async def evaluate(self, message: discord.Message) -> Union[Callable[[discord.Message], Awaitable[bool]], None]:
        if await self.trigger_value.check_command(message):
            return self.action
