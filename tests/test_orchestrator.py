"""
Baseline Orchestrator Tests: Validates JSON parsing and fast-path routing.
Total test count: 7 tests.
"""
from unittest.mock import MagicMock
from ellie.orchestrator import Orchestrator


class TestResponseParsing:
    """5 response parsing tests."""

    def test_parse_clean_json(self):
        orch = Orchestrator()
        raw = '{"action": "open_app", "entities": {"target": "chrome"}}'
        parsed = orch.parse_response(raw)
        assert parsed["action"] == "open_app"
        assert parsed["entities"]["target"] == "chrome"

    def test_parse_markdown_json(self):
        orch = Orchestrator()
        raw = '```json\n{"action": "close_app", "entities": {"target": "notepad"}}\n```'
        parsed = orch.parse_response(raw)
        assert parsed["action"] == "close_app"
        assert parsed["entities"]["target"] == "notepad"

    def test_parse_strips_preamble(self):
        orch = Orchestrator()
        raw = 'Here is the plan:\n{"action": "volume_control", "entities": {"steps": 5}}\nHope this helps!'
        parsed = orch.parse_response(raw)
        assert parsed["action"] == "volume_control"

    def test_parse_malformed_json_fallback(self):
        orch = Orchestrator()
        raw = 'This is completely broken {not valid json'
        parsed = orch.parse_response(raw)
        assert parsed["action"] == "unknown"
        assert "error" in parsed

    def test_parse_empty_response(self):
        orch = Orchestrator()
        parsed = orch.parse_response("")
        assert parsed["action"] == "unknown"


class TestProcessing:
    """2 processing tests."""

    def test_process_fast_path(self):
        mock_ollama = MagicMock()
        orch = Orchestrator(ollama_client=mock_ollama)
        res = orch.process("open chrome")
        assert res["action"] == "open_app"
        assert res.get("fast_path") is True
        # Fast path must NOT call Ollama
        mock_ollama.chat.assert_not_called()

    def test_process_returns_valid_plan(self):
        mock_ollama = MagicMock()
        mock_ollama.chat.return_value = {
            "message": {"content": '{"action": "general_question", "entities": {"query": "einstein"}}'}
        }
        orch = Orchestrator(ollama_client=mock_ollama)
        res = orch.process("who was einstein")
        assert res["action"] == "general_question"
        assert res.get("fast_path") is False
        mock_ollama.chat.assert_called_once()
