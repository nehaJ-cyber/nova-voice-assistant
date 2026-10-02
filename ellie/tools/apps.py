"""
Application management tools.
"""
import subprocess
from typing import Tuple


def open_app(app_name: str) -> Tuple[bool, str]:
    """Launches application by name."""
    try:
        subprocess.Popen([app_name], shell=False)
        return True, f"Launched {app_name}"
    except Exception as e:
        return False, f"Failed to launch {app_name}: {e}"
