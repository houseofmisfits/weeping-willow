from typing import Callable, Union

import discord


class Trigger:
    TRIGGER_DESCRIPTION = 'On'

    def __init__(self, trigger_value, action: Callable[[discord.Message], bool]):
        self.trigger_value = trigger_value
        self.action = action

    def evaluate(self, message: discord.Message) -> Union[Callable[[discord.Message], bool], None]:
        raise NotImplementedError()

    def __str__(self):
        return '<Trigger ({0}): {1}: {2}; {3}>'.format(
            self.__hash__(),
            self.TRIGGER_DESCRIPTION,
            self.trigger_value,
            self.action.__name__
        )
