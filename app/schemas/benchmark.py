from typing import List, Optional

from pydantic import BaseModel, Field


class BenchmarkRunRequest(BaseModel):
    provider: str = Field("Groq", description="Provider name from gateway providers catalog")
    model_name: Optional[str] = Field(None, description="Optional model override")
    optimization_profile: str = Field("balanced", description="Runtime governance profile")
    suites: List[str] = Field(default_factory=lambda: ["smoke", "mmlu-lite", "hellaswag-lite"])
    sample_size: int = Field(3, ge=1, le=20)


class BenchmarkCaseResult(BaseModel):
    suite: str
    prompt: str
    success: bool
    error: Optional[str] = None
    ttft_ms: Optional[float] = None
    tpot_ms: Optional[float] = None
    total_latency_ms: Optional[float] = None
    total_cost_usd: Optional[float] = None
    provider_used: Optional[str] = None
    model_used: Optional[str] = None


class BenchmarkSummary(BaseModel):
    total_cases: int
    passed_cases: int
    failed_cases: int
    avg_ttft_ms: float
    avg_tpot_ms: float
    avg_total_latency_ms: float
    total_cost_usd: float


class BenchmarkJob(BaseModel):
    job_id: str
    status: str
    created_at: str
    updated_at: str
    provider: str
    model_name: Optional[str] = None
    optimization_profile: str
    suites: List[str]
    sample_size: int
    summary: Optional[BenchmarkSummary] = None
    results: List[BenchmarkCaseResult] = Field(default_factory=list)
    error: Optional[str] = None
