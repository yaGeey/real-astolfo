import asyncio
import configparser
import json
import os
import shutil
import subprocess as sp
import threading
import time
import webbrowser
import winsound
from datetime import datetime, timedelta
from io import BytesIO
from typing import cast

import customtkinter as ctk
import keyboard as kb
import obsws_python as obs
import psutil
import requests
import screen_brightness_control as sbc
import telegram
import win32api
import win32gui
import win32process
import winclip32
from comtypes import CoInitialize, CoUninitialize
from infi.systray import SysTrayIcon
from mss.windows import MSS as mss
from PIL import Image
from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
from pynput import keyboard
from pynput.keyboard import Controller, Key
from pypresence import Presence
from telegram import Bot, BotCommand, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes


def log(message):
    time_str = datetime.now().strftime('%H:%M:%S')
    if 'systray' in globals() and systray is not None:
        systray.logs += time_str + ' ' + message + '\n'
    print(time_str + ' ' + message)


def log_error(message):
    winsound.PlaySound('SystemHand', winsound.SND_ALIAS)
    error_message = f'[ERROR] {message}'
    log(error_message)


## ------- CLASSES -------
class Config:
    def __init__(self, location):
        self.location = location
        self.config = configparser.ConfigParser()
        self.lock = threading.Lock()  # Lock for thread safety
        self._last_modified = 0
        self._update()

    def _update(self):
        # Check if file was modified externally to avoid unnecessary disk reads
        try:
            current_mtime = os.path.getmtime(self.location)
            if current_mtime > self._last_modified:
                with self.lock:
                    self.config.read(self.location)
                    self._last_modified = current_mtime
        except OSError:
            pass

    def _write(self):
        with self.lock:
            with open(self.location, 'w') as i:
                self.config.write(i)
            self._last_modified = os.path.getmtime(self.location)

    def get(self, section, key, value=False):
        self._update()
        with self.lock:
            if value:
                return self.config[section].get(key)
            return self.config[section].getboolean(key)

    def set(self, section, key, value):
        with self.lock:
            self.config.set(section, key, str(value))
        self._write()

    def toggle(self, section, key):
        self._update()
        with self.lock:
            new_state = str(int(not self.config[section].getboolean(key)))
            self.config.set(section, key, new_state)
        self._write()


