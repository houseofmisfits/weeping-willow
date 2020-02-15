import asyncio
import logging

from typing import AsyncIterable

from houseofmisfits.weeping_willow.modules import Module
from houseofmisfits.weeping_willow.modules.support.support_session import SupportSession
from houseofmisfits.weeping_willow.triggers import Trigger, Command

from houseofmisfits.weeping_willow.modules.support import SupportChannel, SupportNotAllowedException

import discord

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class SupportModule(Module):

    def __init__(self, client):
        self.client = client

    async def get_triggers(self) -> AsyncIterable[Trigger]:
        yield Command(self.client, 'support', self.on_support).get_trigger()
        yield Command(self.client, 'close', self.on_close_request).get_trigger()

    async def on_support(self, message: discord.Message):
        loop = asyncio.get_running_loop()
        loop.create_task(message.delete())
        loop.create_task(self.start_support_session(message))
        return True

    async def start_support_session(self, message):
        try:
            session = await SupportSession.for_user(message.author, self.client)
            await session.channel.unarchive()
            if session.brand_new:
                await session.channel.send(
                    "Hey there, <@{author.id}>, I see you need some support...".format(author=message.author)
                )
            else:
                await session.channel.send(
                    "Oops, looks like you already have a session open here, <@{author.id}>!".format(
                        author=message.author
                    )
                )
        except SupportNotAllowedException:
            # TODO: figure out what to do when someone can't initiate a support session
            pass

    async def on_close_request(self, message):
        try:
            channel = await SupportChannel.with_channel(message.channel, self.client)
            await message.delete()
            if message.author.id == channel.user_id and await self.confirm_user_close(channel):
                session = await SupportSession.in_channel(channel)
                await session.close()
                return True
            elif self.is_support(message.author):
                session = await SupportSession.in_channel(channel)
                await session.close()
                return True
            else:
                logger.debug("Cancelling the closing of support session")
                return True

        except ValueError:
            logger.debug(".close command issued in non-support channel, skipping")
            return False

    async def confirm_user_close(self, support_channel):
        msg = await support_channel.send("Are you sure you want to close the session?")
        await msg.add_reaction('✅')
        await msg.add_reaction('❌')
        try:
            reaction, user = await self.client.wait_for(
                'reaction_add',
                timeout=30,
                check=lambda r, u: r.message.id == msg.id and u.id == support_channel.user_id
            )
        except asyncio.TimeoutError:
            await msg.delete()
            return False
        await msg.delete()
        return str(reaction.emoji) == '✅'

    def is_support(self, user):
        support_role = self.client.get_config('support_role_id')
        for role in user.roles:
            if str(role.id) == support_role:
                return True
        return False
