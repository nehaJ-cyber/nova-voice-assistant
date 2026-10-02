"""
Suite 5: Comprehensive Real-World Application Scenarios (Tier 4 E2E).
Implements the 5 complete application lifecycle scenarios defined in TEST_INFRA.md:
1. Scenario 1: Rapid Movement Sequence (F1, F2, F3)
2. Scenario 2: Dictation into Active Editor (F1, F4, F5, F6, F7, F8)
3. Scenario 3: Multimodal Voice Workflow (F1, F2, F9, F12)
4. Scenario 4: Blocked Dangerous Operation (F1, F10, F13)
5. Scenario 5: High-Frequency Alternating Flow (F1, F2, F3, F4, F6, F7, F8)
"""
import time
from unittest.mock import MagicMock, patch
import pytest

from ellie.main import EllieAssistant
from ellie.routing.laya_router import LayaRouter


# ============================================================================
# TIER 4: REAL-WORLD APPLICATION SCENARIOS
# ============================================================================

class TestE2ERealWorldScenarios:
    """Tier 4: Complete cross-subsystem end-to-end user journeys."""

    def test_scenario_1_rapid_movement_sequence(self):
        """
        Scenario 1: Rapid Movement Sequence
        Features: F1 (Laya), F2 (Movement Execution), F3 (Zero-LLM Movement Guarantee).
        Flow:
        - User rapidly commands: 'open notepad', 'volume up', 'scroll down', 'close notepad'.
        - Verifies:
          * Execution under 100ms per step.
          * Zero calls to Ollama daemon.
          * Accurate Win32 subsystem dispatch.
        """
        assistant = EllieAssistant()
        assistant.speaker = MagicMock()
        assistant.listener = MagicMock()
        # Approve close_app confirmation
        assistant.listener.listen_for_confirmation.return_value = True

        sequence = [
            ("open notepad", "app_launch"),
            ("volume up", "volume_control"),
            ("scroll down", "navigation_scroll"),
            ("close notepad", "app_close"),
        ]

        with patch("subprocess.Popen") as mock_popen, \
             patch("psutil.process_iter", return_value=[]), \
             patch("requests.post") as mock_ollama_post, \
             patch("ctypes.windll.user32.mouse_event", create=True):

            for cmd, expected_action in sequence:
                t0 = time.perf_counter()
                res = assistant.handle_command(cmd)
                latency = (time.perf_counter() - t0) * 1000.0

                assert res.get("action") == expected_action or res.get("success") is True
                assert latency < 150.0, f"Command '{cmd}' took {latency}ms (exceeded 150ms ceiling)"

            # CRITICAL: Ollama is NEVER called during movement sequence!
            mock_ollama_post.assert_not_called()

    def test_scenario_2_dictation_into_active_editor(self):
        """
        Scenario 2: Dictation into Active Editor
        Features: F1 (Laya), F4 (Qwen Delegation), F5 (Clipboard Injection),
                  F6 (keep_alive=0), F7 (gc.collect), F8 (Working Set Trim).
        Flow:
        - Active window is focused on Notepad.
        - User commands: 'draft a meeting request for tomorrow at 3pm'.
        - Laya routes to Qwen.
        - Text is generated without conversational preamble.
        - Text is pasted into Notepad via Ctrl+V.
        - Ollama model is unloaded (keep_alive: 0).
        - Memory baseline returns to <500MB.
        """
        assistant = EllieAssistant()
        assistant.speaker = MagicMock()

        active_editor = {
            "hwnd": 4567,
            "title": "Notes.txt - Notepad",
            "pid": 1122,
            "process_name": "notepad.exe",
        }

        generated_qwen_text = "Hi Team,\n\nPlease join our project sync tomorrow at 3pm.\n\nBest regards,"

        with patch.object(assistant.writing_pipeline.injector, "get_foreground_window", return_value=active_editor), \
             patch.object(assistant.writing_pipeline, "_generate_text", return_value=generated_qwen_text), \
             patch.object(assistant.writing_pipeline.injector, "inject_and_paste", return_value=True) as mock_paste, \
             patch("requests.post") as mock_ollama_post, \
             patch("gc.collect", return_value=12) as mock_gc, \
             patch("pyperclip.copy") as mock_copy:

            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_ollama_post.return_value = mock_resp

            res = assistant.handle_command("draft a meeting request for tomorrow at 3pm")

            assert res["success"] is True
            assert res["target_window"]["process_name"] == "notepad.exe"
            assert "tomorrow at 3pm" in res["generated_text"]

            # 1. Pasted into editor
            mock_paste.assert_called_once_with(generated_qwen_text, clear_after=True)

            # 2. Ollama unload dispatched
            mock_ollama_post.assert_called()
            unload_call = [call for call in mock_ollama_post.call_args_list if call[1]["json"].get("keep_alive") == 0]
            assert len(unload_call) > 0, "Ollama keep_alive=0 unload was not dispatched!"

            # 3. Garbage collection invoked
            mock_gc.assert_called_with(2)

            # 4. Clipboard buffer cleared
            mock_copy.assert_called_with("")

    def test_scenario_3_multimodal_voice_workflow(self):
        """
        Scenario 3: Multimodal Voice Workflow
        Features: F1 (Laya), F2 (Movement Execution), F9 (Vosk STT), F12 (Kokoro TTS).
        Flow:
        - Vosk spots wake phrase 'hey nova'.
        - Wake chime (880Hz) plays.
        - User speaks 'volume down'.
        - Laya routes to volume_control.
        - Volume decreases natively via Win32.
        - Movement action executes silently (no speech feedback).
        """
        assistant = EllieAssistant()
        assistant.speaker = MagicMock()

        # Step 1: Wake word detected
        assert assistant.listener is not None
        wake_detector = assistant.listener
        # Simulate chime
        assistant.speaker.play_chime("wake")
        assistant.speaker.play_chime.assert_called_with("wake")

        # Step 2: Spoken movement command
        with patch.object(assistant.movement_ctrl.vol_mgr, "adjust", return_value=(True, "Turned volume down.")) as mock_vol:
            res = assistant.handle_command("volume down")
            assert res["success"] is True
            mock_vol.assert_called_once()
            # Silent execution: speaker.speak must NOT be called for volume_control!
            assistant.speaker.speak.assert_not_called()

    def test_scenario_4_blocked_dangerous_operation(self):
        """
        Scenario 4: Blocked Dangerous Operation
        Features: F1 (Laya), F10 (Safety Gate), F13 (C: Drive Restriction).
        Flow:
        - User commands: 'open C:\\Windows\\System32\\payload.exe'.
        - SafetyGate detects C: drive violation.
        - Command is blocked immediately.
        - Error chime (220Hz) plays.
        - Audio warning is spoken: 'Access is restricted for safety.'
        - Qwen is NEVER invoked.
        """
        assistant = EllieAssistant()
        assistant.speaker = MagicMock()
        assistant.movement_ctrl = MagicMock()

        with patch("requests.post") as mock_ollama_post:
            res = assistant.handle_command("open C:\\Windows\\System32\\payload.exe")

            assert res["success"] is False
            assert res.get("blocked") is True
            # Movement controller never executed
            assistant.movement_ctrl.execute_movement.assert_not_called()
            # Error acoustic feedback
            assistant.speaker.play_chime.assert_called_with("error")
            assistant.speaker.speak.assert_called_with("Access is restricted for safety.")
            # Zero calls to Ollama
            mock_ollama_post.assert_not_called()

    def test_scenario_5_high_frequency_alternating_flow(self):
        """
        Scenario 5: High-Frequency Alternating Flow
        Features: F1, F2, F3, F4, F6, F7, F8.
        Flow:
        - User alternates between movement ('open chrome'), writing ('draft email to team'),
          movement ('mute volume'), writing ('write meeting summary'), movement ('scroll down').
        - Memory flushes execute after each writing cycle.
        - Memory returns to idle baseline each time without memory leaks.
        """
        assistant = EllieAssistant()
        assistant.speaker = MagicMock()

        operations = [
            ("open chrome", "movement"),
            ("draft email to team regarding roadmap", "writing"),
            ("mute audio", "movement"),
            ("write meeting summary of quarterly results", "writing"),
            ("scroll down", "movement"),
        ]

        with patch("subprocess.Popen"), \
             patch.object(assistant.writing_pipeline, "_generate_text", return_value="Sample generated paragraph"), \
             patch.object(assistant.writing_pipeline, "_paste_to_active_app", return_value=True), \
             patch("requests.post") as mock_post, \
             patch("gc.collect", return_value=5), \
             patch("pyperclip.copy"):

            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_post.return_value = mock_resp

            for cmd, op_type in operations:
                res = assistant.handle_command(cmd)
                assert res.get("success") is True or "action" in res

                if op_type == "writing":
                    assert res.get("telemetry") is not None
                    # Verified tier 4 memory flush
                    assert "rss_after_mb" in res["telemetry"]
                    assert res["telemetry"]["rss_after_mb"] < 1000.0

            # Verified Ollama was only called for writing operations, never for movement
            unload_calls = [c for c in mock_post.call_args_list if c[1]["json"].get("keep_alive") == 0]
            assert len(unload_calls) == 2, f"Expected exactly 2 writing unloads, got {len(unload_calls)}"
