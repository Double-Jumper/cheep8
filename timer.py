import threading
import time

class Timer:
    period = None
    timer = 0

    #Settings
    thread = None

    def __init__(self, freq = 60):
        self.period = 1./freq
        thread = threading.Thread(target=self.countdown)
        self.timer = 0
        thread.start()
        
    def countdown(self):
        while True:
            if self.timer > 0:
                self.timer -= 1
            time.sleep(self.period)

    def cancel(self):
        self.task.cancel()