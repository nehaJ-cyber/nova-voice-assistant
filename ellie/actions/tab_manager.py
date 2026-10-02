"""
Browser tab navigation manager.
"""
import ctypes
import logging
import time
from typing import Tuple
import psutil

logger = logging.getLogger("ellie.actions.tab_manager")

VK_CONTROL = 0x11
VK_SHIFT = 0x10
VK_TAB = 0x09
VK_T = 0x54
VK_W = 0x57
KEYEVENTF_KEYUP = 0x0002

SUPPORTED_TABBED_APPS = {
    "chrome.exe", "firefox.exe", "msedge.exe", "brave.exe",
    "opera.exe", "windowsterminal.exe", "code.exe"
}


class TabManager:
    """Handles tab operations in browsers and tabbed applications."""

    def __init__(self) -> None:
        self.user32 = ctypes.windll.user32 if hasattr(ctypes, "windll") else None

    def _is_tabbed_app_active(self) -> bool:
        if not self.user32:
            return True
        try:
            hwnd = self.user32.GetForegroundWindow()
            if not hwnd:
                return True
            pid = ctypes.c_ulong()
            self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            proc = psutil.Process(pid.value)
            return proc.name().lower() in SUPPORTED_TABBED_APPS
        except Exception:
            return True

    def perform(self, action: str) -> Tuple[bool, str]:
        if not self._is_tabbed_app_active():
            return False, "Active application does not support tabs."

        if action == "new":
            self._send_hotkey([VK_CONTROL, VK_T])
            return True, "Opened new tab."

        if action == "close":
            self._send_hotkey([VK_CONTROL, VK_W])
            return True, "Closed tab."

        if action == "next":
            self._send_hotkey([VK_CONTROL, VK_TAB])
            return True, "Switched to next tab."

        if action == "previous":
            self._send_hotkey([VK_CONTROL, VK_SHIFT, VK_TAB])
            return True, "Switched to previous tab."

        if action == "reopen":
            self._send_hotkey([VK_CONTROL, VK_SHIFT, VK_T])
            return True, "Reopened closed tab."

        return False, f"Unknown tab action: {action}"

    def _send_hotkey(self, keys: list) -> None:
        if not self.user32:
            return
        try:
            for k in keys:
                self.user32.keybd_event(k, 0, 0, 0)
                time.sleep(0.01)
            time.sleep(0.02)
            for k in reversed(keys):
                self.user32.keybd_event(k, 0, KEYEVENTF_KEYUP, 0)
                time.sleep(0.01)
        except Exception:
            pass
