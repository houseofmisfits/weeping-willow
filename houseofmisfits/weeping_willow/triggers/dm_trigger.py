from typing import Callable, Union, Awaitable

import discord

from houseofmisfits.weeping_willow.triggers import Trigger


class DMTrigger(Trigger):
    def __init__(self, action: Callable[[discord.Message], Awaitable[bool]]):
        # Respond to all DMs
        super(DMTrigger, self).__init__(None, action)

    async def evaluate(self, message: discord.Message) -> Union[Callable[[discord.Message], bool], None]:
        if isinstance(message.channel, discord.DMChannel) and not message.author.bot:
            return self.action
        return None
