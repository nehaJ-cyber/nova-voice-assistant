"""
Orchestrator for Ellie / Nova.
Handles command parsing, fast-path routing, and LLM chat generation.
"""
import json
import logging
import re
from typing import Dict, Any, Optional

from ellie.actions.movement_controller import MovementController
from ellie.delegation.writing_pipeline import WritingDelegationPipeline
from ellie.guardrails.memory_guardrail import MemoryGuardrail
from ellie.listener import Listener
from ellie.routing.laya_router import IntentClassification, LayaRouter
from ellie.safety import SafetyGate, SafetyResult
from ellie.speaker import Speaker

try:
    import ollama
except ImportError:
    ollama = None

logger = logging.getLogger(__name__)

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


class Orchestrator:
    FAST_PATH_TRIGGERS = {
        "open": "open_app",
        "launch": "open_app",
        "start": "open_app",
        "close": "close_app",
        "exit": "close_app",
        "volume": "volume_control",
        "mute": "volume_control",
        "scroll": "scroll_screen",
    }

    def __init__(
        self,
        ollama_client: Optional[Any] = None,
        model: str = "qwen2.5:1.5b",
        router: Optional[LayaRouter] = None,
        movement_ctrl: Optional[MovementController] = None,
        writing_pipeline: Optional[WritingDelegationPipeline] = None,
        safety_gate: Optional[SafetyGate] = None,
        speaker: Optional[Speaker] = None,
        listener: Optional[Listener] = None,
    ):
        self.ollama_client = ollama_client or ollama
        self.model = model
        self.router = router or LayaRouter()
        self.movement_ctrl = movement_ctrl or MovementController()
        self.writing_pipeline = writing_pipeline or WritingDelegationPipeline()
        self.safety_gate = safety_gate or SafetyGate()
        self.speaker = speaker or Speaker()
        self.listener = listener or Listener()
        self.memory_guardrail = MemoryGuardrail()
        self.state = "IDLE"

    def parse_response(self, raw_text: str) -> Dict[str, Any]:
        """Parses model response JSON, stripping markdown code fences or conversational preamble."""
        if not raw_text or not raw_text.strip():
            return {"action": "unknown", "entities": {}, "error": "Empty response"}

        text = raw_text.strip()

        # Extract markdown json blocks
        md_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if md_match:
            text = md_match.group(1).strip()
        else:
            # Strip preamble before first '{'
            brace_idx = text.find("{")
            if brace_idx != -1:
                last_brace = text.rfind("}")
                if last_brace != -1:
                    text = text[brace_idx : last_brace + 1]

        try:
            return json.loads(text)
        except Exception:
            return {
                "action": "unknown",
                "entities": {},
                "raw_text": raw_text,
                "error": "Malformed JSON",
            }

    def process(self, utterance: str) -> Dict[str, Any]:
        """
        Processes user command. If matches fast-path trigger, resolves instantly.
        Otherwise classifies via LayaRouter, and if necessary calls Ollama chat.
        """
        cleaned = utterance.strip().lower()
        if not cleaned:
            return {"action": "unknown", "entities": {}}

        # Fast path check
        first_word = cleaned.split()[0] if cleaned.split() else ""
        if first_word in self.FAST_PATH_TRIGGERS:
            action = self.FAST_PATH_TRIGGERS[first_word]
            remainder = cleaned[len(first_word):].strip()
            return {"action": action, "entities": {"target": remainder}, "fast_path": True}

        # Classify via LayaRouter
        classification = self.router.classify(utterance)
        if classification.is_movement:
            return {
                "action": classification.intent,
                "entities": classification.slots,
                "fast_path": True,
                "is_movement": True,
            }
        if classification.intent == "write_delegation":
            return {
                "action": "write_delegation",
                "entities": classification.slots,
                "fast_path": True,
                "is_movement": False,
            }

        # Ollama LLM chat path
        if self.ollama_client is not None:
            try:
                response = self.ollama_client.chat(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "Output valid JSON with keys 'action' and 'entities'.",
                        },
                        {"role": "user", "content": utterance},
                    ],
                )
                content = response.get("message", {}).get("content", "")
                plan = self.parse_response(content)
                plan["fast_path"] = False
                return plan
            except Exception as e:
                logger.error("Ollama chat failed: %s", e)
                return {"action": "error", "error": str(e), "fast_path": False}

        return {"action": "general_question", "entities": {"query": utterance}, "fast_path": False}

    def handle_command(self, utterance: str) -> Dict[str, Any]:
        """
        Full Milestone 4 command pipeline:
        1. Classifies utterance using LayaRouter.classify(text).
        2. If is_movement:
           - SafetyGate check. If blocked, reject immediately.
           - If confirmation required, prompt via listener.
           - If safe, dispatch directly to MovementController.execute_movement().
           - Zero calls to Ollama or Qwen.
           - Enforce silent intent rule: zero spoken output for movement actions.
        3. If write_delegation:
           - SafetyGate check. If blocked, reject immediately.
           - Dispatch to WritingDelegationPipeline.delegate_writing().
           - Flushes memory guardrail in finally block post-generation.
        """
        self.state = "THINKING"
        classification = self.router.classify(utterance)
        intent = classification.intent
        slots = classification.slots or {}

        # Safety Gate Check: extract entities & check path
        entities: Dict[str, Any] = {}
        for k in ("path", "file_path", "target", "app_name"):
            if k in slots:
                entities[k] = slots[k]
        if "app_name" in slots:
            entities["path"] = slots["app_name"]

        path_match = re.search(r"[a-zA-Z]:[\\/][^\s]+", utterance)
        if path_match:
            entities["path"] = path_match.group(0)

        action_for_safety = "close_app" if intent in ("app_close", "close_app") else intent

        # 1. Movement handling
        if classification.is_movement:
            safety_res = self.safety_gate.check_action(action_for_safety, entities)
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
                if self.speaker:
                    self.speaker.play_chime("error")
                    self.speaker.speak("Access is restricted for safety.")
                self.state = "IDLE"
                return {"success": False, "reason": safety_res.reason, "blocked": True, "action": intent}

            if safety_res.needs_confirmation:
                self.state = "CONFIRMING"
                confirmed = False
                if self.listener:
                    confirmed = self.listener.listen_for_confirmation()
                if not confirmed:
                    if self.speaker:
                        self.speaker.speak("Okay, cancelling.")
                    self.state = "IDLE"
                    return {"success": False, "cancelled": True, "reason": "User cancelled action.", "action": intent}

            self.state = "ACTING"
            res = self.movement_ctrl.execute_movement(classification)

            if intent not in SILENT_INTENTS:
                if self.speaker and res.get("feedback"):
                    self.speaker.speak(res["feedback"])

            self.state = "IDLE"
            return res

        # 2. Write delegation handling
        if intent == "write_delegation":
            safety_res = self.safety_gate.check_action(intent, entities)
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
                if self.speaker:
                    self.speaker.play_chime("error")
                    self.speaker.speak("Access is restricted for safety.")
                self.state = "IDLE"
                return {"success": False, "reason": safety_res.reason, "blocked": True, "action": intent}

            if safety_res.needs_confirmation:
                self.state = "CONFIRMING"
                confirmed = False
                if self.listener:
                    confirmed = self.listener.listen_for_confirmation()
                if not confirmed:
                    if self.speaker:
                        self.speaker.speak("Okay, cancelling.")
                    self.state = "IDLE"
                    return {"success": False, "cancelled": True, "reason": "User cancelled action.", "action": intent}

            self.state = "ACTING"
            prompt = slots.get("prompt", utterance)
            res = self.writing_pipeline.delegate_writing(prompt)
            self.state = "IDLE"
            return res

        # Fallback / General Query
        if self.speaker:
            self.speaker.speak(f"Command processed: {intent}")
        self.state = "IDLE"
        return {"success": True, "intent": intent}

    execute = handle_command
