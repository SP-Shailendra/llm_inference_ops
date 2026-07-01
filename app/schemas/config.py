from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class FeatureFlags(BaseModel):
    enable_cache: bool = True
    enable_prompt_compression: bool = False
    enable_agentic_loop: bool = False
    enable_streaming: bool = True
    enable_auto_routing: bool = True
    enable_speculative_decoding: bool = False
    enable_canary: bool = False
    enable_rollback: bool = False


class RuntimeLimits(BaseModel):
    max_tokens: int = 1024
    temperature: float = 0.7
    top_p: float = 0.95
    max_cost_per_request: float = 0.05
    timeout_seconds: int = 60
    rollback_ttft_ms: float = 1500.0
    rollback_cooldown_seconds: int = 300


class RoutingPolicy(BaseModel):
    primary_model: str = "llama-3.1-8b-instant"
    fallback_model: str = "llama-3.1-8b-instant"
    auto_route: bool = True
    canary_model: Optional[str] = None
    canary_provider: Optional[str] = None
    canary_traffic_percent: int = 5


class BudgetPolicy(BaseModel):
    daily_budget_usd: float = 50.0
    monthly_budget_usd: float = 1000.0
    warning_threshold_percent: int = 80


class AgentControls(BaseModel):
    """Agent circuit breaker and cost containment settings"""
    enable_agent_loop: bool = False
    max_calls_per_session: int = 20
    max_cost_per_session_usd: float = 0.50
    max_duration_seconds: int = 300
    timeout_behavior: str = "stop"  # "stop" or "degrade"


class TrafficSplit(BaseModel):
    """Canary traffic distribution"""
    primary_model: str
    primary_percent: int = 95
    canary_model: Optional[str] = None
    canary_percent: int = 5


class RollbackTriggers(BaseModel):
    """Auto-rollback thresholds for canary deployments"""
    ttft_ms_threshold: float = 1500.0
    cost_multiplier_threshold: float = 1.3
    error_rate_threshold: float = 0.05
    check_window_seconds: int = 60


class Metadata(BaseModel):
    created_by: str = "system"
    version: str = "1.0"
    description: str = ""
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class InferenceProfile(BaseModel):
    profile_name: str

    runtime: RuntimeLimits = RuntimeLimits()

    features: FeatureFlags = FeatureFlags()

    routing: RoutingPolicy = RoutingPolicy()

    budget: BudgetPolicy = BudgetPolicy()
    
    # NEW: Agent cost controls
    agent: AgentControls = AgentControls()
    
    # NEW: Canary deployment config
    traffic_split: Optional[TrafficSplit] = None
    rollback_triggers: Optional[RollbackTriggers] = RollbackTriggers()

    metadata: Metadata = Metadata()