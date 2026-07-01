from fastapi import APIRouter
from app.db.session import analytics_db

router = APIRouter()

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