import discord

from houseofmisfits.weeping_willow.triggers import Trigger


class ChannelTrigger(Trigger):
    def evaluate(self, message: discord.Message):
        if message.channel.id == self.trigger_value:
            return self.action
