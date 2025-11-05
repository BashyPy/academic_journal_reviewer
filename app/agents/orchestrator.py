from datetime import datetime
from typing import Any, Dict
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.middleware.rate_limiter import rate_limiter
from app.models.schemas import TaskStatus
from app.services.document_cache_service import document_cache_service
from app.services.langgraph_workflow import langgraph_workflow
from app.services.mongodb_service import mongodb_service
from app.utils.logger import get_logger


class OrchestratorAgent:  # pylint: disable=too-few-public-methods
    def __init__(self):
        self.logger = get_logger()

    async def process_submission(
        self, submission_id: str, client_ip: str = "unknown", timezone_str: str = "UTC"
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

            # Track concurrent processing
            rate_limiter.check_concurrent_processing(client_ip, submission_id)

            # Update status to running
            await mongodb_service.update_submission(
                submission_id, {"status": TaskStatus.RUNNING.value}
            )

            # Use LangGraph workflow for processing
            workflow_result = await langgraph_workflow.execute_review(submission)

            # Extract final report and detected domain
            if isinstance(workflow_result, dict):
                final_report = workflow_result.get(
                    "final_report", workflow_result.get("report", "")
                )
                detected_domain = workflow_result.get("domain", "general")
            else:
                final_report = workflow_result
                detected_domain = "general"

            # Resolve timezone from provided string, fallback to UTC on error
            try:
                tz = ZoneInfo(timezone_str)
            except (ZoneInfoNotFoundError, KeyError):
                tz = ZoneInfo("UTC")

            completed_at = datetime.now(tz)
            await mongodb_service.update_submission(
                submission_id,
                {
                    "final_report": final_report,
                    "detected_domain": detected_domain,
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

            # Release processing slot
            rate_limiter.release_processing(client_ip, submission_id)

            self.logger.log_review_process(
                submission_id=submission_id,
                stage="orchestration_completed",
                status="success",
                additional_info={"report_length": len(final_report)},
            )

            return {"status": "completed", "submission_id": submission_id}

        except Exception as e:
            self.logger.error(
                e, additional_info={"submission_id": submission_id, "stage": "orchestration"}
            )
            # Ensure a timezone-aware fallback for the failure timestamp as well
            try:
                err_tz = ZoneInfo(timezone_str)
            except (ZoneInfoNotFoundError, KeyError):
                err_tz = ZoneInfo("UTC")

            # Release processing slot on failure
            rate_limiter.release_processing(client_ip, submission_id)

            await mongodb_service.update_submission(
                submission_id,
                {
                    "status": TaskStatus.FAILED.value,
                    "error": str(e),
                    "completed_at": datetime.now(err_tz),
                },
            )
            raise


orchestrator = OrchestratorAgent()
