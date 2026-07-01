from pydantic import BaseModel, Field
from typing import List, Optional

class InferenceMetrics(BaseModel):
    ttft_ms: float          # Time to First Token in milliseconds
    tpot_ms: float          # Time Per Output Token in milliseconds
    total_latency_ms: float # Total request time
    input_tokens: int       # Prompt size
    output_tokens: int      # Generation size
    total_cost_usd: float   # Calculated cost based on the specific model's pricing
    provider_used: str      # e.g., "Groq", "Gemini", "Ollama"
    model_used: str         # e.g., "llama3-8b-8192"
    cache_hit: bool         # True if served from Semantic Cache (cost = $0.00)
    
    # NEW: Agent execution tracking
    agent_calls: int = 0
    agent_total_cost_usd: float = 0.0
    agent_termination_reason: Optional[str] = None  # "completed" | "max_calls_reached" | "budget_exceeded" | "timeout"
    
    # NEW: Canary tracking & rollback status
    routed_via_canary: bool = False
    model_version_tag: Optional[str] = None
    canary_rolled_back: bool = False  # True if canary was auto-reverted due to degradation
    
    # NEW: RAG cost breakdown for vector DB optimization
    retrieval_cost_usd: float = 0.0  # Cost of vector search/embedding
    retrieval_latency_ms: float = 0.0  # Time to retrieve chunks
    llm_cost_usd: float = 0.0  # LLM-only cost (excluding retrieval)
    rag_cost_percent: float = 0.0  # Retrieval as % of total cost
    
    # NEW: Department & tenant tracking for chargeback
    department_id: Optional[str] = None
    tenant_id: Optional[str] = None

class InferenceResponse(BaseModel):
    content: str
    metrics: InferenceMetrics
    trace: Optional[List[str]] = Field(default_factory=list)  # Records the execution pipeline steps