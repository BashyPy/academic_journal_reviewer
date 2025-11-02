"""Authentication routes"""

from fastapi import APIRouter, Depends, HTTPException

from app.middleware.auth import get_api_key
from app.models.auth_schemas import (
    AuthResponse,
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    UpdatePasswordRequest,
    VerifyEmailRequest,
)
from app.models.profile_schemas import (
    ProfileResponse,
    ProfileStats,
    UpdateProfileRequest,
)
from app.services.audit_logger import audit_logger
from app.services.email_service import email_service
from app.services.otp_service import otp_service
from app.services.user_service import user_service
from app.utils.logger import get_logger

router = APIRouter(prefix="/auth", tags=["authentication"])
logger = get_logger(__name__)

OTP_SENT_MESSAGE = "If email exists, OTP has been sent"
USER_NOT_FOUND = "User not found"


@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest):
    """Register new user account"""
    try:
        user = await user_service.create_user(
            email=request.email, password=request.password, name=request.name
        )

        otp = await otp_service.create_otp(request.email, "email_verification")
        email_service.send_otp(request.email, otp, "email verification")

        await audit_logger.log_event(
            event_type="user_registered",
            user_id=request.email,
            details={"name": request.name},
        )

        return AuthResponse(
            message="Registration successful. Please verify your email.",
            user={"email": user["email"], "name": user["name"]},
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")


@router.post("/verify-email", response_model=AuthResponse)
async def verify_email(request: VerifyEmailRequest):
    """Verify email with OTP"""
    if not await otp_service.verify_otp(
        request.email, request.otp, "email_verification"
    ):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    if not await user_service.verify_email(request.email):
        raise HTTPException(status_code=404, detail=USER_NOT_FOUND)

    email_service.send_welcome(request.email, request.email)

    await audit_logger.log_event(event_type="email_verified", user_id=request.email)

    return AuthResponse(message="Email verified successfully")


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """Login user"""
    user = await user_service.authenticate(request.email, request.password)
    if not user:
        await audit_logger.log_auth_attempt(False, "unknown", request.email)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.get("email_verified", False):
        raise HTTPException(status_code=403, detail="Email not verified")

    await audit_logger.log_auth_attempt(True, "unknown", request.email)

    return AuthResponse(
        message="Login successful",
        api_key=user["api_key"],
        user={"email": user["email"], "name": user["name"], "role": user["role"]},
    )


@router.post("/forgot-password", response_model=AuthResponse)
async def forgot_password(request: ForgotPasswordRequest):
    """Request password reset OTP"""
    user = await user_service.get_user_by_email(request.email)
    if not user:
        return AuthResponse(message=OTP_SENT_MESSAGE)

    otp = await otp_service.create_otp(request.email, "password_reset")
    email_service.send_otp(request.email, otp, "password reset")

    await audit_logger.log_event(
        event_type="password_reset_requested", user_id=request.email
    )

    return AuthResponse(message=OTP_SENT_MESSAGE)


@router.post("/reset-password", response_model=AuthResponse)
async def reset_password(request: ResetPasswordRequest):
    """Reset password with OTP"""
    if not await otp_service.verify_otp(request.email, request.otp, "password_reset"):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    if not await user_service.update_password(request.email, request.new_password):
        raise HTTPException(status_code=404, detail=USER_NOT_FOUND)

    await audit_logger.log_event(event_type="password_reset", user_id=request.email)

    return AuthResponse(message="Password reset successful")


@router.post("/update-password", response_model=AuthResponse)
async def update_password(
    request: UpdatePasswordRequest, user: dict = Depends(get_api_key)
):
    """Update password (requires authentication)"""
    current_user = await user_service.authenticate(
        user["email"], request.current_password
    )
    if not current_user:
        raise HTTPException(status_code=401, detail="Invalid current password")

    await user_service.update_password(user["email"], request.new_password)

    await audit_logger.log_event(event_type="password_updated", user_id=user["email"])

    return AuthResponse(message="Password updated successfully")


@router.put("/profile", response_model=AuthResponse)
async def update_profile(
    request: UpdateProfileRequest, user: dict = Depends(get_api_key)
):
    """Update user profile"""
    profile_data = request.model_dump(exclude_unset=True)
    if not profile_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    if not await user_service.update_profile(user["email"], profile_data):
        raise HTTPException(status_code=404, detail=USER_NOT_FOUND)

    await audit_logger.log_event(
        event_type="profile_updated", user_id=user["email"], details=profile_data
    )

    return AuthResponse(message="Profile updated successfully")


@router.get("/profile", response_model=ProfileResponse)
async def get_profile(user: dict = Depends(get_api_key)):
    """Get user profile"""
    return ProfileResponse(
        email=user["email"],
        name=user["name"],
        role=user["role"],
        bio=user.get("bio"),
        organization=user.get("organization"),
        position=user.get("position"),
        phone=user.get("phone"),
        website=user.get("website"),
        location=user.get("location"),
        avatar_url=user.get("avatar_url"),
        email_verified=user.get("email_verified", False),
        active=user.get("active", True),
        created_at=user.get("created_at"),
        updated_at=user.get("updated_at"),
    )


@router.delete("/account", response_model=AuthResponse)
async def delete_account(user: dict = Depends(get_api_key)):
    if not await user_service.delete_user(user["email"]):
        raise HTTPException(status_code=404, detail=USER_NOT_FOUND)

    await audit_logger.log_event(
        event_type="account_deleted", user_id=user["email"], severity="warning"
    )

    return AuthResponse(message="Account deleted successfully")


@router.post("/resend-verification")
async def resend_verification(request: ForgotPasswordRequest):
    """Resend email verification OTP"""
    user = await user_service.get_user_by_email(request.email)
    if not user:
        return AuthResponse(message=OTP_SENT_MESSAGE)

    if user.get("email_verified", False):
        raise HTTPException(status_code=400, detail="Email already verified")

    otp = await otp_service.create_otp(request.email, "email_verification")
    email_service.send_otp(request.email, otp, "email verification")

    return AuthResponse(message="Verification OTP sent")


@router.get("/profile/stats", response_model=ProfileStats)
async def get_profile_stats(user: dict = Depends(get_api_key)):
    """Get user profile statistics"""
    from datetime import datetime, timezone

    db = await mongodb_service.get_database()
    submissions = db["submissions"]

    total = await submissions.count_documents({"user_email": user["email"]})
    completed = await submissions.count_documents(
        {"user_email": user["email"], "status": "completed"}
    )
    pending = await submissions.count_documents(
        {"user_email": user["email"], "status": {"$in": ["pending", "running"]}}
    )

    created_at = user.get("created_at")
    if created_at:
        if not created_at.tzinfo:
            created_at = created_at.replace(tzinfo=timezone.utc)
        age_days = (datetime.now(timezone.utc) - created_at).days
    else:
        age_days = 0

    return ProfileStats(
        total_submissions=total,
        completed_reviews=completed,
        pending_reviews=pending,
        account_age_days=age_days,
    )
