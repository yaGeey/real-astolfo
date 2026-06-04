import os
import winsound
from datetime import datetime

import psutil
from infi.systray import SysTrayIcon

# from ..core.Config import Config
from .Window import Window


class SysTray(SysTrayIcon):
    def __init__(self, config, bus):
        self.bus = bus
        self.config = config

        self.window = None
        self.logs = ''
        self.hint_window = None
        self.hover_text = f'Тиждень {self.config.get("SETTINGS", "week")}, абоба'

        menu = (
            # ("Тека з скринами", 'C:/Users/LEGION/PycharmProjects/game/folder.ico', lambda systray:os.startfile('C:/Users/LEGION/Pictures/Zoom')),
            ('Меню', None, self.create_window),
            ('Відкрити cwd', None, lambda systray: os.startfile(r'C:\Users\LEGION\PycharmProjects\astolfo')),
            # ('Останній урок', None, lambda systray: links.force_start_last_lesson()),
            ('Останній урок', None, lambda systray: self.bus.emit('force-start-last-lesson')),
            ('Відкрити config.ini', None, lambda systray: os.startfile(config.location)),
            ('Відкрити controls.txt', None, lambda systray: os.startfile(r'public/controls.txt')),
            # ('Перемкнути яскравість', 'public/brightness.ico', lambda systray: brightness.toggle(mon=1)),
            ('Перемкнути яскравість', 'public/brightness.ico', lambda systray: self.bus.emit('brightness_toggle', 1)),
        )
        super().__init__('public/astolfo.ico', self.hover_text, menu, on_quit=self.close, default_menu_index=0)
        self.start()

    def close(self, systray):
        # safely close OBS
        self.bus.emit('exit', None)
        # if self.obs_client:
        #     c: int = self.obs_client.client
        #     self.obs_client.execute(lambda: self.obs_client.client.stop_record())
        #     time.sleep(5)
        #     self.obs_client.execute(lambda: self.obs_client.client.exit())
        # close self
        for proc in psutil.process_iter():
            if 'Астольфік' in proc.name():
                proc.kill()

    def close_window(self, systray):
        if self.window is not None:
            # self.window.destroy()
            self.window = None

    def create_window(self, systray):
        if self.window is None:
            self.window = Window(self.config, self.bus)
            self.window.start(self.logs)
        else:
            self.window.destroy()
            self.window = None

    def log(self, message):
        time_str = datetime.now().strftime('%H:%M:%S')
        msg = time_str + ' ' + message
        self.logs += msg + '\n'
        print(msg)

    def log_error(self, message):
        winsound.PlaySound('SystemHand', winsound.SND_ALIAS)
        msg = f'[ERROR] {message}'
        self.log(msg)
        print(msg)
