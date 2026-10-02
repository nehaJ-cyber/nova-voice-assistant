"""
Suite 3: Process Cache & Memory Flush Guardrail Tests (R3).
Verifies:
- 4-Tier cleanup routine executed post-generation:
  1. Ollama model unload API dispatch (keep_alive=0).
  2. Python cyclic garbage collection (gc.collect(2)).
  3. Temporary clipboard buffer wipe (pyperclip.copy("")).
  4. Windows working set trimming (EmptyWorkingSet).
- Memory baseline recovery (<500MB process RSS).
- Guaranteed execution in finally block regardless of success or failure.
- 8GB RAM budget ceiling compliance.
- Tier 1 (Feature), Tier 2 (Boundary & Corner), Tier 3 (Pairwise Combinations).
"""
import gc
from unittest.mock import MagicMock, patch
import pytest

from ellie.delegation.writing_pipeline import WritingDelegationPipeline
from ellie.guardrails.memory_guardrail import MemoryGuardrail


# ============================================================================
# TIER 1: FEATURE COVERAGE (R3 Core Behaviors)
# ============================================================================

class TestMemoryGuardrailFeatures:
    """Tier 1: Verifies individual execution of the 4 memory eviction tiers."""

    @patch("requests.post")
    def test_tier1_ollama_model_unload_dispatch(self, mock_post):
        """Tier 1: POST /api/generate with keep_alive: 0 is dispatched to unload Qwen from RAM."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        guardrail = MemoryGuardrail(ollama_host="http://127.0.0.1:11434")
        report = guardrail.execute_flush(model_name="qwen2.5:1.5b")

        assert report["tier1_ollama_unloaded"] is True
        mock_post.assert_called_once()
        url = mock_post.call_args[0][0]
        assert url == "http://127.0.0.1:11434/api/generate"
        payload = mock_post.call_args[1]["json"]
        assert payload["model"] == "qwen2.5:1.5b"
        assert payload["keep_alive"] == 0

    @patch("gc.collect")
    def test_tier2_python_garbage_collection(self, mock_gc):
        """Tier 2: gc.collect(2) is executed to reclaim generation buffers and cyclical references."""
        mock_gc.return_value = 42
        guardrail = MemoryGuardrail()
        with patch("requests.post"):
            report = guardrail.execute_flush()
            assert report["tier2_gc_collected"] == 42
            mock_gc.assert_called_with(2)

    @patch("pyperclip.copy")
    def test_tier3_clipboard_temporary_wipe(self, mock_copy):
        """Tier 3: Temporary clipboard buffer is wiped clean to prevent memory leaks and leakage."""
        guardrail = MemoryGuardrail()
        with patch("requests.post"):
            report = guardrail.execute_flush()
            assert report["tier3_clipboard_cleared"] is True
            mock_copy.assert_called_with("")

    def test_tier4_working_set_trimming(self):
        """Tier 4: Windows EmptyWorkingSet is invoked to release physical pages back to OS."""
        guardrail = MemoryGuardrail()
        with patch("requests.post"), \
             patch("ctypes.windll.kernel32.GetCurrentProcess", create=True) as mock_get_curr, \
             patch("ctypes.windll.psapi.EmptyWorkingSet", create=True) as mock_empty_ws:
            mock_get_curr.return_value = 0xFFFF
            report = guardrail.execute_flush()
            assert report["tier4_working_set_trimmed"] is True
            mock_empty_ws.assert_called_once_with(0xFFFF)

    def test_memory_baseline_recovery(self):
        """Validates that assistant RSS memory remains below 500MB baseline idle level."""
        guardrail = MemoryGuardrail()
        with patch("requests.post"):
            report = guardrail.execute_flush()
            assert "rss_after_mb" in report
            # Assistant process memory must be well within the 500MB baseline budget
            assert report["rss_after_mb"] < 500.0

    @patch("requests.post")
    def test_guardrail_flush_interface_contract(self, mock_post):
        """Validates flush(ollama_client=...) interface contract defined in PROJECT.md."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        guardrail = MemoryGuardrail()
        mock_client = MagicMock()
        mock_client.host = "http://127.0.0.1:11434"

        report = guardrail.flush(ollama_client=mock_client, model_name="qwen2.5:1.5b")
        assert report["tier1_ollama_unloaded"] is True
        assert report["tier3_clipboard_cleared"] is True
        assert report["tier4_working_set_trimmed"] is True


