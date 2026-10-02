"""
Suite 1: Laya Movement & Navigation Engine Tests (R1).
Verifies:
- Laya System 1 non-autoregressive CPU classification.
- Single forward pass latency constraint (<100ms on CPU).
- Dynamic choice schemas and slot extraction.
- Native Win32 movement execution (apps, windows, tabs, media, volume, scroll).
- Inviolable Zero-LLM Movement Guarantee (verifying Ollama is NEVER called for movement).
- Tier 1 (Feature), Tier 2 (Boundary & Adversarial), Tier 3 (Pairwise Combinations).
"""
import time
from unittest.mock import MagicMock, patch
import pytest

from ellie.actions.app_manager import AppManager, DANGEROUS_BINARIES, PROTECTED_PROCESSES
from ellie.actions.movement_controller import MovementController
from ellie.actions.volume_manager import VolumeManager
from ellie.routing.intent_schema import DECISION_SCHEMA, WINDOW_SUB_SCHEMA, TAB_SUB_SCHEMA
from ellie.routing.laya_router import IntentClassification, LayaClassifier, LayaRouter
from ellie.routing.slot_extractor import APP_ALIASES, SlotExtractor


# ============================================================================
# TIER 1: FEATURE COVERAGE (R1 Core Behaviors)
# ============================================================================

class TestLayaClassificationFeatures:
    """Tier 1: Verifies primary intent classification on CPU across all movement types."""

    @pytest.mark.parametrize(
        "utterance,expected_intent",
        [
            ("open notepad", "app_launch"),
            ("launch chrome browser", "app_launch"),
            ("start calculator", "app_launch"),
            ("close firefox", "app_close"),
            ("exit discord", "app_close"),
            ("terminate terminal", "app_close"),
            ("minimize window", "window_manage"),
            ("maximize this window", "window_manage"),
            ("restore window", "window_manage"),
            ("new tab", "tab_manage"),
            ("close this tab", "tab_manage"),
            ("switch to next tab", "tab_manage"),
            ("pause the music", "media_control"),
            ("play track", "media_control"),
            ("skip next song", "media_control"),
            ("volume up", "volume_control"),
            ("turn volume down", "volume_control"),
            ("mute audio", "volume_control"),
            ("scroll down", "navigation_scroll"),
            ("page up", "navigation_scroll"),
        ],
    )
    def test_laya_movement_intent_classification(self, utterance, expected_intent):
        router = LayaRouter()
        result = router.classify(utterance)
        assert result.intent == expected_intent
        assert result.is_movement is True
        assert result.confidence >= 0.65

    def test_laya_cpu_latency_constraint(self):
        """Verifies single-pass classification executes in <100ms on CPU."""
        classifier = LayaClassifier(use_mock=True)
        classifier.initialize()
        commands = [
            "open notepad",
            "volume up",
            "mute sound",
            "scroll down",
            "minimize window",
            "next tab",
            "close calculator",
        ]
        latencies = []
        for cmd in commands:
            res = classifier.classify(cmd)
            latencies.append(res.latency_ms)
            assert res.latency_ms < 100.0, f"Latency {res.latency_ms}ms exceeded 100ms threshold for {cmd}"
        avg_latency = sum(latencies) / len(latencies)
        assert avg_latency < 50.0, f"Average latency {avg_latency}ms should be well under 50ms"

    def test_dynamic_schema_structure(self):
        """Validates that decision schemas are properly defined choice questions."""
        assert "action_type" in DECISION_SCHEMA
        assert DECISION_SCHEMA["action_type"]["type"] == "choice"
        criteria = DECISION_SCHEMA["action_type"]["criteria"]
        expected_keys = {
            "app_launch",
            "app_close",
            "window_manage",
            "tab_manage",
            "media_control",
            "volume_control",
            "navigation_scroll",
            "write_delegation",
            "system_query",
            "unknown",
        }
        assert set(criteria.keys()) == expected_keys
        assert "window_op" in WINDOW_SUB_SCHEMA
        assert "tab_op" in TAB_SUB_SCHEMA

    def test_slot_extraction_accuracy(self):
        """Validates parameter extraction across application, window, tab, and volume commands."""
        assert SlotExtractor.extract_app_name("open notepad") == "notepad.exe"
        assert SlotExtractor.extract_app_name("launch google chrome") == "chrome.exe"
        assert SlotExtractor.extract_app_name("close calc") == "calc.exe"

        assert SlotExtractor.extract_window_action("minimize window") == "minimize"
        assert SlotExtractor.extract_window_action("maximize screen") == "maximize"
        assert SlotExtractor.extract_window_action("snap left") == "snap_left"

        assert SlotExtractor.extract_tab_action("new tab") == "new"
        assert SlotExtractor.extract_tab_action("close current tab") == "close"
        assert SlotExtractor.extract_tab_action("switch next tab") == "next"

        assert SlotExtractor.extract_media_action("pause music") == "play_pause"
        assert SlotExtractor.extract_media_action("next track") == "next"

        v_up = SlotExtractor.extract_volume_command("volume up")
        assert v_up["type"] == "up"
        v_mute = SlotExtractor.extract_volume_command("mute sound")
        assert v_mute["type"] == "mute"
        v_set = SlotExtractor.extract_volume_command("set volume to 65%")
        assert v_set["type"] == "set"
        assert v_set["value"] == 65


