from typing import List, Optional, Dict
from pydantic import BaseModel, Field


# ============================================================
# Provider Registry
# ============================================================

class ProviderCapability(BaseModel):
    streaming: bool = False
    vision: bool = False
    function_calling: bool = False
    json_mode: bool = False
    reasoning: bool = False
    embeddings: bool = False


class ProviderInfo(BaseModel):
    provider_id: str
    provider_name: str
    endpoint: Optional[str] = None
    status: str = "ONLINE"
    priority: int = 1
    supports_fallback: bool = True
    capabilities: ProviderCapability


# ============================================================
# Deployment Registry
# ============================================================

class DeploymentInfo(BaseModel):
    deployment_id: str
    provider: str
    region: str
    gpu_type: str
    gpu_count: int = 1
    status: str = "RUNNING"
    max_context_window: int
    throughput_tokens_per_sec: float
    average_latency_ms: float


# ============================================================
# Model Registry
# ============================================================

class PricingInfo(BaseModel):
    input_cost_per_1k_tokens: float
    output_cost_per_1k_tokens: float


class QuantizationInfo(BaseModel):
    precision: str
    memory_reduction_percent: float
    expected_accuracy: float


class ModelVariant(BaseModel):
    variant_id: str = Field(
        ...,
        description="Unique identifier of this deployed model variant."
    )

    display_name: str = Field(
        ...,
        description="Human readable model name."
    )

    base_model: str = Field(
        ...,
        description="Original foundation model."
    )

    provider: str

    deployment_id: str

    quantization: QuantizationInfo

    pricing: PricingInfo

    context_window: int

    max_output_tokens: int

    vram_required_gb: float

    accuracy_retention: float

    cost_multiplier: float = 1.0

    is_outlier_sensitive: bool = False

    supports_streaming: bool = True

    supports_tools: bool = True

    supports_json_mode: bool = True

    supports_reasoning: bool = False

    recommended_for: List[str] = []

    tags: List[str] = []


# ============================================================
# Registry Summary
# ============================================================

class RegistrySummary(BaseModel):
    total_models: int
    total_providers: int
    total_deployments: int
    active_deployments: int


# ============================================================
# API Responses
# ============================================================

class RegistryResponse(BaseModel):
    summary: RegistrySummary
    providers: List[ProviderInfo]
    deployments: List[DeploymentInfo]
    variants: List[ModelVariant]


class ModelSearchResponse(BaseModel):
    variants: List[ModelVariant]


class ProviderResponse(BaseModel):
    providers: List[ProviderInfo]


class DeploymentResponse(BaseModel):
    deployments: List[DeploymentInfo]