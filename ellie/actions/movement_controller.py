"""
Central Movement & Navigation Controller.
Dispatches classified System 1 tasks to respective specialized Win32 subsystems.
Guarantees ZERO-LLM execution.
"""
import logging
from typing import Any, Dict, Union

from ellie.actions.app_manager import AppManager
from ellie.actions.media_manager import MediaManager
from ellie.actions.scroll_manager import ScrollManager
from ellie.actions.tab_manager import TabManager
from ellie.actions.volume_manager import VolumeManager
from ellie.actions.window_manager import WindowManager
from ellie.routing.laya_router import DecisionResult, IntentClassification
from ellie.routing.slot_extractor import SlotExtractor

logger = logging.getLogger("ellie.actions.movement")


class MovementController:
    """Coordinates execution of all desktop movement and navigation actions without LLM."""

    def __init__(self) -> None:
        self.app_mgr = AppManager()
        self.win_mgr = WindowManager()
        self.tab_mgr = TabManager()
        self.media_mgr = MediaManager()
        self.vol_mgr = VolumeManager()
        self.scroll_mgr = ScrollManager()

    def execute_movement(self, classification: Union[IntentClassification, DecisionResult]) -> Dict[str, Any]:
        """
        Executes native Win32 movement action according to classification.
        Guaranteed to never call Ollama or autoregressive LLMs.
        """
        if isinstance(classification, IntentClassification):
            action = classification.intent
            slots = classification.slots or {}
            text = slots.get("raw_text", "")
        elif isinstance(classification, DecisionResult):
            action = classification.action_type
            text = classification.input_text
            slots = {}
        elif isinstance(classification, dict):
            action = classification.get("intent") or classification.get("action_type") or ""
            slots = classification.get("slots") or {}
            text = classification.get("text") or ""
        else:
            action = getattr(classification, "intent", getattr(classification, "action_type", ""))
            slots = getattr(classification, "slots", {})
            text = getattr(classification, "input_text", "")

        logger.info("Executing movement action '%s'", action)

        if action == "app_launch":
            app = slots.get("app_name") or SlotExtractor.extract_app_name(text)
            if not app:
                return {"success": False, "feedback": "Could not determine which application to open.", "action": action}
            success, msg = self.app_mgr.launch(app)
            return {"success": success, "feedback": msg, "action": action, "app": app}

        if action == "app_close":
            app = slots.get("app_name") or SlotExtractor.extract_app_name(text)
            if not app:
                return {"success": False, "feedback": "Could not determine which application to close.", "action": action}
            success, msg = self.app_mgr.close(app)
            return {"success": success, "feedback": msg, "action": action, "app": app}

        if action == "window_manage":
            win_action = slots.get("window_action") or SlotExtractor.extract_window_action(text)
            success, msg = self.win_mgr.perform(win_action)
            return {"success": success, "feedback": msg, "action": action, "window_action": win_action}

        if action == "tab_manage":
            tab_action = slots.get("tab_action") or SlotExtractor.extract_tab_action(text)
            success, msg = self.tab_mgr.perform(tab_action)
            return {"success": success, "feedback": msg, "action": action, "tab_action": tab_action}

        if action == "media_control":
            media_action = slots.get("media_action") or SlotExtractor.extract_media_action(text)
            success, msg = self.media_mgr.perform(media_action)
            return {"success": success, "feedback": msg, "action": action, "media_action": media_action}

        if action == "volume_control":
            cmd = slots.get("volume_command") or SlotExtractor.extract_volume_command(text)
            success, msg = self.vol_mgr.adjust(cmd)
            return {"success": success, "feedback": msg, "action": action, "volume_command": cmd}

        if action == "navigation_scroll":
            direction = slots.get("direction") or ("down" if "down" in text.lower() else "up")
            success, msg = self.scroll_mgr.scroll(direction)
            return {"success": success, "feedback": msg, "action": action, "direction": direction}

        return {
            "success": False,
            "feedback": f"Action '{action}' is not a movement action.",
            "action": action,
        }

    def execute(self, decision: Any) -> Dict[str, Any]:
        """Alias for execute_movement."""
        return self.execute_movement(decision)
