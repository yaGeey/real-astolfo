from datetime import datetime

from classes.Brightness import Brightness
from classes.DiscordRPC import DiscordRPC
from classes.Inactive import Inactive
from classes.Links import Links
from classes.SpotifyBindings import SpotifyBindings
from classes.TelegramBot import TelegramBot
from core.Config import Config
from core.SysTray import SysTray
from core.utils import get_dusk_time


class EventBus:
    def __init__(self):
        self.listeners = {}

    def on(self, event_type, listener):
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(listener)

    def emit(self, event_type, data):
        if event_type in self.listeners:
            for listener in self.listeners[event_type]:
                listener(data)


if __name__ == '__main__':
    bus = EventBus()
    config = Config('config.ini')
    brightness = Brightness()
    dusk_time, dawn_time = get_dusk_time()

    systray = SysTray(config, bus)
    bus.on('window_closed', systray.close_window)
    bus.on('log', lambda text: systray.log(text))
    bus.on('log-error', lambda text: systray.log_error(text))

    discord_rpc = DiscordRPC(config, bus)
    inactive = Inactive(config, bus)
    links = Links(config, bus)
    SpotifyBindings()

    def on_inactive_start(data):
        systray.update(icon='public/astolfo_sleep.ico')
        bus.emit('log', 'Inactive...')
        discord_rpc.inactive_since = datetime.now()
        links.is_inactive = True

    def on_inactive_end(data):
        systray.update(icon='public/astolfo.ico')
        bus.emit('log', 'Active again')
        discord_rpc.inactive_since = None
        links.is_inactive = False

    bus.on('inactive-start', on_inactive_start)
    bus.on('inactive-end', on_inactive_end)

    bus.on('brightness_toggle', lambda mon: brightness.toggle(mon=mon))

    bus.on('force-start-last-lesson', lambda recording: links.force_start_last_lesson(recording))
    bus.on('current-lesson-change', lambda lesson: setattr(discord_rpc, 'current_lesson_name', lesson))

    tgbot = TelegramBot()
    bus.on('send-tg-message', lambda msg: tgbot.send_message(msg))
