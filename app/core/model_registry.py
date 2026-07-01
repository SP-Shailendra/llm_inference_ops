from typing import List, Optional
from app.schemas.registry import ModelVariant, PricingInfo, QuantizationInfo

class ModelRegistry:
    def __init__(self):
        # Simulating a database of quantized model variants
        # In a real environment, this tracks actual weights sitting on disk or in HuggingFace
        self.catalog = {
            "llama3-8b-fp16": ModelVariant(
                variant_id="llama3-8b-fp16",
                display_name="Llama 3.1 8B FP16",
                base_model="llama-3.1-8b-instant",
                provider="Groq",
                deployment_id="groq-us-east-1-8b-fp16",
                quantization=QuantizationInfo(
                    precision="FP16",
                    memory_reduction_percent=0.0,
                    expected_accuracy=1.00
                ),
                pricing=PricingInfo(
                    input_cost_per_1k_tokens=0.0005,
                    output_cost_per_1k_tokens=0.0015
                ),
                context_window=8192,
                max_output_tokens=4096,
                vram_required_gb=16.0,
                accuracy_retention=1.00,
                is_outlier_sensitive=False,
                cost_multiplier=1.0,
                recommended_for=["general_chat", "balanced_workloads"],
                tags=["production", "baseline"]
            ),
            "llama3-8b-int8": ModelVariant(
                variant_id="llama3-8b-int8",
                display_name="Llama 3.1 8B INT8",
                base_model="llama-3.1-8b-instant",
                provider="Groq",
                deployment_id="groq-us-east-1-8b-int8",
                quantization=QuantizationInfo(
                    precision="INT8",
                    memory_reduction_percent=47.0,
                    expected_accuracy=0.99
                ),
                pricing=PricingInfo(
                    input_cost_per_1k_tokens=0.0004,
                    output_cost_per_1k_tokens=0.0012
                ),
                context_window=8192,
                max_output_tokens=4096,
                vram_required_gb=8.5,
                accuracy_retention=0.99,
                is_outlier_sensitive=False,
                cost_multiplier=0.8,
                recommended_for=["cost_optimized", "high_qps"],
                tags=["quantized", "economical"]
            ),
            "llama3-8b-int4": ModelVariant(
                variant_id="llama3-8b-int4",
                display_name="Llama 3.1 8B INT4",
                base_model="llama-3.1-8b-instant",
                provider="Groq",
                deployment_id="groq-us-east-1-8b-int4",
                quantization=QuantizationInfo(
                    precision="INT4",
                    memory_reduction_percent=70.0,
                    expected_accuracy=0.94
                ),
                pricing=PricingInfo(
                    input_cost_per_1k_tokens=0.00025,
                    output_cost_per_1k_tokens=0.00075
                ),
                context_window=8192,
                max_output_tokens=4096,
                vram_required_gb=4.8,
                accuracy_retention=0.94,
                is_outlier_sensitive=True,
                cost_multiplier=0.5,  # 50% cheaper to run
                recommended_for=["batch_inference", "latency_sensitive"],
                tags=["quantized", "int4"]
            ),
            "llama3-70b-fp16": ModelVariant(
                variant_id="llama3-70b-fp16",
                display_name="Llama 3.3 70B FP16",
                base_model="llama-3.3-70b-versatile",
                provider="Groq",
                deployment_id="groq-us-east-1-70b-fp16",
                quantization=QuantizationInfo(
                    precision="FP16",
                    memory_reduction_percent=0.0,
                    expected_accuracy=1.00
                ),
                pricing=PricingInfo(
                    input_cost_per_1k_tokens=0.002,
                    output_cost_per_1k_tokens=0.006
                ),
                context_window=32768,
                max_output_tokens=8192,
                vram_required_gb=140.0,  # Requires multiple A100s
                accuracy_retention=1.00,
                is_outlier_sensitive=False,
                cost_multiplier=1.0,
                recommended_for=["deep_reasoning", "long_context"],
                tags=["premium", "high_quality"]
            ),
            "llama3-70b-awq": ModelVariant(
                variant_id="llama3-70b-awq",
                display_name="Llama 3.3 70B AWQ INT4",
                base_model="llama-3.3-70b-versatile",
                provider="Groq",
                deployment_id="groq-us-east-1-70b-awq",
                quantization=QuantizationInfo(
                    precision="AWQ-INT4",
                    memory_reduction_percent=73.0,
                    expected_accuracy=0.97
                ),
                pricing=PricingInfo(
                    input_cost_per_1k_tokens=0.0012,
                    output_cost_per_1k_tokens=0.0036
                ),
                context_window=32768,
                max_output_tokens=8192,
                vram_required_gb=38.0,  # Fits on a single A6000/A40
                accuracy_retention=0.97,
                is_outlier_sensitive=True,
                cost_multiplier=0.6,
                recommended_for=["reasoning", "cost_efficient_long_context"],
                tags=["awq", "quantized", "balanced"]
            )
        }

    def get_variant(self, variant_id: str) -> Optional[ModelVariant]:
        """Fetch a specific model variant's metadata."""
        return self.catalog.get(variant_id)

    def list_variants(self, base_model: Optional[str] = None) -> List[ModelVariant]:
        """List all variants, optionally filtered by the base model family."""
        if base_model:
            return [v for v in self.catalog.values() if v.base_model == base_model]
        return list(self.catalog.values())

    def recommend_variant(self, base_model: str, max_vram_gb: float) -> Optional[ModelVariant]:
        """
        Governance Engine feature:
        Recommends the highest precision variant that fits in the available hardware VRAM.
        """
        available_variants = self.list_variants(base_model)
        valid_variants = [v for v in available_variants if v.vram_required_gb <= max_vram_gb]
        
        if not valid_variants:
            return None
            
        # Sort by accuracy retention (descending) to get the best quality model that fits
        valid_variants.sort(key=lambda x: x.accuracy_retention, reverse=True)
        return valid_variants[0]

# Global instance
model_registry = ModelRegistry()