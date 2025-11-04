"""Admin routes for API key management"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.middleware.auth import auth_service, require_admin
from app.services.audit_logger import audit_logger
from app.services.security_monitor import security_monitor

router = APIRouter(prefix="/admin", tags=["admin"])


class CreateAPIKeyRequest(BaseModel):
    name: str
    role: str = "user"
    expires_days: int = 365


class RevokeAPIKeyRequest(BaseModel):
    api_key: str


@router.post("/api-keys")
async def create_api_key(request: CreateAPIKeyRequest, admin: dict = Depends(require_admin)):
    """Create new API key (admin only)"""
    result = await auth_service.create_api_key(
        name=request.name, role=request.role, expires_days=request.expires_days
    )
    await audit_logger.log_api_key_created(request.name, admin.get("name", "unknown"))
    return result


@router.delete("/api-keys")
async def revoke_api_key(request: RevokeAPIKeyRequest, admin: dict = Depends(require_admin)):
    """Revoke API key (admin only)"""
    success = await auth_service.revoke_api_key(request.api_key)
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")
    await audit_logger.log_api_key_revoked(request.api_key, admin.get("name", "unknown"))
    return {"message": "API key revoked"}


@router.get("/security/stats")
async def get_security_stats(admin: dict = Depends(require_admin)):
    """Get security statistics (admin only)"""
    return security_monitor.get_stats()
