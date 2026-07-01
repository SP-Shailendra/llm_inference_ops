from pydantic import BaseModel, Field
from typing import Optional
import uuid

class InferenceRequest(BaseModel):
    prompt: str = Field(..., description="The user's input prompt or question.")
    request_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique request identifier")
    user_id: Optional[str] = Field("anonymous", description="Used for FinOps tracking per department/user.")
    
    # NEW: Department-level chargeback tracking
    department_id: Optional[str] = Field(None, description="Department for cost allocation (HR, Finance, Engineering, etc.)")
    tenant_id: Optional[str] = Field(None, description="Tenant/workspace identifier for multi-tenant setups")
    
    # NEW: RBAC role tracking for access control
    user_role: Optional[str] = Field("user", description="User role for RBAC: 'viewer', 'user', 'developer', 'admin', 'mlops'")
    
    provider: Optional[str] = Field(
        None,
        description="Optional provider override, e.g. 'Groq' or 'Gemini'."
    )
    model_name: Optional[str] = Field(
        None,
        description="Optional model override. If omitted, profile routing decides the model."
    )
    
    # NEW: Expanded to support the new Inference Config Engine
    optimization_profile: Optional[str] = Field(
        "balanced", 
        description="Choose an optimization profile: 'balanced', 'performance', 'cost_saver'"
    )
    
    # Legacy override for specific model tiering
    routing_tier: Optional[str] = Field(
        "auto", 
        description="Choose: 'auto', 'tier_1_premium', 'tier_2_balanced', 'tier_3_low_cost'"
    )
    
    # NEW: RAG cost tracking fields
    retrieval_context: Optional[str] = Field(None, description="Retrieved context before LLM (for RAG cost tracking)")
    retrieval_chunks_count: Optional[int] = Field(0, description="Number of chunks retrieved")
    
    max_tokens: Optional[int] = Field(1024, description="Maximum tokens to generate.")
    temperature: Optional[float] = Field(0.7, description="Creativity of the response (0.0 to 1.0).")