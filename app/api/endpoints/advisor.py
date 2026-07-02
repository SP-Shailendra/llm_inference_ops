from fastapi import APIRouter
from app.db.session import analytics_db
from app.core.prompt_classifier import prompt_classifier, WorkloadType
from app.core.model_registry import model_registry
from app.core.llm_client import llm_engine
from app.schemas.advisory import AdvisoryRequest, AdvisoryResponse, ModelRecommendation, ParameterRecommendation

router = APIRouter()


# ─────────────────────────────────────────────────────────────────
# Workload → model capability requirements
# ─────────────────────────────────────────────────────────────────

_WORKLOAD_REQUIREMENTS: dict[str, dict] = {
    WorkloadType.CODING:           {"needs_large": True,  "avoid_int4": True,  "prefer_70b": True,  "key_req": ["strong code generation", "deterministic output", "structured formatting"]},
    WorkloadType.CODE_REVIEW:      {"needs_large": True,  "avoid_int4": True,  "prefer_70b": True,  "key_req": ["code understanding", "best practices knowledge", "detailed explanations"]},
    WorkloadType.DEBUGGING:        {"needs_large": True,  "avoid_int4": True,  "prefer_70b": True,  "key_req": ["error diagnosis", "deterministic analysis", "step-by-step reasoning"]},
    WorkloadType.SQL:              {"needs_large": False, "avoid_int4": True,  "prefer_70b": False, "key_req": ["SQL syntax accuracy", "schema understanding", "zero hallucination"]},
    WorkloadType.JSON_GENERATION:  {"needs_large": False, "avoid_int4": True,  "prefer_70b": False, "key_req": ["strict JSON validity", "structured output", "zero temperature"]},
    WorkloadType.EXTRACTION:       {"needs_large": False, "avoid_int4": False, "prefer_70b": False, "key_req": ["information extraction", "structured output", "accuracy"]},
    WorkloadType.TRANSLATION:      {"needs_large": False, "avoid_int4": False, "prefer_70b": False, "key_req": ["multilingual capability", "faithfulness", "fluency"]},
    WorkloadType.SUMMARIZATION:    {"needs_large": False, "avoid_int4": False, "prefer_70b": False, "key_req": ["compression accuracy", "key-point retention", "brevity"]},
    WorkloadType.CREATIVE_WRITING: {"needs_large": True,  "avoid_int4": False, "prefer_70b": True,  "key_req": ["creativity", "narrative coherence", "vocabulary richness"]},
    WorkloadType.RESEARCH:         {"needs_large": True,  "avoid_int4": True,  "prefer_70b": True,  "key_req": ["deep reasoning", "factual accuracy", "comprehensive coverage"]},
    WorkloadType.PLANNING:         {"needs_large": True,  "avoid_int4": False, "prefer_70b": True,  "key_req": ["structured thinking", "strategic reasoning", "completeness"]},
    WorkloadType.RAG:              {"needs_large": False, "avoid_int4": False, "prefer_70b": False, "key_req": ["context grounding", "faithfulness", "low hallucination"]},
    WorkloadType.AGENT_WORKFLOW:   {"needs_large": True,  "avoid_int4": True,  "prefer_70b": True,  "key_req": ["function calling", "multi-step reasoning", "reliability"]},
    WorkloadType.SENTIMENT:        {"needs_large": False, "avoid_int4": False, "prefer_70b": False, "key_req": ["tone detection", "nuance understanding", "consistency"]},
    WorkloadType.CLASSIFICATION:   {"needs_large": False, "avoid_int4": False, "prefer_70b": False, "key_req": ["category accuracy", "consistency", "speed"]},
    WorkloadType.CHAT:             {"needs_large": False, "avoid_int4": False, "prefer_70b": False, "key_req": ["conversational fluency", "low latency", "cost efficiency"]},
    WorkloadType.ADVISORY:         {"needs_large": True,  "avoid_int4": False, "prefer_70b": True,  "key_req": ["broad knowledge", "structured recommendations", "reasoning"]},
    WorkloadType.QUESTION_ANSWER:  {"needs_large": False, "avoid_int4": False, "prefer_70b": False, "key_req": ["factual accuracy", "conciseness", "knowledge depth"]},
    WorkloadType.UNKNOWN:          {"needs_large": False, "avoid_int4": False, "prefer_70b": False, "key_req": ["general capability", "balanced performance"]},
}

