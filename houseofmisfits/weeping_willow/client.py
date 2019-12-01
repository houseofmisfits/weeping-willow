import discord
import yaml

import logging

from houseofmisfits.weeping_willow.modules import VentingModule

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class WeepingWillowClient(discord.Client):
    def __init__(self, bot_config_path='botconfig.yml'):
        super(WeepingWillowClient, self).__init__()
        with open(bot_config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        self.modules = []
        self.channel_triggers = {}
        self.set_up_modules()

    def set_up_modules(self):
        self.modules.append(VentingModule(self))

    async def on_message(self, message: discord.Message):
        if message.channel.id in self.channel_triggers:
            module_fn = self.channel_triggers[message.channel.id]
            logger.debug(
                "Message ID {0.id} ({0.author.display_name} in {0.channel.name}) triggered module {1}".format(
                    message, module_fn.__module__
                )
            )
            module_fn(message)

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
