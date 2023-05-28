import numpy as np
import pyaudio

class BeepPlayer:
    def __init__(self, sample_rate=44100):
        # Set the sample rate for the audio
        self.sample_rate = sample_rate
        # Set the number of samples per frame
        self.samples_per_frame = 1024  # adjust this value if needed
        # Initialize the beep samples to None
        self.beep_samples = None
        # Create an instance of PyAudio
        self.p = pyaudio.PyAudio()
        # Create a continuous audio stream
        self.stream = self.p.open(format=pyaudio.paFloat32, channels=1, rate=self.sample_rate, output=True, stream_callback=self._callback)
        # Start the audio stream
        self.stream.start_stream()

    def _callback(self, in_data, frame_count, time_info, status):
        # If there are beep samples to be played
        if self.beep_samples is not None and len(self.beep_samples) > 0:
            # Get the next frame of beep samples
            output = self.beep_samples[:frame_count]
            # Remove the played samples from the beep samples
            self.beep_samples = self.beep_samples[frame_count:]
            # Pad the output with zeros if it's shorter than a full frame
            output = np.pad(output, (0, frame_count - len(output)))
        else:
            # If there are no beep samples to be played, output silence
            output = np.zeros(frame_count, dtype=np.float32)
        # Return the output samples to be played and continue the stream
        return (output.tobytes(), pyaudio.paContinue)

    def play_beep(self, frequency=440, duration=1):
        # Calculate the time values for each sample
        t = np.arange(int(self.sample_rate * duration)) / self.sample_rate
        # Generate the beep samples as a sinusoidal wave at the given frequency
        samples = np.sin(2 * np.pi * frequency * t).astype(np.float32)
        # If there are already beep samples, append the new samples to the end
        if self.beep_samples is not None:
            self.beep_samples = np.concatenate((self.beep_samples, samples))
        else:
            # If there are no existing beep samples, set the new samples as the beep samples
            self.beep_samples = samples

    def stop(self):
        # Stop the audio stream
        self.stream.stop_stream()
        # Close the audio stream
        self.stream.close()
        # Terminate the PyAudio instance
        self.p.terminate()
