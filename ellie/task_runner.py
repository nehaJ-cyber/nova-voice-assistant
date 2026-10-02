import logging
import time
from typing import Callable, Dict, List, Any

logger = logging.getLogger(__name__)

class TaskRunner:
    """Executes a list of steps by mapping them to Python tool functions."""

    def __init__(self, config: dict, speaker, listener):
        self.config = config
        self.speaker = speaker
        self.listener = listener
        self._tools: Dict[str, Callable] = {}
        
        self._register_default_tools()

    def register_tool(self, name: str, func: Callable):
        """Registers a function as an available tool."""
        self._tools[name] = func
        logger.debug(f"Registered tool: {name}")

    def _register_default_tools(self):
        """Registers built-in tools and imports all tools from the tools package."""
        # Built-in tools
        self.register_tool('log', self._tool_log)
        self.register_tool('await_confirmation', self._tool_await_confirmation)
        
        # Import all tools from the ellie.tools package
        try:
            from ellie.tools import register_all, _registry
            register_all()
            # Copy registered tools into our local dispatch table
            for name, func in _registry.items():
                self.register_tool(name, func)
            logger.info(f"Loaded {len(_registry)} tools from ellie.tools package")
        except Exception as e:
            logger.warning(f"Could not load tools package: {e}. Using built-in tools only.")
            # Register basic open_browser as fallback
            self.register_tool('open_browser', self._tool_open_browser)

    def _handle_confirmation(self, prompt: str) -> bool:
        """Asks user for confirmation and waits for response."""
        self.speaker.speak(prompt)
        # Give a small delay before listening
        time.sleep(0.5)
        return self.listener.listen_for_confirmation()

    def _execute_step(self, step: dict) -> str:
        """Dispatches a single step to the correct tool function."""
        tool_name = step.get('tool')
        if not tool_name:
            logger.warning(f"Step missing 'tool' key: {step}")
            return "Error: Step missing tool name."
            
        if tool_name not in self._tools:
            logger.warning(f"Unknown tool requested: {tool_name}")
            return f"Error: Tool '{tool_name}' not found."
            
        try:
            logger.info(f"Executing tool: {tool_name}")
            tool_func = self._tools[tool_name]
            # Pass the step args, maybe omitting 'tool' itself
            result = tool_func(step)
            return str(result)
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return f"Error executing {tool_name}: {str(e)}"

    def run_steps(self, steps: List[dict]) -> str:
        """Executes a sequence of steps, aborting if confirmation fails."""
        if not steps:
            return "No actions to execute."
            
        final_result = ""
        
        for i, step in enumerate(steps):
            logger.info(f"Running step {i+1}/{len(steps)}: {step.get('tool')}")
            
            # Special handling for explicit confirmation step
            if step.get('tool') == 'await_confirmation':
                prompt = step.get('prompt', 'Do you want to proceed?')
                confirmed = self._handle_confirmation(prompt)
                if not confirmed:
                    logger.info("User denied confirmation. Aborting remaining steps.")
                    return "Action cancelled by user."
                continue
                
            # Execute normal step
            result = self._execute_step(step)
            final_result = result
            
            # Simple check for critical errors to abort
            if result.startswith("Error:"):
                logger.error(f"Step failed, aborting sequence. Error: {result}")
                break
                
        return final_result

    # --- Basic Built-in Tools ---

    def _tool_log(self, args: dict) -> str:
        msg = args.get('message', 'No message')
        logger.info(f"Tool Log: {msg}")
        return "Logged."

    def _tool_await_confirmation(self, args: dict) -> str:
        # Handled specially in run_steps, but here for completeness
        return "Confirmed."

    def _tool_open_browser(self, args: dict) -> str:
        import webbrowser
        url = args.get('url')
        if url:
            webbrowser.open(url)
            return f"Opened browser to {url}"
        return "Error: No URL provided."
