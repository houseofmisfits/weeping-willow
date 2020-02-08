import asyncio
import os

import discord
import asyncpg

import logging

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class SupportChannel:
    def __init__(self):
        self.client = None
        self.user = None
        self.channel = None

    @classmethod
    async def for_user(cls, client, user):
        self = SupportChannel()
        self.client = client
        self.user = user
        self.channel = await self._fetch_channel(None)
        return self

    async def _fetch_channel(self, channel_id):
        if channel_id is not None:
            channel = await self.client.fetch_channel(channel_id)
            return channel
        channel_id = await self.get_support_channel_id()
        if channel_id is not None:
            channel = await self.get_support_channel(channel_id)
        else:
            channel = await self.make_support_channel()
        return channel

    async def get_support_channel_id(self):
        async with self.client.data_connection.pool.acquire() as conn:
            try:
                result = await conn.fetchrow(
                    "SELECT channel_id FROM support_session_channels WHERE member_id = $1",
                    str(self.user.id)
                )
            except asyncpg.UndefinedTableError:
                await SupportChannel.build_support_session_channels_table(conn)
                return None
            return None if result is None else result['channel_id']

    async def get_support_channel(self, channel_id):
        try:
            channel = await self.client.fetch_channel(channel_id)
        except (discord.NotFound, discord.Forbidden):
            logger.info("Channel {} for user {} no longer exists. Making new channel.".format(
                channel_id, self.user.id
            ))
            channel = await self.make_support_channel()
        return channel

    async def make_support_channel(self):
        guild_id = os.getenv("BOT_GUILD_ID")
        guild = await self.client.fetch_guild(guild_id)
        category = await self.get_support_category()
        overwrites = category.overwrites
        overwrites[self.user] = discord.PermissionOverwrite(read_messages=True)
        try:
            channel = await guild.create_text_channel(
                name="support-{}".format(self.user.name),  # TODO: test spaces / other odd characters
                overwrites=overwrites,
                category=category,
                position=2  # TODO: Where to put new support sessions?
            )
        except Exception as e:
            logger.error("Could not create support channel for {}".format(self.user.name), exc_info=True)
            raise e
        asyncio.get_running_loop().create_task(self.set_support_channel_id(channel.id))
        return channel

    async def get_support_category(self) -> discord.CategoryChannel:
        category_id = await self.client.get_config('support_category')
        if category_id is None:
            raise ValueError("support_category is not set")
        return await self.client.fetch_channel(category_id)

    async def set_support_channel_id(self, channel_id):
        async with self.client.data_connection.pool.acquire() as conn, conn.transaction():
            await conn.execute("DELETE FROM support_session_channels WHERE member_id = $1", str(self.user.id))
            await conn.execute("INSERT INTO support_session_channels (channel_id, member_id) VALUES ($1, $2)",
                               str(channel_id), str(self.user.id))

    async def send(self, *args, **kwargs):
        return await self.channel.send(*args, **kwargs)

    @staticmethod
    async def build_support_session_channels_table(conn):
        logger.warning("Support sessions table does not exist! It is being created.")
        try:
            await conn.execute(
                """
                CREATE TABLE support_session_channels (
                    channel_id VARCHAR(40) PRIMARY KEY,
                    member_id VARCHAR(40)
                )
                """
            )
        except asyncpg.SyntaxOrAccessError:
            logger.critical("Could not create the sessions table. Support module will not function.", exc_info=True)