_DEPLOYMENT_ADVICE: dict[str, str] = {
    WorkloadType.CODING:           "Use API-first (Groq/OpenRouter) for speed. Self-host only if code contains proprietary IP.",
    WorkloadType.DEBUGGING:        "API-first recommended. Low latency crucial — use Groq LPU for fastest TTFT.",
    WorkloadType.SQL:              "API-first is sufficient. Ensure JSON mode is enabled to get structured query output.",
    WorkloadType.JSON_GENERATION:  "API-first with JSON mode enforced. Use temperature=0 strictly.",
    WorkloadType.TRANSLATION:      "Gemini Flash recommended for multilingual tasks — strongest non-English performance.",
    WorkloadType.SUMMARIZATION:    "Any provider works. Prioritise cost — use 8B models for routine summarization.",
    WorkloadType.CREATIVE_WRITING: "70B models strongly preferred. Temperature 1.0–1.2 for best creative output.",
    WorkloadType.RESEARCH:         "70B models only. Consider Gemini 1.5 Pro for very long documents (1M token context).",
    WorkloadType.RAG:              "API-first. Pair with a vector DB (Pinecone, Weaviate). Temperature ≤ 0.3 for faithfulness.",
    WorkloadType.AGENT_WORKFLOW:   "Ensure function-calling support. 70B models for complex chains. Add circuit breakers for cost control.",
    WorkloadType.CHAT:             "8B models are sufficient for chat. Use Groq for sub-500ms TTFT. Enable semantic cache.",
    WorkloadType.ADVISORY:         "No inference required — use the platform's advisory engine directly.",
    WorkloadType.UNKNOWN:          "Start with balanced profile. Monitor telemetry and adjust after 50+ requests.",
}


def _build_recommendations(classification, variants) -> list[ModelRecommendation]:
    req = _WORKLOAD_REQUIREMENTS.get(classification.workload_type,
                                     _WORKLOAD_REQUIREMENTS[WorkloadType.UNKNOWN])
    avoid_int4   = req["avoid_int4"]
    prefer_70b   = req["prefer_70b"]

    # Filter out risky variants for this workload
    candidates = [
        v for v in variants
        if not (avoid_int4 and v.is_outlier_sensitive)
    ]
    if not candidates:
        candidates = list(variants)  # fallback: use all

    def _score(v):
        score = 0
        if prefer_70b and "70b" in v.base_model.lower():
            score += 30
        elif not prefer_70b and "8b" in v.base_model.lower():
            score += 20
        score += int(v.accuracy_retention * 50)
        score -= int(v.vram_required_gb / 10)
        if not v.is_outlier_sensitive:
            score += 10
        return score

    ranked = sorted(candidates, key=_score, reverse=True)[:4]

    recommendations = []
    for i, v in enumerate(ranked, 1):
        cost_per_1k = v.pricing.input_cost_per_1k_tokens * 500 + v.pricing.output_cost_per_1k_tokens * 500
        strengths = []
        weaknesses = []

        if "70b" in v.base_model.lower():
            strengths.append("Deep reasoning and complex task handling")
        else:
            strengths.append("Fast inference, cost-efficient")

        if v.accuracy_retention >= 1.0:
            strengths.append("Full precision — maximum accuracy")
        elif v.accuracy_retention >= 0.97:
            strengths.append("Near-full accuracy with memory savings")
        else:
            weaknesses.append(f"Accuracy reduced to {int(v.accuracy_retention*100)}% vs FP16")

        if v.is_outlier_sensitive:
            weaknesses.append("Higher outlier risk on edge-case inputs")

        if v.vram_required_gb > 80:
            weaknesses.append(f"Requires {v.vram_required_gb}GB VRAM — multi-GPU setup needed")

        why_parts = []
        if i == 1:
            why_parts.append("Best overall fit for this workload")
        if prefer_70b and "70b" in v.base_model.lower():
            why_parts.append("70B parameter scale handles reasoning-heavy tasks well")
        if not prefer_70b and "8b" in v.base_model.lower():
            why_parts.append("8B model provides optimal speed/cost ratio for this task")
        if avoid_int4 and not v.is_outlier_sensitive:
            why_parts.append("Stable quantization — safe for production")
        if not why_parts:
            why_parts.append(f"Accuracy {int(v.accuracy_retention*100)}%, cost multiplier {v.cost_multiplier}x")

        recommendations.append(ModelRecommendation(
            rank=i,
            model=v.base_model,
            provider=v.provider,
            variant_id=v.variant_id,
            why=". ".join(why_parts),
            strengths=strengths,
            weaknesses=weaknesses,
            estimated_cost_per_1k_requests=f"${cost_per_1k * 1000:.4f}",
            estimated_ttft_ms="~300–800ms" if v.provider == "Groq" else "~500–2000ms",
            confidence=max(90 - (i - 1) * 12, 50),
            is_available=True,
        ))

    return recommendations