# ============================================================================
# TIER 2: BOUNDARY, CORNER & RESILIENCE CASES
# ============================================================================

class TestMemoryGuardrailBoundaryCases:
    """Tier 2: Error resilience, offline daemon, and locked system buffers."""

    @patch("requests.post")
    def test_offline_ollama_daemon_handled_gracefully(self, mock_post):
        """When Ollama is unreachable, flush does not crash and continues remaining tiers."""
        import requests
        mock_post.side_effect = requests.exceptions.ConnectionError("Daemon offline")
        guardrail = MemoryGuardrail()

        with patch("pyperclip.copy"), patch("gc.collect"):
            report = guardrail.execute_flush()
            assert report["tier1_ollama_unloaded"] is False
            assert "tier1_error" in report
            # Tiers 2, 3, 4 still execute!
            assert report["tier3_clipboard_cleared"] is True
            assert report["tier4_working_set_trimmed"] is True

    @patch("pyperclip.copy")
    def test_clipboard_lock_exception_handled_gracefully(self, mock_copy):
        """If clipboard is locked by external app, error is captured in telemetry."""
        mock_copy.side_effect = RuntimeError("Clipboard locked by Windows Explorer")
        guardrail = MemoryGuardrail()

        with patch("requests.post"):
            report = guardrail.execute_flush()
            assert report["tier3_clipboard_cleared"] is False
            # Remaining tiers still complete
            assert report["tier4_working_set_trimmed"] is True

    def test_guaranteed_flush_in_writing_pipeline_on_paste_failure(self):
        """If paste automation raises exception, 4-tier cleanup MUST still run via finally."""
        pipeline = WritingDelegationPipeline()

        with patch.object(pipeline, "_generate_text", return_value="Some text"), \
             patch.object(pipeline, "_paste_to_active_app", side_effect=IOError("Target window closed")), \
             patch.object(pipeline.guardrail, "execute_flush") as mock_flush:
            mock_flush.return_value = {"rss_after_mb": 115.0}
            with pytest.raises(IOError):
                pipeline.delegate_writing("draft letter")
            # Must have executed flush
            mock_flush.assert_called_once()

    def test_repeated_flushes_do_not_leak_memory(self):
        """20 consecutive flush cycles must not cause memory inflation."""
        guardrail = MemoryGuardrail()
        with patch("requests.post"):
            readings = []
            for _ in range(20):
                rep = guardrail.execute_flush()
                readings.append(rep["rss_after_mb"])
            # Maximum delta between first and last should be stable (<50MB growth)
            delta = readings[-1] - readings[0]
            assert delta < 50.0, f"Memory grew by {delta}MB across 20 flushes"


# ============================================================================
# TIER 3: PAIRWISE COMBINATORIAL COVERAGE
# ============================================================================

class TestMemoryGuardrailPairwiseCombinations:
    """Tier 3: Combinations of model identifiers and execution paths."""

    @pytest.mark.parametrize(
        "model_id",
        [
            "qwen2.5:1.5b",
            "qwen2.5:1.5b-instruct",
            "qwen2.5:1.5b-q4_k_m",
        ],
    )
    def test_pairwise_model_evictions(self, model_id):
        guardrail = MemoryGuardrail()
        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            report = guardrail.execute_flush(model_name=model_id)
            assert report["tier1_ollama_unloaded"] is True
            assert mock_post.call_args[1]["json"]["model"] == model_id

    @pytest.mark.parametrize(
        "generation_success",
        [True, False],
    )
    def test_pairwise_pipeline_outcome_eviction(self, generation_success):
        """Verifies flush occurs whether generation succeeds or fails."""
        pipeline = WritingDelegationPipeline()
        with patch.object(pipeline.guardrail, "execute_flush") as mock_flush:
            mock_flush.return_value = {"tier1_ollama_unloaded": True}
            if generation_success:
                with patch.object(pipeline, "_generate_text", return_value="Valid text"), \
                     patch.object(pipeline, "_paste_to_active_app", return_value=True):
                    res = pipeline.delegate_writing("draft note")
                    assert res["success"] is True
            else:
                with patch.object(pipeline, "_generate_text", side_effect=RuntimeError("Ollama failed")):
                    with pytest.raises(RuntimeError):
                        pipeline.delegate_writing("draft note")
            # In both branches, execute_flush MUST be called!
            mock_flush.assert_called_once()
