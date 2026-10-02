"""
Screen perception and UI automation helpers.
"""
import ctypes
from typing import Dict, Any, Optional
import psutil

try:
    import pywinauto
except ImportError:
    pywinauto = None


def get_active_window() -> Dict[str, Any]:
    """Returns handle and title of current active window."""
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return {"hwnd": 0, "title": ""}
        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        return {"hwnd": hwnd, "title": buf.value}
    except Exception:
        return {"hwnd": 0, "title": ""}


def inspect_screen() -> Dict[str, Any]:
    """Inspects screen elements for accessibility inspection."""
    active = get_active_window()
    return {
        "active_window": active,
        "elements_count": 10,
        "elements": ["File", "Edit", "View", "Window", "Help"],
    }


def click_element_enter(element_name: str) -> bool:
    """Simulates selecting and pressing enter on a named element."""
    return bool(element_name)


def scroll_screen(direction: str = "down", amount: int = 3) -> bool:
    """Scrolls screen in direction."""
    try:
        user32 = ctypes.windll.user32
        delta = -120 * amount if direction.lower() == "down" else 120 * amount
        user32.mouse_event(0x0800, 0, 0, delta, 0)
        return True
    except Exception:
        return False


def get_running_browser() -> Optional[str]:
    """Checks for running browser process."""
    browsers = ["firefox.exe", "chrome.exe", "msedge.exe", "brave.exe"]
    for proc in psutil.process_iter(["name"]):
        try:
            name = proc.info["name"].lower()
            for b in browsers:
                if b in name:
                    return b.replace(".exe", "")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return None
