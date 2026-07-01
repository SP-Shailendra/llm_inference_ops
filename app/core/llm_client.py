import time
import importlib
from dataclasses import dataclass
from typing import Dict, List, Optional
from abc import ABC, abstractmethod
import httpx
from groq import AsyncGroq
from openai import AsyncOpenAI
from fastapi import HTTPException

from app.config import settings
from app.schemas.request import InferenceRequest
from app.schemas.response import InferenceResponse, InferenceMetrics
from app.core.config_engine import config_engine

# Pricing per 1 Million Tokens (USD)
PRICING_TIERS = {
    "llama-3.1-8b-instant": {"input": 0.05, "output": 0.08},
    "llama-3.3-70b-versatile": {"input": 0.59, "output": 0.79},
    "gemini-2.5-flash": {"input": 0.01, "output": 0.02},
    "gemini-1.5-flash": {"input": 0.01, "output": 0.02} # Example pricing
}


@dataclass
class ProviderSpec:
    provider: str
    kind: str
    models: List[str]
    api_key: Optional[str]
    base_url: Optional[str] = None
    reason: Optional[str] = None

# -------------------------------------------------------
# Base Adapter Interface
# -------------------------------------------------------
class BaseInferenceEngine(ABC):
    @abstractmethod
    async def generate(self, request: InferenceRequest, model_name: str) -> InferenceResponse:
        pass

    def _estimate_tokens(self, prompt: str) -> int:
        return max(int(len(prompt) / 4), len(prompt.split()))

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        fallback = next(iter(PRICING_TIERS.values()))
        pricing = PRICING_TIERS.get(model, fallback)
        return (input_tokens / 1_000_000) * pricing["input"] + (output_tokens / 1_000_000) * pricing["output"]

    def _build_response(self, request: InferenceRequest, model_name: str, provider_name: str, content: str, latency_ms: float, usage=None) -> InferenceResponse:
        input_tokens = (
            usage.prompt_tokens
            if usage and getattr(usage, "prompt_tokens", None) is not None
            else self._estimate_tokens(request.prompt)
        )

        output_tokens = (
            usage.completion_tokens
            if usage and getattr(usage, "completion_tokens", None) is not None
            else self._estimate_tokens(content)
        )

        total_cost = self._calculate_cost(model_name, input_tokens, output_tokens)

        metrics = InferenceMetrics(
            ttft_ms=latency_ms,
            tpot_ms=round(latency_ms / max(output_tokens, 1), 4),
            total_latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_cost_usd=round(total_cost, 6),
            provider_used=provider_name,
            model_used=model_name,
            cache_hit=False,
        )

        return InferenceResponse(content=content, metrics=metrics)

# -------------------------------------------------------
# Groq Adapter (Your original logic)
# -------------------------------------------------------
class GroqAdapter(BaseInferenceEngine):
    def __init__(self):
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.provider_name = "Groq"
        self.supported_models = [
            "llama-3.1-8b-instant",
            "llama-3.3-70b-versatile"
        ]

    async def generate(self, request: InferenceRequest, model_name: str) -> InferenceResponse:
        profile = config_engine.get_profile(getattr(request, "optimization_profile", "balanced"))
        start_time = time.perf_counter()

        temperature = (
            request.temperature
            if request.temperature is not None
            else profile.runtime.temperature
        )
        max_tokens = (
            request.max_tokens
            if request.max_tokens is not None
            else profile.runtime.max_tokens
        )

        if not settings.GROQ_API_KEY:
            raise HTTPException(
                status_code=500,
                detail="Groq API key is not configured"
            )

        try:
            completion = await self.client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "user",
                        "content": request.prompt
                    }
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
        except Exception as ex:
            raise HTTPException(
                status_code=502,
                detail=f"Groq generation failed: {str(ex)}"
            ) from ex

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        content = ""
        if completion.choices and completion.choices[0].message:
            content = completion.choices[0].message.content or ""

        return self._build_response(
            request=request,
            model_name=model_name,
            provider_name=self.provider_name,
            content=content,
            latency_ms=latency_ms,
            usage=getattr(completion, "usage", None),
        )


class OpenAICompatibleAdapter(BaseInferenceEngine):
    def __init__(self, provider_name: str, api_key: str, models: List[str], base_url: Optional[str] = None):
        self.provider_name = provider_name
        self.supported_models = models
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        self.client = AsyncOpenAI(**client_kwargs)

    async def generate(self, request: InferenceRequest, model_name: str) -> InferenceResponse:
        profile = config_engine.get_profile(getattr(request, "optimization_profile", "balanced"))
        start_time = time.perf_counter()

        temperature = request.temperature if request.temperature is not None else profile.runtime.temperature
        max_tokens = request.max_tokens if request.max_tokens is not None else profile.runtime.max_tokens

        try:
            completion = await self.client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": request.prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as ex:
            raise HTTPException(
                status_code=502,
                detail=f"{self.provider_name} generation failed: {str(ex)}",
            ) from ex

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        content = ""
        if completion.choices and completion.choices[0].message:
            content = completion.choices[0].message.content or ""

        return self._build_response(
            request=request,
            model_name=model_name,
            provider_name=self.provider_name,
            content=content,
            latency_ms=latency_ms,
            usage=getattr(completion, "usage", None),
        )

