from typing import Any, Dict, List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings


class MongoDBService:
    def __init__(self):
        self.client = AsyncIOMotorClient(settings.MONGODB_URL)
        self.db = self.client[settings.MONGODB_DATABASE]
        self.submissions = self.db.submissions
        self.agent_tasks = self.db.agent_tasks

    async def save_submission(self, submission_data: Dict[str, Any]) -> str:
        result = await self.submissions.insert_one(submission_data)
        return str(result.inserted_id)

    async def get_submission(self, submission_id: str) -> Optional[Dict[str, Any]]:
        doc = await self.submissions.find_one({"_id": ObjectId(submission_id)})
        if doc:
            doc["id"] = str(doc["_id"])
            del doc["_id"]
        return doc

    async def update_submission(self, submission_id: str, data: Dict[str, Any]):
        await self.submissions.update_one(
            {"_id": ObjectId(submission_id)}, {"$set": data}
        )

    async def save_agent_task(self, task_data: Dict[str, Any]) -> str:
        result = await self.agent_tasks.insert_one(task_data)
        return str(result.inserted_id)

    async def update_agent_task(self, task_id: str, data: Dict[str, Any]):
        await self.agent_tasks.update_one({"_id": ObjectId(task_id)}, {"$set": data})

    async def get_agent_tasks(self, submission_id: str) -> List[Dict[str, Any]]:
        cursor = self.agent_tasks.find({"submission_id": submission_id})
        tasks = []
        async for doc in cursor:
            doc["id"] = str(doc["_id"])
            del doc["_id"]
            tasks.append(doc)
        return tasks


mongodb_service = MongoDBService()
