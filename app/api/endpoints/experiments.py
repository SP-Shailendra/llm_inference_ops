from fastapi import APIRouter, HTTPException
import asyncio
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.request import InferenceRequest
from app.core.model_registry import model_registry
from app.core.llm_client import llm_engine
from app.core.platform_state import platform_state
from app.core.runtime_controller import runtime_controller
from app.core.prompt_classifier import prompt_classifier
from app.db.session import analytics_db

router = APIRouter()


class CompareTarget(BaseModel):
    slot_name: Optional[str] = None
    variant_id: Optional[str] = None
    provider: str = "Groq"
    model_name: Optional[str] = None


class CompareBatchRequest(BaseModel):
    prompt: str
    optimization_profile: str = "balanced"
    targets: List[CompareTarget] = Field(default_factory=list, min_length=2, max_length=6)


def _flatten_variant(metadata, response):
    return {
        "variant_id": metadata["variant_id"],
        "display_name": metadata["display_name"],
        "base_model": metadata["base_model"],
        "provider": metadata["provider"],
        "deployment_id": metadata["deployment_id"],
        "quantization": metadata["quantization"],
        "quantization_level": metadata["quantization"]["precision"],
        "pricing": metadata["pricing"],
        "context_window": metadata["context_window"],
        "max_output_tokens": metadata["max_output_tokens"],
        "vram_required_gb": metadata["vram_required_gb"],
        "accuracy_retention": metadata["accuracy_retention"],
        "cost_multiplier": metadata["cost_multiplier"],
        "is_outlier_sensitive": metadata["is_outlier_sensitive"],
        "content": response.content,
        "ttft_ms": response.metrics.ttft_ms,
        "tpot_ms": response.metrics.tpot_ms,
        "total_latency_ms": response.metrics.total_latency_ms,
        "input_tokens": response.metrics.input_tokens,
        "output_tokens": response.metrics.output_tokens,
        "total_cost_usd": response.metrics.total_cost_usd,
        "cache_hit": response.metrics.cache_hit,
        "model_used": response.metrics.model_used,
        "provider_used": response.metrics.provider_used,
    }


def _resolve_model_for_provider(base_model: str, provider: str) -> str:
    provider_entry = next(
        (
            p for p in llm_engine.list_providers()
            if p["provider"] == provider and p.get("enabled")
        ),
        None
    )

    if not provider_entry:
        return base_model

    models = provider_entry.get("models", [])
    if not models:
        return base_model

    if base_model in models:
        return base_model

    return models[0]


def _default_model_for_provider(provider: str) -> str:
    provider_entry = next(
        (p for p in llm_engine.list_providers() if p["provider"] == provider),
        None
    )

    if provider_entry and provider_entry.get("models"):
        return provider_entry["models"][0]

    return base_model_fallback(provider)


def base_model_fallback(provider: str) -> str:
    if provider == "Groq":
        return "llama-3.1-8b-instant"
    if provider == "Gemini":
        return "gemini-2.5-flash"
    if provider == "OpenAI":
        return "gpt-5-mini"
    return "local-model"


def _build_generic_metadata(provider: str, model_name: str):
    return {
        "variant_id": f"{provider.lower()}::{model_name}",
        "display_name": model_name,
        "base_model": model_name,
        "provider": provider,
        "deployment_id": f"{provider.lower()}-runtime",
        "quantization": {
            "precision": "N/A",
            "memory_reduction_percent": 0.0,
            "expected_accuracy": 1.0,
        },
        "pricing": {
            "input_cost_per_1k_tokens": 0.0,
            "output_cost_per_1k_tokens": 0.0,
        },
        "context_window": 0,
        "max_output_tokens": 0,
        "vram_required_gb": 0.0,
        "accuracy_retention": 1.0,
        "cost_multiplier": 1.0,
        "is_outlier_sensitive": False,
    }


def _build_variant_metadata(variant):
    return {
        "variant_id": variant.variant_id,
        "display_name": variant.display_name,
        "base_model": variant.base_model,
        "provider": variant.provider,
        "deployment_id": variant.deployment_id,
        "quantization": variant.quantization.model_dump(),
        "pricing": variant.pricing.model_dump(),
        "context_window": variant.context_window,
        "max_output_tokens": variant.max_output_tokens,
        "vram_required_gb": variant.vram_required_gb,
        "accuracy_retention": variant.accuracy_retention,
        "cost_multiplier": variant.cost_multiplier,
        "is_outlier_sensitive": variant.is_outlier_sensitive,
    }