# -------------------------------------------------------
# Gemini Adapter
# -------------------------------------------------------
class GeminiAdapter(BaseInferenceEngine):
    def __init__(self):
        self.provider_name = "Gemini"
        self._client = None
        self.supported_models = [
            "gemini-2.5-flash",
            "gemini-1.5-flash"
        ]

    def _get_client(self):
        if self._client is not None:
            return self._client

        if not settings.GEMINI_API_KEY:
            raise HTTPException(
                status_code=500,
                detail="Gemini API key is not configured"
            )

        try:
            genai_module = importlib.import_module("google.genai")
        except ImportError as ex:
            raise HTTPException(
                status_code=500,
                detail="Gemini provider requires package 'google-genai'"
            ) from ex

        self._client = genai_module.Client(api_key=settings.GEMINI_API_KEY)
        return self._client

    async def generate(self, request: InferenceRequest, model_name: str) -> InferenceResponse:
        client = self._get_client()
        start_time = time.perf_counter()

        candidate_models = [model_name]
        for fallback_model in self.supported_models:
            if fallback_model not in candidate_models:
                candidate_models.append(fallback_model)

        response = None
        selected_model = model_name
        last_error = None

        for candidate in candidate_models:
            try:
                response = await client.aio.models.generate_content(
                    model=candidate,
                    contents=request.prompt
                )
                selected_model = candidate
                break
            except Exception as ex:
                last_error = ex

        if response is None:
            raise HTTPException(
                status_code=502,
                detail=f"Gemini generation failed: {str(last_error)}"
            ) from last_error

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        input_tokens = self._estimate_tokens(request.prompt)
        content = response.text if getattr(response, "text", None) else str(response)
        output_tokens = self._estimate_tokens(content)

        pricing = PRICING_TIERS.get(selected_model, PRICING_TIERS["gemini-2.5-flash"])
        total_cost = (
            (input_tokens / 1_000_000) * pricing["input"]
            + (output_tokens / 1_000_000) * pricing["output"]
        )

        metrics = InferenceMetrics(
            ttft_ms=latency_ms,
            tpot_ms=round(latency_ms / max(output_tokens, 1), 4),
            total_latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_cost_usd=round(total_cost, 6),
            provider_used=self.provider_name,
            model_used=selected_model,
            cache_hit=False
        )

        return InferenceResponse(content=content, metrics=metrics)