class Window(ctk.CTk):
    def __init__(self, *args):
        super().__init__()
        self.geometry('700x500')
        self.minsize(500, 350)
        self.title('Астольфік')
        self.iconbitmap('public/astlofo4.ico')
        self.focus_force()  # Set focus
        self.protocol('WM_DELETE_WINDOW', self.close)

        self.rowconfigure((0, 1, 2, 3, 4), weight=1, uniform='a')
        self.columnconfigure((0, 1, 2, 3, 4), weight=1, uniform='a')

        # Widgets
        self.font = ctk.CTkFont('Helvetica', 20)
        self.text_field().grid(row=0, column=0, rowspan=4, columnspan=4, sticky='nsew')
        self.check_buttons_frame().grid(row=4, column=0, columnspan=4, sticky='nsew', padx=10, pady=10)
        self.week_select_frame().grid(row=0, column=4, rowspan=2, sticky='nsew', padx=10, pady=10)

        self.bind('<Escape>', lambda event: self.close())

    # Calling window
    def start(self, text):
        self.textbox.insert('end', text)
        self.mainloop()

    def close(self):
        systray.window = None
        self.destroy()

    def text_field(self):
        self.textbox = ctk.CTkTextbox(self)
        # Commands
        self.textbox.bind(
            '<Return>',  # Enter pressed
            lambda event: self.textbox.delete(0.0, 'end') if 'cls' in self.textbox.get(0.0, 'end') else None,
        )
        self.textbox.bind(
            '<Return>',
            lambda event: links.force_start_last_lesson() if 'links last' in self.textbox.get(0.0, 'end') else None,
        )
        return self.textbox

    def check_buttons_frame(self):
        frame = ctk.CTkFrame(self)
        frame.rowconfigure((0, 1), weight=1, uniform='b')
        frame.columnconfigure((0, 1, 2), weight=1, uniform='b')

        discord_var = ctk.BooleanVar(value=config.get('STATES', 'discord'))
        ctk.CTkCheckBox(
            frame,
            text='Discord RPC',
            variable=discord_var,
            command=lambda: config.toggle('STATES', 'discord'),
        ).grid(row=0, column=0, sticky='w', padx=10, pady=5)

        inactive_var = ctk.BooleanVar(value=config.get('STATES', 'inactive'))
        ctk.CTkCheckBox(
            frame,
            text='Inactive',
            variable=inactive_var,
            command=lambda: config.toggle('STATES', 'inactive'),
        ).grid(row=1, column=0, sticky='w', padx=10, pady=5)

        recognition_var = ctk.BooleanVar(value=config.get('STATES', 'recognition'))
        ctk.CTkCheckBox(
            frame,
            text='Speech Recognition',
            variable=recognition_var,
            command=lambda: config.toggle('STATES', 'recognition'),
        ).grid(row=0, column=1, sticky='w', padx=10, pady=5)

        links_var = ctk.BooleanVar(value=config.get('STATES', 'links'))
        ctk.CTkCheckBox(
            frame,
            text='Links',
            variable=links_var,
            command=lambda: config.toggle('STATES', 'links'),
        ).grid(row=1, column=1, sticky='w', padx=10, pady=5)

        obs_var = ctk.BooleanVar(value=config.get('STATES', 'obs'))
        ctk.CTkCheckBox(
            frame,
            text='OBS',
            variable=obs_var,
            command=lambda: config.toggle('STATES', 'obs'),
        ).grid(row=0, column=2, sticky='w', padx=10, pady=5)

        return frame

    def week_select_frame(self):
        frame = ctk.CTkFrame(self)
        ctk.CTkLabel(frame, text=f'Тиждень {config.get("DEFAULT", "week", True)}', font=self.font).pack(
            expand=True, padx=10, pady=5
        )
        return frame


class SysTray(SysTrayIcon):
    def __init__(self, obs_client):
        self.obs_client = obs_client
        self.window = None
        self.logs = ''
        self.hint_window = None
        self.hover_text = f'Тиждень {config.get("DEFAULT", "week", True)}, абоба'

        menu = (
            ('Меню', None, self.create_window),
            (
                'Відкрити cwd',
                None,
                lambda systray: os.startfile(r'C:\Users\LEGION\PycharmProjects\astolfo'),
            ),
            ('Останній урок', None, lambda systray: links.force_start_last_lesson()),
            (
                'Відкрити config.ini',
                None,
                lambda systray: os.startfile(config.location),
            ),
            (
                'Відкрити controls.txt',
                None,
                lambda systray: os.startfile(r'public/controls.txt'),
            ),
            (
                'Перемкнути яскравість',
                'public/brightness.ico',
                lambda systray: brightness.toggle(mon=1),
            ),
        )
        super().__init__(
            'public/astolfo.ico',
            self.hover_text,
            menu,
            on_quit=self.close,
            default_menu_index=0,
        )
        self.start()

    def close(self, systray):
        # Safely close OBS
        if self.obs_client:
            c: int = self.obs_client.client
            self.obs_client.execute(lambda: self.obs_client.client.stop_record())
            time.sleep(5)
            self.obs_client.execute(lambda: self.obs_client.client.exit())
        # Close self
        for proc in psutil.process_iter():
            if 'Астольфік' in proc.name():
                proc.kill()

    def create_window(self, systray):
        if self.window is None:
            self.window = Window()
            self.window.start(self.logs)
        else:
            self.window.destroy()
            self.window = None


