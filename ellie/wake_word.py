"""
Vosk Microphone Wake-Word spotter.
"""
from typing import Callable, Optional
import numpy as np


class WakeWordDetector:
    WAKE_EXACT = ["hey nova", "wake up nova", "nova"]
    WAKE_FUZZY = [
        "hey no", "hey no but", "hey no va", "hey no vet", "hey over",
        "hey nah", "hey no one", "hey know", "a nova", "the nova",
        "no va", "no but", "hanover", "hannover", "hey november",
        "hey nope", "hey noir", "hey nor", "hey nota", "hello nova"
    ]

    def __init__(
        self,
        callback: Optional[Callable[[], None]] = None,
        model_path: str = "models/vosk-model-small-en-us-0.15",
        mic_gain: float = 6.0,
    ):
        self.callback = callback
        self.model_path = model_path
        self.mic_gain = mic_gain

    def amplify_audio(self, audio_np: np.ndarray) -> np.ndarray:
        amplified = audio_np.astype(np.float32) * self.mic_gain
        amplified = np.clip(amplified, -32768, 32767)
        return amplified.astype(np.int16)

    def is_wake_word(self, phrase: str) -> bool:
        norm = phrase.strip().lower()
        if norm in self.WAKE_EXACT:
            return True
        return any(fuzz in norm for fuzz in self.WAKE_FUZZY)
