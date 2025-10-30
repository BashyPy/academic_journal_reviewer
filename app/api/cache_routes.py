from fastapi import APIRouter
from app.services.cache_service import cache_service
from app.services.document_cache_service import document_cache_service

router = APIRouter(prefix="/api/v1/cache", tags=["cache"])

@router.delete("/expired")
async def clear_expired_cache():
    """Clear expired cache entries."""
    deleted_count = await cache_service.clear_expired()
    return {"deleted_count": deleted_count}

@router.get("/stats")
async def get_cache_stats():
    """Get cache statistics."""
    from app.services.mongodb_service import mongodb_service
    
    total_entries = await mongodb_service.db["llm_cache"].count_documents({})
    expired_entries = await mongodb_service.db["llm_cache"].count_documents({
        "expires_at": {"$lt": mongodb_service.get_current_time()}
    })
    
    # Document cache stats
    doc_total = await mongodb_service.db["document_cache"].count_documents({})
    doc_expired = await mongodb_service.db["document_cache"].count_documents({
        "expires_at": {"$lt": mongodb_service.get_current_time()}
    })
    
    return {
        "llm_cache": {
            "total_entries": total_entries,
            "active_entries": total_entries - expired_entries,
            "expired_entries": expired_entries
        },
        "document_cache": {
            "total_entries": doc_total,
            "active_entries": doc_total - doc_expired,
            "expired_entries": doc_expired
        }
    }