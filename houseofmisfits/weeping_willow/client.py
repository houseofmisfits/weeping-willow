import discord
import yaml


class WeepingWillowClient(discord.Client):
    def __init__(self, bot_config_path='botconfig.yml'):
        super(WeepingWillowClient, self).__init__()
        with open(bot_config_path, 'r') as f:
            self.config = yaml.safe_load(f)

    async def on_message(self, message: discord.Message):
        print('{0.author} in {0.channel.name}: {0.content}'.format(message))

    def run(self, *args, **kwargs):
        super(WeepingWillowClient, self).run(self.config['client_token'], *args, **kwargs)