class MonitorBrightness:
    def __init__(self):
        self.monitors = sbc.list_monitors()
        self.values = self.update()

    def set(self, value, mon=-1):
        monitors = sbc.list_monitors()
        if mon == -1:
            for i in range(len(monitors)):
                sbc.set_brightness(value, display=i)
            self.values = sbc.get_brightness()
        else:
            sbc.set_brightness(value, display=mon)
            self.values[mon] = value

    def update(self):
        self.values = sbc.get_brightness()
        return self.values

    def toggle(self, mon):
        new_value = 0 if bool(self.values[mon]) else 100
        self.values[mon] = new_value
        sbc.set_brightness(new_value, display=mon)


class MuteSpotify:
    def __init__(self):
        self.state = True
        self.kb = Controller()
        threading.Thread(target=self.shortcuts, daemon=True).start()

    def shortcuts(self):
        with keyboard.GlobalHotKeys(
            {
                '<alt_gr>+-': lambda: self.mute('Spotify.exe'),
                '<alt>+-': lambda: self.mute(self.get_active_window()),
                '<alt_gr>+8': lambda: self.kb.press(Key.media_previous),
                '<alt_gr>+9': lambda: self.kb.press(Key.media_play_pause),
                '<alt_gr>+0': lambda: self.kb.press(Key.media_next),
            }
        ) as h:
            h.join()

    def mute(self, proc_name: str):
        CoInitialize()
        for session in AudioUtilities.GetAllSessions():
            volume = session._ctl.QueryInterface(ISimpleAudioVolume)
            if session.Process and session.Process.name() == proc_name:
                if self.state:
                    volume.SetMute(1, None)
                    self.state = False
                else:
                    volume.SetMute(0, None)
                    self.state = True
        CoUninitialize()

    def get_active_window(self):
        _, process_id = win32process.GetWindowThreadProcessId(win32gui.GetForegroundWindow())
        process = psutil.Process(process_id)
        return process.name()


class DiscordRPC:
    def __init__(self):
        self.connected = False
        self.description = 'basic'

        self.rpc = Presence('1195490094065397770', pipe=0)

        threading.Thread(target=self.update_rpc, daemon=True).start()
        threading.Thread(target=self.get_all_proc, daemon=True).start()

    def update_rpc(self):
        while True:
            if config.get('STATES', 'discord'):
                if not self.connected:
                    try:
                        self.rpc.connect()
                        self.connected = True
                    except:
                        log_error("[Discord] Не вдалось під'єднатись до бота")

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
                    if inactive.since:
                        data['state'] = f'Я реально АФК з {inactive.since}'
                        data['large_image'] = 'https://media1.tenor.com/m/_qrM4wvVu28AAAAd/anime-girl.gif'

                    if not inactive.since:
                        data['state'] = 'шота дєлаю'
                        data['large_image'] = 'https://media1.tenor.com/m/ZI3TMFCULq0AAAAC/uwu-anime.gif'

                # Description
                if self.description == 'zoom':
                    activeness()
                    data['details'] = 'ААААА ААА Я НА ПАРІ'
                    data['large_image'] = 'https://media1.tenor.com/m/HoSYZR66fsQAAAAC/senko-light.gif'
                    data['large_text'] = links.current_lesson

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


