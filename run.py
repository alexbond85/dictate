import rumps
import sounddevice as sd
import scipy.io.wavfile
import whisper
import threading
import subprocess
import numpy as np
import tempfile
from pynput import keyboard



class DictationApp(rumps.App):
    def __init__(self):
        super(DictationApp, self).__init__("Dictation", icon="mic_off.png")
        self.recording = False
        self.recording_thread = None
        self.fs = 16000  # Sample rate
        self.audio_data = []

        # Prepare the menu item with a callback
        self.toggle_item = rumps.MenuItem("Start Recording", callback=self.toggle_recording)
        self.menu = [self.toggle_item]

        # Register global hotkey with the neutral key combination
        self.hotkey = keyboard.GlobalHotKeys({
            '<cmd>+<shift>+p': self.on_activate,
        })
        self.hotkey.start()

        # Timer for blinking icon
        self.blink_timer = rumps.Timer(self.blink_icon, 0.5)
        self.icon_visible = True

        # Load the Whisper model once
        print("Loading Whisper model...")
        self.model = whisper.load_model("turbo")

    def on_activate(self):
        self.toggle_recording(self.toggle_item)

    def toggle_recording(self, sender):
        if not self.recording:
            self.start_recording(sender)
        else:
            self.stop_recording(sender)

    def start_recording(self, sender):
        print("Recording started...")
        self.recording = True
        sender.title = "Stop Recording"
        self.audio_data = []

        # Check if the previous thread is still running
        if self.recording_thread and self.recording_thread.is_alive():
            print("Waiting for previous recording thread to finish...")
            self.recording_thread.join()

        self.recording_thread = threading.Thread(target=self.record_audio)
        self.recording_thread.start()

        # Start blinking icon
        self.blink_timer.start()

    def stop_recording(self, sender):
        print("Recording stopped.")
        self.recording = False
        sender.title = "Start Recording"

        if self.recording_thread:
            self.recording_thread.join()
            self.recording_thread = None

        # Stop blinking icon and reset to default
        self.blink_timer.stop()
        self.icon = "mic_off.png"

        self.process_audio()

    def record_audio(self):
        try:
            with sd.InputStream(samplerate=self.fs, channels=1, dtype='int16', callback=self.audio_callback):
                while self.recording:
                    sd.sleep(100)
        except Exception as e:
            print(f"An error occurred during recording: {e}")

    def audio_callback(self, indata, frames, time, status):
        if status:
            print(f"Audio callback status: {status}")
        self.audio_data.append(indata.copy())

    def process_audio(self):
        if not self.audio_data:
            print("No audio data to process.")
            return

        try:
            audio = np.concatenate(self.audio_data, axis=0)
            with tempfile.NamedTemporaryFile(suffix=".wav") as temp_audio_file:
                scipy.io.wavfile.write(temp_audio_file.name, self.fs, audio)
                text = self.transcribe_audio(temp_audio_file.name)
                self.paste_text(text)
        except Exception as e:
            print(f"An error occurred during audio processing: {e}")

    def transcribe_audio(self, filename):
        try:
            print("Transcribing audio...")
            result = self.model.transcribe(filename)
            text = result["text"]
            print(f"Transcription: {text}")
            return text
        except Exception as e:
            print(f"An error occurred during transcription: {e}")
            return ""

    def paste_text(self, text):
        if not text:
            print("No text to paste.")
            return

        try:
            process = subprocess.Popen('pbcopy', env={'LANG': 'en_US.UTF-8'}, stdin=subprocess.PIPE)
            process.communicate(text.encode('utf-8'))

            applescript = '''
            tell application "System Events"
                keystroke "v" using command down
            end tell
            '''
            subprocess.run(['osascript', '-e', applescript])
        except Exception as e:
            print(f"An error occurred while pasting text: {e}")

    def blink_icon(self, sender):
        if self.icon_visible:
            self.icon = None  # Hide icon
        else:
            self.icon = "mic_on.png"  # Show recording icon
        self.icon_visible = not self.icon_visible


if __name__ == "__main__":
    DictationApp().run()
