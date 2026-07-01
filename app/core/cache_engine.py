import hashlib
import copy
from typing import Optional
from app.schemas.response import InferenceResponse

class CacheEngine:
    def __init__(self):
        # In a full production environment, this dictionary would be replaced 
        # by Redis or a Vector Database (like Pinecone or Weaviate)
        self._cache = {}

    def _generate_key(self, prompt: str, model: str) -> str:
        """Generates a deterministic hash for the cache key."""
        unique_string = f"{prompt.strip().lower()}_{model}"
        return hashlib.md5(unique_string.encode()).hexdigest()

    async def check_cache(self, prompt: str, model: str) -> Optional[InferenceResponse]:
        """Checks if a semantically identical prompt exists in memory."""
        key = self._generate_key(prompt, model)
        if key in self._cache:
            # We return a deep copy so we can modify the metrics (like TTFT) 
            # for this specific request without corrupting the stored cache
            return copy.deepcopy(self._cache[key])
        return None

    async def store_cache(self, prompt: str, model: str, response: InferenceResponse):
        """Stores the successful LLM response in memory."""
        key = self._generate_key(prompt, model)
        self._cache[key] = copy.deepcopy(response)

semantic_cache = CacheEngine()