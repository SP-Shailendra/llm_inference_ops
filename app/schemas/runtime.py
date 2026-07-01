"""
Runtime Context Schema

This module defines the execution context that flows through the
Enterprise Runtime Controller.

Instead of passing multiple objects between stages, the RuntimeContext
acts as a single source of truth during the lifecycle of an inference
request.

Future Extensions:
------------------
✓ Budget Engine
✓ Policy Engine
✓ Provider Manager
✓ Canary Deployments
✓ Rollback
✓ Guardrails
✓ RAG
✓ Streaming
✓ AI Advisor
✓ Forecasting
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field

from app.schemas.request import InferenceRequest
from app.schemas.response import InferenceResponse
from app.schemas.config import InferenceProfile


class RuntimeMetrics(BaseModel):
    """
    Internal runtime metrics.

    These are platform-level metrics and should not be confused with
    LLM inference metrics returned to the client.
    """

    execution_time_ms: float = 0.0

    governance_time_ms: float = 0.0

    routing_time_ms: float = 0.0

    cache_lookup_time_ms: float = 0.0

    inference_time_ms: float = 0.0

    telemetry_time_ms: float = 0.0


class RuntimeWarnings(BaseModel):
    warnings: List[str] = Field(default_factory=list)

    def add(self, message: str):
        self.warnings.append(message)


class RuntimeContext(BaseModel):
    """
    Shared runtime object passed through every execution stage.
    """

    ####################################################################
    # Incoming Request
    ####################################################################

    request: InferenceRequest

    ####################################################################
    # Governance
    ####################################################################

    profile: Optional[InferenceProfile] = None

    ####################################################################
    # Routing
    ####################################################################

    selected_model: Optional[str] = None

    selected_provider: Optional[str] = None

    ####################################################################
    # Cache
    ####################################################################

    cache_enabled: bool = False

    cache_hit: bool = False

    cached_response: Optional[InferenceResponse] = None

    ####################################################################
    # Prompt Optimization
    ####################################################################

    original_prompt: Optional[str] = None

    optimized_prompt: Optional[str] = None

    prompt_compressed: bool = False

    ####################################################################
    # Agentic Execution
    ####################################################################

    agent_mode: bool = False

    agent_steps: int = 1

    ####################################################################
    # Response
    ####################################################################

    response: Optional[InferenceResponse] = None

    ####################################################################
    # Runtime Metadata
    ####################################################################

    metrics: RuntimeMetrics = Field(
        default_factory=RuntimeMetrics
    )

    warnings: RuntimeWarnings = Field(
        default_factory=RuntimeWarnings
    )

    ####################################################################
    # Future Modules
    ####################################################################

    budget: Dict[str, Any] = Field(default_factory=dict)

    policy: Dict[str, Any] = Field(default_factory=dict)

    advisor: Dict[str, Any] = Field(default_factory=dict)

    telemetry: Dict[str, Any] = Field(default_factory=dict)

    tags: Dict[str, Any] = Field(default_factory=dict)