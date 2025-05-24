from typing import Callable, List, Dict, Any
from state.shared_state import update_state

class AgentStep:
    def __init__(self, name: str, agent: Any, preconditions: List[str], effects: List[str]):
        self.name = name
        self.agent = agent
        self.preconditions = preconditions
        self.effects = effects

    def is_ready(self, state: Dict[str, Any]) -> bool:
        return all(key in state for key in self.preconditions)

    def run(self, state: Dict[str, Any]) -> None:
        if not self.is_ready(state):
            raise RuntimeError(f"Preconditions not met for agent: {self.name}")

        print(f"Running agent step: {self.name}")
        result = self.agent.run(state)
        for key, value in result.items():
            update_state(key, value)