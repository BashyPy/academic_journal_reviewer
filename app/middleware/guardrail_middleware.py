from fastapi import Request
from fastapi.responses import JSONResponse
import logging

from app.services.guardrails import guardrails


logger = logging.getLogger(__name__)


class GuardrailMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive)
            
            # Check if this is a submission endpoint
            if "/submit" in request.url.path:
                try:
                    body = await request.body()
                    if body:
                        # Parse and validate submission
                        import json
                        data = json.loads(body)
                        violations = guardrails.validate_submission(data)
                        
                        # Block critical violations
                        critical_violations = [v for v in violations if v.severity == "critical"]
                        if critical_violations:
                            response = JSONResponse(
                                status_code=400,
                                content={
                                    "error": "Submission blocked due to policy violations",
                                    "violations": [v.message for v in critical_violations]
                                }
                            )
                            await response(scope, receive, send)
                            return
                        
                        # Log warnings
                        warning_violations = [v for v in violations if v.severity in ["high", "medium"]]
                        if warning_violations:
                            logger.warning(f"Submission warnings: {[v.message for v in warning_violations]}")
                
                except Exception as e:
                    logger.error(f"Guardrail validation error: {e}")
        
        await self.app(scope, receive, send)


def apply_review_guardrails(review_content: str) -> str:
    """Apply guardrails to review output before returning to user"""
    violations = guardrails.validate_review_output(review_content)
    
    # Log any violations
    if violations:
        logger.info(f"Review guardrail violations: {[v.message for v in violations]}")
    
    # Sanitize content if needed
    sanitized_content = guardrails.sanitize_content(review_content, violations)
    
    return sanitized_content