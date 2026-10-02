"""Background Subagent Manager for Ellie/Nova.
Allows Nova to spawn, track, and manage background helper subagents
for multi-step tasks, research, and screen monitoring with user permission.
"""
import logging
import threading
import time
import uuid
from typing import Dict, Any, Callable

logger = logging.getLogger(__name__)

class Subagent:
    """Represents a single background worker subagent."""
    def __init__(self, agent_id: str, name: str, task_fn: Callable, args: tuple = ()):
        self.agent_id = agent_id
        self.name = name
        self.task_fn = task_fn
        self.args = args
        self.status = "idle"
        self.result = None
        self.error = None
        self._thread = None
        self._stop_event = threading.Event()

    def start(self):
        self.status = "running"
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info(f"Subagent '{self.name}' ({self.agent_id}) started.")

    def _run(self):
        try:
            self.result = self.task_fn(self._stop_event, *self.args)
            self.status = "completed"
            logger.info(f"Subagent '{self.name}' completed successfully.")
        except Exception as e:
            self.error = str(e)
            self.status = "failed"
            logger.error(f"Subagent '{self.name}' encountered error: {e}")

    def stop(self):
        self._stop_event.set()
        self.status = "stopped"
        logger.info(f"Subagent '{self.name}' requested to stop.")

class SubagentManager:
    """Manages active subagents across Nova."""
    def __init__(self):
        self._subagents: Dict[str, Subagent] = {}
        self._lock = threading.Lock()

    def spawn(self, name: str, task_fn: Callable, args: tuple = ()) -> str:
        agent_id = f"subagent-{uuid.uuid4().hex[:6]}"
        agent = Subagent(agent_id, name, task_fn, args)
        with self._lock:
            self._subagents[agent_id] = agent
        agent.start()
        return agent_id

    def list_active(self) -> list[dict]:
        with self._lock:
            return [
                {
                    "id": a.agent_id,
                    "name": a.name,
                    "status": a.status,
                    "result": a.result,
                    "error": a.error
                }
                for a in self._subagents.values()
            ]

    def stop(self, agent_id: str) -> bool:
        with self._lock:
            if agent_id in self._subagents:
                self._subagents[agent_id].stop()
                return True
        return False

# Global instance
manager = SubagentManager()

def deploy_subagent(step: dict) -> str:
    """Tool handler to deploy a background subagent."""
    task_name = step.get('name') or step.get('task') or 'Background Task'
    instructions = step.get('instructions') or step.get('query') or ''

    def _worker_task(stop_event, instructions_text):
        logger.info(f"Subagent executing task: {instructions_text}")
        # Perform task (e.g. background search or screen check)
        time.sleep(1.0)
        return f"Completed: {instructions_text}"

    agent_id = manager.spawn(task_name, _worker_task, (instructions,))
    return f"Deployed subagent '{task_name}' (ID: {agent_id}) in the background."

def list_subagents(step: dict) -> str:
    """Lists currently deployed subagents."""
    active = manager.list_active()
    if not active:
        return "No background subagents are currently running."
    summary = [f"{a['name']} ({a['status']})" for a in active]
    return f"Active subagents: {', '.join(summary)}"
