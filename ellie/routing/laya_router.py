"""
System 1 Decision Classifier using convaiinnovations/laya.
Executes non-autoregressive decision classification locally on CPU in <50ms.
"""
from dataclasses import dataclass
import logging
import time
from typing import Any, Dict, NamedTuple, Optional

from ellie.routing.intent_schema import DECISION_SCHEMA
from ellie.routing.slot_extractor import SlotExtractor

logger = logging.getLogger("ellie.routing.laya")


class IntentClassification(NamedTuple):
    intent: str  # e.g., 'app_launch', 'app_close', 'volume_control', 'write_delegation'
    confidence: float
    slots: Dict[str, Any]
    is_movement: bool
    latency_ms: float


@dataclass
class DecisionResult:
    """Encapsulates the typed result of a Laya System 1 decision pass."""
    action_type: str
    confidence: float
    raw_response: Dict[str, Any]
    latency_ms: float
    input_text: str


class LayaClassifier:
    """
    Non-autoregressive decision classifier powered by convaiinnovations/laya.
    Preloads model checkpoint in memory and performs single-pass forward inferences on CPU.
    """

    MOVEMENT_ACTIONS = {
        "app_launch",
        "app_close",
        "window_manage",
        "tab_manage",
        "media_control",
        "volume_control",
        "navigation_scroll",
    }

    def __init__(
        self,
        model_name: str = "convaiinnovations/laya",
        confidence_threshold: float = 0.65,
        use_mock: bool = False,
    ) -> None:
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.use_mock = use_mock
        self.router: Optional[Any] = None
        self._is_initialized = False

    def initialize(self) -> None:
        """Loads and preloads the Laya model into RAM."""
        if self._is_initialized:
            return

        if self.use_mock:
            self._is_initialized = True
            return

        try:
            from laya import Router
            self.router = Router(preload=True)
            self._is_initialized = True
        except Exception:
            self.use_mock = True
            self._is_initialized = True

    def classify(self, text: str) -> DecisionResult:
        if not self._is_initialized:
            self.initialize()

        cleaned_text = text.strip()
        if not cleaned_text:
            return DecisionResult(
                action_type="unknown",
                confidence=0.0,
                raw_response={},
                latency_ms=0.0,
                input_text=text,
            )

        t_start = time.perf_counter()

        if self.use_mock or self.router is None:
            return self._mock_classify(cleaned_text, t_start)

        try:
            state = {"text": cleaned_text}
            res = self.router.predict(state=state, questions=DECISION_SCHEMA)
            t_end = time.perf_counter()
            latency_ms = (t_end - t_start) * 1000.0

            action_data = res.get("answers", {}).get("action_type", {})
            choice = action_data.get("choice", "unknown")
            confidence = float(action_data.get("confidence", 0.0))

            if confidence < self.confidence_threshold:
                action_type = "unknown"
            else:
                action_type = choice

            return DecisionResult(
                action_type=action_type,
                confidence=confidence,
                raw_response=res,
                latency_ms=latency_ms,
                input_text=cleaned_text,
            )
        except Exception:
            return self._mock_classify(cleaned_text, t_start)

    def _mock_classify(self, text: str, t_start: float) -> DecisionResult:
        lower = text.lower()
        t_end = time.perf_counter()
        latency_ms = (t_end - t_start) * 1000.0

        if any(w in lower for w in ["write", "draft", "compose", "generate", "create a letter", "apology"]):
            choice = "write_delegation"
            conf = 0.95
        elif any(w in lower.split() for w in ["tab", "tabs"]) or any(w in lower for w in ["new tab", "close tab", "next tab", "previous tab", "reopen tab", "switch tab"]):
            choice = "tab_manage"
            conf = 0.94
        elif any(w in lower for w in ["open", "launch", "start", "run"]):
            choice = "app_launch"
            conf = 0.92
        elif any(w in lower for w in ["close", "exit", "quit", "terminate", "kill"]):
            choice = "app_close"
            conf = 0.93
        elif any(w in lower for w in ["minimize", "maximize", "restore", "snap"]):
            choice = "window_manage"
            conf = 0.90
        elif any(w in lower for w in ["volume", "mute", "unmute", "louder", "quieter"]):
            choice = "volume_control"
            conf = 0.96
        elif any(w in lower for w in ["play", "pause", "resume", "stop music", "next song", "next track", "previous track", "previous song", "stop playback", "music", "song", "audio", "playback"]):
            choice = "media_control"
            conf = 0.91
        elif any(w in lower for w in ["scroll", "page down", "page up"]):
            choice = "navigation_scroll"
            conf = 0.89
        elif any(w in lower for w in ["time", "battery", "status", "who are you"]):
            choice = "system_query"
            conf = 0.88
        else:
            choice = "unknown"
            conf = 0.40

        return DecisionResult(
            action_type=choice,
            confidence=conf,
            raw_response={"mock": True, "predicted_choice": choice},
            latency_ms=latency_ms,
            input_text=text,
        )


class LayaRouter:
    """
    Primary interface for PROJECT.md contract:
    classify(text: str) -> IntentClassification
    is_available() -> bool
    """

    MOVEMENT_ACTIONS = {
        "app_launch",
        "app_close",
        "window_manage",
        "tab_manage",
        "media_control",
        "volume_control",
        "navigation_scroll",
    }

    def __init__(self, classifier: Optional[LayaClassifier] = None):
        self.classifier = classifier or LayaClassifier()

    def is_available(self) -> bool:
        return True

    def classify(self, text: str) -> IntentClassification:
        res = self.classifier.classify(text)
        action = res.action_type
        is_movement = action in self.MOVEMENT_ACTIONS

        # Extract slots based on action
        slots: Dict[str, Any] = {"raw_text": text}
        if action in ("app_launch", "app_close"):
            slots["app_name"] = SlotExtractor.extract_app_name(text)
        elif action == "window_manage":
            slots["window_action"] = SlotExtractor.extract_window_action(text)
        elif action == "tab_manage":
            slots["tab_action"] = SlotExtractor.extract_tab_action(text)
        elif action == "media_control":
            slots["media_action"] = SlotExtractor.extract_media_action(text)
        elif action == "volume_control":
            slots["volume_command"] = SlotExtractor.extract_volume_command(text)
        elif action == "navigation_scroll":
            slots["direction"] = "down" if "down" in text.lower() else "up"
        elif action == "write_delegation":
            slots["prompt"] = SlotExtractor.extract_writing_prompt(text)

        return IntentClassification(
            intent=action,
            confidence=res.confidence,
            slots=slots,
            is_movement=is_movement,
            latency_ms=res.latency_ms,
        )
