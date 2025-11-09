"""Embedding cache service for reusing embeddings of similar content."""

import hashlib
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from app.services.mongodb_service import mongodb_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EmbeddingCacheService:
    """Manages embedding cache with content hash-based lookup."""

    def __init__(self):
        self.collection = mongodb_service.db["embedding_cache"]
        self.ttl_days = 30  # Cache embeddings for 30 days

    async def initialize(self):
        """Create necessary indexes for the collection."""
        await self.collection.create_index("content_hash", unique=True)
        await self.collection.create_index("created_at")

    def _generate_content_hash(self, content: str) -> str:
        """Generate SHA256 hash of content."""
        return hashlib.sha256(content.encode()).hexdigest()

    async def get_cached_embeddings(self, content: str) -> Optional[List[str]]:
        """Get cached embedding IDs for content."""
        try:
            content_hash = self._generate_content_hash(content)

            cache_entry = await self.collection.find_one({"content_hash": content_hash})

            if cache_entry:
                try:
                    # Check if not expired
                    created_at = cache_entry.get("created_at")
                    if created_at:
                        expiry = created_at + timedelta(days=self.ttl_days)
                        if datetime.now(timezone.utc) < expiry:
                            logger.info(f"Embedding cache hit: {content_hash[:8]}")
                            return cache_entry.get("embedding_ids", [])
                except TypeError:
                    logger.warning(
                        f"Invalid 'created_at' in cache for hash {content_hash[:8]}. Deleting entry."
                    )

                # Expired or invalid, delete it
                await self.collection.delete_one({"content_hash": content_hash})

            return None

        except Exception as e:
            logger.error(
                e,
                additional_info={
                    "component": "embedding_cache_service",
                    "function": "get_cached_embeddings",
                },
            )
            return None

    async def cache_embeddings(
        self, content: str, embedding_ids: List[str], metadata: dict = None
    ) -> bool:
        """Cache embedding IDs for content."""
        try:
            content_hash = self._generate_content_hash(content)

            cache_entry = {
                "content_hash": content_hash,
                "embedding_ids": embedding_ids,
                "metadata": metadata or {},
                "created_at": datetime.now(timezone.utc),
                "content_length": len(content),
            }

            await self.collection.update_one(
                {"content_hash": content_hash}, {"$set": cache_entry}, upsert=True
            )

            logger.info(f"Embeddings cached: {content_hash[:8]} ({len(embedding_ids)} chunks)")
            return True

        except Exception as e:
            logger.error(
                e,
                additional_info={
                    "component": "embedding_cache_service",
                    "function": "cache_embeddings",
                },
            )
            return False

    async def cleanup_expired(self) -> int:
        """Remove expired cache entries."""
        try:
            expiry_date = datetime.now(timezone.utc) - timedelta(days=self.ttl_days)

            result = await self.collection.delete_many({"created_at": {"$lt": expiry_date}})

            if result.deleted_count > 0:
                logger.info(f"Cleaned up {result.deleted_count} expired embedding caches")

            return result.deleted_count

        except Exception as e:
            logger.error(
                e,
                additional_info={
                    "component": "embedding_cache_service",
                    "function": "cleanup_expired",
                },
            )
            raise


embedding_cache_service = EmbeddingCacheService()
