import configparser
import threading
import os

class Config:
    def __init__(self, location):
        self.location = location
        self.config = configparser.ConfigParser()
        self.lock = threading.Lock()
        self._last_modified = 0
        self.reload()

    def reload(self):
        # with self.lock:
        self.config.read(self.location)
        self._last_modified = os.path.getmtime(self.location)

    def _write(self):
        # with self.lock:
        with open(self.location, 'w') as i:
            self.config.write(i)
        self._last_modified = os.path.getmtime(self.location)

    def set(self, section: str, key: str, value):
        # with self.lock:
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, key, str(value))
        self._write()

    def get(self, section: str, key: str) -> str:
        # with self.lock:
        if self._last_modified < os.path.getmtime(self.location):
            self.reload()
        return self.config.get(section, key)

    def toggle(self, section: str, key: str):
        print('Toggling', section, key)
        # with self.lock:
        if not self.config.has_section(section):
            self.config.add_section(section)
        current = self.config.getboolean(section, key)
        self.config.set(section, key, str(not current))
        self._write()
        print('Toggled', section, key, 'to', not current)