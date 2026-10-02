"""
Slot and entity extraction for classified System 1 commands.
Extracts target application names, volume steps, directions, and writing prompts.
"""
import re
from typing import Any, Dict, Optional

# Canonical alias mapping for Windows applications
APP_ALIASES: Dict[str, str] = {
    "notepad": "notepad.exe",
    "notes": "notepad.exe",
    "text editor": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "firefox": "firefox.exe",
    "mozilla": "firefox.exe",
    "edge": "msedge.exe",
    "microsoft edge": "msedge.exe",
    "browser": "chrome.exe",
    "code": "code.cmd",
    "vs code": "code.cmd",
    "vscode": "code.cmd",
    "terminal": "wt.exe",
    "cmd": "cmd.exe",
    "command prompt": "cmd.exe",
    "powershell": "powershell.exe",
    "explorer": "explorer.exe",
    "files": "explorer.exe",
    "file explorer": "explorer.exe",
    "spotify": "spotify.exe",
    "music": "spotify.exe",
    "paint": "mspaint.exe",
    "task manager": "taskmgr.exe",
}


class SlotExtractor:
    """Extracts parameters from user utterance according to classified intent."""

    @staticmethod
    def extract_app_name(text: str) -> Optional[str]:
        """Extracts and resolves application target name or executable."""
        lower = text.lower()
        cleaned = re.sub(
            r"^(please\s+)?(can\s+you\s+)?(open|launch|start|run|close|exit|quit|kill)\s+",
            "",
            lower,
        ).strip()
        cleaned = re.sub(r"^(the\s+|an\s+|a\s+)", "", cleaned).strip()

        if cleaned in APP_ALIASES:
            return APP_ALIASES[cleaned]

        for alias, exe in APP_ALIASES.items():
            if alias in cleaned:
                return exe

        tokens = cleaned.split()
        if tokens:
            tok = tokens[0]
            if tok.endswith((".exe", ".bat", ".cmd")):
                return tok
            return tok + ".exe"
        return None

    @staticmethod
    def extract_window_action(text: str) -> str:
        """Determines the window manipulation action."""
        lower = text.lower()
        if ("snap" in lower and "left" in lower) or "left half" in lower:
            return "snap_left"
        if ("snap" in lower and "right" in lower) or "right half" in lower:
            return "snap_right"
        if "minimize" in lower or "hide" in lower:
            return "minimize"
        if "maximize" in lower or "full screen" in lower:
            return "maximize"
        if "restore" in lower or "normal size" in lower:
            return "restore"
        return "minimize"

    @staticmethod
    def extract_tab_action(text: str) -> str:
        """Determines the browser tab action."""
        lower = text.lower()
        if "new" in lower or "open" in lower:
            return "new"
        if "close" in lower or "shut" in lower:
            return "close"
        if "next" in lower or "switch forward" in lower:
            return "next"
        if "prev" in lower or "previous" in lower or "back" in lower:
            return "previous"
        if "reopen" in lower or "restore" in lower:
            return "reopen"
        return "new"

    @staticmethod
    def extract_media_action(text: str) -> str:
        """Determines the media playback action."""
        lower = text.lower()
        if "pause" in lower or "resume" in lower or "play" in lower:
            return "play_pause"
        if "next" in lower or "skip" in lower:
            return "next"
        if "prev" in lower or "previous" in lower or "back" in lower:
            return "previous"
        if "stop" in lower:
            return "stop"
        return "play_pause"

    @staticmethod
    def extract_volume_command(text: str) -> Dict[str, Any]:
        """Extracts volume operation type and value."""
        lower = text.lower()
        if "mute" in lower and "unmute" not in lower:
            return {"type": "mute"}
        if "unmute" in lower:
            return {"type": "unmute"}

        match = re.search(r"(\d{1,3})\s*(%|percent)?", lower)
        if match:
            val = int(match.group(1))
            val = max(0, min(100, val))
            return {"type": "set", "value": val}

        if any(w in lower for w in ["up", "higher", "louder", "increase"]):
            return {"type": "up", "steps": 5}
        if any(w in lower for w in ["down", "lower", "quieter", "decrease"]):
            return {"type": "down", "steps": 5}

        return {"type": "up", "steps": 5}

    @staticmethod
    def extract_writing_prompt(text: str) -> str:
        """Extracts clean generation prompt for Qwen writing delegation."""
        cleaned = re.sub(
            r"^(please\s+)?(can\s+you\s+)?(write|draft|compose|generate|create)\s+(an?\s+)?",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()
        return cleaned if cleaned else text