class OtherHotkeys:
    def __init__(self):
        kb.add_hotkey('print screen', self.copy_mon_screen)
        kb.add_hotkey('ctrl+win+print screen', self.save_one_mon_screen)
        kb.add_hotkey('ctrl+print screen', lambda: self.copy_mon_screen(all=True))

    def save_one_mon_screen(self):
        log('[Screen] Save one monitor screen')
        try:
            with mss() as sct:
                im = Image.open(sct.shot(mon=1))
                winsound.PlaySound('SystemAsterisk', winsound.SND_ALIAS)

                img_count = [
                    int(name.split(' ')[-1].split('.')[0][1:-1])
                    for name in os.listdir('C:/Users\LEGION\Pictures\Screenshots')
                    if name.split(' ')[-1].split('.')[0][1:-1].isdigit()
                ]
                im.save(f'C:/Users\LEGION\Pictures\Screenshots/Знімок екрана ({max(img_count) + 1}).png')
        except Exception as e:
            log_error('[Screen]' + str(e))

    def copy_mon_screen(self, all=False):
        log('[Screen] Copy monitor screen')
        try:
            with mss() as sct:
                im = Image.open(sct.shot(mon=-1 if all else 1))

                output = BytesIO()
                im.convert('RGB').save(output, 'DIB')
                data = output.getvalue()
                output.close()

                winclip32.set_clipboard_data(winclip32.BITMAPINFO_STD_STRUCTURE, data)
        except Exception as e:
            log_error('[Screen]' + str(e))


class Process:
    def __init__(self, process_name, path=None, cwd=None):
        self.process_name = process_name
        self.path = path
        self.cwd = cwd
        self.start()

    def check(self):
        pname = self.process_name.lower()
        for proc in psutil.process_iter(['name', 'cmdline']):
            try:
                name = (proc.info.get('name') or '').lower()
                if pname == name:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    def start(self, wait_seconds=60):
        if self.check():
            return True
        if not self.path:
            self.path = shutil.which(self.process_name)
            if not self.path:
                log_error(f'Не вдалося знайти шлях до {self.process_name}.')
                return False
        try:
            log('Запускаю:' + self.path)
            sp.Popen(
                [self.path],
                cwd=self.cwd,
                stdout=sp.DEVNULL,
                stderr=sp.DEVNULL,
                close_fds=True,
                creationflags=sp.CREATE_NO_WINDOW,
            )
        except Exception as e:
            log_error(f'Failed to start {self.process_name}: {e}')
            return False

        # Wait for the process to appear
        deadline = time.time() + wait_seconds
        while time.time() < deadline:
            if self.check():
                log(f'{self.process_name} started successfully.')
                return True
            time.sleep(1)

        log_error(f'Timeout waiting for {self.process_name} to start exceeded.')
        return False


class OBS:
    def __init__(self):
        self.connected = False
        self.client = None
        self.process = Process(
            'obs64.exe',
            r'D:\obs-studio\bin\64bit\obs64.exe',
            r'D:\obs-studio\bin\64bit',
        )
        self.lock = threading.Lock()

        threading.Thread(target=self._ensure_connected, daemon=True).start()

    def _ensure_connected(self):
        while True:
            # Use lock to guarantee atomicity
            with self.lock:
                if not self.connected:
                    try:
                        self.process.start()
                        self.client = obs.ReqClient(host='192.168.0.10', port=4455)
                        response = self.client.get_version()
                        log(f'[OBS] Connected to OBS v{response.obs_version}')
                        self.connected = True
                    except Exception as e:
                        self.connected = False
                        self.client = None
                        log_error(f'[OBS] failed to connect to OBS WebSocket: {e}')
            time.sleep(5)

    def execute(self, request):
        if not config.get('STATES', 'obs'):
            return

        with self.lock:
            if self.connected:
                try:
                    return request()
                except Exception as e:
                    log_error(f'[OBS] Execute error:, {e}')
                    self.connected = False
                    self.client = None
            else:
                log('[OBS] not connected – skipping execute')


