import discord

from houseofmisfits.weeping_willow.triggers import Trigger


class ChannelTrigger(Trigger):
    async def evaluate(self, message: discord.Message):
        if message.channel.id == int(self.trigger_value):
            return self.action
