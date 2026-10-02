import logging
import json
import re
import requests
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class Executor:
    """Interfaces with Qwen2.5-1.5B to plan and execute complex tasks."""

    def __init__(self, config: dict):
        self.config = config
        models_cfg = config.get('models', {})
        self.model_name = models_cfg.get('executor', 'qwen2.5:1.5b')
        self.host = models_cfg.get('ollama_host', 'http://127.0.0.1:11434')
        self.system_prompt = self._load_prompt('D:/Ellie/config/prompts/executor.txt', 
                                              "You are an executor. Return JSON array of steps.")
        
        import ollama
        self.client = ollama.Client(host=self.host)
        
        # Intents that don't need LLM planning
        self.simple_intents = {
            'open_app', 'google_search', 'youtube_search', 
            'system_info', 'volume_control', 'media_control',
            'general_question', 'open_url',
            'inspect_screen', 'see_screen', 'get_active_window',
            'click_element', 'scroll_screen', 'capture_screen',
            'deploy_subagent', 'list_subagents',
        }

    def _load_prompt(self, path: str, default: str) -> str:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return default

    def _unload_model(self):
        """Unloads the model to free RAM."""
        try:
            url = f"{self.host}/api/generate"
            payload = {
                "model": self.model_name,
                "keep_alive": 0
            }
            requests.post(url, json=payload)
            logger.info(f"Model {self.model_name} unloaded from memory.")
        except Exception as e:
            logger.error(f"Failed to unload executor model: {e}")

    def _should_use_executor(self, plan: dict) -> bool:
        """Determines if the LLM is needed for this intent."""
        intent = plan.get('intent', 'unknown')
        if intent in self.simple_intents:
            return False
        return True

    def generate_simple_steps(self, plan: dict) -> List[dict]:
        """Generates steps for simple intents without using the LLM."""
        intent = plan.get('intent')
        entities = plan.get('entities', {})
        response = plan.get('response', '')
        
        steps = []
        if intent == 'open_app':
            app_name = entities.get('app_name', '')
            if app_name:
                steps.append({"tool": "open_app", "app_name": app_name})
        elif intent == 'google_search':
            query = entities.get('query', '')
            browser = entities.get('browser', None)
            if query:
                steps.append({"tool": "google_search", "query": query, "browser": browser})
        elif intent == 'youtube_search':
            query = entities.get('query', '')
            browser = entities.get('browser', None)
            if query:
                steps.append({"tool": "youtube_search", "query": query, "browser": browser})
        elif intent == 'open_url':
            url = entities.get('url', '')
            browser = entities.get('browser', None)
            if url:
                steps.append({"tool": "open_browser", "url": url, "browser": browser})
        elif intent == 'general_question':
            # The orchestrator already gave us the answer in 'response' — just speak it
            steps.append({"tool": "answer_question", "text": response})
        elif intent == 'system_info':
            info_type = entities.get('info_type', 'time')
            steps.append({"tool": "get_info", "type": info_type})
        elif intent in ('inspect_screen', 'see_screen'):
            steps.append({"tool": "inspect_screen"})
        elif intent == 'get_active_window':
            steps.append({"tool": "get_active_window"})
        elif intent == 'click_element':
            element = entities.get('name') or entities.get('element') or entities.get('text')
            steps.append({"tool": "click_element", "name": element})
        elif intent == 'scroll_screen':
            direction = entities.get('direction', 'down')
            steps.append({"tool": "scroll_screen", "direction": direction})
        elif intent == 'capture_screen':
            steps.append({"tool": "capture_screen"})
        elif intent == 'deploy_subagent':
            task = entities.get('task') or entities.get('name') or 'Background Task'
            instructions = entities.get('instructions') or response
            steps.append({"tool": "deploy_subagent", "name": task, "instructions": instructions})
        elif intent == 'list_subagents':
            steps.append({"tool": "list_subagents"})
        # Add more mappings as needed
        
        if not steps:
            # Fallback if we couldn't construct simple steps
            steps.append({"tool": "log", "message": f"Could not perform simple action for {intent}"})
            
        return steps

    def _build_prompt(self, plan: dict) -> str:
        """Formats the orchestration plan into a prompt for the executor."""
        return f"Generate a JSON array of execution steps for the following plan:\n{json.dumps(plan, indent=2)}"

    def _parse_steps(self, raw: str, plan: dict) -> List[dict]:
        """Robustly parses JSON array from LLM output."""
        try:
            # Try parsing directly
            data = json.loads(raw)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'steps' in data:
                return data['steps']
        except json.JSONDecodeError:
            pass
            
        try:
            # Extract JSON array from markdown
            match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', raw, re.DOTALL)
            if match:
                return json.loads(match.group(1))
                
            # Find anything resembling a JSON array
            match = re.search(r'\[.*\]', raw, re.DOTALL)
            if match:
                return json.loads(match.group(0))
        except Exception as e:
            logger.error(f"Failed to extract JSON array from executor response: {e}")

        logger.warning("Failed to parse steps, generating fallback step.")
        # Fallback step
        return [{"tool": "log", "message": f"Execution parsing failed for intent: {plan.get('intent')}"}]

    def execute(self, plan: dict) -> List[dict]:
        """Takes an orchestration plan and generates execution steps."""
        if not self._should_use_executor(plan):
            logger.info(f"Skipping executor LLM for simple intent: {plan.get('intent')}")
            return self.generate_simple_steps(plan)
            
        try:
            logger.info(f"Calling Executor LLM ({self.model_name}) for complex intent: {plan.get('intent')}")
            prompt = self._build_prompt(plan)
            
            response = self.client.chat(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                options={
                    "temperature": 0.1,
                    "num_predict": 512
                }
            )
            
            raw_content = response['message']['content']
            logger.debug(f"Raw executor response: {raw_content}")
            
            steps = self._parse_steps(raw_content, plan)
            self._unload_model()
            return steps
            
        except Exception as e:
            logger.error(f"Error communicating with Executor LLM: {e}")
            self._unload_model()
            return [{"tool": "log", "message": f"Executor error: {str(e)}"}]
