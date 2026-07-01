from fastapi import APIRouter
from app.db.session import analytics_db
from app.core.platform_state import platform_state
from app.core.infra_collectors import infra_collector

router = APIRouter()

@router.get("/metrics", summary="Get real-time FinOps and Infrastructure metrics")
async def get_metrics():
    logs = analytics_db.get_all()
    
    # Simple aggregation
    total_requests = len(logs)
    total_cost = sum(log.get("total_cost_usd", 0) for log in logs)
    avg_latency = sum(log.get("total_latency_ms", 0) for log in logs) / total_requests if total_requests > 0 else 0
    
    # Advanced observability metrics (TTFT, TPOT, Cache Rate)
    avg_ttft = sum(log.get("ttft_ms", 0) for log in logs) / total_requests if total_requests > 0 else 0
    avg_tpot = sum(log.get("tpot_ms", 0) for log in logs) / total_requests if total_requests > 0 else 0
    cache_hits = sum(1 for log in logs if log.get("cache_hit", False))
    cache_hit_rate = (cache_hits / total_requests * 100) if total_requests > 0 else 0
    total_tokens = sum(log.get("input_tokens", 0) + log.get("output_tokens", 0) for log in logs)
    
    # NEW: Agent metrics aggregation
    total_agent_calls = sum(log.get("agent_calls", 0) for log in logs)
    total_agent_cost = sum(log.get("agent_total_cost_usd", 0) for log in logs)
    avg_calls_per_request = (total_agent_calls / total_requests) if total_requests > 0 else 0
    
    # Count requests terminated by agent budget limits
    budget_terminated = sum(
        1 for log in logs 
        if log.get("agent_termination_reason") in ["budget_exceeded", "max_calls_reached", "timeout"]
    )
    
    # Count canary-routed requests
    canary_requests = sum(1 for log in logs if log.get("routed_via_canary", False))
    canary_rate = (canary_requests / total_requests * 100) if total_requests > 0 else 0
    
    # NEW: RAG cost breakdown
    total_retrieval_cost = sum(log.get("retrieval_cost_usd", 0) for log in logs)
    total_llm_cost = sum(log.get("llm_cost_usd", 0) for log in logs)
    avg_rag_percent = sum(log.get("rag_cost_percent", 0) for log in logs) / total_requests if total_requests > 0 else 0
    
    # NEW: Canary rollback stats
    canary_rolled_back = sum(1 for log in logs if log.get("canary_rolled_back", False))
    canary_rollback_rate = (canary_rolled_back / canary_requests * 100) if canary_requests > 0 else 0
    
    # NEW: Department chargeback breakdown
    dept_breakdown = {}
    for log in logs:
        dept = log.get("department_id") or "unassigned"
        if dept not in dept_breakdown:
            dept_breakdown[dept] = {"requests": 0, "cost_usd": 0.0}
        dept_breakdown[dept]["requests"] += 1
        dept_breakdown[dept]["cost_usd"] += log.get("total_cost_usd", 0)
    
    base_infra = platform_state.infrastructure_health()
    external_infra = await infra_collector.collect()

    merged_nodes = []
    merged_nodes.extend(base_infra.get("nodes", []))

    external_nodes = external_infra.get("nodes", [])
    if external_nodes:
        merged_nodes.extend(external_nodes)

    merged_infra = {
        "global_active_requests": max(
            int(base_infra.get("global_active_requests", 0)),
            int(external_infra.get("global_active_requests", 0)),
        ),
        "nodes": merged_nodes,
        "collector_errors": external_infra.get("collector_errors", []),
    }

    return {
        "summary": {
            "total_requests": total_requests,
            "total_cost_usd": round(total_cost, 6),
            "avg_latency_ms": round(avg_latency, 2),
            "avg_ttft_ms": round(avg_ttft, 2),
            "avg_tpot_ms": round(avg_tpot, 2),
            "cache_hit_rate_percent": round(cache_hit_rate, 2),
            "total_tokens": total_tokens,
            "agent_metrics": {
                "total_agent_calls": total_agent_calls,
                "total_agent_cost_usd": round(total_agent_cost, 6),
                "avg_calls_per_request": round(avg_calls_per_request, 2),
                "budget_terminated_requests": budget_terminated,
                "canary_routed_requests": canary_requests,
                "canary_rate_percent": round(canary_rate, 2)
            },
            # NEW: RAG cost optimization metrics
            "rag_metrics": {
                "total_retrieval_cost_usd": round(total_retrieval_cost, 6),
                "total_llm_cost_usd": round(total_llm_cost, 6),
                "avg_retrieval_percent": round(avg_rag_percent, 1),
                "retrieval_savings_percent": round(((total_retrieval_cost / total_cost * 100)) if total_cost > 0 else 0, 1)
            },
            # NEW: Canary deployment metrics
            "canary_metrics": {
                "total_canary_requests": canary_requests,
                "canary_rate_percent": round(canary_rate, 2),
                "canary_rollbacks": canary_rolled_back,
                "rollback_rate_percent": round(canary_rollback_rate, 2)
            },
            # NEW: Department chargeback breakdown
            "chargeback_by_department": dict(
                sorted(
                    [(k, {"requests": v["requests"], "cost_usd": round(v["cost_usd"], 6)}) 
                     for k, v in dept_breakdown.items()],
                    key=lambda x: x[1]["cost_usd"],
                    reverse=True
                )
            )
        },
        "infrastructure": merged_infra,
        "recent_logs": logs[::-1] # Return latest logs first
    }