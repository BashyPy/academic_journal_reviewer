import asyncio
from datetime import datetime
from typing import Any, Dict, List

from app.agents.specialist_agents import (
    ClarityAgent,
    EthicsAgent,
    LiteratureAgent,
    MethodologyAgent,
)
from app.agents.synthesis_agent import SynthesisAgent
from app.models.schemas import AgentType, TaskStatus
from app.services.mongodb_service import mongodb_service


class OrchestratorAgent:
    def __init__(self):
        self.specialist_agents = {
            AgentType.METHODOLOGY: MethodologyAgent(),
            AgentType.LITERATURE: LiteratureAgent(),
            AgentType.CLARITY: ClarityAgent(),
            AgentType.ETHICS: EthicsAgent(),
        }
        self.synthesis_agent = SynthesisAgent()

    async def process_submission(self, submission_id: str) -> Dict[str, Any]:
        submission = await mongodb_service.get_submission(submission_id)
        if not submission:
            raise ValueError(f"Submission {submission_id} not found")

        tasks = await self.create_agent_tasks(submission_id, submission)
        await self.execute_specialist_agents(tasks)
        await self.wait_for_completion(submission_id)

        final_report = await self.execute_synthesis(submission_id)

        await mongodb_service.update_submission(
            submission_id,
            {
                "final_report": final_report,
                "status": TaskStatus.COMPLETED.value,
                "completed_at": datetime.now(),
            },
        )

        return {"status": "completed", "submission_id": submission_id}

    async def create_agent_tasks(
        self, submission_id: str, submission: Dict[str, Any]
    ) -> List[str]:
        tasks = []
        context = {
            "content": submission["content"],
            "title": submission["title"],
            "metadata": submission["file_metadata"],
        }

        for agent_type in self.specialist_agents.keys():
            task_data = {
                "agent_type": agent_type.value,
                "submission_id": submission_id,
                "status": TaskStatus.PENDING.value,
                "context": context,
                "created_at": datetime.now(),
            }
            task_id = await mongodb_service.save_agent_task(task_data)
            tasks.append(task_id)

        return tasks

    async def execute_specialist_agents(self, task_ids: List[str]):
        async def execute_task(task_id: str):
            task_doc = await mongodb_service.agent_tasks.find_one({"_id": task_id})
            task_data = task_doc

            agent_type = AgentType(task_data["agent_type"])
            agent = self.specialist_agents[agent_type]

            await mongodb_service.update_agent_task(
                task_id, {"status": TaskStatus.RUNNING.value}
            )

            try:
                critique = await agent.execute_task(task_data["context"])

                await mongodb_service.update_agent_task(
                    task_id,
                    {
                        "status": TaskStatus.COMPLETED.value,
                        "result": critique.dict(),
                        "completed_at": datetime.now(),
                    },
                )
            except Exception as e:
                await mongodb_service.update_agent_task(
                    task_id,
                    {
                        "status": TaskStatus.FAILED.value,
                        "error": str(e),
                        "completed_at": datetime.now(),
                    },
                )

        await asyncio.gather(*[execute_task(task_id) for task_id in task_ids])

    async def wait_for_completion(self, submission_id: str):
        timeout = 300
        try:
            with asyncio.timeout(timeout):
                while True:
                    tasks = await mongodb_service.get_agent_tasks(submission_id)
                    if all(
                        task["status"]
                        in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value]
                        for task in tasks
                    ):
                        return
                    await asyncio.sleep(5)
        except TimeoutError:
            raise TimeoutError("Agent tasks did not complete within timeout")

    async def execute_synthesis(self, submission_id: str) -> str:
        tasks = await mongodb_service.get_agent_tasks(submission_id)
        critiques = [
            task["result"]
            for task in tasks
            if task["status"] == TaskStatus.COMPLETED.value
        ]

        submission = await mongodb_service.get_submission(submission_id)

        context = {"submission": submission, "critiques": critiques}

        return await self.synthesis_agent.generate_final_report(context)


orchestrator = OrchestratorAgent()
