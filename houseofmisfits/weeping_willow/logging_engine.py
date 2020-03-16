import logging
import os

import discord

COLORS = {
    10: discord.Color.greyple(),
    20: discord.Color.dark_green(),
    30: discord.Color.gold(),
    40: discord.Color.red(),
    50: discord.Color.magenta()
}


class LoggingEngine(logging.StreamHandler):
    LOG_LEVELS = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARN': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }

    def __init__(self, client):
        logging.StreamHandler.__init__(self)
        self.client = client
        self.open = False
        self.channel = None

    async def setup(self):
        self.channel = int(await self.client.get_config('logging_channel'))
        if self.channel is not None:
            level_name = (await self.client.get_config('log_level', 'INFO')).upper()
            self.setLevel(LoggingEngine.LOG_LEVELS[level_name])
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
        plaintext = None if record.levelno < 40 else '<@&{}>'.format(os.getenv('BOT_TECH_ROLE'))
        await channel.send(plaintext, embed=embed)
