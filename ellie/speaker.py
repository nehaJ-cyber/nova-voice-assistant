"""
Kokoro-ONNX and pyttsx3 Text-to-Speech Speaker for Ellie / Nova.
"""
import logging
import queue
import threading
from typing import Optional
import numpy as np

try:
    from kokoro_onnx import Kokoro
except ImportError:
    Kokoro = None

try:
    import sounddevice as sd
except ImportError:
    sd = None

logger = logging.getLogger(__name__)


class Speaker:
    def __init__(
        self,
        model_path: str = "models/kokoro-v1.0.onnx",
        voices_path: str = "models/voices-v1.0.bin",
        default_voice: str = "af_bella",
        speed: float = 1.0,
    ):
        self.model_path = model_path
        self.voices_path = voices_path
        self.default_voice = default_voice
        self.speed = speed
        self._lock = threading.Lock()
        self._queue: queue.Queue = queue.Queue()
        self.kokoro = None
        self._init_kokoro()

    def _init_kokoro(self) -> None:
        if Kokoro is not None:
            try:
                self.kokoro = Kokoro(self.model_path, self.voices_path)
            except Exception as e:
                logger.warning("Failed to initialize Kokoro: %s", e)
                self.kokoro = None

    def speak(self, text: str, voice: Optional[str] = None) -> None:
        """Generates synthetic speech and plays audio through sounddevice."""
        if not text:
            return
        target_voice = voice or self.default_voice
        with self._lock:
            if self.kokoro and sd:
                try:
                    samples, sample_rate = self.kokoro.create(
                        text, voice=target_voice, speed=self.speed, lang="en-us"
                    )
                    sd.play(samples, sample_rate)
                    sd.wait()
                    return
                except Exception as e:
                    logger.error("Kokoro TTS playback failed: %s", e)

            # Fallback mock or print
            logger.info("Speech: %s", text)

    def speak_async(self, text: str, voice: Optional[str] = None) -> None:
        """Queues speech asynchronously."""
        threading.Thread(target=self.speak, args=(text, voice), daemon=True).start()

    def play_chime(self, chime_type: str = "wake") -> None:
        """Synthesizes pure sine tone chimes."""
        freq_map = {"wake": 880.0, "sleep": 440.0, "error": 220.0}
        freq = freq_map.get(chime_type, 440.0)
        duration = 0.3 if chime_type != "error" else 0.5
        sample_rate = 24000
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        audio = 0.3 * np.sin(2 * np.pi * freq * t)
        # Apply fade in and fade out
        fade = int(sample_rate * 0.05)
        audio[:fade] *= np.linspace(0, 1, fade)
        audio[-fade:] *= np.linspace(1, 0, fade)

        if sd:
            try:
                sd.play(audio.astype(np.float32), sample_rate)
                sd.wait()
            except Exception:
                pass

    def stop(self) -> None:
        if sd:
            try:
                sd.stop()
            except Exception:
                pass
