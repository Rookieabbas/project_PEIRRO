import threading
import warnings

# Suppress harmless SAPI5 comtypes version warnings on newer Python builds
warnings.filterwarnings("ignore", category=FutureWarning, module=".*comtypes.*")

import pyttsx3


class VoiceEngine:
    _lock = threading.Lock()

    def __init__(self):
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty("rate", 185)

            # Pick a natural female/smoother voice if available (e.g. Zira)
            voices = self.engine.getProperty("voices")
            for v in voices:
                if "zira" in v.name.lower() or "female" in v.name.lower():
                    self.engine.setProperty("voice", v.id)
                    break
        except Exception as e:
            print(f"[!] Warning: VoiceEngine init failed: {e}")
            self.engine = None

    def speak(self, text: str):
        if not self.engine or not text:
            return

        with self._lock:
            try:
                print(f"[Peirro Voice]: {text}")
                self.engine.say(text)
                self.engine.runAndWait()
            except Exception as e:
                print(f"[TTS Error Handled]: {e}")

    def stop(self):
        """Immediately halts speech output when Ctrl + Space is pressed."""
        if self.engine:
            try:
                self.engine.stop()
            except Exception:
                pass