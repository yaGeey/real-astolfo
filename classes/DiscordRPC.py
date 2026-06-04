import os
import threading
import time

import psutil
from dotenv import load_dotenv
from pypresence import Presence

load_dotenv()


class DiscordRPC:
    def __init__(self, config, bus):
        self.config = config
        self.bus = bus

        self.inactive_since = None
        self.current_lesson_name = None

        self.connected = False
        self.description = 'basic'

        self.rpc = Presence(os.getenv('DISCORD_PRESENSE'), pipe=0)

        threading.Thread(target=self.update_rpc, daemon=True).start()
        threading.Thread(target=self.get_all_proc, daemon=True).start()

    def update_rpc(self):
        while True:
            if self.config.get('STATES', 'discord'):
                if not self.connected:
                    try:
                        self.rpc.connect()
                        self.connected = True
                    except:
                        self.bus.emit('log-error', "[Discord] Не вдалось під'єднатись до бота")

                # Basic data
                data = {
                    'buttons': [
                        {
                            'label': 'літералі мі🥀',
                            'url': 'https://i.imgur.com/r0ff8xf.mp4',
                        }
                    ]
                }

                def activeness():
                    nonlocal data
                    if self.inactive_since:
                        data['state'] = f'Я реально АФК з {self.inactive_since}'
                        data['large_image'] = 'https://media1.tenor.com/m/_qrM4wvVu28AAAAd/anime-girl.gif'

                    if not self.inactive_since:
                        data['state'] = 'шота дєлаю'
                        data['large_image'] = 'https://media1.tenor.com/m/ZI3TMFCULq0AAAAC/uwu-anime.gif'

                # Description
                if self.description == 'zoom':
                    activeness()
                    data['details'] = 'ААААА ААА Я НА ПАРІ'
                    data['large_image'] = 'https://media1.tenor.com/m/HoSYZR66fsQAAAAC/senko-light.gif'
                    data['large_text'] = self.current_lesson_name

                if self.description == 'basic':
                    activeness()
                    data['details'] = 'я хочу ласки'
                    data['large_text'] = None

                try:
                    self.rpc.update(**data)
                except Exception:
                    pass
            else:
                data = {}
                if self.connected:
                    self.rpc.close()
                    self.connected = False

            time.sleep(5)

    def get_all_proc(self):
        while True:
            self.description = (
                'zoom' if 'zoom.exe' in [proc.name().lower() for proc in psutil.process_iter()] else 'basic'
            )
            time.sleep(30)
