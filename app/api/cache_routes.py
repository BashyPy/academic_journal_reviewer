import asyncio

from fastapi import APIRouter

from app.services.cache_service import cache_service

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

    # Reuse current time and run DB calls concurrently to avoid sequential waits
    now = mongodb_service.get_current_time()
    llm_col = mongodb_service.db["llm_cache"]
    doc_col = mongodb_service.db["document_cache"]

    # Use estimated_document_count for fast total estimates and count_documents for expired counts.
    tasks = [
        llm_col.estimated_document_count(),
        llm_col.count_documents({"expires_at": {"$lt": now}}),
        doc_col.estimated_document_count(),
        doc_col.count_documents({"expires_at": {"$lt": now}}),
    ]

    total_entries, expired_entries, doc_total, doc_expired = await asyncio.gather(*tasks)

    return {
        "llm_cache": {
            "total_entries": total_entries,
            "active_entries": total_entries - expired_entries,
            "expired_entries": expired_entries,
        },
        "document_cache": {
            "total_entries": doc_total,
            "active_entries": doc_total - doc_expired,
            "expired_entries": doc_expired,
        },
    }
