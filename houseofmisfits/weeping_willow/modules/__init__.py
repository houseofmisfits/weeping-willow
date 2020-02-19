__module_list__ = ['BotAdministrationModule', 'VentingModule', 'DMHandlerModule', 'MeditationModule', 'EventModule']

__all__ = ['Module'] + __module_list__

from .module import Module
from .venting import VentingModule
from .dm_handler import DMHandlerModule
from .bot_administration import BotAdministrationModule
from .meditation import MeditationModule
from .event_module import EventModule
