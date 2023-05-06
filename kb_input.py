from pynput import keyboard
import threading
import queue

class KB_Input:
    key_map = None
    last_key = None
    thread = None

    #TODO: configurable keymap
    def __init__(self, key_map = None):
        if key_map is None:
            self.key_map = {
                #TODO work with numpad, or test on desktop
                0x0: keyboard.KeyCode(char="0"),
                0x1: keyboard.KeyCode(char="1"),
                0x2: keyboard.KeyCode(char="2"),
                0x3: keyboard.KeyCode(char="3"),
                0x4: keyboard.KeyCode(char="4"),
                0x5: keyboard.KeyCode(char="5"),
                0x6: keyboard.KeyCode(char="6"),
                0x7: keyboard.KeyCode(char="7"),
                0x8: keyboard.KeyCode(char="8"),
                0x9: keyboard.KeyCode(char="9"),
                0xA: keyboard.KeyCode(char="a"),
                0xB: keyboard.KeyCode(char="b"),
                0xC: keyboard.KeyCode(char="c"),
                0xD: keyboard.KeyCode(char="d"),
                0xE: keyboard.KeyCode(char="e"),
                0xF: keyboard.KeyCode(char="f"),
            }
        self.last_key = queue.Queue(1)
        thread = threading.Thread(target=self.detect_key_press)
        thread.start()
    
    def is_pressed(self, key):
        if self.last_key.full():
            res = key == self.last_key.queue[0]
            return res
        return False
    
    def on_press(self, key):
        for hexa, keycode in self.key_map.items():
            if key == keycode:
                if self.last_key.full():
                    self.last_key.get_nowait()
                    self.last_key.task_done()
                self.last_key.put(hexa)
                return True
    
    def on_release(self, key):
        if self.last_key.full():
            for hexa, keycode in self.key_map.items():
                if key == keycode:
                    if hexa == self.last_key.queue[0]:
                        self.last_key.get_nowait()
                        self.last_key.task_done()
                    return True 

    def detect_key_press(self):
        while True:
            with keyboard.Listener(on_press=self.on_press, on_release=self.on_release) as listener:
                listener.join()
        