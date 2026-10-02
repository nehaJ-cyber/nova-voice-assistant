"""
Browser control tools.
"""
import urllib.parse
import webbrowser
from typing import Tuple


def open_browser(url: str = "https://www.google.com") -> Tuple[bool, str]:
    """Opens specified URL in default browser."""
    try:
        webbrowser.open(url)
        return True, f"Opened URL {url}"
    except Exception as e:
        return False, f"Failed to open browser: {e}"


def google_search(query: str) -> Tuple[bool, str]:
    """Performs Google search for query."""
    encoded = urllib.parse.quote_plus(query)
    url = f"https://www.google.com/search?q={encoded}"
    return open_browser(url)
