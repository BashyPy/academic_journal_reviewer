import hashlib
import json
from typing import Optional, Any
from datetime import datetime, timedelta
from app.services.mongodb_service import mongodb_service

class CacheService:
    def __init__(self, default_ttl_hours: int = 24):
        self.default_ttl_hours = default_ttl_hours
        self.collection_name = "llm_cache"

    def _generate_cache_key(self, prompt: str, provider: str, model_params: dict = None) -> str:
        """Generate deterministic cache key from prompt and parameters."""
        cache_data = {
            "prompt": prompt.strip(),
            "provider": provider,
            "params": model_params or {}
        }
        return hashlib.sha256(json.dumps(cache_data, sort_keys=True).encode()).hexdigest()

    async def get(self, prompt: str, provider: str, model_params: dict = None) -> Optional[str]:
        """Retrieve cached LLM response if available and not expired."""
        cache_key = self._generate_cache_key(prompt, provider, model_params)
        
        cached_item = await mongodb_service.db[self.collection_name].find_one({
            "cache_key": cache_key,
            "expires_at": {"$gt": datetime.utcnow()}
        })
        
        return cached_item["response"] if cached_item else None

    async def set(self, prompt: str, provider: str, response: str, 
                  model_params: dict = None, ttl_hours: int = None) -> None:
        """Cache LLM response with expiration."""
        cache_key = self._generate_cache_key(prompt, provider, model_params)
        ttl = ttl_hours or self.default_ttl_hours
        expires_at = datetime.utcnow() + timedelta(hours=ttl)
        
        await mongodb_service.db[self.collection_name].update_one(
            {"cache_key": cache_key},
            {
                "$set": {
                    "cache_key": cache_key,
                    "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest()[:16],
                    "provider": provider,
                    "response": response,
                    "created_at": datetime.utcnow(),
                    "expires_at": expires_at,
                    "model_params": model_params or {}
                }
            },
            upsert=True
        )

    async def clear_expired(self) -> int:
        """Remove expired cache entries."""
        result = await mongodb_service.db[self.collection_name].delete_many({
            "expires_at": {"$lt": datetime.utcnow()}
        })
        return result.deleted_count

cache_service = CacheService()