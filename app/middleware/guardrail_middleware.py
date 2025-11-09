import asyncio

from fastapi import Request
from fastapi.responses import JSONResponse

from app.services.guardrails import guardrails
from app.utils.logger import get_logger

logger = get_logger(__name__)


class GuardrailMiddleware:
    def __init__(self, app):
        self.app = app

    def _is_submission_path(self, scope) -> bool:
        path = scope.get("path", "") or ""
        return "/submit" in path

    async def _process_submission_request(self, scope, receive, send):
        """
        Read the request body, validate it with guardrails and optionally send a blocking response.
        Returns a tuple (handled: bool, receive_override: callable|None).
        If handled is True a response was already sent and the middleware should return.
        If receive_override is not None it should be used as the receive callable for downstream.
        """
        try:
            request = Request(scope, receive)
            body = await request.body()
            if not body:
                return False, None

            import json

            data = json.loads(body)
            violations = guardrails.validate_submission(data)

            # Block critical violations
            critical_violations = [
                v for v in violations if getattr(v, "severity", None) == "critical"
            ]
            if critical_violations:
                response = JSONResponse(
                    status_code=400,
                    content={
                        "error": "Submission blocked due to policy violations",
                        "violations": [v.message for v in critical_violations],
                    },
                )
                await response(scope, receive, send)
                return True, None

            # Log warnings
            warning_violations = [
                v for v in violations if getattr(v, "severity", None) in ("high", "medium")
            ]
            if warning_violations:
                logger.warning(f"Submission warnings: {[v.message for v in warning_violations]}")

            # Replay the body for downstream consumers by providing a custom receive
            async def receive_with_body():
                # perform a no-op await so linters/formatters recognize this as an async function
                await asyncio.sleep(0)
                return {"type": "http.request", "body": body, "more_body": False}

            return False, receive_with_body

        except Exception as e:
            logger.error(
                e,
                {
                    "component": "guardrail_middleware",
                    "function": "_process_submission_request",
                },
            )
            return False, None

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http" and self._is_submission_path(scope):
            handled, receive_override = await self._process_submission_request(scope, receive, send)
            if handled:
                return
            if receive_override is not None:
                receive = receive_override

        await self.app(scope, receive, send)


def apply_review_guardrails(review_content: str) -> str:
    """Apply guardrails to review output before returning to user with robust error handling."""
    try:
        violations = guardrails.validate_review_output(review_content) or []

        # Ensure violations is a list-like structure
        if not isinstance(violations, list):
            try:
                violations = list(violations)
            except Exception:
                violations = [violations]

        # Log any violations safely
        if violations:
            logger.info(
                "Review guardrail violations: %s",
                [getattr(v, "message", repr(v)) for v in violations],
            )

        # Sanitize content if needed
        sanitized_content = guardrails.sanitize_content(review_content, violations)

        # If sanitization fails or returns None, fallback to original content
        if sanitized_content is None:
            logger.warning(
                "Guardrails returned None for sanitized content; returning original content."
            )
            return review_content

        return sanitized_content

    except Exception:
        logger.exception("Unexpected error applying review guardrails; returning original content.")
        return review_content
