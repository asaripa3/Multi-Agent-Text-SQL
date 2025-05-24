from typing import List, Dict, Any
from planning.agent_step import AgentStep

class Planner:
    def __init__(self, steps: List[AgentStep]):
        self.steps = steps

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        executed_steps = set()
        while True:
            progress = False
            for step in self.steps:
                print(f"Checking step: {step.name}")
                print(f"  Preconditions: {step.preconditions}")
                print(f"  Current state keys: {list(state.keys())}")
                if step.name not in executed_steps and step.is_ready(state):
                    print(f"Running agent step: {step.name}")
                    step.run(state)
                    executed_steps.add(step.name)
                    progress = True
            if not progress:
                break
        return state