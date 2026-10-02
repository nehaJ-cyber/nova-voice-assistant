"""
Intent schema and decision criteria definitions for convaiinnovations/laya.
Defines dynamic question specifications for System 1 single-pass routing.
"""
from typing import Any, Dict

# Primary action classification schema for Laya Router
DECISION_SCHEMA: Dict[str, Any] = {
    "action_type": {
        "type": "choice",
        "instructions": (
            "Classify the user's spoken or textual command into the exact desktop action "
            "or delegation category required. Choose exactly one option."
        ),
        "criteria": {
            "app_launch": (
                "Open, launch, start, or run a desktop application, software, game, or tool. "
                "Examples: 'open notepad', 'launch chrome', 'start calculator', 'run spotify'."
            ),
            "app_close": (
                "Close, exit, quit, terminate, or kill a running desktop application or window. "
                "Examples: 'close firefox', 'exit discord', 'kill notepad', 'quit excel'."
            ),
            "window_manage": (
                "Minimize, maximize, restore, snap, or focus application windows. "
                "Examples: 'minimize window', 'maximize this', 'restore window', 'snap window left', 'snap right'."
            ),
            "tab_manage": (
                "Browser tab navigation such as opening a new tab, closing current tab, "
                "switching to next/previous tab, or reopening closed tabs. "
                "Examples: 'new tab', 'close this tab', 'next tab', 'switch tab', 'reopen tab'."
            ),
            "media_control": (
                "Control media playback including play, pause, resume, stop, next track, or previous track. "
                "Examples: 'play music', 'pause song', 'resume playback', 'next track', 'stop audio'."
            ),
            "volume_control": (
                "Adjust audio volume level, turn volume up or down, mute, or unmute speakers. "
                "Examples: 'volume up', 'turn it down', 'mute sound', 'unmute', 'set volume to 40 percent'."
            ),
            "navigation_scroll": (
                "Scroll documents, pages, or screens up, down, top, or bottom. "
                "Examples: 'scroll down', 'scroll up', 'page down', 'scroll to bottom'."
            ),
            "write_delegation": (
                "Request to write, compose, draft, or generate text such as an email, letter, apology, "
                "essay, message, or notes to be pasted into the active application. "
                "Examples: 'write an apology letter to boss', 'draft an email about meeting', 'compose a poem'."
            ),
            "system_query": (
                "Questions regarding system time, date, battery status, CPU load, or assistant identity. "
                "Examples: 'what time is it', 'battery percentage', 'system status', 'who are you'."
            ),
            "unknown": (
                "Unrecognized, ambiguous, unsupported, or incomplete commands."
            ),
        },
    }
}

# Sub-criteria for window management actions
WINDOW_SUB_SCHEMA: Dict[str, Any] = {
    "window_op": {
        "type": "choice",
        "instructions": "Determine the specific window manipulation requested.",
        "criteria": {
            "minimize": "Minimize the active window or hide it to the taskbar.",
            "maximize": "Maximize the window to fill the entire screen.",
            "restore": "Restore the window to its normal unmaximized windowed size.",
            "snap_left": "Snap or position the window to the left half of the screen.",
            "snap_right": "Snap or position the window to the right half of the screen.",
        },
    }
}

# Sub-criteria for browser tab management actions
TAB_SUB_SCHEMA: Dict[str, Any] = {
    "tab_op": {
        "type": "choice",
        "instructions": "Determine the specific tab navigation action requested.",
        "criteria": {
            "new": "Open a new empty browser tab.",
            "close": "Close the currently active browser tab.",
            "next": "Switch to the next tab to the right.",
            "previous": "Switch to the previous tab to the left.",
            "reopen": "Reopen the most recently closed browser tab.",
        },
    }
}
