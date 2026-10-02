"""
Suite 4: Voice & Safety Integration Tests (R4).
Verifies:
- Vosk STT listener streaming, wake-word detection, and energy VAD.
- Kokoro-ONNX speaker silent intent execution for movement actions.
- Acoustic feedback chimes (wake, sleep, error).
- Inviolable SafetyGate C: drive restriction across path variations.
- Voice confirmation dialogs for sensitive/destructive operations (close_app, delete_file, send_message).
- Tier 1 (Feature), Tier 2 (Boundary & Corner), Tier 3 (Pairwise Combinations).
"""
from unittest.mock import MagicMock, patch
import numpy as np
import pytest

from ellie.listener import Listener
from ellie.main import EllieAssistant, SILENT_INTENTS
from ellie.safety import SafetyGate
from ellie.speaker import Speaker
from ellie.wake_word import WakeWordDetector


# ============================================================================
# TIER 1: FEATURE COVERAGE (R4 Core Behaviors)
# ============================================================================

class TestVoiceAndSafetyFeatures:
    """Tier 1: Verifies voice capture, silent intent suppression, and safety gate integration."""

    @pytest.mark.parametrize(
        "wake_phrase,expected_match",
        [
            ("hey nova", True),
            ("wake up nova", True),
            ("nova", True),
            ("hey no va", True),  # Fuzzy Vosk variant
            ("hello nova", True),
            ("random words", False),
            ("hey siri", False),
        ],
    )
    def test_vosk_wake_word_spotter(self, wake_phrase, expected_match):
        detector = WakeWordDetector()
        assert detector.is_wake_word(wake_phrase) is expected_match

    def test_listener_energy_vad_silence_detection(self):
        """Verifies RMS calculation identifies silence vs active speech audio."""
        listener = Listener()
        # Pure silence
        silence_chunk = np.zeros(4000, dtype=np.int16)
        assert listener._detect_silence(silence_chunk, threshold=500) is True

        # Loud speech signal
        speech_chunk = (np.random.randn(4000) * 5000).astype(np.int16)
        assert listener._detect_silence(speech_chunk, threshold=500) is False

    @pytest.mark.parametrize(
        "response_text,expected_confirmed",
        [
            ("yes", True),
            ("yeah", True),
            ("confirm", True),
            ("sure", True),
            ("go ahead", True),
            ("no", False),
            ("nope", False),
            ("cancel", False),
            ("don't do that", False),
            ("maybe later", False),  # Unrecognized defaults to safe False
        ],
    )
    def test_voice_confirmation_dialog_decision(self, response_text, expected_confirmed):
        listener = Listener()
        result = listener.listen_for_confirmation(simulated_response=response_text)
        assert result is expected_confirmed

    def test_movement_command_silent_intent_execution(self):
        """Movement actions MUST execute silently without spoken voice feedback."""
        assistant = EllieAssistant()
        assistant.speaker = MagicMock()
        assistant.movement_ctrl = MagicMock()
        assistant.movement_ctrl.execute_movement.return_value = {
            "success": True,
            "feedback": "Turned volume up.",
            "action": "volume_control",
        }

        # Issue movement command
        res = assistant.handle_command("volume up")

        # Movement executed
        assistant.movement_ctrl.execute_movement.assert_called_once()
        # CRITICAL: Speaker.speak must NOT be called because volume_control is in SILENT_INTENTS!
        assert "volume_control" in SILENT_INTENTS
        assistant.speaker.speak.assert_not_called()

    def test_c_drive_safety_blocks_before_execution(self):
        """Commands accessing C: drive are blocked by SafetyGate before execution."""
        assistant = EllieAssistant()
        assistant.speaker = MagicMock()
        assistant.movement_ctrl = MagicMock()

        # Command attempting to launch dangerous executable on C: drive
        res = assistant.handle_command("open C:\\Windows\\System32\\cmd.exe")

        assert res["success"] is False
        assert res.get("blocked") is True
        # Safety gate blocked execution
        assistant.movement_ctrl.execute_movement.assert_not_called()
        # Error chime played
        assistant.speaker.play_chime.assert_called_with("error")
        assistant.speaker.speak.assert_called_with("Access is restricted for safety.")

    def test_speaker_acoustic_chime_generation(self):
        """Verifies pure sine wave chime synthesis for wake, sleep, error."""
        speaker = Speaker()
        with patch("ellie.speaker.sd") as mock_sd:
            speaker.play_chime("wake")
            assert mock_sd.play.called
            speaker.play_chime("error")
            assert mock_sd.play.called