# -------------------------------------------------------
# Unified Orchestrator
# -------------------------------------------------------
class UnifiedLLMEngine:
    def __init__(self):
        self.adapters: Dict[str, BaseInferenceEngine] = {}
        self.provider_aliases: Dict[str, str] = {}
        self.provider_specs = self._build_provider_specs()
        self._register_adapters()

    def _build_provider_specs(self) -> List[ProviderSpec]:
        return [
            ProviderSpec("Groq", "groq", ["llama-3.1-8b-instant", "llama-3.3-70b-versatile", "deepseek-r1-distill-llama-70b"], settings.GROQ_API_KEY),
            ProviderSpec("Gemini", "gemini", ["gemini-2.5-flash", "gemini-1.5-flash"], settings.GEMINI_API_KEY),
            ProviderSpec("OpenAI", "openai_compatible", ["gpt-5", "gpt-5-mini", "gpt-5-nano", "o3", "o4-mini"], settings.OPENAI_API_KEY, settings.OPENAI_BASE_URL),
            ProviderSpec("Anthropic", "placeholder", ["claude-opus-4-1", "claude-sonnet-4", "claude-3-5-haiku"], settings.ANTHROPIC_API_KEY, reason="Native Anthropic adapter is not implemented yet"),
            ProviderSpec("xAI", "openai_compatible", ["grok-4", "grok-3"], settings.XAI_API_KEY, settings.XAI_BASE_URL),
            ProviderSpec("Mistral", "openai_compatible", ["mistral-large", "codestral", "mixtral-8x7b-instruct"], settings.MISTRAL_API_KEY, settings.MISTRAL_BASE_URL),
            ProviderSpec("DeepSeek", "openai_compatible", ["deepseek-v3", "deepseek-r1", "deepseek-coder"], settings.DEEPSEEK_API_KEY, settings.DEEPSEEK_BASE_URL),
            ProviderSpec("OpenRouter", "openai_compatible", ["openrouter/auto", "anthropic/claude-sonnet-4", "openai/gpt-5-mini"], settings.OPENROUTER_API_KEY, settings.OPENROUTER_BASE_URL),
            ProviderSpec("NVIDIA NIM", "openai_compatible", ["meta/llama-3.1-70b-instruct", "mistralai/mixtral-8x7b-instruct-v0.1"], settings.NVIDIA_NIM_API_KEY, settings.NVIDIA_NIM_BASE_URL),
            ProviderSpec("Alibaba", "openai_compatible", ["qwen-plus", "qwen-max", "qwen-turbo"], settings.ALIBABA_API_KEY, settings.ALIBABA_BASE_URL),
            ProviderSpec("Ollama", "openai_compatible", ["local-model"], "local" if settings.OLLAMA_BASE_URL else None, settings.OLLAMA_BASE_URL),
            ProviderSpec("vLLM", "openai_compatible", ["local-model"], "local" if settings.VLLM_BASE_URL else None, settings.VLLM_BASE_URL),
            ProviderSpec("Hugging Face TGI", "openai_compatible", ["local-model"], "local" if settings.TGI_BASE_URL else None, settings.TGI_BASE_URL),
            ProviderSpec("llama.cpp", "openai_compatible", ["local-model"], "local" if settings.LLAMACPP_BASE_URL else None, settings.LLAMACPP_BASE_URL),
        ]

    def _is_endpoint_reachable(self, base_url: Optional[str]) -> bool:
        if not base_url:
            return False

        models_url = f"{base_url.rstrip('/')}/models"

        try:
            response = httpx.get(models_url, timeout=1.2)
            return response.status_code < 500
        except Exception:
            return False

    def _register_adapters(self):
        for spec in self.provider_specs:
            if spec.kind == "placeholder":
                continue

            if not spec.api_key:
                continue

            if spec.api_key == "local" and not self._is_endpoint_reachable(spec.base_url):
                spec.reason = f"Local endpoint unreachable at {spec.base_url}"
                continue

            try:
                if spec.kind == "groq":
                    adapter = GroqAdapter()
                elif spec.kind == "gemini":
                    adapter = GeminiAdapter()
                elif spec.kind == "openai_compatible":
                    adapter = OpenAICompatibleAdapter(
                        provider_name=spec.provider,
                        api_key=spec.api_key,
                        models=spec.models,
                        base_url=spec.base_url,
                    )
                else:
                    continue

                self.adapters[spec.provider] = adapter
                self.provider_aliases[spec.provider.strip().lower()] = spec.provider
            except Exception:
                if spec.reason is None:
                    spec.reason = f"Initialization failed for {spec.provider}"
                continue

        if "Groq" not in self.adapters and settings.GROQ_API_KEY:
            self.adapters["Groq"] = GroqAdapter()
            self.provider_aliases["groq"] = "Groq"

    def _try_activate_local_provider(self, spec: ProviderSpec):
        """Attempt to activate a local OpenAI-compatible provider at runtime.

        This lets providers appear after local servers start, without requiring
        a process restart.
        """

        if spec.provider in self.adapters:
            return

        if spec.kind != "openai_compatible" or spec.api_key != "local":
            return

        if not self._is_endpoint_reachable(spec.base_url):
            spec.reason = f"Local endpoint unreachable at {spec.base_url}"
            return

        try:
            adapter = OpenAICompatibleAdapter(
                provider_name=spec.provider,
                api_key=spec.api_key,
                models=spec.models,
                base_url=spec.base_url,
            )
            self.adapters[spec.provider] = adapter
            self.provider_aliases[spec.provider.strip().lower()] = spec.provider
            spec.reason = None
        except Exception:
            spec.reason = f"Initialization failed for {spec.provider}"

    def normalize_provider(self, provider_name: str) -> str:
        if not provider_name:
            if "Groq" in self.adapters:
                return "Groq"
            if self.adapters:
                return next(iter(self.adapters.keys()))
            raise HTTPException(status_code=500, detail="No configured LLM providers available")

        normalized = self.provider_aliases.get(
            provider_name.strip().lower()
        )

        if not normalized:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported provider '{provider_name}'"
            )

        return normalized

    def list_providers(self):
        providers = []

        # Opportunistically activate local providers that became reachable
        # after app startup.
        for spec in self.provider_specs:
            self._try_activate_local_provider(spec)

        enabled_map = {name: adapter for name, adapter in self.adapters.items()}
        for spec in self.provider_specs:
            adapter = enabled_map.get(spec.provider)
            enabled = adapter is not None
            reason = None if enabled else (spec.reason or f"Missing configuration for {spec.provider}")

            models = spec.models
            if enabled and hasattr(adapter, "supported_models"):
                models = getattr(adapter, "supported_models")

            providers.append(
                {
                    "provider": spec.provider,
                    "enabled": enabled,
                    "reason": reason,
                    "models": models,
                }
            )

        return providers

    async def generate(self, request: InferenceRequest, model_name: str, provider_name: str = "Groq") -> InferenceResponse:
        provider_name = self.normalize_provider(provider_name)
        adapter = self.adapters.get(provider_name)
        if not adapter:
            raise HTTPException(status_code=500, detail=f"Provider {provider_name} not found")
        return await adapter.generate(request, model_name)

llm_engine = UnifiedLLMEngine()