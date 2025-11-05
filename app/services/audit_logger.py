"""Audit Logger Service"""

from datetime import datetime
from typing import Any, Dict, Optional

from app.services.mongodb_service import mongodb_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AuditLogger:
    """Service for logging audit events"""

    async def log_event(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        severity: str = "info",
    ):
        """Log an audit event"""
        try:
            db = await mongodb_service.get_database()

            audit_entry = {
                "event_type": event_type,
                "user_id": user_id,
                "user_email": user_email,
                "ip_address": ip_address,
                "details": details or {},
                "severity": severity,
                "timestamp": datetime.now(),
            }

            await db.audit_logs.insert_one(audit_entry)
            logger.info(f"Audit event logged: {event_type}")

        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")

    async def log_auth_attempt(
        self,
        success: bool,
        ip_address: Optional[str] = None,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
    ):
        """Log authentication attempt"""
        await self.log_event(
            event_type="login_success" if success else "login_failed",
            user_id=user_id,
            user_email=user_email,
            ip_address=ip_address,
            severity="info" if success else "warning",
        )


audit_logger = AuditLogger()
