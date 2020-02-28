from typing import AsyncIterable

import asyncpg
import discord

from houseofmisfits.weeping_willow.modules import Module
from houseofmisfits.weeping_willow.triggers import Trigger, Command
from houseofmisfits.weeping_willow import LoggingEngine

import os
import logging

logger = logging.getLogger(__name__)


class BotAdministrationModule(Module):
    def __init__(self, client):
        self.client = client

    async def get_triggers(self) -> AsyncIterable[Trigger]:
        yield Command(self.client, 'wrestart', self.restart).get_trigger()
        yield Command(self.client, 'setconfig', self.set_config).get_trigger()
        yield Command(self.client, 'getconfig', self.get_config).get_trigger()
        yield Command(self.client, 'clearconfig', self.clear_config).get_trigger()
        yield Command(self.client, 'loglevel', self.set_log_level).get_trigger()

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

    async def restart(self, message: discord.Message):
        if not await self.test_authorization(message):
            return True
        await message.channel.send('Rebooting server')
        await self.client.change_presence(status=discord.Status.invisible)
        result = os.system("reboot")
        if result > 0:
            logger.error("Reboot failed")
            await message.channel.send("Couldn't reboot :(")
            await self.client.change_presence(status=discord.Status.online)

    async def set_config(self, message: discord.message):
        if not await self.test_authorization(message):
            return True
        args = message.content.split(' ')
        args = [arg for arg in args if arg]
        if len(args) != 3:
            await message.channel.send(
                embed=discord.Embed(
                    description="Syntax is incorrect. Should be `{} config_name config_value`.".format(args[0]),
                    color=discord.Color.red()
                )
            )
            return True
        config_key = args[1]
        value = args[2]
        try:
            await self.client.set_config(config_key, value)
        except asyncpg.SyntaxOrAccessError as e:
            await message.channel.send(
                embed=discord.Embed(
                    description="Something went wrong 😢".format(args[0]),
                    color=discord.Color.red()
                )
            )
        await message.add_reaction('✅')
        return True

    async def get_config(self, message: discord.message):
        if not await self.test_authorization(message):
            return True
        args = message.content.split(' ')
        args = [arg for arg in args if arg]
        if len(args) != 2:
            await message.channel.send(
                embed=discord.Embed(
                    description="Syntax is incorrect. Should be `{} config_name`.".format(args[0]),
                    color=discord.Color.red()
                )
            )
        config_key = args[1]
        try:
            val = await self.client.get_config(config_key)
            await message.channel.send(
                embed=discord.Embed(
                    title=config_key,
                    description=val,
                    color=discord.Color.orange()
                )
            )
        except asyncpg.SyntaxOrAccessError as e:
            await message.channel.send(
                embed=discord.Embed(
                    description="Something went wrong 😢".format(args[0]),
                    color=discord.Color.red()
                )
            )
        return True

    async def clear_config(self, message: discord.message):
        if not await self.test_authorization(message):
            return True
        args = message.content.split(' ')
        args = [arg for arg in args if arg]
        if len(args) != 2:
            await message.channel.send(
                embed=discord.Embed(
                    description="Syntax is incorrect. Should be `{} config_name`.".format(args[0]),
                    color=discord.Color.red()
                )
            )
        config_key = args[1]
        try:
            await self.client.set_config(config_key, None)
        except asyncpg.SyntaxOrAccessError as e:
            await message.channel.send(
                embed=discord.Embed(
                    description="Something went wrong 😢".format(args[0]),
                    color=discord.Color.red()
                )
            )
        await message.add_reaction('✅')
        return True

    async def set_log_level(self, message: discord.Message):
        if not await self.test_authorization(message):
            return True
        args = [arg for arg in message.content.split(' ') if arg]
        if len(args) != 2 or args[1].upper() not in LoggingEngine.LOG_LEVELS:
            await message.channel.send(
                embed=discord.Embed(
                    description="Syntax is incorrect. Should be `{} debug|info|warn|error|critical`.".format(args[0]),
                    color=discord.Color.red()
                )
            )
        try:
            await self.client.set_config('log_level', args[1].upper())
            self.client.logging_engine.setLevel(LoggingEngine.LOG_LEVELS[args[1].upper()])
        except Exception as e:
            await message.channel.send(
                embed=discord.Embed(
                    description="Something went wrong 😢".format(args[0]),
                    color=discord.Color.red()
                )
            )
            raise e
        await message.add_reaction('✅')
        return True

