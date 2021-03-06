from typing import List, ClassVar, Union
from houseofmisfits.weeping_willow.triggers import Trigger
from houseofmisfits.weeping_willow import WeepingWillowDataConnection, LoggingEngine, upgrades

import discord
import os

import logging

from houseofmisfits.weeping_willow import modules

logger = logging.getLogger(__name__)


class WeepingWillowClient(discord.Client):
    """
    House of Misfits Weeping Willow Bot. Contains specific integrations for House of Misfits.
    """
    def __init__(self):
        super(WeepingWillowClient, self).__init__()
        self.data_connection = WeepingWillowDataConnection(self)
        self.get_config = self.data_connection.get_config
        self.set_config = self.data_connection.set_config
        self.logging_engine = LoggingEngine(self)
        self.guild: Union[discord.Guild, None] = None
        self.modules = []
        self.triggers: List[Trigger] = []

    def run(self, *args, **kwargs):
        logger.info("Bot is starting, use {} to invite bot to server".format(
            discord.utils.oauth_url(
                client_id=os.getenv('BOT_CLIENT_ID'),
                permissions=discord.Permissions(8)
            )
        ))
        self.data_connection.connect()
        logger.info("Successfully connected to internal database")
        upgrades.upgrade_database(self)
        super(WeepingWillowClient, self).run(os.getenv('BOT_CLIENT_TOKEN'), *args, **kwargs)

    async def close(self):
        logger.warning("Bot is shutting down")
        await self.change_presence(status=discord.Status.invisible)
        await self.data_connection.close()
        self.logging_engine.close()
        await super(WeepingWillowClient, self).close()

    async def on_ready(self):
        """
        Runs when the bot is connected to Discord and ready to do stuff
        """
        self.guild = self.get_guild(int(os.getenv('BOT_GUILD_ID')))
        self.loop.set_exception_handler(self.handle_exception)
        await self.set_up_logging()
        await self.set_up_modules()

    async def set_up_logging(self):
        """
        When we are connected to Discord, let's go ahead and start logging to the logging channel.
        """
        await self.logging_engine.setup()
        hom_logger = logging.getLogger('houseofmisfits')
        hom_logger.addHandler(self.logging_engine)

    async def set_up_modules(self):
        """
        Gets all of the modules in the modules package and sets them up
        """
        logger.debug("Setting up modules")
        # Remember that trigger processing is first-come, first-serve! If there is any kind of conflict, the first
        # module registered takes precedence.
        for module_name in modules.__module_list__:
            module_class: ClassVar[modules.Module] = getattr(modules, module_name)
            module = module_class(self)
            await self.add_module(module)
            logger.debug("Added module: {}".format(module_class.__name__))

    async def add_module(self, module):
        self.modules.append(module)
        async for trigger in module.get_triggers():
            self.add_trigger(trigger)

    def add_trigger(self, trigger: Trigger):
        logger.debug("Adding trigger {}".format(str(trigger)))
        if trigger is not None:
            self.triggers.append(trigger)

    async def on_message(self, message: discord.Message):
        """
        When a message occurs, this cycles through all of the triggers that have been set up and checks if any of them
        match.
        """
        for trigger in self.triggers:
            triggered_fn = await trigger.evaluate(message)
            if triggered_fn:
                # noinspection PyUnresolvedReferences
                logger.debug(
                    "Message ID {0.id} ({0.author.display_name} in {0.channel.id}) triggered module {1}".format(
                        message, triggered_fn.__module__
                    )
                )
                # noinspection PyBroadException
                try:
                    if await triggered_fn(message):
                        return
                except Exception as e:
                    logger.error("Trigger threw unhandled exception.", exc_info=True)
                # noinspection PyUnresolvedReferences
                logger.debug("Message {0.id}: {1} did not report successful processing. Continuing processing.".format(
                    message, triggered_fn.__module__
                ))

    async def get_admin_users(self):
        """
        Returns all of the users in the designated roles who can perform administration commands, etc.
        """
        guild_id = os.getenv('BOT_GUILD_ID')
        if guild_id is None:
            logger.warning("Cannot get admin users - Guild ID not set")
            return
        tech_role = int(os.getenv('BOT_TECH_ROLE'))
        admin_role = int(os.getenv('BOT_ADMIN_ROLE'))
        if tech_role is None and admin_role is None:
            logger.warning("Cannot get admin users - no admin/tech role set")
            return
        guild: discord.Guild = self.get_guild(int(guild_id))
        admin_users = []
        for role in guild.roles:
            if role.id in [tech_role, admin_role]:
                admin_users += role.members
        return admin_users

    @staticmethod
    def handle_exception(loop, context):
        logger.error("An unhandled exception occurred: " + context['message'], exc_info=context['exception'])
