import asyncio
from typing import AsyncIterable

import discord

from houseofmisfits.weeping_willow.modules import Module
from houseofmisfits.weeping_willow.triggers import Trigger, Command

MEDITATION_SOURCE = 'http://www.freemindfulness.org/MARC5MinuteBreathing.mp3'


class MeditationModule(Module):
    def __init__(self, client):
        self.client = client
        self.vc = None

    async def get_triggers(self) -> AsyncIterable[Trigger]:
        yield Command(self.client, 'meditate', self.meditate).get_trigger()
        yield Command(self.client, 'stop', self.stop_meditation).get_trigger()

    async def meditate(self, message):
        author = message.author
        if not author.voice:
            await message.channel.send('You need to be in a voice channel to do that!')
            return False
        elif self.vc is not None:
            await message.channel.send("I'm already meditating.")
            return False
        self.vc = await author.voice.channel.connect()
        self.vc.play(discord.FFmpegPCMAudio(MEDITATION_SOURCE))
        asyncio.get_event_loop().create_task(self.wait_to_stop())
        return True

    async def wait_to_stop(self):
        while self.vc and self.vc.is_playing:
            await asyncio.sleep(1)
        self.vc.stop()
        await self.vc.disconnect()
        self.vc = None

    async def stop_meditation(self, message):
        if not self.vc:
            return False
        self.vc.stop()
        await self.vc.disconnect()
        self.vc = None
