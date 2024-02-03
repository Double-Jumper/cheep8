from PyQt5.QtWidgets import (QApplication, QMainWindow, QMenuBar, QMenu, QLabel, QAction)
from PyQt5.QtGui import QImage, QPixmap, qRgba

import threading
import queue
import time
import os
import sys
from core import Core

class Emulator:
    #System
    core = None
    core_thread = None
    display_queue = None
    application = None
    main_window = None
    image_label = None
    image = None
    running = False

    #UI
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
    def __init__(self, w=64, h=32, scale:int=1, refresh_rate=60, file="/home/jumper/Games/Breakout (Brix hack) [David Winter, 1997].ch8"):
        #Initialize display and UI
        self.scale = scale
        self.refresh_rate = refresh_rate
        w *= self.scale
        h *= self.scale
        win_w = max(round(w), 250) #leave enough room in the title bar to show the title and be draggable
        win_h = round(h)
        self.application = QApplication(sys.argv)
        self.main_window = QMainWindow()
        self.main_window.setWindowTitle("Cheep8")
        self.main_window.setFixedWidth(win_w)
        self.main_window.setFixedHeight(win_h)
        self.image_label = QLabel()
        self.image = QImage(w,h,QImage.Format.Format_Mono)
        self.image.setColorCount(2)
        self.image.setColor(0, qRgba(0,0,0,255))
        self.image.setColor(1, qRgba(255,255,255,255))

        self.image_label.setPixmap(QPixmap.fromImage(self.image))
        self.main_window.setCentralWidget(self.image_label)
        self.create_ui()
        self.main_window.show()
        
        self.display_queue = queue.Queue(1)
        
        if file is not None:
            self.start_core(file)

    def create_ui(self):
        menu_bar = QMenuBar()

        self.file_menu = QMenu("File", menu_bar)
        # self.file_menu.addAction(text="Open", slot=self.select_rom)
        # self.file_menu.addSeparator()
        quit_item = QAction("Quit")
        quit_item.triggered.connect(self.quit)
        self.file_menu.addAction(quit_item)

        # settings_menu = QMenu("Settings", menu_bar)
        # settings_menu.addAction(text="Settings", slot=self.settings)

        self.main_window.setMenuBar(menu_bar)
    
    # def select_rom(self):
    #     file = filedialog.askopenfilename(title="Select a ROM", filetypes=[("CHIP8 ROMs", "*.ch8")])
    #     #TODO: check how to properly kill all these threads so it can support resetting/loading a second ROM
    #     #and self.running can actually mean *something*
    #     self.file_menu.entryconfig("Open", state="disabled")
    #     # if self.running:
    #     #     self.core_thread
    #     self.start_core(file)
        
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
                
                if self.scale > 1:
                    display_data = [
                        [p for p in line for _ in range(self.scale)]
                        for line in display_data for _ in range(self.scale)
                    ]
                
                for j, line in enumerate(display_data):
                    for i, pixel in enumerate(line):
                        self.image.setPixel(i, j, pixel)
                self.image_label.setPixmap(QPixmap.fromImage(self.image))
            
            if self.quirks['display_wait']:
                elapsed = time.time() - last_refresh
                remaining = 1./self.refresh_rate - elapsed
                if remaining > 0:
                    time.sleep(remaining)
                else:
                    print(f"Uh oh, display took {elapsed*1000:.2f}ms to refresh "
                        f"(target is {1000*1./self.refresh_rate:.2f}ms for {self.refresh_rate}Hz)")
                last_refresh = time.time()

            self.application.processEvents()
