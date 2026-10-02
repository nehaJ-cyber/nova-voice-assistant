"""
Baseline Speaker Tests: Validates Kokoro-ONNX initialization and audio dispatch.
Total test count: 2 tests.
"""
from unittest.mock import patch, MagicMock
import numpy as np
from ellie.speaker import Speaker


def test_initialization():
    with patch("ellie.speaker.Kokoro") as mock_kokoro:
        speaker = Speaker(
            model_path="test_model.onnx",
            voices_path="test_voices.bin",
            default_voice="af_bella",
            speed=1.2,
        )
        assert speaker.default_voice == "af_bella"
        assert speaker.speed == 1.2
        mock_kokoro.assert_called_once_with("test_model.onnx", "test_voices.bin")


def test_speak_generates_audio():
    with patch("ellie.speaker.Kokoro") as mock_kokoro, \
         patch("ellie.speaker.sd") as mock_sd:
        mock_engine = MagicMock()
        mock_kokoro.return_value = mock_engine
        fake_samples = np.zeros(24000, dtype=np.float32)
        mock_engine.create.return_value = (fake_samples, 24000)

        speaker = Speaker()
        speaker.speak("Hello world")

        mock_engine.create.assert_called_once_with("Hello world", voice="af_bella", speed=1.0, lang="en-us")
        mock_sd.play.assert_called_once_with(fake_samples, 24000)
        mock_sd.wait.assert_called_once()
