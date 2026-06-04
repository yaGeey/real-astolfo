import customtkinter as ctk

class Window(ctk.CTk):
    def __init__(self, config, bus):
        self.config = config
        self.bus = bus
        super().__init__()
        self.geometry('700x500')
        self.minsize(500,350)
        self.title('Астольфік')
        self.iconbitmap('public/astlofo4.ico')
        self.focus_force()  # set focus
        self.protocol("WM_DELETE_WINDOW", self.close) # WM_TAKE_FOCUS (получение фокуса), WM_DELETE_WINDOW (удаление окна)

        self.rowconfigure((0, 1, 2, 3, 4), weight=1, uniform='a')
        self.columnconfigure((0, 1, 2, 3, 4), weight=1, uniform='a')

        # widgets
        self.font = ctk.CTkFont('Helvetica', 20)
        self.text_field().grid(row=0, column=0, rowspan=4, columnspan=4, sticky='nsew')
        self.check_buttons_frame().grid(row=4, column=0, columnspan=4, sticky='nsew', padx=10, pady=10)
        self.week_select_frame().grid(row=0, column=4, rowspan=2, sticky='nsew', padx=10, pady=10)

        self.bind('<Escape>', lambda event: self.close())

    # calling window
    def start(self, text):
        self.textbox.insert('end', text)
        self.mainloop()

    def close(self):
        self.bus.emit('window_closed', None)
        # systray.window = None
        self.destroy()

    def text_field(self):
        self.textbox = ctk.CTkTextbox(self)
        # commands
        self.textbox.bind('<Return>', # Enter pressed
                          lambda event: self.textbox.delete(0.0, 'end') if 'cls' in self.textbox.get(0.0,'end') else None)
        self.textbox.bind('<Return>',
                          lambda event: self.bus.emit('force_start_last_lesson', None)
                          if 'links last' in self.textbox.get(0.0, 'end') else None)
        return self.textbox

    def check_buttons_frame(self):
        frame = ctk.CTkFrame(self)
        frame.rowconfigure((0,1), weight=1, uniform='b')
        frame.columnconfigure((0,1,2), weight=1, uniform='b')

        discord_var = ctk.BooleanVar(value=self.config.get('STATES', 'discord'))
        ctk.CTkCheckBox(frame, text='Discord RPC', variable=discord_var, command=lambda: self.config.toggle('STATES', 'discord')) \
            .grid(row=0, column=0, sticky='w', padx=10, pady=5)

        inactive_var = ctk.BooleanVar(value=self.config.get('STATES', 'inactive'))
        ctk.CTkCheckBox(frame, text='Inactive', variable=inactive_var, command=lambda: self.config.toggle('STATES', 'inactive')) \
            .grid(row=1, column=0, sticky='w', padx=10, pady=5)

        recognition_var = ctk.BooleanVar(value=self.config.get('STATES', 'recognition'))
        ctk.CTkCheckBox(frame, text='Speech Recognition', variable=recognition_var, command=lambda: self.config.toggle('STATES', 'recognition')) \
            .grid(row=0, column=1, sticky='w', padx=10, pady=5)

        links_var = ctk.BooleanVar(value=self.config.get('STATES', 'links'))
        ctk.CTkCheckBox(frame, text='Links', variable=links_var, command=lambda: self.config.toggle('STATES', 'links')) \
            .grid(row=1, column=1, sticky='w', padx=10, pady=5)

        obs_var = ctk.BooleanVar(value=self.config.get('STATES', 'obs'))
        ctk.CTkCheckBox(frame, text='OBS', variable=obs_var, command=lambda: self.config.toggle('STATES', 'obs')) \
            .grid(row=0, column=2, sticky='w', padx=10, pady=5)

        return frame

    def week_select_frame(self):
        frame = ctk.CTkFrame(self)
        ctk.CTkLabel(frame, text=f"Тиждень {self.config.get('SETTINGS', 'week')}", font=self.font).pack(expand=True, padx=10, pady=5)
        return frame