"""
Ollama Client for Ellie / Nova.
Handles communication with local Ollama daemon for Qwen text generation.
Enforces keep_alive=0 to prevent RAM retention on 8GB machines.
"""
from typing import Optional, Dict, Any
import requests
import logging

logger = logging.getLogger(__name__)


class OllamaClient:
    def __init__(self, host: str = "http://127.0.0.1:11434", default_model: str = "qwen2.5:1.5b"):
        self.host = host.rstrip("/")
        self.default_model = default_model

    def is_alive(self) -> bool:
        try:
            r = requests.get(f"{self.host}/api/tags", timeout=2.0)
            return r.status_code == 200
        except Exception:
            return False

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        keep_alive: int = 0,
        temperature: float = 0.7,
        num_predict: int = 512,
        timeout: float = 30.0,
    ) -> str:
        target_model = model or self.default_model
        payload: Dict[str, Any] = {
            "model": target_model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": keep_alive,
            "options": {
                "temperature": temperature,
                "num_predict": num_predict,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        url = f"{self.host}/api/generate"
        try:
            response = requests.post(url, json=payload, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "").strip()
        except requests.exceptions.RequestException as e:
            logger.error("Ollama generate request failed: %s", e)
            raise RuntimeError(f"Ollama generation failed: {e}") from e

    def unload_model(self, model: Optional[str] = None) -> bool:
        target_model = model or self.default_model
        url = f"{self.host}/api/generate"
        try:
            response = requests.post(
                url,
                json={"model": target_model, "keep_alive": 0},
                timeout=5.0,
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning("Failed to unload model %s: %s", target_model, e)
            return False

    def unload(self, model: Optional[str] = None) -> bool:
        """Standalone unload endpoint alias."""
        return self.unload_model(model=model)
