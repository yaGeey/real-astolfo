import screen_brightness_control as sbc
class Brightness:
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