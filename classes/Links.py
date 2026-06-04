import json
import os
import threading
import time
import webbrowser
import winsound
from datetime import datetime, timedelta

import psutil


class Links:
    def __init__(self, config, bus, obs_client_factory=None):
        self.bus = bus
        self.config = config

        self.is_inactive = False

        self.les_links = self.fetch_links_json()
        self.current_lesson = None
        self.obs_client = None
        self.obs_temp_client = obs_client_factory

        self.schedule = [
            [
                [[], ['РІС', 'Л'], ['NLP', 'Л'], ['ХС', 'Л']],
                [
                    ['БІС', 'Л'],
                    ['ТР', 'Л'],
                    ['ІМУС', 'Л'],
                ],
                [[], [], ['Англ', 'П'], ['ІМУС', 'П']],
                [[], ['ХС', 'П'], [], ['NLP', 'П']],
                [[]],
                [[]],
                [[]],
            ],
            [
                [[], ['РІС', 'Л'], ['NLP', 'Л'], ['ХС', 'Л']],
                [
                    ['БІС', 'Л'],
                    ['ТР', 'Л'],
                    ['ІМУС', 'Л'],
                ],
                [[], ['БІС', 'П'], ['Англ', 'П'], ['ІМУС', 'П']],
                [[], ['РІС', 'П']],
                [[]],
                [[]],
                [[]],
            ],
        ]
        self.les_start = ['8:29', '10:24', '12:19', '14:14', '16:09', '18:29']
        self.les_end = ['10:05', '12:00', '13:55', '15:50', '17:45', '19:55']

        self.calculate_week('2025-01-01')
        threading.Thread(target=self.links, daemon=True).start()

    def calculate_week(self, date_string):
        start_date = datetime.strptime(date_string, '%Y-%m-%d').date()
        if datetime.now().date() == start_date:
            self.config.set('SETTINGS', 'week', 1)
        else:
            delta = datetime.now().date() - start_date
            week = (delta.days // 7) % 2 + 1
            self.config.set('SETTINGS', 'week', week)

    def start_lesson(self, name, les_type, force_start=False, recording=False):
        self.current_lesson = f'{name} {les_type}'
        self.bus.emit('current-lesson-change', f'{name} {les_type}')

        if not self.les_links[name][les_type].get('winPrefered', False) and not force_start:
            self.bus.emit('log', f'[Links] Lesson {self.current_lesson} is not winPrefered')
            return False
        url = self.les_links[name][les_type]['link']
        if not url:
            self.bus.emit('log_error', f'[Links] No link found for {self.current_lesson}')
            return False
        webbrowser.open(url)

        # Notifications
        winsound.PlaySound('*', winsound.SND_ALIAS)

        if recording:
            self.bus.emit('log', '[Links] Starting recording in OBS')
            if not self.obs_client:
                self.obs_client = self.obs_temp_client()
            self.obs_client.execute(lambda: self.obs_client.client.set_current_profile('Zoom'))
            self.obs_client.execute(lambda: self.obs_client.client.set_current_program_scene('Zoom'))
            self.obs_client.execute(lambda: self.obs_client.client.start_record())

    def links(self):
        while self.config.get('STATES', 'links'):
            timenow = datetime.now().strftime('%H:%M')
            day = datetime.today().weekday()

            week = int(self.config.get('SETTINGS', 'week')) - 1
            for i, lesson in enumerate(self.schedule[week][day]):
                # Lesson start
                if lesson and timenow == self.les_start[i]:
                    name, les_type = lesson
                    if self.les_links[name][les_type]:
                        self.bus.emit('log', f'[Links] Starting lesson {name} {les_type}')
                        self.start_lesson(name, les_type)
                    else:
                        self.bus.emit('send-tg-message', f'❗❗ Немає посилання на {name} {les_type}\n ')

                        # Retry every 30 seconds for 5 minutes if no link is found
                        while True:
                            dt = datetime.strptime(self.les_start[i], '%H:%M')
                            if datetime.now() < dt + timedelta(minutes=5):
                                self.les_links = self.fetch_links_json()
                                time.sleep(30)
                                if self.les_links[name][les_type]:
                                    self.start_lesson(name, les_type)
                                    break
                            else:
                                break

                # Lesson end
                if timenow == self.les_end[i] and self.is_inactive:
                    self.bus.emit('log', f'[Links] Ending lesson {self.current_lesson}')
                    self.bus.emit('current-lesson-change', None)
                    self.current_lesson = None
                    self.obs_client.execute(lambda: self.obs_client.client.stop_record())

                    # Close zoom if inactive
                    if self.config.get('SETTINGS', 'inactive'):
                        try:
                            if 'zoom.exe' in [proc.name().lower() for proc in psutil.process_iter()]:
                                os.system('taskkill /f /im zoom.exe')
                        except Exception as e:
                            self.bus.emit('log_error', f'[Links] {e}')

            time.sleep(60)

    def fetch_links_json(self):
        with open(r'links.json', 'r', encoding='utf-8') as f:
            return json.load(f)

    def force_start_last_lesson(self, recording=False):
        day = datetime.today().weekday()
        week = int(self.config.get('SETTINGS', 'week', True)) - 1
        self.bus.emit('log', '[Links] Force starting last lesson')

        for i in range(len(self.schedule[week][day]) - 1, -1, -1):
            lesson = self.schedule[week][day][i]
            if lesson and datetime.now().time() >= datetime.strptime(self.les_start[i], '%H:%M').time():
                self.start_lesson(lesson[0], lesson[1], True, recording)
                break

    def add_minutes(self, time_str: str, minutes: int) -> str:
        t = datetime.strptime(time_str, '%H:%M')
        t_new = t + timedelta(minutes=minutes)
        return t_new.strftime('%H:%M')
