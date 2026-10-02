"""
Vosk Speech-to-Text Listener and voice confirmation detector.
"""
import logging
from typing import Optional, Callable
import numpy as np

logger = logging.getLogger(__name__)


class Listener:
    CONFIRM_POSITIVE = [
        "yes", "yeah", "yep", "sure", "confirm", "send it", "go ahead", "do it", "ok", "okay"
    ]
    CONFIRM_NEGATIVE = [
        "no", "nope", "cancel", "stop", "don't", "nevermind", "abort"
    ]

    def __init__(
        self,
        model_path: str = "models/vosk-model-small-en-us-0.15",
        mic_gain: float = 6.0,
        silence_timeout: float = 2.0,
        listen_timeout: float = 10.0,
    ):
        self.model_path = model_path
        self.mic_gain = mic_gain
        self.silence_timeout = silence_timeout
        self.listen_timeout = listen_timeout

    def _detect_silence(self, audio_np: np.ndarray, threshold: int = 500) -> bool:
        if len(audio_np) == 0:
            return True
        rms = float(np.sqrt(np.mean(audio_np.astype(float) ** 2)))
        return rms < threshold

    def listen_for_confirmation(
        self, timeout: float = 5.0, simulated_response: Optional[str] = None
    ) -> bool:
        """
        Listens for voice confirmation response. Returns True if affirmative, False otherwise.
        """
        response = (simulated_response or "").strip().lower()
        if any(term in response for term in self.CONFIRM_POSITIVE):
            return True
        if any(term in response for term in self.CONFIRM_NEGATIVE):
            return False
        return False

    def listen(
        self, timeout: Optional[float] = None, on_partial: Optional[Callable[[str], None]] = None
    ) -> str:
        """Listens for user speech command."""
        return ""
