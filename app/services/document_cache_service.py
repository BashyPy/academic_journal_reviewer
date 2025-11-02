import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from app.services.mongodb_service import mongodb_service


class DocumentCacheService:
    def __init__(self):
        self.collection_name = "document_cache"

    def _generate_content_hash(self, content: str) -> str:
        """Generate SHA256 hash of document content."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    async def get_cached_submission(self, content: str) -> Optional[Dict[str, Any]]:
        """Get cached submission by content hash."""
        content_hash = self._generate_content_hash(content)

        # compute now once to avoid multiple evaluations and use projection to reduce
        # data transferred from MongoDB (only fetch submission_data)
        now = datetime.now(timezone.utc)
        cached_doc = await mongodb_service.db[self.collection_name].find_one(
            {"content_hash": content_hash, "expires_at": {"$gt": now}},
            {"submission_data": 1, "_id": 0},
        )

        return cached_doc.get("submission_data") if cached_doc else None

    async def cache_submission(
        self, content: str, submission_data: Dict[str, Any], ttl_hours: int = 168
    ) -> None:  # 7 days default
        """Cache submission data by content hash."""
        content_hash = self._generate_content_hash(content)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)

        # Try to increment access_count for existing document
        result = await mongodb_service.db[self.collection_name].update_one(
            {"content_hash": content_hash}, {"$inc": {"access_count": 1}}
        )

        # If no document exists, create new one
        if result.matched_count == 0:
            await mongodb_service.db[self.collection_name].update_one(
                {"content_hash": content_hash},
                {
                    "$set": {
                        "content_hash": content_hash,
                        "submission_data": submission_data,
                        "created_at": datetime.now(timezone.utc),
                        "expires_at": expires_at,
                        "access_count": 1,
                    }
                },
                upsert=True,
            )


document_cache_service = DocumentCacheService()
