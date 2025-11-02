from typing import Any, Dict, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings
from app.utils.logger import get_logger


class MongoDBService:
    def __init__(self):
        # Enable TLS/SSL for MongoDB connection
        connection_params = (
            {
                "tls": True,
                "tlsAllowInvalidCertificates": False,
            }
            if settings.MONGODB_URL.startswith("mongodb+srv://")
            else {}
        )

        self.client = AsyncIOMotorClient(settings.MONGODB_URL, **connection_params)
        self.db = self.client[settings.MONGODB_DATABASE]
        self.submissions = self.db.submissions
        self.logger = get_logger()

    async def get_database(self):
        """Get database instance"""
        return self.db

    async def save_submission(self, submission_data: Dict[str, Any]) -> str:
        try:
            result = await self.submissions.insert_one(submission_data)
            submission_id = str(result.inserted_id)
            self.logger.debug(
                f"Submission saved: {submission_id}",
                additional_info={
                    "submission_id": submission_id,
                    "title": submission_data.get("title", "unknown"),
                },
            )
            return submission_id
        except Exception as e:
            self.logger.exception(
                e,
                "Error saving submission",
                additional_info={"operation": "save_submission"},
            )
            raise

    async def get_submission(self, submission_id: str) -> Optional[Dict[str, Any]]:
        try:
            if not submission_id or not isinstance(submission_id, str):
                raise ValueError(f"Invalid submission_id: {submission_id}")

            try:
                oid = ObjectId(submission_id)
            except Exception as e:
                # Invalid ObjectId format, surface a clear error and keep original cause
                self.logger.warning(
                    f"Invalid ObjectId for submission_id: {submission_id}"
                )
                raise ValueError(f"Invalid submission_id: {submission_id}") from e

            doc = await self.submissions.find_one({"_id": oid})
            return doc
        except Exception as e:
            self.logger.exception(
                e,
                "Error retrieving submission",
                additional_info={
                    "operation": "get_submission",
                    "submission_id": submission_id,
                },
            )
            raise

    async def update_submission(self, submission_id: str, data: Dict[str, Any]):
        try:
            if not submission_id or not isinstance(submission_id, str):
                raise ValueError(f"Invalid submission_id: {submission_id}")

            if not data or not isinstance(data, dict):
                raise ValueError("Invalid update data")

            try:
                oid = ObjectId(submission_id)
            except Exception as e:
                # Invalid ObjectId format, surface a clear error and keep original cause
                self.logger.warning(
                    f"Invalid ObjectId for submission_id: {submission_id}"
                )
                raise ValueError(f"Invalid submission_id: {submission_id}") from e

            result = await self.submissions.update_one({"_id": oid}, {"$set": data})

            if result.matched_count == 0:
                self.logger.warning(f"Submission not found: {submission_id}")
            else:
                # provide useful debug info about the update outcome
                self.logger.debug(
                    f"Submission updated: {submission_id}",
                    additional_info={
                        "submission_id": submission_id,
                        "matched_count": result.matched_count,
                        "modified_count": getattr(result, "modified_count", None),
                    },
                )
        except Exception as e:
            # log the exception object consistently and include contextual information, then re-raise
            self.logger.exception(
                e,
                "Error updating submission",
                additional_info={
                    "operation": "update_submission",
                    "submission_id": submission_id,
                    "data_keys": list(data.keys()) if isinstance(data, dict) else None,
                },
            )
            raise


mongodb_service = MongoDBService()
