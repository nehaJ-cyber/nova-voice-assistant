"""
Media playback control manager using Windows Virtual Keys.
"""
import ctypes
import logging
import time
from typing import Tuple

logger = logging.getLogger("ellie.actions.media_manager")

VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3
KEYEVENTF_KEYUP = 0x0002


class MediaManager:
    """Manages global media playback keystrokes."""

    def __init__(self) -> None:
        self.user32 = ctypes.windll.user32 if hasattr(ctypes, "windll") else None

    def perform(self, action: str) -> Tuple[bool, str]:
        if action == "play_pause":
            self._tap_key(VK_MEDIA_PLAY_PAUSE)
            return True, "Toggled media playback."

        if action == "next":
            self._tap_key(VK_MEDIA_NEXT_TRACK)
            return True, "Skipped to next track."

        if action == "previous":
            self._tap_key(VK_MEDIA_PREV_TRACK)
            return True, "Playing previous track."

        if action == "stop":
            self._tap_key(VK_MEDIA_STOP)
            return True, "Stopped media playback."

        return False, f"Unknown media action: {action}"

    def _tap_key(self, vk: int) -> None:
        if not self.user32:
            return
        try:
            self.user32.keybd_event(vk, 0, 0, 0)
            time.sleep(0.01)
            self.user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
        except Exception:
            pass
