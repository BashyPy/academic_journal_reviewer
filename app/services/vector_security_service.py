"""Vector store security service for user isolation and content validation."""

import re
from typing import Any, Dict

from app.utils.logger import get_logger

logger = get_logger(__name__)


class VectorSecurityService:
    """Manages security for vector store operations."""

    def __init__(self):
        # PII patterns to detect
        pii_patterns_raw = {
            "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
            "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
            "credit_card": r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
        }
        self.pii_patterns = {}
        for pii_type, pattern in pii_patterns_raw.items():
            try:
                self.pii_patterns[pii_type] = re.compile(pattern)
            except re.error as e:
                logger.error(f"Failed to compile PII pattern '{pii_type}': {e}")

    def validate_content(self, content: str) -> Dict[str, Any]:
        """Validate content before embedding."""
        issues = []

        # Check for PII
        for pii_type, pattern in self.pii_patterns.items():
            matches = re.findall(pattern, content)
            if matches:
                issues.append(
                    {
                        "type": "pii_detected",
                        "category": pii_type,
                        "count": len(matches),
                    }
                )

        # Check content length
        if len(content) > 100000:
            issues.append({"type": "content_too_long", "length": len(content)})

        # Check for malicious patterns
        malicious_patterns = ["<script", "javascript:", "eval(", "exec("]
        content_lower = content.lower()
        for pattern in malicious_patterns:
            if pattern in content_lower:
                issues.append({"type": "malicious_pattern", "pattern": pattern})

        has_issues = len(issues) > 0
        return {
            "valid": not has_issues,
            "issues": issues,
            "sanitized": has_issues,
        }

    def sanitize_content(self, content: str) -> str:
        """Sanitize content by removing PII."""
        sanitized = content

        # Replace PII with placeholders
        for pii_type, pattern in self.pii_patterns.items():
            sanitized = re.sub(pattern, f"[{pii_type.upper()}_REDACTED]", sanitized)

        return sanitized

    def add_user_isolation(self, metadata: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Add user isolation metadata, ensuring inputs are valid."""
        if not isinstance(metadata, dict):
            logger.error("Invalid metadata provided. Must be a dictionary.")
            raise TypeError("Metadata must be a dictionary.")
        if not user_id or not isinstance(user_id, str):
            logger.error("Invalid user_id provided. Must be a non-empty string.")
            raise ValueError("user_id must be a non-empty string.")

        new_metadata = metadata.copy()
        new_metadata["user_id"] = user_id
        new_metadata["isolated"] = True
        return new_metadata

    def check_access(self, metadata: Dict[str, Any], user_id: str, user_role: str) -> bool:
        """Check if user can access this embedding."""
        try:
            # Super admin and admin can access all
            if user_role in ["super_admin", "admin"]:
                return True

            # Check user isolation
            if metadata.get("isolated"):
                return metadata.get("user_id") == user_id

            # Public embeddings accessible to all
            return True
        except AttributeError:
            logger.warning("Invalid metadata object provided to check_access.")
            return False

    def get_security_stats(self) -> Dict[str, Any]:
        """Get security statistics."""
        # This would be enhanced with actual tracking
        return {
            "pii_detections": 0,
            "sanitizations": 0,
            "access_denials": 0,
            "malicious_content_blocked": 0,
        }


vector_security_service = VectorSecurityService()
