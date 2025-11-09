"""Persistent memory checkpointing service for LangGraph workflow recovery."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pymongo.errors import PyMongoError

from app.services.mongodb_service import mongodb_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CheckpointService:
    """Manages workflow checkpoints in MongoDB."""

    def __init__(self):
        if mongodb_service.db is None:
            raise RuntimeError("MongoDB connection not initialized")
        self.collection = mongodb_service.db["workflow_checkpoints"]

    async def save_checkpoint(self, submission_id: str, state: Dict[str, Any], stage: str) -> bool:
        """Save workflow checkpoint to MongoDB."""
        try:
            checkpoint = {
                "submission_id": submission_id,
                "stage": stage,
                "state": state,
                "created_at": datetime.now(timezone.utc),
            }

            await self.collection.update_one(
                {"submission_id": submission_id},
                {"$set": checkpoint},
                upsert=True,
            )
            logger.info(f"Checkpoint saved: {submission_id} at {stage}")
            return True

        except PyMongoError as e:
            logger.error(
                "Failed to save checkpoint",
                additional_info={
                    "component": "checkpoint_service",
                    "function": "save_checkpoint",
                    "submission_id": submission_id,
                    "error": str(e),
                },
            )
            return False

    async def load_checkpoint(self, submission_id: str) -> Optional[Dict[str, Any]]:
        """Load workflow checkpoint from MongoDB."""
        try:
            checkpoint = await self.collection.find_one({"submission_id": submission_id})
            if checkpoint:
                return checkpoint.get("state")
            return None

        except PyMongoError as e:
            logger.error(
                "Failed to load checkpoint",
                additional_info={
                    "component": "checkpoint_service",
                    "function": "load_checkpoint",
                    "submission_id": submission_id,
                    "error": str(e),
                },
            )
            return None

    async def delete_checkpoint(self, submission_id: str) -> bool:
        """Delete checkpoint after successful completion."""
        try:
            result = await self.collection.delete_one({"submission_id": submission_id})
            if result.deleted_count > 0:
                logger.info(f"Checkpoint deleted: {submission_id}")
            return True

        except PyMongoError as e:
            logger.error(
                "Failed to delete checkpoint",
                additional_info={
                    "component": "checkpoint_service",
                    "function": "delete_checkpoint",
                    "submission_id": submission_id,
                    "error": str(e),
                },
            )
            return False


checkpoint_service = CheckpointService()
