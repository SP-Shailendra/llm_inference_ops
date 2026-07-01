import uuid
from datetime import datetime
from typing import Dict, List

from app.core.llm_client import llm_engine
from app.db.session import benchmark_db
from app.schemas.benchmark import BenchmarkCaseResult, BenchmarkRunRequest, BenchmarkSummary
from app.schemas.request import InferenceRequest


BENCHMARK_PROMPTS: Dict[str, List[str]] = {
    "smoke": [
        "Summarize why batching improves LLM throughput in two sentences.",
        "What is TTFT and why does it matter for chat UX?",
        "Give one reason to use semantic caching for inference ops.",
    ],
    "mmlu-lite": [
        "In one paragraph, explain the trade-off between precision and recall.",
        "What does Bayes theorem compute in practical terms?",
        "Explain the difference between supervised and unsupervised learning.",
    ],
    "hellaswag-lite": [
        "Finish this logically: The engineer reduced token latency by...",
        "Continue naturally: To prevent rollout incidents, the team first...",
        "Complete the scenario: A canary deployment is useful because...",
    ],
}


class BenchmarkEngine:
    def _pick_model_for_provider(self, provider: str, requested_model: str | None) -> str:
        provider_entry = next((p for p in llm_engine.list_providers() if p["provider"] == provider), None)
        models = provider_entry.get("models", []) if provider_entry else []
        if requested_model and requested_model in models:
            return requested_model
        if requested_model and not models:
            return requested_model
        if models:
            return models[0]
        return requested_model or "local-model"

    def _make_job(self, req: BenchmarkRunRequest, resolved_model: str) -> Dict:
        now = datetime.utcnow().isoformat()
        return {
            "job_id": str(uuid.uuid4()),
            "status": "running",
            "created_at": now,
            "updated_at": now,
            "provider": req.provider,
            "model_name": resolved_model,
            "optimization_profile": req.optimization_profile,
            "suites": req.suites,
            "sample_size": req.sample_size,
            "results": [],
            "summary": None,
            "error": None,
        }

    def _build_summary(self, results: List[Dict]) -> BenchmarkSummary:
        passed = [r for r in results if r.get("success")]
        failed = len(results) - len(passed)

        def avg(key: str) -> float:
            vals = [float(r.get(key, 0.0)) for r in passed if r.get(key) is not None]
            if not vals:
                return 0.0
            return round(sum(vals) / len(vals), 2)

        total_cost = round(sum(float(r.get("total_cost_usd", 0.0) or 0.0) for r in passed), 6)

        return BenchmarkSummary(
            total_cases=len(results),
            passed_cases=len(passed),
            failed_cases=failed,
            avg_ttft_ms=avg("ttft_ms"),
            avg_tpot_ms=avg("tpot_ms"),
            avg_total_latency_ms=avg("total_latency_ms"),
            total_cost_usd=total_cost,
        )

    async def run(self, req: BenchmarkRunRequest) -> Dict:
        provider = llm_engine.normalize_provider(req.provider)
        model_name = self._pick_model_for_provider(provider, req.model_name)

        job = self._make_job(req, model_name)
        benchmark_db.create_job(job)

        case_results: List[Dict] = []

        try:
            for suite in req.suites:
                prompts = BENCHMARK_PROMPTS.get(suite, BENCHMARK_PROMPTS["smoke"])[: req.sample_size]
                for prompt in prompts:
                    inference_req = InferenceRequest(
                        prompt=prompt,
                        optimization_profile=req.optimization_profile,
                        provider=provider,
                        model_name=model_name,
                    )

                    try:
                        response = await llm_engine.generate(inference_req, model_name, provider_name=provider)
                        case = BenchmarkCaseResult(
                            suite=suite,
                            prompt=prompt,
                            success=True,
                            ttft_ms=response.metrics.ttft_ms,
                            tpot_ms=response.metrics.tpot_ms,
                            total_latency_ms=response.metrics.total_latency_ms,
                            total_cost_usd=response.metrics.total_cost_usd,
                            provider_used=response.metrics.provider_used,
                            model_used=response.metrics.model_used,
                        )
                    except Exception as ex:
                        case = BenchmarkCaseResult(
                            suite=suite,
                            prompt=prompt,
                            success=False,
                            error=str(ex),
                        )

                    case_results.append(case.model_dump())

            summary = self._build_summary(case_results)

            benchmark_db.update_job(
                job["job_id"],
                {
                    "status": "completed",
                    "updated_at": datetime.utcnow().isoformat(),
                    "results": case_results,
                    "summary": summary.model_dump(),
                },
            )
        except Exception as ex:
            benchmark_db.update_job(
                job["job_id"],
                {
                    "status": "failed",
                    "updated_at": datetime.utcnow().isoformat(),
                    "error": str(ex),
                    "results": case_results,
                },
            )

        return benchmark_db.get_job(job["job_id"]) or job


benchmark_engine = BenchmarkEngine()
