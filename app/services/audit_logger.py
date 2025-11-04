"""Audit logging service"""

from datetime import datetime
from typing import Any, Dict, Optional

from app.services.mongodb_service import mongodb_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AuditLogger:
    """Audit logging for security events"""

    def __init__(self):
        self.collection = None

    async def initialize(self):
        """Initialize audit collection"""
        if self.collection is None:
            db = await mongodb_service.get_database()
            self.collection = db["audit_logs"]
            await self.collection.create_index("timestamp")
            await self.collection.create_index("event_type")
            await self.collection.create_index("user_id")
            await self.collection.create_index("ip_address")

    async def log_event(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        severity: str = "info",
    ):
        """Log audit event"""
        await self.initialize()

        event = {
            "timestamp": datetime.now(),
            "event_type": event_type,
            "user_id": user_id,
            "ip_address": ip_address,
            "details": details or {},
            "severity": severity,
        }

        try:
            await self.collection.insert_one(event)
            logger.info(f"Audit log: {event_type}", additional_info=event)
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    async def log_auth_attempt(self, success: bool, ip_address: str, user_id: Optional[str] = None):
        """Log authentication attempt"""
        await self.log_event(
            event_type="auth_attempt",
            user_id=user_id,
            ip_address=ip_address,
            details={"success": success},
            severity="warning" if not success else "info",
        )

    async def log_api_key_created(self, name: str, created_by: str):
        """Log API key creation"""
        await self.log_event(
            event_type="api_key_created",
            user_id=created_by,
            details={"key_name": name},
            severity="info",
        )

    async def log_api_key_revoked(self, name: str, revoked_by: str):
        """Log API key revocation"""
        await self.log_event(
            event_type="api_key_revoked",
            user_id=revoked_by,
            details={"key_name": name},
            severity="warning",
        )

    async def log_submission(self, submission_id: str, user_id: str, ip_address: str):
        """Log manuscript submission"""
        await self.log_event(
            event_type="submission_created",
            user_id=user_id,
            ip_address=ip_address,
            details={"submission_id": submission_id},
            severity="info",
        )

    async def log_security_event(self, event_type: str, ip_address: str, details: Dict[str, Any]):
        """Log security event"""
        await self.log_event(
            event_type=event_type,
            ip_address=ip_address,
            details=details,
            severity="critical",
        )


audit_logger = AuditLogger()
