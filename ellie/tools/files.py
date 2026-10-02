"""
File system tools with mandatory safety gate validation.
"""
from pathlib import Path
from typing import Union

BLOCKED_DRIVES = ["C"]


def _check_safety(path: Union[str, Path]) -> tuple[bool, str]:
    """Ensures file access does not touch blocked drives."""
    try:
        resolved = Path(path).resolve()
        drive_letter = resolved.drive.rstrip(":").upper()
        if drive_letter in BLOCKED_DRIVES:
            return False, "Safety Violation: Access to drive C: is blocked for safety."
        # Also check raw string drive prefix
        raw = str(path).strip().lower()
        if raw.startswith("c:") or raw.startswith("/c:") or raw.startswith("\\c:"):
            return False, "Safety Violation: Access to drive C: is blocked for safety."
        return True, "Path safe."
    except Exception as e:
        return False, f"Invalid path: {e}"


def read_file(path: str) -> str:
    """Reads file content if safe, otherwise returns safety violation message."""
    is_safe, msg = _check_safety(path)
    if not is_safe:
        return msg

    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"File not found: {path}"
    except Exception as e:
        return f"Error reading file {path}: {e}"
