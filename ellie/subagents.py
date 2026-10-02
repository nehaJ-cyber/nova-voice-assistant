"""
Subagent lifecycle and background worker management.
"""
import threading
import time
from typing import Dict, Any, Optional


class SubagentManager:
    """Manages background task subagents."""

    def __init__(self):
        self.active_agents: Dict[str, Dict[str, Any]] = {}

    def deploy_subagent(self, agent_id: str, task: str) -> bool:
        """Deploys a background subagent."""
        if not agent_id or not task:
            return False

        def _worker():
            self.active_agents[agent_id] = {"status": "running", "task": task}
            time.sleep(0.1)
            self.active_agents[agent_id]["status"] = "completed"

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        self.active_agents[agent_id] = {"status": "started", "task": task}
        return True

    def get_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        return self.active_agents.get(agent_id)
