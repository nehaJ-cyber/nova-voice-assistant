"""System information tools for Ellie."""
import logging
import time
import socket
import datetime
import psutil
from ellie.tools import register

logger = logging.getLogger(__name__)

def get_info(step: dict) -> str:
    """Retrieve requested system information."""
    info_type = step.get('type', '').lower()
    try:
        if info_type == 'time':
            return datetime.datetime.now().strftime("%I:%M %p")
        elif info_type == 'date':
            return datetime.datetime.now().strftime("%A, %B %d, %Y")
        elif info_type == 'battery':
            if not hasattr(psutil, "sensors_battery"):
                return "Battery information not available."
            battery = psutil.sensors_battery()
            if battery is None:
                return "No battery detected (likely a desktop PC)."
            status = "charging" if battery.power_plugged else "not charging"
            return f"Battery is at {battery.percent}%, {status}"
        elif info_type == 'cpu':
            usage = psutil.cpu_percent(interval=1)
            return f"CPU usage is {usage}%"
        elif info_type == 'ram':
            mem = psutil.virtual_memory()
            used_gb = round(mem.used / (1024**3), 2)
            total_gb = round(mem.total / (1024**3), 2)
            return f"RAM usage is {mem.percent}% ({used_gb} GB used of {total_gb} GB)"
        elif info_type == 'disk':
            # psutil.disk_usage on windows usually takes a drive letter
            # using 'C:\\' as default root if '/' fails or implies main drive
            drive = step.get('drive', 'C:\\')
            disk = psutil.disk_usage(drive)
            return f"Disk usage on {drive} is {disk.percent}%"
        elif info_type == 'ip':
            hostname = socket.gethostname()
            ip_address = socket.gethostbyname(hostname)
            return f"Local IP address is {ip_address}"
        elif info_type == 'uptime':
            boot_time = psutil.boot_time()
            uptime_seconds = time.time() - boot_time
            hours = int(uptime_seconds // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            return f"System uptime is {hours} hours and {minutes} minutes"
        else:
            return f"Unknown info type: {info_type}"
    except Exception as e:
        logger.error(f"Error retrieving {info_type} info: {e}")
        return f"Error retrieving {info_type} info: {e}"

# Register system info tools
register('get_info', get_info)