@router.post("/recommend", response_model=AdvisoryResponse, summary="AI Solution Advisor — Model Recommendation")
async def recommend_model(body: AdvisoryRequest):
    """
    Advisory Mode — Zero inference cost.
    Analyze a business scenario and recommend the best model/provider/parameters.
    No LLM call is made; recommendations are driven by registry data + workload rules.
    """
    classification = prompt_classifier.classify(body.scenario)
    variants = model_registry.list_variants()
    req = _WORKLOAD_REQUIREMENTS.get(classification.workload_type,
                                     _WORKLOAD_REQUIREMENTS[WorkloadType.UNKNOWN])

    # Parse any constraint overrides from the free-text constraints field
    constraints_text = (body.constraints or "").lower()
    warnings = []
    if "int4" in constraints_text or "cheap" in constraints_text:
        warnings.append("INT4 models are not recommended for this workload type — outlier risk is HIGH for structured/code tasks.")
    if classification.safety_risk == "high":
        warnings.append("Safety risk detected in scenario description. Ensure content filtering is applied.")
    if "self-host" in constraints_text or "on-premise" in constraints_text:
        warnings.append("Self-hosted deployment requires significant GPU infrastructure. See VRAM requirements per variant in the Catalog.")

    recommendations = _build_recommendations(classification, variants)

    deployment_advice = _DEPLOYMENT_ADVICE.get(
        classification.workload_type,
        _DEPLOYMENT_ADVICE[WorkloadType.UNKNOWN]
    )

    return AdvisoryResponse(
        scenario=body.scenario,
        detected_workload=classification.workload_type,
        complexity=classification.complexity,
        key_requirements=req["key_req"],
        recommended_parameters=ParameterRecommendation(
            temperature=classification.recommended_temperature,
            max_tokens=classification.recommended_max_tokens,
            reasoning=f"Optimized for '{classification.workload_type}' workload — "
                      f"{classification.classification_reason.lower()}"
        ),
        model_recommendations=recommendations,
        deployment_advice=deployment_advice,
        warnings=warnings,
        classification_confidence=classification.confidence,
    )


@router.get("/insights", summary="System Optimization Insights")
async def generate_insights():
    logs = analytics_db.get_all()
    total_requests = len(logs)
    
    if total_requests == 0:
        return {"message": "System is accumulating data. Run more traffic to generate insights!"}

    total_cost = sum(l.get("total_cost_usd", 0) for l in logs)
    cache_hits = sum(1 for l in logs if l.get("cache_hit", False))
    cache_rate = (cache_hits / total_requests) * 100 if total_requests > 0 else 0
    
    insights = []

    # 1. Cost Optimization (Quantization)
    expensive_calls = [l for l in logs if "70b" in str(l.get("model_used", "")) or "fp16" in str(l.get("model_used", "")).lower()]
    if len(expensive_calls) > 0:
        actual_cost = sum(l.get("total_cost_usd", 0) for l in expensive_calls)
        savings = actual_cost * 0.5 
        if savings > 0.000005: # Only show if savings are meaningful
            insights.append({
                "type": "Cost Reduction (Quantization)",
                "recommendation": f"Switch to INT4 Quantization to cut precision costs. Estimated savings: ${round(savings, 6)}."
            })

    # 2. Cache Tuning (Only trigger if they have made at least 5 requests)
    if total_requests >= 5:
        if cache_rate < 20.0:
            insights.append({
                "type": "Latency & Cost Optimization",
                "recommendation": f"Semantic Cache hit rate is low ({round(cache_rate, 1)}%). Lower the similarity threshold to increase hits."
            })
        elif cache_rate > 80.0:
            insights.append({
                "type": "Excellent Cache Utilization",
                "recommendation": f"Your cache hit rate is stellar ({round(cache_rate, 1)}%). You are saving significantly on compute."
            })

    # 3. Model Size Downgrade
    if total_requests > 3 and total_cost > 0.0005:
        insights.append({
            "type": "Compute Downgrade",
            "recommendation": "High spend detected. Try routing simple tasks to the 8B model instead of 70B."
        })

    # 4. Fallback / Profiling State (NEW STATS ADDED HERE)
    if not insights:
        if total_requests < 5:
            # Card 1: Status
            insights.append({
                "type": "System Profiling Active",
                "recommendation": f"Currently establishing baseline metrics ({total_requests} requests analyzed). Run more traffic or A/B tests to unlock deep insights."
            })
            
            # Card 2: Preliminary Stats
            avg_ttft = sum(l.get("ttft_ms", 0) for l in logs) / total_requests
            avg_tpot = sum(l.get("tpot_ms", 0) for l in logs) / total_requests
            insights.append({
                "type": "Preliminary Telemetry",
                "recommendation": f"Averages across {total_requests} runs: TTFT is {round(avg_ttft, 1)}ms, TPOT is {round(avg_tpot, 1)}ms. Cache hit rate is at {round(cache_rate, 1)}%."
            })
        else:
            insights.append({
                "type": "System Optimal",
                "recommendation": "All inference metrics (Cost, Latency, Cache) are currently within optimal bounds. No architecture changes required."
            })

    # Calculate a platform grade based on the insights
    grade = "A"
    if any(i["type"] == "Latency & Cost Optimization" or "Downgrade" in i["type"] for i in insights):
        grade = "B+"
    if any("Quantization" in i["type"] for i in insights):
        grade = "A-"

    return {
        "platform_grade": grade,
        "total_analyzed_requests": total_requests,
        "current_total_spend": round(total_cost, 6),
        "ai_recommendations": insights
    }