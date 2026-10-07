import threading
import logging
from typing import Optional

logger = logging.getLogger("TTS")

class TextToSpeech:
    def __init__(self, rate: int = 175, volume: float = 0.9):
        self.rate = rate
        self.volume = volume
        self._lock = threading.Lock()

    def speak(self, text: str):
        """Speak text aloud asynchronously using local Windows speech synthesizer."""
        def _run():
            with self._lock:
                try:
                    import pyttsx3
                    engine = pyttsx3.init()
                    engine.setProperty("rate", self.rate)
                    engine.setProperty("volume", self.volume)
                    # Optional: pick female voice if available
                    voices = engine.getProperty("voices")
                    if voices and len(voices) > 1:
                        engine.setProperty("voice", voices[1].id)
                    engine.say(text)
                    engine.runAndWait()
                    engine.stop()
                except Exception as e:
                    logger.error(f"TTS error: {e}")

        t = threading.Thread(target=_run, daemon=True)
        t.start()

tts = TextToSpeech()
