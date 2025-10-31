from datetime import datetime
from typing import Any, Dict
from zoneinfo import ZoneInfo

from app.models.schemas import TaskStatus
from app.services.document_cache_service import document_cache_service
from app.services.langgraph_workflow import langgraph_workflow
from app.services.mongodb_service import mongodb_service
from app.utils.logger import get_logger


class OrchestratorAgent:
    def __init__(self):
        self.logger = get_logger()

    async def process_submission(
        self, submission_id: str, timezone_str: str = "UTC"
    ) -> Dict[str, Any]:
        self.logger.log_review_process(
            submission_id=submission_id,
            stage="orchestration_started",
            status="processing",
        )

        try:
            submission = await mongodb_service.get_submission(submission_id)
            if not submission:
                raise ValueError(f"Submission {submission_id} not found")

            # Update status to running
            await mongodb_service.update_submission(
                submission_id, {"status": TaskStatus.RUNNING.value}
            )

            # Use LangGraph workflow for processing
            final_report = await langgraph_workflow.execute_review(submission)

            # Resolve timezone from provided string, fallback to UTC on error
            try:
                tz = ZoneInfo(timezone_str)
            except Exception:
                tz = ZoneInfo("UTC")

            completed_at = datetime.now(tz)
            await mongodb_service.update_submission(
                submission_id,
                {
                    "final_report": final_report,
                    "status": TaskStatus.COMPLETED.value,
                    "completed_at": completed_at,
                },
            )

            # Update document cache with completed results
            await document_cache_service.cache_submission(
                submission["content"],
                {
                    "_id": submission_id,
                    "title": submission["title"],
                    "status": TaskStatus.COMPLETED.value,
                    "final_report": final_report,
                    "completed_at": completed_at,
                },
                ttl_hours=168,  # Cache completed reviews for 7 days
            )

            self.logger.log_review_process(
                submission_id=submission_id,
                stage="orchestration_completed",
                status="success",
                additional_info={"report_length": len(final_report)},
            )

            return {"status": "completed", "submission_id": submission_id}

        except Exception as e:
            self.logger.error(
                e,
                additional_info={
                    "submission_id": submission_id,
                    "stage": "orchestration",
                },
            )
            # Ensure a timezone-aware fallback for the failure timestamp as well
            try:
                err_tz = ZoneInfo(timezone_str)
            except Exception:
                err_tz = ZoneInfo("UTC")

            await mongodb_service.update_submission(
                submission_id,
                {
                    "status": TaskStatus.FAILED.value,
                    "error": str(e),
                    "completed_at": datetime.now(err_tz),
                },
            )
            raise
            raise


orchestrator = OrchestratorAgent()
