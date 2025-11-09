import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.services.mongodb_service import mongodb_service
from app.utils.logger import get_logger


class CacheService:
    def __init__(self, default_ttl_hours: int = 24):
        self.default_ttl_hours = default_ttl_hours
        self.collection_name = "llm_cache"
        self.logger = get_logger()

    def _ensure_aware(self, dt: Optional[datetime]) -> Optional[datetime]:
        """Ensure a datetime is timezone-aware in UTC; if naive, assume UTC."""
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    def _generate_cache_key(
        self, prompt: str, provider: str, model_params: Optional[dict] = None
    ) -> str:
        """Generate deterministic cache key from prompt and parameters."""
        cache_data = {
            "prompt": prompt.strip(),
            "provider": provider,
            "params": model_params or {},
        }
        # use compact separators to reduce produced string size and speed up serialization
        return hashlib.sha256(
            json.dumps(cache_data, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    async def get(
        self, prompt: str, provider: str, model_params: Optional[dict] = None
    ) -> Optional[str]:
        """Retrieve cached LLM response if not expired."""
        try:
            if not prompt or not provider:
                return None

            cache_key = self._generate_cache_key(prompt, provider, model_params)
            now = datetime.now(timezone.utc)

            # Retrieve by key and perform a safe expiration check in Python to avoid
            # mixing naive/aware datetimes returned from the DB.
            cached_item = await mongodb_service.db[self.collection_name].find_one(
                {"cache_key": cache_key}
            )

            if not cached_item:
                return None

            expires_at = cached_item.get("expires_at")
            if isinstance(expires_at, datetime):
                expires_at = self._ensure_aware(expires_at)
                # now is timezone-aware in UTC too, safe to compare
                if expires_at > now:
                    return cached_item.get("response")
                # expired: try to remove stale cache entry
                try:
                    await mongodb_service.db[self.collection_name].delete_one(
                        {"cache_key": cache_key}
                    )
                except Exception as e:
                    self.logger.warning(
                        f"Failed to delete expired cache entry: {e}",
                        additional_info={"operation": "cache_delete_stale", "cache_key": cache_key},
                    )

            return None
        except Exception as e:
            self.logger.error(e, additional_info={"operation": "cache_get", "provider": provider})
            return None

    async def set(
        self,
        prompt: str,
        provider: str,
        response: str,
        model_params: Optional[dict] = None,
        ttl_hours: Optional[int] = None,
    ) -> None:
        """Cache LLM response with expiration."""
        try:
            if not prompt or not provider or not response:
                return

            cache_key = self._generate_cache_key(prompt, provider, model_params)
            ttl = ttl_hours or self.default_ttl_hours
            now = datetime.now(timezone.utc)
            expires_at = now + timedelta(hours=ttl)
            await mongodb_service.db[self.collection_name].update_one(
                {"cache_key": cache_key},
                {
                    "$set": {
                        "cache_key": cache_key,
                        # reuse the already-computed cache_key prefix instead of hashing prompt again
                        "prompt_hash": cache_key[:16],
                        "provider": provider,
                        "response": response,
                        "created_at": now,
                        "expires_at": expires_at,
                        "model_params": model_params or {},
                    }
                },
                upsert=True,
            )
        except Exception as e:
            self.logger.error(e, additional_info={"operation": "cache_set", "provider": provider})

    async def clear_expired(self) -> int:
        """Remove expired cache entries."""
        try:
            if mongodb_service.db is None:
                self.logger.warning("Database not available, skipping cache clearing.")
                return 0
            now = datetime.now(timezone.utc)
            result = await mongodb_service.db[self.collection_name].delete_many(
                {"expires_at": {"$lt": now}}
            )
            return result.deleted_count
        except Exception as e:
            self.logger.error(e, additional_info={"operation": "cache_clear_expired"})
            return 0


cache_service = CacheService()
