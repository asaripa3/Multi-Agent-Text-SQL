from typing import Any, Dict

# Global state dictionary
_agent_state: Dict[str, Any] = {}

def get_state(key: str) -> Any:
    return _agent_state.get(key)

def update_state(key: str, value: Any) -> None:
    _agent_state[key] = value

def reset_state() -> None:
    global _agent_state
    _agent_state = {}

def get_full_state() -> Dict[str, Any]:
    return dict(_agent_state)

def get_state_reference():
    return _agent_state  # the global dict object