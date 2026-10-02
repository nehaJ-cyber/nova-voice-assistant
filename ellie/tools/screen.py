"""Screen and UI perception tools for Ellie/Nova.
Provides Windows Voice Access style UI inspection, active window detection,
element clicking, scrolling, and screen capture.
"""
import os
import logging
import psutil
import pyautogui
from ellie.tools import register

logger = logging.getLogger(__name__)

TEMP_DIR = r"D:\Ellie\temp"

def _get_active_window_info() -> dict:
    """Helper to detect the active foreground window, application, and title."""
    info = {"title": "", "app": "unknown", "pid": 0}
    try:
        import win32gui
        import win32process
        hwnd = win32gui.GetForegroundWindow()
        if hwnd:
            title = win32gui.GetWindowText(hwnd)
            info["title"] = title.strip()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            info["pid"] = pid
            if pid:
                try:
                    proc = psutil.Process(pid)
                    info["app"] = proc.name().replace(".exe", "")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
    except Exception as e:
        logger.debug(f"win32gui foreground error: {e}")

    # Fallback to pygetwindow if win32gui title was empty
    if not info["title"]:
        try:
            import pygetwindow as gw
            active = gw.getActiveWindow()
            if active and active.title:
                info["title"] = active.title.strip()
        except Exception:
            pass

    return info

def get_active_window(step: dict) -> str:
    """Returns the title and application of the current active window."""
    info = _get_active_window_info()
    if info["title"]:
        return f"Active window: {info['title']} ({info['app']})"
    elif info["app"] != "unknown":
        return f"Active application is {info['app']}"
    return "Could not determine the active window."

def inspect_screen(step: dict) -> str:
    """Inspects the active window for visible UI elements like buttons, tabs, and text."""
    info = _get_active_window_info()
    elements = []
    
    # Try pywinauto UI Automation inspection
    try:
        from pywinauto import Desktop
        desktop = Desktop(backend="uia")
        # Connect to active window or desktop top window
        window = desktop.active()
        if window:
            win_title = window.window_text()
            if win_title and not info["title"]:
                info["title"] = win_title
            
            # Find interactive child controls (buttons, edit fields, tabs, links)
            for child in window.descendants()[:25]:
                try:
                    text = child.window_text().strip()
                    ctrl_type = child.friendly_class_name()
                    if text and len(text) < 50:
                        elements.append(f"{ctrl_type}: '{text}'")
                except Exception:
                    continue
    except Exception as e:
        logger.debug(f"UIA inspection error: {e}")

    summary_parts = []
    if info["title"]:
        summary_parts.append(f"Window: '{info['title']}' ({info['app']})")
    
    if elements:
        # Deduplicate while preserving order
        unique_elems = list(dict.fromkeys(elements))[:12]
        summary_parts.append("Visible elements: " + ", ".join(unique_elems))
    else:
        summary_parts.append("Window contents visible on screen.")

    return ". ".join(summary_parts)

def click_element(step: dict) -> str:
    """Finds and clicks a UI button or element by name/text."""
    target_name = step.get('name') or step.get('text') or step.get('element')
    if not target_name:
        return "Error: No element name provided to click."

    target_clean = target_name.strip().lower()

    # Strategy 1: pywinauto UIA button/tab click
    try:
        from pywinauto import Desktop
        desktop = Desktop(backend="uia")
        window = desktop.active()
        if window:
            for child in window.descendants():
                try:
                    c_text = child.window_text().strip().lower()
                    if target_clean in c_text or c_text in target_clean:
                        child.click_input()
                        return f"Clicked '{child.window_text()}'"
                except Exception:
                    continue
    except Exception as e:
        logger.debug(f"UIA click error: {e}")

    # Strategy 2: If target is Enter/Space/Escape, press it
    if target_clean in ['enter', 'return']:
        pyautogui.press('enter')
        return "Pressed Enter"
    elif target_clean == 'escape':
        pyautogui.press('esc')
        return "Pressed Escape"
    elif target_clean in ['tab', 'next']:
        pyautogui.press('tab')
        return "Pressed Tab"

    return f"Could not find or click element '{target_name}'"

def scroll_screen(step: dict) -> str:
    """Scrolls the screen up or down."""
    direction = (step.get('direction') or 'down').lower()
    amount = int(step.get('amount') or 5)
    clicks = amount if direction == 'up' else -amount
    pyautogui.scroll(clicks * 100)
    return f"Scrolled {direction}"

def capture_screen(step: dict) -> str:
    """Captures a screenshot and saves it to the temp directory."""
    try:
        os.makedirs(TEMP_DIR, exist_ok=True)
        out_path = os.path.join(TEMP_DIR, "screen.png")
        screenshot = pyautogui.screenshot()
        screenshot.save(out_path)
        return f"Screenshot saved to {out_path}"
    except Exception as e:
        logger.error(f"Error capturing screen: {e}")
        return f"Error capturing screen: {e}"

# Register screen tools
register('get_active_window', get_active_window)
register('inspect_screen', inspect_screen)
register('see_screen', inspect_screen)
register('click_element', click_element)
register('scroll_screen', scroll_screen)
register('capture_screen', capture_screen)
