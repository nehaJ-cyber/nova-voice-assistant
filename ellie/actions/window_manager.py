"""
Window manipulation manager using Win32 user32.
"""
import ctypes
import logging
import time
from typing import Tuple

logger = logging.getLogger("ellie.actions.window_manager")

SW_HIDE = 0
SW_MAXIMIZE = 3
SW_MINIMIZE = 6
SW_RESTORE = 9

VK_LWIN = 0x5B
VK_LEFT = 0x25
VK_UP = 0x26
VK_RIGHT = 0x27
VK_DOWN = 0x28
KEYEVENTF_KEYUP = 0x0002


class WindowManager:
    """Controls foreground and active application window states."""

    def __init__(self) -> None:
        self.user32 = ctypes.windll.user32 if hasattr(ctypes, "windll") else None

    def get_active_window(self) -> int:
        if self.user32:
            try:
                return self.user32.GetForegroundWindow()
            except Exception:
                return 0
        return 0

    def perform(self, action: str) -> Tuple[bool, str]:
        hwnd = self.get_active_window()
        if not hwnd and self.user32:
            hwnd = 1

        if action == "minimize":
            if self.user32:
                self.user32.ShowWindow(hwnd, SW_MINIMIZE)
            return True, "Minimized window."

        if action == "maximize":
            if self.user32:
                self.user32.ShowWindow(hwnd, SW_MAXIMIZE)
            return True, "Maximized window."

        if action == "restore":
            if self.user32:
                self.user32.ShowWindow(hwnd, SW_RESTORE)
            return True, "Restored window."

        if action == "snap_left":
            self._simulate_snap(VK_LEFT)
            return True, "Snapped window left."

        if action == "snap_right":
            self._simulate_snap(VK_RIGHT)
            return True, "Snapped window right."

        return False, f"Unknown window action: {action}"

    def _simulate_snap(self, arrow_vk: int) -> None:
        if not self.user32:
            return
        try:
            self.user32.keybd_event(VK_LWIN, 0, 0, 0)
            time.sleep(0.02)
            self.user32.keybd_event(arrow_vk, 0, 0, 0)
            time.sleep(0.02)
            self.user32.keybd_event(arrow_vk, 0, KEYEVENTF_KEYUP, 0)
            time.sleep(0.02)
            self.user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)
        except Exception:
            pass
