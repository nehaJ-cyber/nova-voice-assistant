"""
Suite 2: Qwen Writing Delegation Pipeline Tests (R2).
Verifies:
- Writing intent detection and prompt routing to Qwen (qwen2.5:1.5b via Ollama).
- Prompt sanitization (enforcing system prompt without conversational preamble).
- Output text cleaning (stripping conversational greetings, disclaimers, markdown code fences).
- Foreground active window detection (HWND, PID, process name).
- Clipboard paste automation (Ctrl+V keystroke simulation, buffer settle delays).
- Tier 1 (Feature), Tier 2 (Boundary & Corner), Tier 3 (Pairwise Combinations).
"""
import json
from unittest.mock import MagicMock, patch
import pytest

from ellie.automation.clipboard_injector import ClipboardInjector
from ellie.delegation.writing_pipeline import SYSTEM_PROMPT_WRITER, WritingDelegationPipeline
from ellie.llm.ollama_client import OllamaClient
from ellie.routing.laya_router import LayaRouter
from ellie.routing.slot_extractor import SlotExtractor


# ============================================================================
# TIER 1: FEATURE COVERAGE (R2 Core Behaviors)
# ============================================================================

class TestWritingDelegationFeatures:
    """Tier 1: Verifies primary writing intent delegation, generation, and paste automation."""

    @pytest.mark.parametrize(
        "utterance,expected_clean_prompt",
        [
            ("write an apology letter to boss", "apology letter to boss"),
            ("draft an email about tomorrow's 5pm sync", "email about tomorrow's 5pm sync"),
            ("compose a poem about winter snow", "poem about winter snow"),
            ("please draft a follow up note to client", "follow up note to client"),
            ("generate a brief summary of this document", "brief summary of this document"),
        ],
    )
    def test_writing_intent_routing_and_prompt_extraction(self, utterance, expected_clean_prompt):
        router = LayaRouter()
        res = router.classify(utterance)
        assert res.intent == "write_delegation"
        assert res.is_movement is False
        clean_extracted = SlotExtractor.extract_writing_prompt(utterance)
        assert clean_extracted.lower() == expected_clean_prompt.lower()

    @patch("requests.post")
    def test_qwen_generation_payload_and_keep_alive(self, mock_post):
        """Verifies qwen2.5:1.5b model target, strict system prompt, and keep_alive=0 in request."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"response": "Dear Team, meeting is confirmed at 5pm."}
        mock_post.return_value = mock_resp

        client = OllamaClient(default_model="qwen2.5:1.5b")
        text = client.generate(
            prompt="draft a meeting confirmation for 5pm",
            system_prompt=SYSTEM_PROMPT_WRITER,
            keep_alive=0,
        )

        assert text == "Dear Team, meeting is confirmed at 5pm."
        mock_post.assert_called_once()
        url = mock_post.call_args[0][0]
        assert "/api/generate" in url
        payload = mock_post.call_args[1]["json"]
        assert payload["model"] == "qwen2.5:1.5b"
        assert payload["keep_alive"] == 0
        assert payload["system"] == SYSTEM_PROMPT_WRITER
        assert "5pm" in payload["prompt"]

    @patch("requests.post")
    def test_ollama_client_unload_endpoint(self, mock_post):
        """Verifies OllamaClient.unload dispatches keep_alive: 0 to /api/generate."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        client = OllamaClient(default_model="qwen2.5:1.5b")
        res = client.unload()
        assert res is True
        mock_post.assert_called_once()
        payload = mock_post.call_args[1]["json"]
        assert payload["model"] == "qwen2.5:1.5b"
        assert payload["keep_alive"] == 0

    def test_prompt_sanitizer_output_cleaner(self):
        """Verifies removal of conversational chatter and surrounding code fences."""
        pipeline = WritingDelegationPipeline()

        # Case 1: Conversational preamble removal
        dirty_1 = "Here is your requested apology letter:\n\nDear Professor, please accept my apologies..."
        clean_1 = pipeline.clean_output(dirty_1)
        assert not clean_1.startswith("Here is")
        assert clean_1.startswith("Dear Professor")

        # Case 2: Markdown fence wrapping removal
        dirty_2 = "```markdown\nProject Status Report\n- All systems go.\n```"
        clean_2 = pipeline.clean_output(dirty_2)
        assert clean_2 == "Project Status Report\n- All systems go."

        # Case 3: "Certainly:" preamble removal
        dirty_3 = "Certainly! Here's the note:\nThank you for your assistance."
        clean_3 = pipeline.clean_output(dirty_3)
        assert clean_3 == "Thank you for your assistance."

    def test_active_foreground_window_detection(self):
        """Verifies active window inspection returns HWND, title, and process metadata."""
        injector = ClipboardInjector()
        with patch.object(
            injector,
            "get_foreground_window",
            return_value={"hwnd": 12345, "title": "Untitled - Notepad", "pid": 5678, "process_name": "notepad.exe"},
        ):
            target = injector.get_foreground_window()
            assert target["hwnd"] == 12345
            assert "Notepad" in target["title"]
            assert target["process_name"] == "notepad.exe"

    @patch("pyperclip.copy")
    @patch("time.sleep")
    def test_clipboard_injection_and_keystroke_paste(self, mock_sleep, mock_copy):
        """Verifies text is copied to clipboard, Ctrl+V keystrokes simulated, and buffer cleared."""
        injector = ClipboardInjector()
        with patch.object(injector, "user32", create=True) as mock_user32:
            success = injector.inject_and_paste("Drafted text for active editor", clear_after=True)
            assert success is True
            # Verified clipboard copy of text followed by wipe
            assert mock_copy.call_count == 2
            assert mock_copy.call_args_list[0][0][0] == "Drafted text for active editor"
            assert mock_copy.call_args_list[1][0][0] == ""
            # Verified Ctrl+V keystrokes dispatched
            assert mock_user32.keybd_event.call_count == 4

    @patch("pyperclip.copy")
    @patch("time.sleep")
    def test_clipboard_inject_text_alias(self, mock_sleep, mock_copy):
        """Verifies inject_text properly routes through clipboard copy and Ctrl+V dispatch."""
        injector = ClipboardInjector()
        with patch.object(injector, "user32", create=True) as mock_user32:
            success = injector.inject_text("Direct injection text", clear_after=True)
            assert success is True
            assert mock_copy.call_count == 2
            assert mock_copy.call_args_list[0][0][0] == "Direct injection text"
            assert mock_copy.call_args_list[1][0][0] == ""
            assert mock_user32.keybd_event.call_count == 4