class Inactive:
    def __init__(self):
        self.since = None
        self.dusk_time, self.dawn_time = self.get_dusk_time()
        self.brightness_temp = None
        self.is_in_deep_sleep = False
        # Set as daemon to allow program to exit properly
        threading.Thread(target=self.inactive, daemon=True).start()

    def get_dusk_time(self):
        try:
            # Set timeout in seconds to prevent thread hanging
            res = requests.get('https://api.sunrisesunset.io/json?lat=50.4501&lng=30.5234', timeout=5)
            dusk_str = res.json()['results']['dusk']
            dusk_time = datetime.strptime(dusk_str, '%I:%M:%S %p')
            dawn_str = res.json()['results']['dawn']
            dawn_time = datetime.strptime(dawn_str, '%I:%M:%S %p')
            return [dusk_time.time(), dawn_time.time()]
        except Exception:
            # Fallback times
            return [
                datetime.strptime('20:00', '%H:%M').time(),
                datetime.strptime('06:00', '%H:%M').time(),
            ]

    def inactive(self):
        while config.get('STATES', 'inactive'):
            try:
                # Execute checks inside try block to catch post-sleep exceptions
                output = sp.check_output(['powercfg', '-getactivescheme'], creationflags=sp.DETACHED_PROCESS)
                lastInputTimeDelta = win32api.GetTickCount() - win32api.GetLastInputInfo()

                if lastInputTimeDelta > int(config.get('STATES', 'inactiveMin', True)) * 60000:
                    # --- INACTIVE ---
                    if not output.startswith(b'Power Scheme GUID: 30edd295'):
                        sp.call(
                            'powercfg /s 30edd295-bb03-4f04-9ca5-1d6625c371f5',
                            creationflags=sp.CREATE_NO_WINDOW,
                        )
                        systray.update(icon='public/astolfo_sleep.ico')
                        log('[Inactive] "Power Saving" scheme')
                    if not self.since:
                        self.since = datetime.now().strftime('%H:%M')

                    # Deep Sleep
                    if lastInputTimeDelta > 10 * 60000:
                        if not self.is_in_deep_sleep:
                            cur_b = brightness.update()
                            if cur_b[0] and (
                                datetime.now().time() > self.dusk_time or datetime.now().time() < self.dawn_time
                            ):
                                self.brightness_temp = cur_b
                                brightness.set(0)
                                self.is_in_deep_sleep = True
                                log('[Inactive] Monitors dimmed')

                else:
                    # --- ACTIVE ---
                    if not output.startswith(b'Power Scheme GUID: 04d7a134'):
                        # Restore brightness
                        if self.is_in_deep_sleep:
                            try:
                                if self.brightness_temp is not None:
                                    brightness.set(self.brightness_temp[0], 0)
                                    self.is_in_deep_sleep = False
                                    self.brightness_temp = None
                                    log('[Active] Brightness restored')
                            except Exception as e:
                                log_error(f'[Active] Monitor not ready yet: {e}')

                        sp.call(
                            'powercfg /s 04d7a134-5010-4cd2-ac8e-0bd74104d4fa',
                            creationflags=sp.CREATE_NO_WINDOW,
                        )
                        systray.update(icon='public/astolfo.ico')
                        log('[Active] "Balanced" scheme')

                    if self.since:
                        self.since = None

            except Exception as e:
                # Log WMI and subprocess errors after waking up
                log_error(f'[Inactive] Loop error: {e}')

            time.sleep(1)


