from tkinter import (Tk, Canvas, PhotoImage, Menu, filedialog, Toplevel,
    Checkbutton, IntVar, Button)
import threading
import queue
import time
import os
from core import Core

class Emulator:
    #System
    core = None
    core_thread = None
    display_queue = None
    running = False

    #UI
    tk = None
    file_menu = None
    canvas = None
    img = None
    settings_window = None
    quirk_checkbuttons = None

    #Settings
    scale = None
    refresh_rate = None
    mode = "CHIP-8"
    quirks = {
        'vf_reset': True,
        'memory': True,
        'display_wait': True,
        'clipping': True,
        'shifting': False,
        'jumping': False
    }

    #TODO: support different colors
    def __init__(self, w=64, h=32, scale:int=1, refresh_rate=60, file=None):
        #Initialize display and UI
        self.scale = scale
        self.refresh_rate = refresh_rate
        w *= self.scale
        h *= self.scale
        self.tk = Tk()
        self.tk.title("Cheep8")
        self.tk.protocol("WM_DELETE_WINDOW", self.quit)
        win_w = max(round(w*1.2), 250) #leave enough room in the title bar to show the title and be draggable
        win_h = round(h*1.2)
        self.tk.geometry(f"{win_w}x{win_h}")
        self.canvas = Canvas(self.tk, width=w, height=h, highlightthickness=0)
        self.canvas.place(relx=.5, rely=.5, anchor="c")
        self.img = PhotoImage(width=w, height=h)
        self.canvas.create_image((w/2, h/2), image=self.img, state="normal")
        self.display_queue = queue.Queue(1)
        self.create_ui()
        self.tk.update()
        
        if file is not None:
            self.start_core(file)
        self.tk.mainloop()

    #UI

    def create_ui(self):
        menu_bar = Menu(self.tk)
        self.file_menu = Menu(menu_bar, tearoff=False)
        self.file_menu.add_command(label="Open", command=self.select_rom)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Quit", command=self.quit)
        menu_bar.add_cascade(label="File", menu=self.file_menu)

        settings_menu = Menu(menu_bar, tearoff=False)
        settings_menu.add_command(label="Settings", command=self.settings)
        menu_bar.add_cascade(label="Settings", menu=settings_menu)

        self.tk.config(menu=menu_bar)
    
    def settings(self):
        self.settings_window = Toplevel(self.tk)
        self.settings_window.geometry("300x250")
        self.settings_window.title("Settings")
        self.quirk_checkbuttons = []
        for i, (key, value) in enumerate(self.quirks.items()):
            v = IntVar(self.settings_window, value=value)
            checkbutton = Checkbutton(
                self.settings_window, text=key, variable=v, onvalue=True, offvalue=False
            )
            checkbutton.grid(row=i, column=0, sticky='w')
            self.quirk_checkbuttons.append(checkbutton)
        b = Button(self.settings_window, text="Ok", command=self.settings_ok)
        b.grid(row=len(self.quirk_checkbuttons))
        self.settings_window.mainloop()
    
    def settings_ok(self):
        for checkbutton in self.quirk_checkbuttons:
            key = checkbutton['text']
            self.quirks[key] = checkbutton.getvar()
    
    def select_rom(self):
        file = filedialog.askopenfilename(title="Select a ROM", filetypes=[("CHIP8 ROMs", "*.ch8")])
        #TODO: check how to properly kill all these threads so it can support resetting/loading a second ROM
        #and self.running can actually mean *something*
        self.file_menu.entryconfig("Open", state="disabled")
        # if self.running:
        #     self.core_thread
        self.start_core(file)
    
    #System

    def start_core(self, file):
        self.core = Core(display_queue=self.display_queue, display_hz=self.refresh_rate)
        self.core.setup(file, quirks=self.quirks)
        self.core_thread = threading.Thread(target=self.core.run)
        self.core_thread.start()
        self.running = True
        self.display_loop()
    
    def quit(self):
        os._exit(1)
    
    def display_loop(self):
        last_refresh = time.time()
        loops = 0
        while self.running:
            loops += 1
            if not self.display_queue.empty():
                display_data = self.display_queue.get()
                self.display_queue.task_done()
                
                str_data = [
                    ["#FFF" if pixel == 1 else "#000" for pixel in line]
                    for line in display_data
                ]
                if self.scale > 1:
                    str_data = [
                        [p for p in line for _ in range(self.scale)]
                        for line in str_data for _ in range(self.scale)
                    ]
                self.img.put(str_data)
            
            self.tk.update()
            
            if self.quirks['display_wait']:
                elapsed = time.time() - last_refresh
                remaining = 1./self.refresh_rate - elapsed
                if remaining > 0:
                    time.sleep(remaining)
                else:
                    print(f"Uh oh, display took {elapsed*1000:.2f}ms to refresh "
                        f"(target is {1000*1./self.refresh_rate:.2f}ms for {self.refresh_rate}Hz)")
                last_refresh = time.time()

