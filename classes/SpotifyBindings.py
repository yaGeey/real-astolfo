import threading

import psutil
import win32gui
import win32process
from comtypes import CoInitialize, CoUninitialize
from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
from pynput import keyboard
from pynput.keyboard import Controller, Key


class SpotifyBindings:
    def __init__(self):
        self.state = True
        self.kb = Controller()
        threading.Thread(target=self.shortcuts, daemon=True).start()

    def shortcuts(self):
        with keyboard.GlobalHotKeys(
            {
                '<alt_gr>+-': lambda: self.mute('Spotify.exe'),
                # '<alt>+-': lambda: self.mute(self.get_active_window()),
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
