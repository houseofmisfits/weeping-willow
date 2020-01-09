from typing import List, Tuple, Callable, Awaitable

import asyncpg
import asyncio
import logging
import os

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class WeepingWillowDataConnection:

    def __init__(self, client):
        self.client = client
        self.pool = None
        self.is_connected = False
        self.config_change_actions: List[Tuple[str, Callable]] = []

    def connect(self):
        logger.debug("Waiting to continue until connected to database")
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        loop.create_task(self.create_connection_pool(future))
        loop.run_until_complete(future)
        self.pool = future.result()
        logger.debug("Connection pool made!")

    async def create_connection_pool(self, future):
        """
        Creates a connection pool for the data connection.
        """
        try:
            pool = await asyncpg.create_pool(
                database=os.getenv("POSTGRES_USER"),
                user=os.getenv("POSTGRES_USER"),
                password=os.getenv("POSTGRES_PASSWORD"),
                host=os.getenv("POSTGRES_HOST"),
                min_size=3,
                max_size=5
            )
            future.set_result(pool)
        except Exception as e:
            future.set_exception(e)
        future.done()

    async def close(self):
        await self.pool.close()

    async def get_config(self, key, default=None):
        """
        Gets a raw value from the config table.
        :param key: The name of the configuration to get
        :param default: Sets the configuration value if it has not already been set
        :return: The configuration value, or None if it's not set and no default has been provided.
        """
        async with self.pool.acquire() as conn:
            try:
                result = await conn.fetchrow("SELECT config_val FROM bot_config WHERE config_key = $1", key)
            except asyncpg.UndefinedTableError:
                await self.build_config_table(conn)
                return await self.get_config(key, default)
            except asyncpg.SyntaxOrAccessError:
                logger.error("Could not get config!", exc_info=True)
                return None

            if result is None and default is not None:
                logger.warning("Config value {} does not exist, setting to default ({})".format(key, default))
                await self.set_config(key, default)
                return default
            if result is None:
                return None
            return result['config_val']

    async def set_config(self, key, value):
        """
        Sets the configuration value by deleting the existing value and replacing it
        :param key: The name of the configuration to set
        :param value: The value to set the configuration to
        """
        async with self.pool.acquire() as conn, conn.transaction():
            try:
                await conn.execute("DELETE FROM bot_config WHERE config_key = $1", key)
                await conn.execute("INSERT INTO bot_config (config_key, config_val) VALUES ($1, $2)", key, value)
                logger.debug("Config {} set to '{}'".format(key, value))
            except asyncpg.SyntaxOrAccessError:
                logger.critical("Could not set the requested configuration value. The bot may not function correctly.")
            actions = [action for watched_key, action in self.config_change_actions if key == watched_key]
            for action in actions:
                self.client.loop.create_task(action(key, value))

    async def on_config_change(self, key, callback: Callable[[str, str], Awaitable]):
        """
        Configures a coroutine to run when a specific configuration value is set
        :param key: The configuration key to watch
        :param callback: A coroutine with two string args (key and value) to run when the config value is set
        """
        self.config_change_actions.append((key, callback))

    async def build_config_table(self, conn):
        """
        Should only be run when initially setting up the bot. Creates the initial config table.
        :param conn: An active PostgreSQL connection
        """
        logger.warning("Config table does not exist! Creating the table.")
        try:
            await conn.execute(
                """
                CREATE TABLE bot_config (
                    config_key VARCHAR(40) PRIMARY KEY,
                    config_val VARCHAR(100)
                )
                """
            )
        except asyncpg.SyntaxOrAccessError:
            logger.critical("Could not create the configuration table. The bot will not function correctly.", exc_info=True)