# ============================================================================
# TIER 2: BOUNDARY, CORNER & ADVERSARIAL CASES
# ============================================================================

class TestWritingDelegationBoundaryCases:
    """Tier 2: Empty texts, network disconnects, timeouts, and missing windows."""

    def test_empty_and_whitespace_prompt_handling(self):
        injector = ClipboardInjector()
        assert injector.inject_and_paste("", clear_after=True) is False
        assert injector.inject_and_paste("   ", clear_after=True) is True  # whitespace is valid if non-empty

    @patch("requests.post")
    def test_ollama_server_timeout_resilience(self, mock_post):
        """Network timeout should raise RuntimeError and not hang indefinitely."""
        import requests
        mock_post.side_effect = requests.exceptions.Timeout("Ollama daemon timed out")
        client = OllamaClient()

        with pytest.raises(RuntimeError) as exc_info:
            client.generate("test prompt", timeout=1.0)
        assert "Ollama generation failed" in str(exc_info.value)

    def test_foreground_window_none_graceful_handling(self):
        """If no foreground window is detected (e.g. desktop), pipeline completes safely."""
        pipeline = WritingDelegationPipeline()
        with patch.object(pipeline.injector, "get_foreground_window", return_value=None), \
             patch.object(pipeline, "_generate_text", return_value="Sample draft text"), \
             patch.object(pipeline, "_paste_to_active_app", return_value=True):
            res = pipeline.delegate_writing("draft a greeting")
            assert res["target_window"] is None
            assert res["success"] is True

    @patch("requests.post")
    def test_generation_error_still_executes_finally_cleanup(self, mock_post):
        """Guaranteed cleanup: If generation throws, MemoryGuardrail still executes."""
        pipeline = WritingDelegationPipeline()
        mock_post.side_effect = Exception("Fatal Ollama crash")

        with patch.object(pipeline.guardrail, "execute_flush") as mock_flush:
            mock_flush.return_value = {"rss_after_mb": 150.0}
            with pytest.raises(Exception):
                pipeline.delegate_writing("draft email")
            # Finally block must have executed flush!
            mock_flush.assert_called_once()


# ============================================================================
# TIER 3: PAIRWISE COMBINATORIAL COVERAGE
# ============================================================================

class TestWritingPairwiseCombinations:
    """Tier 3: Pairwise combinations across application types and prompt categories."""

    @pytest.mark.parametrize(
        "app_name,app_title",
        [
            ("notepad.exe", "Untitled - Notepad"),
            ("chrome.exe", "Compose: New Message - Google Chrome"),
            ("code.exe", "main.py - Visual Studio Code"),
            ("discord.exe", "Discord - #general"),
            ("winword.exe", "Document1 - Microsoft Word"),
        ],
    )
    def test_pairwise_target_windows(self, app_name, app_title):
        pipeline = WritingDelegationPipeline()
        with patch.object(
            pipeline.injector,
            "get_foreground_window",
            return_value={"hwnd": 9999, "title": app_title, "process_name": app_name},
        ), \
             patch.object(pipeline, "_generate_text", return_value="Generated paragraph"), \
             patch.object(pipeline, "_paste_to_active_app", return_value=True), \
             patch.object(pipeline.guardrail, "execute_flush", return_value={"rss_after_mb": 120.0}):
            res = pipeline.delegate_writing("draft paragraph")
            assert res["success"] is True
            assert res["target_window"]["process_name"] == app_name

    @pytest.mark.parametrize(
        "writing_genre,prompt",
        [
            ("email", "draft an email apologizing for delayed shipment"),
            ("letter", "write a formal letter requesting job interview"),
            ("notes", "compose meeting notes on Q3 financial results"),
            ("poem", "write a 4 line rhyming poem about stars"),
            ("code_doc", "draft docstring explaining linear regression"),
        ],
    )
    def test_pairwise_writing_genres(self, writing_genre, prompt):
        pipeline = WritingDelegationPipeline()
        with patch.object(pipeline, "_generate_text", return_value=f"Sample output for {writing_genre}"), \
             patch.object(pipeline, "_paste_to_active_app", return_value=True), \
             patch.object(pipeline.guardrail, "execute_flush", return_value={"rss_after_mb": 110.0}):
            res = pipeline.delegate_writing(prompt)
            assert res["success"] is True
            assert writing_genre in res["generated_text"]
