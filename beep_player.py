import numpy as np
import pyaudio

class BeepPlayer:
    def __init__(self, sample_rate=44100):
        self.sample_rate = sample_rate
        self.samples_per_frame = 1024  # adjust this value if needed
        self.beep_samples = None
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(format=pyaudio.paFloat32, channels=1, rate=self.sample_rate, output=True, stream_callback=self._callback)
        self.stream.start_stream()

    def _callback(self, in_data, frame_count, time_info, status):
        if self.beep_samples is not None and len(self.beep_samples) > 0:
            output = self.beep_samples[:frame_count]
            self.beep_samples = self.beep_samples[frame_count:]
            output = np.pad(output, (0, frame_count - len(output)))
        else:
            output = np.zeros(frame_count, dtype=np.float32)
        return (output.tobytes(), pyaudio.paContinue)

    def play_beep(self, frequency=440, duration=1):
        t = np.arange(int(self.sample_rate * duration)) / self.sample_rate
        samples = np.sin(2 * np.pi * frequency * t).astype(np.float32)
        if self.beep_samples is not None:
            self.beep_samples = np.concatenate((self.beep_samples, samples))
        else:
            self.beep_samples = samples

    def stop(self):
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()