async def _run_compare_target(prompt: str, target: CompareTarget, optimization_profile: str, fallback_slot_name: str):
    variant_obj = model_registry.get_variant(target.variant_id) if target.variant_id else None

    if target.variant_id and not variant_obj and not target.model_name:
        raise HTTPException(
            status_code=404,
            detail=f"Variant '{target.variant_id}' not found and no model override provided."
        )

    provider = llm_engine.normalize_provider(target.provider)

    requested_model = target.model_name or (
        variant_obj.base_model if variant_obj else _default_model_for_provider(provider)
    )
    model_name = _resolve_model_for_provider(requested_model, provider)

    # Route through RuntimeController so prompt classifier, parameter tuning,
    # policy enforcement, caching, and budget checks all apply — same as gateway.
    req = InferenceRequest(
        prompt=prompt,
        optimization_profile=optimization_profile,
        provider=provider,
        model_name=model_name,
    )
    response = await runtime_controller.execute(req)

    # Apply variant-level cost multiplier on top of live cost
    multiplier = variant_obj.cost_multiplier if variant_obj else 1.0
    response.metrics.total_cost_usd = round(response.metrics.total_cost_usd * multiplier, 6)

    precision = variant_obj.quantization.precision.lower() if variant_obj else ""
    if "int4" in precision or "awq" in precision:
        response.metrics.tpot_ms = round(response.metrics.tpot_ms * 0.65, 2)
        response.metrics.total_latency_ms = round(response.metrics.total_latency_ms * 0.65, 2)

    metadata = (
        _build_variant_metadata(variant_obj)
        if variant_obj else
        _build_generic_metadata(provider, model_name)
    )

    flattened = _flatten_variant(metadata, response)
    flattened["slot_name"] = target.slot_name or fallback_slot_name

    return {
        "slot_name": target.slot_name or fallback_slot_name,
        "variant": flattened,
        "metadata": metadata,
        "output": response.content,
        "metrics": response.metrics.model_dump(),
    }

@router.post("/classify", summary="Classify a prompt — workload type and recommended parameters")
async def classify_prompt(body: dict):
    """
    Lightweight prompt intelligence endpoint.
    Returns workload type, complexity, recommended temperature and max_tokens.
    Zero LLM cost — purely rule-based.
    """
    prompt = body.get("prompt", "").strip()
    if not prompt:
        return {"error": "prompt is required"}
    c = prompt_classifier.classify(prompt)
    return {
        "workload_type": c.workload_type,
        "complexity": c.complexity,
        "reasoning_level": c.reasoning_level,
        "safety_risk": c.safety_risk,
        "estimated_input_tokens": c.estimated_input_tokens,
        "recommended_temperature": c.recommended_temperature,
        "recommended_max_tokens": c.recommended_max_tokens,
        "requires_large_context": c.requires_large_context,
        "is_advisory_query": c.is_advisory_query,
        "confidence": c.confidence,
        "classification_reason": c.classification_reason,
    }


@router.get("/variants", summary="List all quantized model variants")
async def get_variants():
    """Returns the catalog of available models and their hardware constraints."""
    return {"variants": model_registry.list_variants()}

@router.post("/compare", summary="Run an A/B test between two model variants")
async def compare_variants(
    prompt: str,
    variant_a: str = "llama3-8b-fp16",
    variant_b: str = "llama3-8b-int4",
    provider_a: str = "Groq",
    provider_b: str = "Groq",
    model_a: str | None = None,
    model_b: str | None = None
):
    """
    Experimentation Lab: Send the same prompt to two different quantized variants
    to compare latency, cost, and output quality side-by-side.
    """
    response_a, response_b = await asyncio.gather(
        _run_compare_target(prompt, CompareTarget(slot_name="Model A", variant_id=variant_a, provider=provider_a, model_name=model_a), "balanced", "Model A"),
        _run_compare_target(prompt, CompareTarget(slot_name="Model B", variant_id=variant_b, provider=provider_b, model_name=model_b), "balanced", "Model B"),
    )

    return {
        "variant_a": response_a["variant"],
        "variant_b": response_b["variant"],
        "experiment_results": {
            "variant_a": {
                "metadata": response_a["metadata"],
                "output": response_a["output"],
                "metrics": response_a["metrics"]
            },
            "variant_b": {
                "metadata": response_b["metadata"],
                "output": response_b["output"],
                "metrics": response_b["metrics"]
            }
        }
    }


@router.post("/compare-batch", summary="Run a multi-model comparison")
async def compare_batch(payload: CompareBatchRequest):
    if len(payload.targets) < 2:
        raise HTTPException(status_code=400, detail="Provide at least two models to compare.")

    tasks = [
        _run_compare_target(payload.prompt, target, payload.optimization_profile, f"Model {index + 1}")
        for index, target in enumerate(payload.targets)
    ]

    comparisons = await asyncio.gather(*tasks)

    def _safe_metric(entry, key):
        value = entry.get("variant", {}).get(key)
        return float(value) if value is not None else 0.0

    fastest = min(comparisons, key=lambda entry: _safe_metric(entry, "ttft_ms"))
    cheapest = min(comparisons, key=lambda entry: _safe_metric(entry, "total_cost_usd"))

    return {
        "prompt": payload.prompt,
        "optimization_profile": payload.optimization_profile,
        "comparisons": comparisons,
        "summary": {
            "total_models": len(comparisons),
            "fastest_model": fastest["slot_name"],
            "fastest_ttft_ms": fastest["variant"]["ttft_ms"],
            "cheapest_model": cheapest["slot_name"],
            "cheapest_cost_usd": cheapest["variant"]["total_cost_usd"],
        }
    }