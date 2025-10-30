import hashlib
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from app.services.mongodb_service import mongodb_service

class DocumentCacheService:
    def __init__(self):
        self.collection_name = "document_cache"

    def _generate_content_hash(self, content: str) -> str:
        """Generate SHA256 hash of document content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    async def get_cached_submission(self, content: str) -> Optional[Dict[str, Any]]:
        """Get cached submission by content hash."""
        content_hash = self._generate_content_hash(content)
        
        cached_doc = await mongodb_service.db[self.collection_name].find_one({
            "content_hash": content_hash,
            "expires_at": {"$gt": datetime.utcnow()}
        })
        
        return cached_doc["submission_data"] if cached_doc else None

    async def cache_submission(self, content: str, submission_data: Dict[str, Any], 
                              ttl_hours: int = 168) -> None:  # 7 days default
        """Cache submission data by content hash."""
        content_hash = self._generate_content_hash(content)
        expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)
        
        await mongodb_service.db[self.collection_name].update_one(
            {"content_hash": content_hash},
            {
                "$set": {
                    "content_hash": content_hash,
                    "submission_data": submission_data,
                    "created_at": datetime.utcnow(),
                    "expires_at": expires_at,
                    "access_count": 1
                },
                "$inc": {"access_count": 1}
            },
            upsert=True
        )

document_cache_service = DocumentCacheService()