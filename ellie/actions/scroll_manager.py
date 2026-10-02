"""
Document and webpage scrolling manager.
"""
import ctypes
import logging
import time
from typing import Tuple

logger = logging.getLogger("ellie.actions.scroll_manager")

MOUSEEVENTF_WHEEL = 0x0800
WHEEL_DELTA = 120
VK_PRIOR = 0x21
VK_NEXT = 0x22
KEYEVENTF_KEYUP = 0x0002


class ScrollManager:
    """Handles desktop document and screen scrolling."""

    def __init__(self) -> None:
        self.user32 = ctypes.windll.user32 if hasattr(ctypes, "windll") else None

    def scroll(self, direction: str, pages: bool = False) -> Tuple[bool, str]:
        is_down = direction.lower() == "down"

        if pages:
            if self.user32:
                vk = VK_NEXT if is_down else VK_PRIOR
                self.user32.keybd_event(vk, 0, 0, 0)
                time.sleep(0.02)
                self.user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
            dir_str = "down" if is_down else "up"
            return True, f"Paged {dir_str}."

        delta = -3 * WHEEL_DELTA if is_down else 3 * WHEEL_DELTA
        if self.user32:
            self.user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, delta, 0)
        dir_str = "down" if is_down else "up"
        return True, f"Scrolled {dir_str}."
