"""Vector store validation service for RAG functionality."""

from typing import Any, Dict

from pymongo.errors import ConnectionFailure, OperationFailure

from app.services.mongodb_service import mongodb_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


class VectorStoreValidator:
    """Validates vector store setup and health."""

    def __init__(self):
        """Initialize the VectorStoreValidator."""
        self.is_available = False
        self.error_message = None

    async def validate_vector_store(self) -> Dict[str, Any]:
        """Validate vector store configuration and availability."""
        try:
            # Check if document_embeddings collection exists
            collections = await mongodb_service.db.list_collection_names()

            if "document_embeddings" not in collections:
                self.is_available = False
                self.error_message = "document_embeddings collection not found"
                logger.warning("Vector store not available: collection missing")
                return {"available": False, "error": self.error_message, "rag_enabled": False}

            # Check if collection has vector index (Atlas only)
            collection = mongodb_service.db["document_embeddings"]

            # Use list_search_indexes for Atlas Search indexes (not regular indexes)
            search_indexes = await collection.list_search_indexes().to_list(length=100)
            has_vector_index = any(idx.get("name") == "vector_index" for idx in search_indexes)

            if not has_vector_index:
                self.is_available = False
                self.error_message = "vector_index not found (Atlas Vector Search required)"
                logger.warning(
                    "Vector store not fully configured: vector_index missing. "
                    "Create via Atlas UI: Index name='vector_index', "
                    "Field='embedding', Dimensions=1536, Similarity='cosine'"
                )
                return {
                    "available": False,
                    "error": self.error_message,
                    "rag_enabled": False,
                    "note": "Create vector index in MongoDB Atlas",
                }

            self.is_available = True
            self.error_message = None
            logger.info("✅ Vector store validated successfully")

            return {
                "available": True,
                "index": "vector_index",
            }

        except (ConnectionFailure, OperationFailure) as e:
            self.is_available = False
            self.error_message = f"MongoDB connection/operation error: {e}"
            logger.error(
                f"MongoDB error during vector store validation: {e}",
                additional_info={
                    "component": "vector_store_validator",
                    "function": "validate_vector_store",
                },
            )
            return {"available": False, "error": self.error_message, "rag_enabled": False}
        except Exception as e:
            self.is_available = False
            self.error_message = f"An unexpected error occurred: {e}"
            logger.error(
                f"Unexpected error in vector store validation: {e}",
                exc_info=True,
                additional_info={
                    "function": "validate_vector_store",
                },
            )
            return {"available": False, "error": self.error_message, "rag_enabled": False}


vector_store_validator = VectorStoreValidator()
