"""
Main entry point and assistant loop for Ellie / Nova.
"""
import logging
from typing import Dict, Any, Optional

import re
from ellie.actions.movement_controller import MovementController
from ellie.delegation.writing_pipeline import WritingDelegationPipeline
from ellie.guardrails.memory_guardrail import MemoryGuardrail
from ellie.listener import Listener
from ellie.orchestrator import Orchestrator
from ellie.routing.laya_router import LayaRouter
from ellie.safety import SafetyGate, SafetyResult
from ellie.speaker import Speaker

logger = logging.getLogger("ellie.main")

SILENT_INTENTS = {
    "open_app",
    "close_app",
    "app_launch",
    "app_close",
    "window_manage",
    "tab_manage",
    "google_search",
    "youtube_search",
    "open_url",
    "volume_control",
    "media_control",
    "click_element",
    "scroll_screen",
    "navigation_scroll",
}


class EllieAssistant:
    def __init__(
        self,
        router: Optional[LayaRouter] = None,
        movement_ctrl: Optional[MovementController] = None,
        writing_pipeline: Optional[WritingDelegationPipeline] = None,
        safety_gate: Optional[SafetyGate] = None,
        speaker: Optional[Speaker] = None,
        listener: Optional[Listener] = None,
        orchestrator: Optional[Orchestrator] = None,
    ):
        self.router = router or LayaRouter()
        self.movement_ctrl = movement_ctrl or MovementController()
        self.writing_pipeline = writing_pipeline or WritingDelegationPipeline()
        self.safety_gate = safety_gate or SafetyGate()
        self.speaker = speaker or Speaker()
        self.listener = listener or Listener()
        self.memory_guardrail = MemoryGuardrail()
        self.orchestrator = orchestrator or Orchestrator(
            router=self.router,
            movement_ctrl=self.movement_ctrl,
            writing_pipeline=self.writing_pipeline,
            safety_gate=self.safety_gate,
            speaker=self.speaker,
            listener=self.listener,
        )
        self.state = "IDLE"

    def handle_command(self, utterance: str) -> Dict[str, Any]:
        """
        End-to-end command handler:
        1. Classify via Laya System 1 Router (<50ms CPU).
        2. Check SafetyGate (C: drive restrictions & confirmation).
        3. If writing, delegate to Qwen pipeline + 4-tier memory flush.
        4. If movement, execute Win32 movement silently without LLM.
        """
        self.state = "THINKING"
        classification = self.router.classify(utterance)
        intent = classification.intent

        # Safety Gate Check: extract entities & check path
        slots = classification.slots or {}
        entities: Dict[str, Any] = {}
        for k in ("path", "file_path", "target", "app_name"):
            if k in slots:
                entities[k] = slots[k]
        if "app_name" in slots:
            entities["path"] = slots["app_name"]

        path_match = re.search(r"[a-zA-Z]\s*:[\\/][^\s]+", utterance)
        if path_match:
            entities["path"] = path_match.group(0)

        action_name = "close_app" if intent in ("app_close", "close_app") else intent
        safety_res = self.safety_gate.check_action(action_name, entities)

        if path_match and safety_res.allowed:
            path_allowed, path_reason = self.safety_gate.check_path(path_match.group(0))
            if not path_allowed:
                safety_res = SafetyResult(
                    allowed=False,
                    needs_confirmation=False,
                    reason=path_reason,
                    blocked_reason="RESTRICTED_DRIVE",
                )

        if not safety_res.allowed:
            self.speaker.play_chime("error")
            self.speaker.speak("Access is restricted for safety.")
            self.state = "IDLE"
            return {"success": False, "reason": safety_res.reason, "blocked": True, "action": intent}

        if safety_res.needs_confirmation:
            self.state = "CONFIRMING"
            confirmed = self.listener.listen_for_confirmation()
            if not confirmed:
                self.speaker.speak("Okay, cancelling.")
                self.state = "IDLE"
                return {"success": False, "cancelled": True, "reason": "User cancelled action.", "action": intent}

        self.state = "ACTING"

        # Route to Writing Delegation
        if intent == "write_delegation":
            prompt = slots.get("prompt", utterance)
            try:
                res = self.writing_pipeline.delegate_writing(prompt)
                return res
            finally:
                self.state = "IDLE"

        # Route to Movement Execution (Silent Intent)
        if classification.is_movement:
            res = self.movement_ctrl.execute_movement(classification)
            # Silent execution: do not speak self-evident movement actions
            if intent not in SILENT_INTENTS:
                if res.get("feedback"):
                    self.speaker.speak(res["feedback"])
            self.state = "IDLE"
            return res

        # Fallback / General Query
        self.speaker.speak(f"Command processed: {intent}")
        self.state = "IDLE"
        return {"success": True, "intent": intent}

    def _on_command(self, utterance: str) -> Dict[str, Any]:
        return self.handle_command(utterance)


def main():
    import sys
    import time
    logger.info("Initializing Ellie / Nova Assistant with Laya Decision Orchestrator...")
    assistant = EllieAssistant()
    print("==================================================================")
    print(" Nova Voice & Automation Assistant (Laya Orchestrator Active)")
    print("==================================================================")
    
    # If run in an interactive console, allow typing commands
    if sys.stdin and sys.stdin.isatty():
        print("Ready for commands. Type 'exit' to quit.\n")
        while True:
            try:
                line = input("Nova> ")
                if not line.strip():
                    continue
                if line.strip().lower() in ("exit", "quit"):
                    break
                res = assistant.handle_command(line)
                print(f"-> {res}")
            except (KeyboardInterrupt, EOFError):
                break
            except Exception as e:
                logger.error(f"Error handling command: {e}")
    else:
        # Background / Service daemon mode
        logger.info("Running in background service mode.")
        try:
            while True:
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            pass


if __name__ == "__main__":
    main()