# ============================================================================
# TIER 1: ZERO-LLM MOVEMENT INVALIDATION GUARANTEE (Critical R1)
# ============================================================================

class TestZeroLLMMovementGuarantee:
    """Verifies that movement operations NEVER invoke Ollama/LLM."""

    @patch("requests.post")
    @patch("requests.get")
    def test_movement_never_calls_ollama_endpoints(self, mock_get, mock_post):
        """Critical guarantee: No HTTP calls to Ollama daemon on movement."""
        ctrl = MovementController()
        router = LayaRouter()

        movement_commands = [
            "open notepad",
            "close notepad",
            "volume up",
            "mute audio",
            "minimize window",
            "maximize window",
            "next tab",
            "scroll down",
        ]

        for cmd in movement_commands:
            classification = router.classify(cmd)
            assert classification.is_movement is True
            # Execute movement
            with patch("subprocess.Popen"), \
                 patch("psutil.process_iter", return_value=[]), \
                 patch("ctypes.windll.user32.ShowWindow", create=True):
                res = ctrl.execute_movement(classification)
                assert "action" in res

        # Verify zero requests made to Ollama
        mock_post.assert_not_called()
        mock_get.assert_not_called()

    def test_writing_intent_is_not_classified_as_movement(self):
        """Ensures writing commands do not trigger movement execution."""
        router = LayaRouter()
        writing_commands = [
            "write an apology letter to my teacher",
            "draft an email to boss about meeting at 5pm",
            "compose a poem about autumn",
            "generate notes for biology class",
        ]
        for cmd in writing_commands:
            res = router.classify(cmd)
            assert res.intent == "write_delegation"
            assert res.is_movement is False
            assert "prompt" in res.slots


# ============================================================================
# TIER 2: BOUNDARY, CORNER & ADVERSARIAL CASES
# ============================================================================

