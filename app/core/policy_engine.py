from app.schemas.config import InferenceProfile
from app.core.exceptions import PolicyViolationException

class PolicyEngine:
    """
    Enforces runtime constraints and safety guardrails.
    """
    def validate_runtime_constraints(self, profile: InferenceProfile, estimated_cost: float):
        # Enforce hard cost limit per request
        if estimated_cost > profile.runtime.max_cost_per_request:
            raise PolicyViolationException(
                f"Request exceeds allowed cost per request: ${profile.runtime.max_cost_per_request}"
            )
        
        # Enforce temperature bounds
        if not (0 <= profile.runtime.temperature <= 2):
            raise PolicyViolationException("Temperature must be between 0 and 2.")

policy_engine = PolicyEngine()