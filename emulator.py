import sdl2.ext
import threading
import queue
import time
import os
import ctypes
from core import Core

class Emulator:
    #System
    core = None
    core_thread = None
    display_queue = None
    window = None
    surface = None
    u32_pixels = None
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
    def __init__(self, w=64, h=32, scale:int=1, refresh_rate=60, file="/home/jumper/Games/Breakout (Brix hack) [David Winter, 1997].ch8"):
        #Initialize display and UI
        self.scale = scale
        self.refresh_rate = refresh_rate
        w *= self.scale
        h *= self.scale
        win_w = max(round(w), 250) #leave enough room in the title bar to show the title and be draggable
        win_h = round(h)
        sdl2.ext.init()
        self.window = sdl2.SDL_CreateWindow(
            b"Cheep8", sdl2.SDL_WINDOWPOS_CENTERED, sdl2.SDL_WINDOWPOS_CENTERED,
            win_w, win_h, sdl2.SDL_WINDOW_SHOWN
        )
        self.surface = sdl2.SDL_GetWindowSurface(self.window)
        self.u32_pixels = ctypes.cast(self.surface[0].pixels, ctypes.POINTER(ctypes.c_uint32));
        
        self.display_queue = queue.Queue(1)
        
        if file is not None:
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
                
                # Clear Surface
                sdl2.SDL_FillRect(self.surface, None, 0)
                win_width = ctypes.c_int()
                win_height = ctypes.c_int()
                sdl2.SDL_GetWindowSize(self.window, win_width, win_height)
                win_width = win_width.value

                pixel_data = [
                    [0xffffffff if pixel == 1 else 0x0 for pixel in line]
                    for line in display_data
                ]
                if self.scale > 1:
                    pixel_data = [
                        [p for p in line for _ in range(self.scale)]
                        for line in pixel_data for _ in range(self.scale)
                    ]
                
                for j, line in enumerate(pixel_data):
                    for i, pixel in enumerate(line):
                        self.u32_pixels[j*win_width+i] = pixel
            
            sdl2.SDL_UpdateWindowSurface(self.window, self.surface)
            
            if self.quirks['display_wait']:
                elapsed = time.time() - last_refresh
                remaining = 1./self.refresh_rate - elapsed
                if remaining > 0:
                    time.sleep(remaining)
                else:
                    print(f"Uh oh, display took {elapsed*1000:.2f}ms to refresh "
                        f"(target is {1000*1./self.refresh_rate:.2f}ms for {self.refresh_rate}Hz)")
                last_refresh = time.time()

        ev = sdl2.SDL_Event()
        while(sdl2.SDL_PollEvent(ev)):
            if(ev.type == sdl2.SDL_QUIT):
                self.quit()
