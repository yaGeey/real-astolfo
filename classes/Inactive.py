import subprocess as sp
import threading
import time

import win32api


class Inactive:
    def __init__(self, config, bus):
        self.bus = bus
        self.config = config

        self.brightness_temp = None
        self.is_in_deep_sleep = False

        threading.Thread(target=self.inactive).start()

    def inactive(self):
        while self.config.get('STATES', 'inactive'):
            # res = obs.execute(obswebsocket.requests.GetReplayBufferStatus())
            output = sp.check_output(['powercfg', '-getactivescheme'], creationflags=sp.DETACHED_PROCESS)
            lastInputTimeDelta = win32api.GetTickCount() - win32api.GetLastInputInfo()

            if lastInputTimeDelta > int(self.config.get('SETTINGS', 'inactiveMin')) * 60000:
                # if lastInputTimeDelta > 1000:
                # --- INACTIVE ---
                if not output.startswith(b'Power Scheme GUID: 30edd295'):
                    sp.call('powercfg /s 30edd295-bb03-4f04-9ca5-1d6625c371f5', creationflags=sp.CREATE_NO_WINDOW)
                    self.bus.emit('inactive-start')

            else:
                # --- ACTIVE ---
                if not output.startswith(b'Power Scheme GUID: 04d7a134'):
                    sp.call('powercfg /s 04d7a134-5010-4cd2-ac8e-0bd74104d4fa', creationflags=sp.CREATE_NO_WINDOW)
                    self.bus.emit('inactive-end')
                    # if not brightness.update()[0]: brightness.set(self.brightness_temp[0], 0)

            time.sleep(1)
