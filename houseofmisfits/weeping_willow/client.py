from typing import List, ClassVar
from houseofmisfits.weeping_willow.triggers import Trigger

import discord
import yaml

import logging

from houseofmisfits.weeping_willow import modules

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class WeepingWillowClient(discord.Client):
    """
    House of Misfits Weeping Willow Bot. Contains specific integrations for House of Misfits.
    """
    def __init__(self, bot_config_path='botconfig.yml'):
        super(WeepingWillowClient, self).__init__()
        with open(bot_config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        self.modules = []
        self.triggers: List[Trigger] = []

    def set_up_modules(self):
        logger.debug("Setting up modules")
        # Remember that trigger processing is first-come, first-serve! If there is any kind of conflict, the first
        # module registered takes precedence.
        for module_name in modules.__module_list__:
            module_class: ClassVar[modules.Module] = getattr(modules, module_name)
            module = module_class(self)
            self.modules.append(module)
            logger.debug("Added module: {}".format(module_class.__name__))
            for trigger in module.get_triggers():
                self.add_trigger(trigger)

    def add_trigger(self, trigger: Trigger):
        logger.debug("Adding trigger {}".format(str(trigger)))
        self.triggers.append(trigger)

    async def on_ready(self):
        self.set_up_modules()

    async def on_message(self, message: discord.Message):
        for trigger in self.triggers:
            triggered_fn = trigger.evaluate(message)
            if triggered_fn:
                # noinspection PyUnresolvedReferences
                logger.debug(
                    "Message ID {0.id} ({0.author.display_name} in {0.channel.id}) triggered module {1}".format(
                        message, triggered_fn.__module__
                    )
                )
                if triggered_fn(message):
                    return
                # noinspection PyUnresolvedReferences
                logger.debug("Message {0.id}: {1} did not report successful processing. Continuing processing.".format(
                    message, triggered_fn.__module__
                ))

    def run(self, *args, **kwargs):
        logger.info("Bot is starting, use {} to invite bot to server".format(
            discord.utils.oauth_url(
                client_id=self.config['client_id'],
                permissions=discord.Permissions(8)
            )
        ))
        super(WeepingWillowClient, self).run(self.config['client_token'], *args, **kwargs)

    async def close(self):
        logger.warning("Bot is shutting down")
        await super(WeepingWillowClient, self).close()

    async def get_admin_users(self):
        guild: discord.Guild = self.get_guild(self.config['guild_id'])
        admin_users = []
        for role in guild.roles:
            if role.id in [self.config['tech_role'], self.config['admin_role']]:
                admin_users += role.members
        #for user in guild.members:
            #logger.debug("{}".format(user.id))
            #if self.config['admin_role'] in user.roles or self.config['tech_role'] in user.roles:
                #admin_users.append(user)
        logger.debug("Admin members:\n" + "\n".join(str(member.id) for member in admin_users))
        return admin_users
