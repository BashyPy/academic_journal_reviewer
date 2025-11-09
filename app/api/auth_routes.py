"""Authentication routes"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from app.middleware.auth import get_api_key
from app.middleware.jwt_auth import create_access_token
from app.models.auth_schemas import (
    AuthResponse,
    ForgotPasswordRequest,
    LoginRequest,
    PasskeyAuthenticationRequest,
    PasskeyRegistrationRequest,
    RegisterRequest,
    ResetPasswordRequest,
    UpdatePasswordRequest,
    VerifyEmailRequest,
)
from app.models.profile_schemas import ProfileResponse, ProfileStats, UpdateProfileRequest
from app.services.audit_logger import audit_logger
from app.services.email_service import email_service
from app.services.mongodb_service import mongodb_service
from app.services.otp_service import otp_service
from app.services.totp_service import totp_service
from app.services.user_service import user_service
from app.services.webauthn_service import webauthn_service
from app.utils.common_operations import create_user_common
from app.utils.logger import get_logger
from app.utils.request_utils import get_client_ip

router = APIRouter(prefix="/auth", tags=["authentication"])
logger = get_logger(__name__)


OTP_SENT_MESSAGE = "If email exists, OTP has been sent"
USER_NOT_FOUND = "User not found"
INVALID_OR_EXPIRED_OTP = "Invalid or expired OTP"
PWD_RESET_EVENT = "password_reset"
INVALID_CODE = "Invalid code"
INTERNAL_SERVER_ERROR = "An internal server error occurred."


@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest, req: Request):
    """Register new user account"""
    try:
        user = await create_user_common(
            email=request.email,
            password=request.password,
            name=request.name,
            username=request.username,
        )

        otp = await otp_service.create_otp(request.email, "email_verification")
        # TODO(email): Uncomment when email is configured
        # email_service.send_otp(request.email, otp, "email verification")
        logger.info(f"OTP for {request.email}: {otp}")  # Temporary: Log OTP for testing

        await audit_logger.log_event(
            event_type="user_registered",
            user_id=str(user["_id"]),
            user_email=user["email"],
            ip_address=get_client_ip(req),
            details={"name": request.name},
        )

        return AuthResponse(
            message="Registration successful. Please verify your email.",
            user={"email": user["email"], "name": user["name"]},
        )
    except HTTPException as e:
        # Re-raise HTTPException to be handled by FastAPI
        raise e
    except Exception as e:
        logger.error(f"An unexpected error occurred during registration: {e}")
        await audit_logger.log_event(
            event_type="registration_failed",
            ip_address=get_client_ip(req),
            details={"error": str(e)},
        )
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR)


@router.post("/verify-email", response_model=AuthResponse)
@router.post("/verify-email", response_model=AuthResponse)
async def verify_email(request: VerifyEmailRequest, req: Request):
    """Verify email with OTP"""
    is_valid = await otp_service.verify_otp(request.email, request.otp, "email_verification")
    if not is_valid:
        await audit_logger.log_event(
            event_type="email_verification_failed",
            user_email=request.email,
            ip_address=get_client_ip(req),
            details={"reason": "Invalid OTP"},
        )
        raise HTTPException(status_code=400, detail=INVALID_OR_EXPIRED_OTP)
    user = await user_service.verify_email(request.email)
    if not user:
        await audit_logger.log_event(
            event_type="email_verification_failed",
            user_email=request.email,
            ip_address=get_client_ip(req),
            details={"reason": "User not found during verification"},
        )
        raise HTTPException(status_code=404, detail=USER_NOT_FOUND)

    # TODO(email): Uncomment when email is configured
    # email_service.send_welcome(request.email, request.email)

    await audit_logger.log_event(
        event_type="email_verified",
        user_id=str(user["_id"]),
        user_email=user["email"],
        ip_address=get_client_ip(req),
    )

    return AuthResponse(message="Email verified successfully")


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest, req: Request):
    """Login user with email or username"""
    try:
        user = await user_service.authenticate(request.email_or_username, request.password)
        if not user:
            await audit_logger.log_auth_attempt(False, get_client_ip(req), None, None)
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if not user.get("email_verified", False):
            raise HTTPException(status_code=403, detail="Email not verified")

        await audit_logger.log_auth_attempt(
            True, get_client_ip(req), str(user["_id"]), user["email"]
        )

        # Generate JWT token
        access_token = create_access_token(user)

        return AuthResponse(
            message="Login successful",
            access_token=access_token,
            api_key=user["api_key"],
            user={"email": user["email"], "name": user["name"], "role": user["role"]},
        )
    except Exception as e:
        await audit_logger.log_auth_attempt(
            False, get_client_ip(req), None, request.email_or_username, error=str(e)
        )
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR)


@router.post("/forgot-password", response_model=AuthResponse)
@router.post("/forgot-password", response_model=AuthResponse)
async def forgot_password(request: ForgotPasswordRequest, req: Request):
    """Request password reset OTP"""
    user = await user_service.get_user_by_email(request.email)
    if not user:
        await audit_logger.log_event(
            event_type="password_reset_requested_user_not_found",
            user_email=request.email,
            ip_address=get_client_ip(req),
        )
        return AuthResponse(message=OTP_SENT_MESSAGE)

    otp = await otp_service.create_otp(request.email, PWD_RESET_EVENT)
    # TODO(email): Uncomment when email is configured
    # email_service.send_otp(request.email, otp, "password reset")
    logger.info(f"Password reset OTP for {request.email}: {otp}")  # Temporary: Log OTP

    await audit_logger.log_event(
        event_type="password_reset_requested",
        user_id=str(user["_id"]),
        user_email=user["email"],
        ip_address=get_client_ip(req),
    )

    return AuthResponse(message=OTP_SENT_MESSAGE)


@router.post("/reset-password", response_model=AuthResponse)
async def reset_password(request: ResetPasswordRequest, req: Request):
    """Reset password with OTP"""
    if not await otp_service.verify_otp(request.email, request.otp, PWD_RESET_EVENT):
        raise HTTPException(status_code=400, detail=INVALID_OR_EXPIRED_OTP)
    if not await user_service.update_password(request.email, request.new_password):
        raise HTTPException(status_code=404, detail=USER_NOT_FOUND)

    user = await user_service.get_user_by_email(request.email)
    await audit_logger.log_event(
        event_type=PWD_RESET_EVENT,
        user_id=str(user["_id"]) if user else None,
        user_email=user["email"] if user else None,
        ip_address=get_client_ip(req),
    )

    return AuthResponse(message="Password reset successful")


@router.post("/update-password", response_model=AuthResponse)
async def update_password(
    request: UpdatePasswordRequest,
    req: Request,
    user: dict = Depends(get_api_key),
):
    """Update password (requires authentication)"""
    current_user = await user_service.authenticate(user["email"], request.current_password)
    if not current_user:
        raise HTTPException(status_code=401, detail="Invalid current password")

    if not await user_service.update_password(user["email"], request.new_password):
        raise HTTPException(status_code=404, detail=USER_NOT_FOUND)

    await audit_logger.log_event(
        event_type="password_updated",
        user_id=str(user["_id"]),
        user_email=user["email"],
        ip_address=get_client_ip(req),
    )

    return AuthResponse(message="Password updated successfully")


async def _update_and_log_profile(user: dict, profile_data: dict, ip_address: str) -> None:
    """Helper to update profile, raising exceptions on failure and logging."""
    if not await user_service.update_profile(user["email"], profile_data):
        raise HTTPException(status_code=404, detail=USER_NOT_FOUND)

    await audit_logger.log_event(
        event_type="profile_updated",
        user_id=str(user["_id"]),
        user_email=user["email"],
        ip_address=ip_address,
        details=profile_data,
    )


@router.put("/profile", response_model=AuthResponse)
async def update_profile(
    request: UpdateProfileRequest,
    req: Request,
    user: dict = Depends(get_api_key),
):
    """Update user profile"""
    profile_data = request.model_dump(exclude_unset=True)
    if not profile_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    await _update_and_log_profile(user, profile_data, get_client_ip(req))

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
        active=user.get("is_active", True),
        created_at=user.get("created_at"),
        updated_at=user.get("updated_at"),
    )


@router.delete("/account", response_model=AuthResponse)
async def delete_account(req: Request, user: dict = Depends(get_api_key)):
    if not await user_service.delete_user(user["email"]):
        raise HTTPException(status_code=404, detail=USER_NOT_FOUND)

    await audit_logger.log_event(
        event_type="account_deleted",
        user_id=str(user["_id"]),
        user_email=user["email"],
        ip_address=get_client_ip(req),
        severity="warning",
    )

    return AuthResponse(message="Account deleted successfully")


@router.post("/resend-verification")
async def resend_verification(request: ForgotPasswordRequest, req: Request):
    """Resend email verification OTP"""
    user = await user_service.get_user_by_email(request.email)
    if not user:
        await audit_logger.log_event(
            event_type="resend_verification_user_not_found",
            user_email=request.email,
            ip_address=get_client_ip(req),
        )
        return AuthResponse(message=OTP_SENT_MESSAGE)

    if user.get("email_verified", False):
        await audit_logger.log_event(
            event_type="resend_verification_already_verified",
            user_id=str(user["_id"]),
            user_email=user["email"],
            ip_address=get_client_ip(req),
        )
        raise HTTPException(status_code=400, detail="Email already verified")

    otp = await otp_service.create_otp(request.email, "email_verification")
    email_service.send_otp(request.email, otp, "email verification")
    logger.info(f"Resend OTP for {request.email}: {otp}")  # Temporary: Log OTP

    await audit_logger.log_event(
        event_type="verification_email_resent",
        user_id=str(user["_id"]),
        user_email=user["email"],
        ip_address=get_client_ip(req),
    )

    return AuthResponse(message="Verification OTP sent")


@router.get("/profile/stats", response_model=ProfileStats)
async def get_profile_stats(user: dict = Depends(get_api_key)):
    """Get user profile statistics"""
    db = await mongodb_service.get_database()
    submissions = db["submissions"]
    user_email = str(user["email"])

    total = await submissions.count_documents({"user_email": user_email})
    completed = await submissions.count_documents({"user_email": user_email, "status": "completed"})
    pending = await submissions.count_documents(
        {"user_email": user_email, "status": {"$in": ["pending", "running"]}}
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


@router.post("/2fa/enable")
async def enable_2fa(req: Request, user: dict = Depends(get_api_key)):
    """Enable 2FA for user"""
    secret = totp_service.generate_secret()
    uri = totp_service.get_totp_uri(user["email"], secret)
    qr_code = totp_service.generate_qr_code(uri)

    await user_service.update_profile(user["email"], {"totp_secret": secret, "totp_enabled": False})

    await audit_logger.log_event(
        event_type="2fa_setup_initiated",
        user_id=str(user["_id"]),
        user_email=user["email"],
        ip_address=get_client_ip(req),
    )

    return {"secret": secret, "qr_code": qr_code, "message": "Scan QR code and verify"}


@router.post("/2fa/verify")
async def verify_2fa(code: str, req: Request, user: dict = Depends(get_api_key)):
    """Verify and activate 2FA"""
    user_data = await user_service.get_user_by_email(user["email"])
    secret = user_data.get("totp_secret")

    if not secret:
        await audit_logger.log_event(
            event_type="2fa_verify_failed",
            user_id=str(user["_id"]),
            user_email=user["email"],
            ip_address=get_client_ip(req),
            details={"reason": "2FA not initialized"},
        )
        raise HTTPException(status_code=400, detail="2FA not initialized")
    if not totp_service.verify_code(secret, code):
        await audit_logger.log_event(
            event_type="2fa_verify_failed",
            user_id=str(user["_id"]),
            user_email=user["email"],
            ip_address=get_client_ip(req),
            details={"reason": INVALID_CODE},
        )
        raise HTTPException(status_code=400, detail=INVALID_CODE)

    await user_service.update_profile(user["email"], {"totp_enabled": True})
    await user_service.update_profile(user["email"], {"totp_enabled": True})
    await audit_logger.log_event(
        event_type="2fa_enabled",
        user_id=str(user["_id"]),
        user_email=user["email"],
        ip_address=get_client_ip(req),
    )

    return AuthResponse(message="2FA enabled successfully")


@router.post("/2fa/disable")
async def disable_2fa(code: str, user: dict = Depends(get_api_key)):
    """Disable 2FA"""
    user_data = await user_service.get_user_by_email(user["email"])
    secret = user_data.get("totp_secret")
    if not secret or not user_data.get("totp_enabled"):
        raise HTTPException(status_code=400, detail="2FA not enabled")

    if not totp_service.verify_code(secret, code):
        raise HTTPException(status_code=400, detail=INVALID_CODE)

    await user_service.update_profile(user["email"], {"totp_enabled": False, "totp_secret": None})
    await audit_logger.log_event(
        event_type="2fa_disabled",
        user_id=str(user["_id"]),
        user_email=user["email"],
    )

    return AuthResponse(message="2FA disabled successfully")


@router.post("/request-email-change")
async def request_email_change(new_email: str, req: Request, user: dict = Depends(get_api_key)):
    """Request email change with OTP"""
    try:
        existing = await user_service.get_user_by_email(new_email)
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use")

        otp = await otp_service.create_otp(new_email, "email_change")
        # TODO(email): Send OTP to new_email
        logger.info(f"Email change OTP for {new_email}: {otp}")

        await user_service.update_profile(user["email"], {"pending_email": new_email})

        await audit_logger.log_event(
            event_type="email_change_requested",
            user_id=str(user["_id"]),
            user_email=user["email"],
            ip_address=get_client_ip(req),
            details={"new_email": new_email},
        )

        return AuthResponse(message="OTP sent to new email address for verification.")
    except HTTPException as e:
        raise e  # Re-raise FastAPI's HTTP exceptions
    except Exception as e:
        logger.error(f"Error requesting email change for {user['email']}: {e}")
        await audit_logger.log_event(
            event_type="email_change_request_failed",
            user_email=user["email"],
            ip_address=get_client_ip(req),
            details={"error": str(e)},
        )
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR)


@router.post("/confirm-email-change")
@router.post("/confirm-email-change")
async def confirm_email_change(otp: str, req: Request, user: dict = Depends(get_api_key)):
    """Confirm email change with OTP"""
    try:
        current_user = await user_service.get_user_by_email(user["email"])
        new_email = current_user.get("pending_email")

        if not new_email:
            raise HTTPException(status_code=400, detail="No pending email change.")

        if not await otp_service.verify_otp(new_email, otp, "email_change"):
            raise HTTPException(status_code=400, detail=INVALID_OR_EXPIRED_OTP)

        await user_service.change_email(user["email"], new_email)
        await user_service.update_profile(new_email, {"pending_email": None})

        await audit_logger.log_event(
            event_type="email_changed",
            user_id=str(user["_id"]),
            user_email=new_email,
            ip_address=get_client_ip(req),
            details={"old_email": user["email"]},
        )

        return AuthResponse(message="Email changed successfully")
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error confirming email change for {user['email']}: {e}")
        await audit_logger.log_event(
            event_type="email_change_confirm_failed",
            user_email=user["email"],
            ip_address=get_client_ip(req),
            details={"error": str(e)},
        )
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR)


@router.post("/passkey/register-options")
@router.post("/passkey/register-options")
async def passkey_register_options(user: dict = Depends(get_api_key)):
    """Get WebAuthn registration options for passkey"""
    options = await webauthn_service.generate_registration_options(user["email"], str(user["_id"]))
    return options


@router.post("/passkey/register")
async def passkey_register(request: PasskeyRegistrationRequest, user: dict = Depends(get_api_key)):
    """Complete passkey registration"""
    success = await webauthn_service.verify_registration(user["email"], request.credential)
    if not success:
        raise HTTPException(status_code=400, detail="Passkey registration failed")

    await audit_logger.log_event(
        event_type="passkey_registered",
        user_id=str(user["_id"]),
        user_email=user["email"],
    )
    return AuthResponse(message="Passkey registered successfully")


@router.post("/passkey/auth-options")
async def passkey_auth_options():
    """Get WebAuthn authentication options for passkey login"""
    options = await webauthn_service.generate_authentication_options()
    return options


@router.post("/passkey/authenticate")
async def passkey_authenticate(request: PasskeyAuthenticationRequest, req: Request):
    """Authenticate with passkey (biometric)"""
    try:
        user_email = await webauthn_service.verify_authentication(request.credential)
        if not user_email:
            raise HTTPException(status_code=401, detail="Passkey authentication failed")

        user = await user_service.get_user_by_email(user_email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        await audit_logger.log_auth_attempt(
            True, get_client_ip(req), str(user["_id"]), user["email"]
        )
        access_token = create_access_token(user)

        return AuthResponse(
            message="Passkey authentication successful",
            access_token=access_token,
            api_key=user["api_key"],
            user={"email": user["email"], "name": user["name"], "role": user["role"]},
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        await audit_logger.log_auth_attempt(False, get_client_ip(req), None, None, error=str(e))
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR)


@router.get("/passkey/list")
@router.get("/passkey/list")
async def list_passkeys(req: Request, user: dict = Depends(get_api_key)):
    """List all registered passkeys"""
    try:
        passkeys = await webauthn_service.list_passkeys(user["email"])
        await audit_logger.log_event(
            event_type="passkeys_listed",
            user_id=str(user["_id"]),
            user_email=user["email"],
            ip_address=get_client_ip(req),
        )
        return {"passkeys": passkeys}
    except Exception as e:
        logger.error(f"Error listing passkeys for {user['email']}: {e}")
        await audit_logger.log_event(
            event_type="list_passkeys_failed",
            user_id=str(user["_id"]),
            user_email=user["email"],
            ip_address=get_client_ip(req),
            details={"error": str(e)},
            severity="error",
        )
        raise HTTPException(status_code=500, detail="Failed to list passkeys.")


@router.delete("/passkey/{credential_id}")
async def delete_passkey(credential_id: str, req: Request, user: dict = Depends(get_api_key)):
    """Delete a passkey"""
    success = await webauthn_service.delete_passkey(user["email"], credential_id)
    if not success:
        raise HTTPException(status_code=404, detail="Passkey not found")

    await audit_logger.log_event(
        event_type="passkey_deleted",
        user_id=str(user["_id"]),
        user_email=user["email"],
        ip_address=get_client_ip(req),
        details={"credential_id": credential_id},
    )
    return AuthResponse(message="Passkey deleted successfully")
