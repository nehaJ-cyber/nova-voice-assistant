"""
System information tools.
"""
from datetime import datetime
import psutil


def get_battery() -> str:
    """Returns current battery status percentage and charging status."""
    battery = psutil.sensors_battery()
    if battery is None:
        return "No battery sensor detected or system running on AC power."
    percent = int(battery.percent)
    charging = "charging" if battery.power_plugged else "on battery"
    return f"Battery is at {percent}%, {charging}."


def get_current_time() -> str:
    """Returns formatted current system time."""
    now = datetime.now()
    return now.strftime("%I:%M %p, %A, %B %d, %Y")
