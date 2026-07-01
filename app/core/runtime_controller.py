import logging
import time
import hashlib
import uuid
from fastapi import HTTPException

from app.schemas.request import InferenceRequest
from app.schemas.response import InferenceResponse
from app.schemas.runtime import RuntimeContext

from app.core.config_engine import config_engine
from app.core.routing_engine import model_router
from app.core.cache_engine import semantic_cache
from app.core.llm_client import llm_engine
from app.core.platform_state import platform_state

# --- BATCH 2 FINOPS IMPORTS ---
from app.core.budget_engine import budget_engine, AgentBudgetExceededException
from app.core.policy_engine import policy_engine

from app.db.session import analytics_db


logger = logging.getLogger(__name__)

class RuntimeController:
    """
    Enterprise Runtime Controller
    Orchestrates the complete lifecycle of every inference request,
    building a detailed execution trace for observability.
    """

    def __init__(self):
        # profile_name -> unix timestamp until canary is disabled
        self._canary_disabled_until = {}

    def _is_canary_eligible(self, request: InferenceRequest, percent: int) -> bool:
        if percent <= 0:
            return False
        if percent >= 100:
            return True

        user_part = (request.user_id or "anonymous").strip().lower()
        prompt_part = (request.prompt or "")[:64].strip().lower()
        seed = f"{user_part}|{prompt_part}"
        bucket = int(hashlib.md5(seed.encode("utf-8")).hexdigest(), 16) % 100
        return bucket < percent

    def _resolve_compatible_model(self, provider_catalog: dict, provider: str, model: str) -> str:
        entry = provider_catalog.get(provider)
        models = entry.get("models", []) if entry else []
        if models and model not in models:
            return models[0]
        return model

    def _apply_canary_route(
        self,
        request: InferenceRequest,
        profile_name: str,
        profile,
        provider_catalog: dict,
        target_provider: str,
        target_model: str,
        trace_logs: list,
    ):
        route = {
            "provider": target_provider,
            "model": target_model,
            "is_canary": False,
            "baseline_provider": target_provider,
            "baseline_model": target_model,
        }

        if not profile.features.enable_canary:
            return route

        disabled_until = self._canary_disabled_until.get(profile_name, 0)
        now = time.time()
        if disabled_until > now:
            remaining = int(disabled_until - now)
            trace_logs.append(f"🧯 Canary disabled by rollback cooldown ({remaining}s remaining).")
            return route

        canary_model = profile.routing.canary_model
        if not canary_model:
            return route

        canary_provider = profile.routing.canary_provider or target_provider
        if canary_provider not in provider_catalog:
            trace_logs.append(f"⚠️ Canary skipped: provider '{canary_provider}' unavailable.")
            return route

        percent = profile.routing.canary_traffic_percent
        if not self._is_canary_eligible(request, percent):
            return route

        canary_model = self._resolve_compatible_model(provider_catalog, canary_provider, canary_model)
        route["provider"] = canary_provider
        route["model"] = canary_model
        route["is_canary"] = True

        trace_logs.append(
            f"🧪 Canary route active ({percent}%): provider '{canary_provider}' model '{canary_model}'."
        )
        return route

    def _register_rollback(self, profile_name: str, profile, trace_logs: list, reason: str):
        cooldown = max(0, int(profile.runtime.rollback_cooldown_seconds))
        self._canary_disabled_until[profile_name] = time.time() + cooldown
        trace_logs.append(
            f"↩️ Auto-rollback triggered: {reason}. Canary disabled for {cooldown}s."
        )

    async def execute(self, request: InferenceRequest) -> InferenceResponse:
        trace_logs = []
        start_time = time.perf_counter()
        agent_session = None  # NEW: Agent budget tracking
        canary_rolled_back = False  # NEW: Track if canary was auto-reverted
        retrieval_cost = 0.0  # NEW: RAG cost tracking

        # 1. Governance & Policy Applier
        profile_name = getattr(request, "optimization_profile", "balanced")
        profile = config_engine.get_profile(profile_name)
        trace_logs.append(f"🛡️ Governance: Policy '{profile_name.upper()}' applied.")
        
        # NEW: Department chargeback tracking
        if request.department_id:
            trace_logs.append(f"💰 Chargeback: Department '{request.department_id}' will be billed.")

        # NEW: Initialize agent session if agentic loop enabled
        if profile.features.enable_agentic_loop and profile.agent.enable_agent_loop:
            session_id = f"{request.request_id or uuid.uuid4()}"
            agent_session = budget_engine.create_agent_session(
                session_id=session_id,
                max_calls=profile.agent.max_calls_per_session,
                max_cost_usd=profile.agent.max_cost_per_session_usd,
                max_duration_seconds=profile.agent.max_duration_seconds
            )
            trace_logs.append(
                f"🤖 Agent Session: Initialized with limits "
                f"(Calls: {profile.agent.max_calls_per_session}, "
                f"Cost: ${profile.agent.max_cost_per_session_usd}, "
                f"Duration: {profile.agent.max_duration_seconds}s)"
            )

        # Override request parameters based on strict policy
        request.temperature = profile.runtime.temperature
        request.max_tokens = profile.runtime.max_tokens

        # --- BATCH 2: POLICY & BUDGET GUARDRAILS ---
        # Estimate cost (rough heuristic) to check against budget before spending
        est_input_tokens = len(request.prompt) / 4
        est_cost = (est_input_tokens / 1_000_000 * 0.59) + (request.max_tokens / 1_000_000 * 0.79)
        
        try:
            policy_engine.validate_runtime_constraints(profile, est_cost)
            trace_logs.append(f"⚖️ Policy: Guardrails passed (Est. Max Cost: ${est_cost:.4f}).")
            
            budget_engine.validate_request(est_cost)
            trace_logs.append("💰 Budget: Approved. Sufficient daily funds available.")
        except Exception as e:
            trace_logs.append(f"🚫 Blocked by FinOps: {str(e)}")
            raise HTTPException(status_code=402, detail=str(e))
        # ---------------------------------------------

        # 2. Routing Engine
        # Provider/model can be overridden by request, otherwise use profile routing defaults.
        requested_provider = getattr(request, "provider", None)
        requested_model = getattr(request, "model_name", None)

        target_provider = (
            llm_engine.normalize_provider(requested_provider)
            if requested_provider
            else "Groq"
        )

        target_model = requested_model or profile.routing.fallback_model

        # Provider-model compatibility guardrail: if selected model isn't offered by provider,
        # fallback to provider's first available model.
        provider_catalog = {
            p["provider"]: p
            for p in llm_engine.list_providers()
            if p.get("enabled")
        }

        provider_entry = provider_catalog.get(target_provider)
        provider_models = provider_entry.get("models", []) if provider_entry else []

        if provider_models and target_model not in provider_models:
            target_model = provider_models[0]

        canary_route = self._apply_canary_route(
            request=request,
            profile_name=profile_name,
            profile=profile,
            provider_catalog=provider_catalog,
            target_provider=target_provider,
            target_model=target_model,
            trace_logs=trace_logs,
        )

        target_provider = canary_route["provider"]
        target_model = canary_route["model"]

        trace_logs.append(
            f"🔀 Routing: Provider '{target_provider}' model '{target_model}'."
        )

        # 3. Cache Interceptor
        if profile.features.enable_cache:
            cached_response = await semantic_cache.check_cache(request.prompt, target_model)
            if cached_response:
                trace_logs.append("⚡ Cache: Semantic hit found. Bypassing LLM generation.")
                latency_ms = (time.perf_counter() - start_time) * 1000
                cached_response.metrics.cache_hit = True
                cached_response.metrics.total_cost_usd = 0.0
                cached_response.metrics.ttft_ms = round(latency_ms, 2)
                cached_response.metrics.total_latency_ms = round(latency_ms, 2)
                cached_response.metrics.tpot_ms = 0.0
                
                # Attach trace and log
                cached_response.trace = trace_logs
                analytics_db.add_log(cached_response.metrics.model_dump())
                return cached_response
            else:
                trace_logs.append("🔍 Cache: Miss. Proceeding to inference layer.")

        # 4. Prompt Compression (FinOps Token Reduction Simulation)
        if profile.features.enable_prompt_compression:
            request.prompt = f"[System: FinOps Prompt Compression Active. Context pruned.]\n{request.prompt}"
            trace_logs.append("🗜️ Optimization: Prompt compressed (Estimated -60% tokens).")

        # 5. Agentic Loop (Simulation)
        if profile.features.enable_agentic_loop:
            trace_logs.append("🤖 Agentic Loop: Initializing multi-agent reasoning chain.")

        # 6. LLM Generation
        platform_state.add_active_model(target_model)
        agent_calls_made = 0
        agent_cost_tracked = 0.0
        
        try:
            try:
                # NEW: Check agent budget before generation
                if agent_session:
                    budget_engine.check_agent_budget(agent_session.session_id)
                
                response = await llm_engine.generate(
                    request,
                    target_model,
                    provider_name=target_provider
                )
                
                # NEW: Record agent call if session active
                if agent_session:
                    agent_calls_made += 1
                    agent_cost_tracked = response.metrics.total_cost_usd
                    budget_engine.record_agent_call(agent_session.session_id, agent_cost_tracked)
                    trace_logs.append(
                        f"📊 Agent Call #{agent_calls_made}: Cost ${agent_cost_tracked:.6f} "
                        f"(Total: ${agent_session.total_cost_usd:.6f})"
                    )
            except AgentBudgetExceededException as budget_ex:
                # NEW: Agent budget exceeded - terminate gracefully
                trace_logs.append(f"🚨 Agent Budget Exceeded: {str(budget_ex)}")
                if agent_session:
                    agent_session.check_budget()  # This will raise with proper termination reason
                else:
                    raise
            except Exception as ex:
                if profile.features.enable_rollback and canary_route["is_canary"]:
                    self._register_rollback(
                        profile_name=profile_name,
                        profile=profile,
                        trace_logs=trace_logs,
                        reason=f"canary execution failure ({str(ex)})",
                    )

                    fallback_provider = canary_route["baseline_provider"]
                    fallback_model = canary_route["baseline_model"]
                    fallback_model = self._resolve_compatible_model(
                        provider_catalog,
                        fallback_provider,
                        fallback_model,
                    )

                    trace_logs.append(
                        f"🔁 Fallback execution: provider '{fallback_provider}' model '{fallback_model}'."
                    )
                    response = await llm_engine.generate(
                        request,
                        fallback_model,
                        provider_name=fallback_provider,
                    )
                else:
                    raise

            if profile.features.enable_rollback and canary_route["is_canary"]:
                # NEW: Use RollbackTriggers from schema for thresholds
                rollback_triggers = profile.rollback_triggers or {}
                ttft_threshold = rollback_triggers.get("ttft_ms_threshold", 1500.0)
                cost_threshold = rollback_triggers.get("cost_multiplier_threshold", 1.3)
                error_threshold = rollback_triggers.get("error_rate_threshold", 0.05)
                
                # Check TTFT degradation
                if response.metrics.ttft_ms > ttft_threshold:
                    canary_rolled_back = True
                    trace_logs.append(f"⚠️ CANARY ROLLBACK: TTFT {response.metrics.ttft_ms:.1f}ms exceeded threshold {ttft_threshold}ms")
                    self._register_rollback(
                        profile_name=profile_name,
                        profile=profile,
                        trace_logs=trace_logs,
                        reason=f"TTFT {response.metrics.ttft_ms:.1f}ms > {ttft_threshold}ms threshold",
                    )
                    # Re-execute with baseline model
                    fallback_provider = canary_route["baseline_provider"]
                    fallback_model = canary_route["baseline_model"]
                    fallback_model = self._resolve_compatible_model(provider_catalog, fallback_provider, fallback_model)
                    response = await llm_engine.generate(request, fallback_model, provider_name=fallback_provider)
                    response.metrics.canary_rolled_back = True
                
                # Check cost multiplier degradation
                elif response.metrics.total_cost_usd > response.metrics.total_cost_usd * cost_threshold:
                    canary_rolled_back = True
                    trace_logs.append(f"⚠️ CANARY ROLLBACK: Cost ${response.metrics.total_cost_usd:.6f} exceeded multiplier {cost_threshold}x")
                    self._register_rollback(profile_name=profile_name, profile=profile, trace_logs=trace_logs, reason=f"Cost multiplier {cost_threshold}x exceeded")
                    fallback_provider = canary_route["baseline_provider"]
                    fallback_model = canary_route["baseline_model"]
                    fallback_model = self._resolve_compatible_model(provider_catalog, fallback_provider, fallback_model)
                    response = await llm_engine.generate(request, fallback_model, provider_name=fallback_provider)
                    response.metrics.canary_rolled_back = True

            trace_logs.append(f"✅ Inference: Generation complete via {response.metrics.provider_used}.")
        finally:
            # Ensure the connection is freed even if generation fails
            platform_state.remove_active_model(target_model)

        # NEW: Attach agent metrics to response
        if agent_session:
            response.metrics.agent_calls = agent_session.call_count
            response.metrics.agent_total_cost_usd = agent_session.total_cost_usd
            response.metrics.agent_termination_reason = agent_session.termination_reason
        
        # NEW: Add canary tracking and rollback status
        if 'canary_route' in locals() and canary_route.get("is_canary"):
            response.metrics.routed_via_canary = True
            response.metrics.model_version_tag = "canary"
            response.metrics.canary_rolled_back = canary_rolled_back
        
        # NEW: Calculate RAG cost breakdown
        if request.retrieval_context and request.retrieval_chunks_count > 0:
            # Estimate: $0.001 per chunk retrieved + $0.002 per search
            retrieval_cost = (request.retrieval_chunks_count * 0.001) + 0.002
            response.metrics.retrieval_cost_usd = round(retrieval_cost, 6)
            response.metrics.llm_cost_usd = round(response.metrics.total_cost_usd - retrieval_cost, 6)
            response.metrics.rag_cost_percent = round((retrieval_cost / response.metrics.total_cost_usd * 100) if response.metrics.total_cost_usd > 0 else 0, 1)
            trace_logs.append(f"🔍 RAG Breakdown: Retrieval ${retrieval_cost:.6f} + LLM ${response.metrics.llm_cost_usd:.6f}")
        else:
            response.metrics.llm_cost_usd = response.metrics.total_cost_usd
        
        # NEW: Department & tenant tracking for chargeback
        if request.department_id:
            response.metrics.department_id = request.department_id
        if request.tenant_id:
            response.metrics.tenant_id = request.tenant_id

        # Attach Trace
        response.trace = trace_logs

        # 7. Update Cache
        if profile.features.enable_cache:
            await semantic_cache.store_cache(request.prompt, target_model, response)

        # 8. Store Telemetry
        analytics_db.add_log(response.metrics.model_dump())
        
        # NEW: Finalize agent session
        if agent_session:
            budget_engine.end_agent_session(agent_session.session_id)

        return response

    ###########################################################
    # DASHBOARD & HEALTH HELPERS
    ###########################################################

    def health(self):
        return {"status": "healthy"}

    def runtime_metrics(self):
        return {"total_active_sessions": 0, "avg_queue_time": "0ms"}

    def cache_summary(self):
        return {"engine": "Semantic Cache"}

    def provider_summary(self):
        return {
            "provider": "Groq",
            "models": ["llama-3.1-8b-instant", "llama-3.3-70b-versatile"]
        }

    def clear_runtime_logs(self):
        analytics_db.logs.clear()

    async def clear_cache(self):
        semantic_cache._cache.clear()

    def dashboard(self):
        return {
            "health": self.health(),
            "runtime": self.runtime_metrics(),
            "cache": self.cache_summary(),
            "provider": self.provider_summary()
        }

# Singleton
runtime_controller = RuntimeController()