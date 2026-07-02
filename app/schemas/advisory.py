"""
Advisory Recommendation Schemas
---------------------------------
Pydantic models for the AI Solution Advisor (Advisory Mode).
Used by POST /api/v1/advisor/recommend
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class AdvisoryRequest(BaseModel):
    scenario: str = Field(..., description="Business scenario or question, e.g. 'I want to build a test generator platform'")
    constraints: Optional[str] = Field(None, description="Optional constraints: budget, latency, self-hosted, etc.")


class ModelRecommendation(BaseModel):
    rank: int
    model: str
    provider: str
    variant_id: Optional[str] = None
    why: str
    strengths: List[str] = []
    weaknesses: List[str] = []
    estimated_cost_per_1k_requests: str
    estimated_ttft_ms: str
    confidence: int               # 0–100
    is_available: bool = True


class ParameterRecommendation(BaseModel):
    temperature: float
    max_tokens: int
    reasoning: str


class AdvisoryResponse(BaseModel):
    scenario: str
    detected_workload: str
    complexity: str
    key_requirements: List[str]
    recommended_parameters: ParameterRecommendation
    model_recommendations: List[ModelRecommendation]
    deployment_advice: str
    warnings: List[str] = []
    classification_confidence: int
