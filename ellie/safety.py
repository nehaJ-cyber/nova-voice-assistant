"""
Safety Gate for Ellie / Nova.
Enforces C: drive blocking and voice confirmation workflows for sensitive operations.
"""
from dataclasses import dataclass
import os
import re
from typing import Dict, Any, Optional, Tuple


@dataclass
class SafetyResult:
    allowed: bool
    needs_confirmation: bool
    reason: str
    blocked_reason: str = ""


class SafetyGate:
    BLOCKED_DRIVES = ["c"]
    BLOCKED_ACTIONS = [
        "run_shell",
        "install_software",
        "modify_registry",
        "access_credentials",
    ]
    CONFIRMATION_ACTIONS = [
        "send_message",
        "delete_file",
        "close_app",
        "app_close",
        "deploy_subagent",
    ]

    def __init__(self, blocked_drives: Optional[list] = None):
        self.blocked_drives = [d.lower() for d in (blocked_drives or self.BLOCKED_DRIVES)]

    def check_path(self, path: str) -> Tuple[bool, str]:
        """
        Validates if a file or directory path accesses restricted drives (e.g. C:).
        Returns (is_allowed, reason).
        """
        if not path or not isinstance(path, str):
            return True, "Empty or non-string path permitted."

        raw_stripped = path.strip()

        # Regular expressions for obfuscation attempts:
        # 1. c: or C: at start
        # 2. whitespace between c and :
        # 3. UNC format \\?\c: or \\.\c:
        # 4. URL or forward-slash /c: or /C:
        c_patterns = [
            r"(?:^|[\s/\\])[cC]\s*:",
            r"^[/\\]+[cC]:",
            r"^\\\\(\.|\?)\\[cC]:",
            r"^/[cC]:",
        ]
        for pat in c_patterns:
            if re.search(pat, raw_stripped):
                return False, "Access to drive C: is blocked for safety."

        # Normalized path checks
        try:
            norm = os.path.normpath(raw_stripped)
            drive, _ = os.path.splitdrive(norm)
            clean_drive = drive.rstrip(":").replace("\\", "").replace("/", "").lower()
            if clean_drive in self.blocked_drives:
                return False, "Access to drive C: is blocked for safety."
        except Exception:
            pass

        return True, "Path permitted."

    def check_action(self, action: str, entities: Optional[Dict[str, Any]] = None) -> SafetyResult:
        """
        Evaluates safety permissions for a requested action and its entities.
        """
        entities = entities or {}

        # 1. Blocked action check
        if action in self.BLOCKED_ACTIONS:
            return SafetyResult(
                allowed=False,
                needs_confirmation=False,
                reason=f"Action '{action}' is permanently restricted by system safety policy.",
                blocked_reason="BLOCKED_ACTION",
            )

        # 2. Check path safety inside entities
        for key, value in entities.items():
            if any(term in key.lower() for term in ["path", "file", "dir"]):
                if isinstance(value, str):
                    allowed, reason = self.check_path(value)
                    if not allowed:
                        return SafetyResult(
                            allowed=False,
                            needs_confirmation=False,
                            reason=reason,
                            blocked_reason="RESTRICTED_DRIVE",
                        )

        # 3. Confirmation required actions
        if action in self.CONFIRMATION_ACTIONS:
            return SafetyResult(
                allowed=True,
                needs_confirmation=True,
                reason=f"Action '{action}' requires user voice confirmation before execution.",
            )

        return SafetyResult(
            allowed=True,
            needs_confirmation=False,
            reason="Action permitted without restriction.",
        )
