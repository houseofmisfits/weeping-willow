import logging
import discord

COLORS = {
    10: discord.Color.greyple(),
    20: discord.Color.dark_green(),
    30: discord.Color.orange(),
    40: discord.Color.gold(),
    50: discord.Color.red()
}


class LoggingEngine(logging.StreamHandler):

    def __init__(self, client):
        logging.StreamHandler.__init__(self)
        self.client = client
        self.open = False
        self.channel = None

    async def setup(self):
        self.channel = int(await self.client.get_config('logging_channel'))
        if self.channel is not None:
            self.open = True

    def close(self):
        self.channel = None
        self.open = False

    def emit(self, record):
        if not self.open:
            # Logging engine not started, drop record
            return
        message = self.format(record)
        self.client.loop.create_task(self.push_log(record, message))

    async def push_log(self, record: logging.LogRecord, message):
        channel = self.client.get_channel(self.channel)
        color = COLORS[record.levelno]
        embed = discord.Embed()
        embed.description = message
        embed.set_footer(text=record.name)
        embed.colour = color
        await channel.send(embed=embed)
