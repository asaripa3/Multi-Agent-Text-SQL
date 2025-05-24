def should_run_fallback(validation_result: dict) -> bool:
    """
    Determine if the fallback SQL generator should run based on the validation result.
    """
    if not validation_result:
        return False
    return not validation_result.get("is_valid", True)

def inject_fallback_step(steps: list, fallback_step: object) -> list:
    """
    Inject fallback step at the appropriate point in the step sequence.
    """
    if fallback_step.name not in [s.name for s in steps]:
        steps.append(fallback_step)
    return steps