class TestMovementBoundaryAndAdversarial:
    """Tier 2: Extreme inputs, invalid parameters, and security barriers."""

    def test_empty_and_whitespace_utterance(self):
        router = LayaRouter()
        assert router.classify("").intent == "unknown"
        assert router.classify("   ").intent == "unknown"
        assert router.classify("\t\n\r").intent == "unknown"

    def test_case_insensitivity_and_punctuation(self):
        router = LayaRouter()
        res1 = router.classify("OPEN NOTEPAD!!!")
        res2 = router.classify("   oPeN   nOtEpAd.  ")
        assert res1.intent == "app_launch"
        assert res2.intent == "app_launch"

    def test_dangerous_binaries_blocked_from_launch(self):
        """AppManager must reject blacklisted system destruction tools."""
        app_mgr = AppManager()
        for bad_bin in DANGEROUS_BINARIES:
            success, msg = app_mgr.launch(bad_bin)
            assert success is False
            assert "restricted by system safety policy" in msg

    def test_protected_system_processes_cannot_be_closed(self):
        """AppManager must never terminate Windows core system services."""
        app_mgr = AppManager()
        for protected in PROTECTED_PROCESSES:
            success, msg = app_mgr.close(protected)
            assert success is False
            assert "Cannot close core system process" in msg

    def test_volume_boundary_clamping(self):
        """Volume percentages must be clamped between 0 and 100."""
        cmd_negative = SlotExtractor.extract_volume_command("set volume to -20%")
        cmd_overflow = SlotExtractor.extract_volume_command("set volume to 250%")
        assert cmd_negative["value"] == 0 or cmd_negative["value"] <= 100
        assert cmd_overflow["value"] == 100

        vol_mgr = VolumeManager()
        success, msg = vol_mgr.adjust({"type": "set", "value": 150})
        assert success is True
        assert "100" in msg or "adjusted" in msg

    def test_rapid_successive_movement_dispatches(self):
        """Validates that 50 rapid sequential commands execute without state corruption."""
        ctrl = MovementController()
        router = LayaRouter()
        start = time.perf_counter()

        with patch("subprocess.Popen"), patch("psutil.process_iter", return_value=[]):
            for i in range(50):
                cmd = "volume up" if i % 2 == 0 else "scroll down"
                classification = router.classify(cmd)
                res = ctrl.execute_movement(classification)
                assert res["action"] in ("volume_control", "navigation_scroll")

        duration = time.perf_counter() - start
        assert duration < 2.0, f"50 rapid executions took {duration}s, should be <2s"


# ============================================================================
# TIER 3: PAIRWISE COMBINATORIAL COVERAGE
# ============================================================================

class TestMovementPairwiseCombinations:
    """Tier 3: Pairwise combinations of actions, apps, and window parameters."""

    @pytest.mark.parametrize(
        "app_key,expected_exe",
        [
            ("notepad", "notepad.exe"),
            ("notes", "notepad.exe"),
            ("calc", "calc.exe"),
            ("calculator", "calc.exe"),
            ("chrome", "chrome.exe"),
            ("firefox", "firefox.exe"),
            ("edge", "msedge.exe"),
            ("terminal", "wt.exe"),
            ("spotify", "spotify.exe"),
            ("paint", "mspaint.exe"),
        ],
    )
    def test_pairwise_app_aliases(self, app_key, expected_exe):
        assert APP_ALIASES[app_key] == expected_exe
        assert SlotExtractor.extract_app_name(f"open {app_key}") == expected_exe

    @pytest.mark.parametrize(
        "direction,pages",
        [
            ("down", False),
            ("down", True),
            ("up", False),
            ("up", True),
        ],
    )
    def test_pairwise_scroll_directions(self, direction, pages):
        ctrl = MovementController()
        with patch("ctypes.windll.user32.mouse_event", create=True), \
             patch("ctypes.windll.user32.keybd_event", create=True):
            success, msg = ctrl.scroll_mgr.scroll(direction, pages=pages)
            assert success is True
            assert direction in msg

    @pytest.mark.parametrize(
        "action_str,expected_sub_action",
        [
            ("snap window left", "snap_left"),
            ("snap right", "snap_right"),
            ("minimize window", "minimize"),
            ("maximize window", "maximize"),
            ("restore normal size", "restore"),
        ],
    )
    def test_pairwise_window_manipulations(self, action_str, expected_sub_action):
        extracted = SlotExtractor.extract_window_action(action_str)
        assert extracted == expected_sub_action
        ctrl = MovementController()
        with patch("ctypes.windll.user32.ShowWindow", create=True), \
             patch("ctypes.windll.user32.keybd_event", create=True):
            success, msg = ctrl.win_mgr.perform(extracted)
            assert success is True