class Links:
    def __init__(self, obs_client_factory):
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
            config.set('DEFAULT', 'week', 1)
        else:
            delta = datetime.now().date() - start_date
            week = (delta.days // 7) % 2 + 1
            config.set('DEFAULT', 'week', week)

    def start_lesson(self, name, les_type, force_start=False, recording=False):
        self.current_lesson = f'{name} {les_type}'
        if not self.les_links[name][les_type].get('winPrefered', False) and not force_start:
            log(f'[Links] Lesson {self.current_lesson} is not winPrefered')
            return False
        url = self.les_links[name][les_type]['link']
        if not url:
            log(f'❗❗ Немає посилання на {self.current_lesson}\n ')
            return False
        webbrowser.open(url)

        # Notifications
        winsound.PlaySound('*', winsound.SND_ALIAS)

        if recording:
            log('[Links] Starting recording in OBS')
            if not self.obs_client:
                self.obs_client = self.obs_temp_client()
            self.obs_client.execute(lambda: self.obs_client.client.set_current_profile('Zoom'))
            self.obs_client.execute(lambda: self.obs_client.client.set_current_program_scene('Zoom'))
            self.obs_client.execute(lambda: self.obs_client.client.start_record())

    def links(self):
        while config.get('STATES', 'links'):
            timenow = datetime.now().strftime('%H:%M')
            day = datetime.today().weekday()

            week = int(config.get('DEFAULT', 'week', True)) - 1
            for i, lesson in enumerate(self.schedule[week][day]):
                # Lesson start
                if lesson and timenow == self.les_start[i]:
                    name, les_type = lesson
                    if self.les_links[name][les_type]:
                        log(f'{timenow} - lesson start')
                        self.start_lesson(name, les_type)
                    else:
                        tg.send_message(f'❗❗ Немає посилання на {name} {les_type}\n ')

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
                if timenow == self.les_end[i] and inactive.since:
                    log(f'{timenow} - lesson end')
                    self.current_lesson = None
                    self.obs_client.execute(lambda: self.obs_client.client.stop_record())

                    # Close zoom if inactive
                    if config.get('STATES', 'inactive'):
                        try:
                            if 'zoom.exe' in [proc.name().lower() for proc in psutil.process_iter()]:
                                os.system('taskkill /f /im zoom.exe')
                        except Exception as e:
                            log_error(f'[Links] {e}')

            time.sleep(60)

    def fetch_links_json(self):
        with open(r'C:\Users\LEGION\shared\links.json', 'r', encoding='utf-8') as f:
            return json.load(f)

    def force_start_last_lesson(self, recording=False):
        day = datetime.today().weekday()
        week = int(config.get('DEFAULT', 'week', True)) - 1
        log('[Links] Force starting last lesson')

        for i in range(len(self.schedule[week][day]) - 1, -1, -1):
            lesson = self.schedule[week][day][i]
            if lesson and datetime.now().time() >= datetime.strptime(self.les_start[i], '%H:%M').time():
                self.start_lesson(lesson[0], lesson[1], True, recording)
                break

    def add_minutes(self, time_str: str, minutes: int) -> str:
        t = datetime.strptime(time_str, '%H:%M')
        t_new = t + timedelta(minutes=minutes)
        return t_new.strftime('%H:%M')


class TGBot:
    def __init__(self):
        TOKEN = '6847368589:AAEoz4TdpACktNTyP1gzqlyHi3fJ6qw4o84'
        self.application = ApplicationBuilder().token(TOKEN).build()
        self.bot = cast(Bot, self.application.bot)

        force_start_handler = CommandHandler('force_start', self.force_start)
        self.application.add_handler(force_start_handler)

        self.application.post_init = self.setup_bot
        self.application.run_polling()

    async def setup_bot(self, app):
        await self.bot.set_my_commands(
            [
                BotCommand('force_start', 'ластовенькє урокє'),
            ]
        )

    async def force_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) and (context.args[0] not in ['l', 'w'] or context.args[1] not in ['0', '1']):
            await update.message.reply_text(
                'Usage: /force_start <device(l/w)> <recording(0/1)>\nDefault: linux with no recording'
            )
            return

        recording = bool(int(context.args[1])) if len(context.args) else False
        links.force_start_last_lesson(recording)
        await update.message.reply_text(
            f'Force starting lesson on a <b>Windows {"w recording 🎥" if recording else ""}</b>',
            parse_mode=telegram.constants.ParseMode.HTML,
        )

    def send_message(self, text):
        asyncio.run(self.bot.sendMessage('1738939513', text, parse_mode=telegram.constants.ParseMode.HTML))


try:
    config = Config('config.ini')
    brightness = MonitorBrightness()
    links = Links(OBS)
    systray = SysTray(links.obs_client)
    inactive = Inactive()
    MuteSpotify()
    discord_rpc = DiscordRPC()
    OtherHotkeys()
    tg = TGBot()
except Exception as e:
    log_error(f'[MAIN] {e}')