# ============================================================================
# TIER 2: BOUNDARY & ADVERSARIAL CASES
# ============================================================================

class TestVoiceSafetyBoundaryCases:
    """Tier 2: Obfuscated paths, confirmation cancellation, and multi-step dialogs."""

    @pytest.mark.parametrize(
        "obfuscated_c_path",
        [
            r"\\?\c:\Windows",
            r"c :\Windows",
            "/c:/Windows/System32",
            r"C:\..\C:\secret.txt",
            r"\\.\c:\temp",
        ],
    )
    def test_obfuscated_c_drive_patterns_blocked(self, obfuscated_c_path):
        gate = SafetyGate()
        allowed, reason = gate.check_path(obfuscated_c_path)
        assert allowed is False
        assert "blocked" in reason.lower()

    def test_destructive_action_cancelled_when_voice_confirmation_denied(self):
        """When user says 'no', close_app command is aborted without closing process."""
        assistant = EllieAssistant()
        assistant.speaker = MagicMock()
        assistant.listener = MagicMock()
        assistant.movement_ctrl = MagicMock()
        # Simulate user saying 'no'
        assistant.listener.listen_for_confirmation.return_value = False

        res = assistant.handle_command("close notepad")

        assert res["success"] is False
        assert res.get("cancelled") is True
        # App was NOT closed
        assistant.movement_ctrl.execute_movement.assert_not_called()
        assistant.speaker.speak.assert_called_with("Okay, cancelling.")

    def test_destructive_action_executed_when_voice_confirmation_approved(self):
        """When user says 'yes', close_app command proceeds to execute."""
        assistant = EllieAssistant()
        assistant.speaker = MagicMock()
        assistant.listener = MagicMock()
        assistant.movement_ctrl = MagicMock()
        assistant.movement_ctrl.execute_movement.return_value = {"success": True, "action": "app_close"}
        # Simulate user saying 'yes'
        assistant.listener.listen_for_confirmation.return_value = True

        res = assistant.handle_command("close notepad")

        assert res["success"] is True
        assistant.movement_ctrl.execute_movement.assert_called_once()


# ============================================================================
# TIER 3: PAIRWISE COMBINATORIAL COVERAGE
# ============================================================================

class TestVoiceSafetyPairwiseCombinations:
    """Tier 3: Pairwise combinations across voice inputs, intents, and safety conditions."""

    @pytest.mark.parametrize(
        "action,needs_confirm,blocked",
        [
            ("open_app", False, False),
            ("close_app", True, False),
            ("delete_file", True, False),
            ("send_message", True, False),
            ("deploy_subagent", True, False),
            ("run_shell", False, True),
            ("install_software", False, True),
            ("modify_registry", False, True),
        ],
    )
    def test_pairwise_action_safety_matrix(self, action, needs_confirm, blocked):
        gate = SafetyGate()
        res = gate.check_action(action)
        if blocked:
            assert res.allowed is False
        else:
            assert res.allowed is True
            assert res.needs_confirmation is needs_confirm

    @pytest.mark.parametrize(
        "intent_name,is_silent",
        [
            ("volume_control", True),
            ("media_control", True),
            ("navigation_scroll", True),
            ("open_app", True),
            ("general_question", False),
            ("system_query", False),
        ],
    )
    def test_pairwise_silent_intents(self, intent_name, is_silent):
        assert (intent_name in SILENT_INTENTS) is is_silent
