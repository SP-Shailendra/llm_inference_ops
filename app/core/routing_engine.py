from app.schemas.request import InferenceRequest


class RoutingEngine:
    """
    Enterprise Intelligent Routing Engine

    Responsibilities
    ----------------
    • Manual Tier Routing
    • Automatic Model Selection
    • Profile-aware Routing
    • Future Provider Selection
    • Future Budget-aware Routing
    """

    def __init__(self):

        # Model mapping must exactly match llm_client.py
        self.tier_mapping = {
            "tier_1_premium": "llama-3.3-70b-versatile",
            "tier_2_balanced": "llama-3.1-8b-instant",
            "tier_3_low_cost": "llama-3.1-8b-instant",
        }

    # -------------------------------------------------------
    # Public API
    # -------------------------------------------------------

    def determine_model(self, request: InferenceRequest) -> str:
        """
        Determines the best model for the request.
        Priority:

        1. Optimization Profile
        2. Manual Routing Tier
        3. Automatic Complexity Analysis
        """

        profile = getattr(request, "optimization_profile", "balanced")

        # -----------------------------------------
        # Cost Saver Profile
        # -----------------------------------------

        if profile == "cost_saver":
            return self.tier_mapping["tier_3_low_cost"]

        # -----------------------------------------
        # Performance Profile
        # -----------------------------------------

        if profile == "performance":
            return self.tier_mapping["tier_1_premium"]

        # -----------------------------------------
        # Manual Tier Override
        # -----------------------------------------

        if (
            request.routing_tier != "auto"
            and request.routing_tier in self.tier_mapping
        ):
            return self.tier_mapping[request.routing_tier]

        # -----------------------------------------
        # Automatic Routing
        # -----------------------------------------

        return self._auto_route(request)

    # -------------------------------------------------------
    # Internal Routing Logic
    # -------------------------------------------------------

    def _auto_route(self, request: InferenceRequest) -> str:
        """
        Intelligent routing based on prompt complexity.
        """

        prompt = request.prompt.lower()

        word_count = len(prompt.split())

        # Long context usually benefits from larger models
        if word_count > 400:
            return self.tier_mapping["tier_1_premium"]

        # Detect reasoning-heavy requests

        reasoning_keywords = [

            "analyze",
            "analysis",
            "architecture",
            "design",
            "optimize",
            "research",
            "compare",
            "evaluate",
            "strategy",
            "complex",
            "enterprise",
            "framework",
            "reason",
            "explain deeply"

        ]

        score = sum(
            keyword in prompt
            for keyword in reasoning_keywords
        )

        if score >= 2:
            return self.tier_mapping["tier_1_premium"]

        # Large generation requests

        if request.max_tokens and request.max_tokens > 3000:
            return self.tier_mapping["tier_1_premium"]

        # Default model

        return self.tier_mapping["tier_2_balanced"]

    # -------------------------------------------------------
    # Future Provider Routing
    # -------------------------------------------------------

    def determine_provider(self, model_name: str) -> str:
        """
        Placeholder for future multi-provider support.

        Future:
            - Groq
            - OpenAI
            - Gemini
            - Ollama
            - vLLM
        """

        return "Groq"


model_router = RoutingEngine()