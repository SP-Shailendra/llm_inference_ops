"""
Platform State Manager

Acts as the in-memory control plane for the entire platform.

Every major module can publish runtime information here,
allowing dashboards, advisors and governance APIs to access
a unified system view.

Version 1:
----------
- In-memory only
- Thread-safe enough for single-process FastAPI
- Easy to migrate to Redis later
"""

from datetime import datetime, timedelta
from typing import Any, Dict


class PlatformState:

    def __init__(self):

        # --------------------------------------------------
        # Runtime
        # --------------------------------------------------

        self.start_time = datetime.utcnow()

        self.active_requests = 0

        self.total_requests = 0

        self.failed_requests = 0

        # --------------------------------------------------
        # Cache
        # --------------------------------------------------

        self.cache_hits = 0

        self.cache_misses = 0

        # --------------------------------------------------
        # Cost
        # --------------------------------------------------

        self.total_cost = 0.0

        self.total_input_tokens = 0

        self.total_output_tokens = 0

        # --------------------------------------------------
        # Models
        # --------------------------------------------------

        self.model_usage: Dict[str, int] = {}

        # Track concurrent active models in-flight
        self.active_models: Dict[str, int] = {}

        # Track last-seen timestamp for each model so infra UI can show
        # recently active deployments instead of appearing empty between polls.
        self.model_last_seen: Dict[str, datetime] = {}
        self.recent_model_window_seconds = 45

        # --------------------------------------------------
        # Provider Usage
        # --------------------------------------------------

        self.provider_usage: Dict[str, int] = {}

        # --------------------------------------------------
        # Runtime Profiles
        # --------------------------------------------------

        self.profile_usage: Dict[str, int] = {}

        # --------------------------------------------------
        # Advisor
        # --------------------------------------------------

        self.last_recommendation = None

        # --------------------------------------------------
        # Alerts
        # --------------------------------------------------

        self.alerts = []

    # ======================================================
    # Request Lifecycle
    # ======================================================

    def request_started(self):

        self.active_requests += 1

        self.total_requests += 1

    def request_completed(self):

        if self.active_requests > 0:
            self.active_requests -= 1

    def request_failed(self):

        self.failed_requests += 1

        if self.active_requests > 0:
            self.active_requests -= 1

    # ======================================================
    # Cache
    # ======================================================

    def cache_hit(self):

        self.cache_hits += 1

    def cache_miss(self):

        self.cache_misses += 1

    # ======================================================
    # Cost
    # ======================================================

    def update_cost(
        self,
        cost: float,
        input_tokens: int,
        output_tokens: int
    ):

        self.total_cost += cost

        self.total_input_tokens += input_tokens

        self.total_output_tokens += output_tokens

    # ======================================================
    # Model Usage
    # ======================================================

    def record_model(self, model: str):

        self.model_usage[model] = (
            self.model_usage.get(model, 0) + 1
        )

    def add_active_model(self, model_name: str):
        """Increments active concurrent requests for a specific model."""

        self.active_requests += 1

        self.model_last_seen[model_name] = datetime.utcnow()

        self.active_models[model_name] = (
            self.active_models.get(model_name, 0) + 1
        )

    def remove_active_model(self, model_name: str):
        """Decrements active concurrent requests for a specific model."""

        self.active_requests = max(0, self.active_requests - 1)

        self.model_last_seen[model_name] = datetime.utcnow()

        if (
            model_name in self.active_models
            and self.active_models[model_name] > 0
        ):
            self.active_models[model_name] -= 1

    def infrastructure_health(self):
        """
        Simulates GPU load and hardware health based on active concurrent requests.
        Also includes recently used models so dashboard does not look empty
        between polling intervals.
        """

        nodes = []

        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self.recent_model_window_seconds)

        models_to_render = set(self.active_models.keys())
        for model, ts in self.model_last_seen.items():
            if ts >= cutoff:
                models_to_render.add(model)

        # Drop stale last-seen records to keep memory bounded.
        stale_models = [m for m, ts in self.model_last_seen.items() if ts < cutoff]
        for model in stale_models:
            self.model_last_seen.pop(model, None)

        for model in sorted(models_to_render):

            count = self.active_models.get(model, 0)
            last_seen = self.model_last_seen.get(model)
            seconds_ago = int((now - last_seen).total_seconds()) if last_seen else None

            if count > 0:
                load = min(100, 10 + (count * 35))
                status = "overloaded" if load >= 80 else "healthy"
            else:
                load = 6
                status = "idle"

            nodes.append({
                "model": model,
                "active_connections": count,
                "simulated_gpu_load_percent": load,
                "status": status,
                "last_seen_seconds_ago": seconds_ago,
            })

        return {
            "global_active_requests": self.active_requests,
            "nodes": nodes
        }

    # ======================================================
    # Provider Usage
    # ======================================================

    def record_provider(self, provider: str):

        self.provider_usage[provider] = (
            self.provider_usage.get(provider, 0) + 1
        )

    # ======================================================
    # Profile Usage
    # ======================================================

    def record_profile(self, profile: str):

        self.profile_usage[profile] = (
            self.profile_usage.get(profile, 0) + 1
        )

    # ======================================================
    # Advisor
    # ======================================================

    def set_recommendation(self, recommendation):

        self.last_recommendation = recommendation

    # ======================================================
    # Alerts
    # ======================================================

    def add_alert(self, message: str):

        self.alerts.append({
            "timestamp": datetime.utcnow().isoformat(),
            "message": message
        })

    # ======================================================
    # Dashboard
    # ======================================================

    def summary(self):

        return {

            "uptime": str(datetime.utcnow() - self.start_time),

            "active_requests": self.active_requests,

            "total_requests": self.total_requests,

            "failed_requests": self.failed_requests,

            "cache_hits": self.cache_hits,

            "cache_misses": self.cache_misses,

            "total_cost": round(self.total_cost, 6),

            "input_tokens": self.total_input_tokens,

            "output_tokens": self.total_output_tokens,

            "models": self.model_usage,

            "providers": self.provider_usage,

            "profiles": self.profile_usage,

            "alerts": self.alerts[-10:]
        }


platform_state = PlatformState()