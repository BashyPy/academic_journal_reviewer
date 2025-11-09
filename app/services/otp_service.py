"""OTP service for email verification and password reset"""

import secrets
from datetime import datetime, timedelta

from app.services.mongodb_service import mongodb_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


class OTPService:
    def __init__(self):
        self.collection = None
        self.otp_expiry_minutes = 10  # OTP expires in 10 minutes

    async def initialize(self):
        """Initialize users collection"""
        if self.collection is None:
            db = await mongodb_service.get_database()
            self.collection = db["users"]

    def generate_otp(self) -> str:
        """Generate a 6-digit OTP"""
        return f"{secrets.randbelow(900000) + 100000:06d}"

    async def create_otp(self, email: str, purpose: str) -> str:
        """Create and store OTP for user"""
        await self.initialize()

        otp = self.generate_otp()
        expires_at = datetime.now() + timedelta(minutes=self.otp_expiry_minutes)

        try:
            # Update user record with OTP
            result = await self.collection.update_one(
                {"email": email},
                {
                    "$set": {
                        "otp": otp,
                        "otp_purpose": purpose,
                        "otp_expires_at": expires_at,
                        "updated_at": datetime.now(),
                    }
                },
            )

            if result.matched_count == 0:
                logger.warning(f"Attempted to create OTP for non-existent user: {email}")
                raise ValueError(f"User with email {email} not found.")

            logger.info(f"OTP created for {email} with purpose: {purpose}")
            return otp
        except Exception as e:
            logger.error(f"Failed to create OTP for {email}: {e}")
            raise

    async def _clear_expired_otp(self, email: str):
        """Clear expired OTP for a user."""
        if not self.collection:
            logger.error("OTP clearing failed: database collection not initialized.")
            return
        try:
            await self.collection.update_one(
                {"email": email},
                {
                    "$unset": {"otp": "", "otp_purpose": "", "otp_expires_at": ""},
                    "$set": {"updated_at": datetime.now()},
                },
            )
        except Exception as e:
            logger.error(f"Failed to clear expired OTP for {email}: {e}")
            # Depending on requirements, this might need to raise the exception.

    async def verify_otp(self, email: str, otp: str, purpose: str) -> bool:
        """Verify OTP for user"""
        if not all(isinstance(arg, str) and arg for arg in [email, otp, purpose]):
            logger.warning("Invalid arguments provided to verify_otp")
            return False

        await self.initialize()

        user = await self.collection.find_one({"email": email})
        if not user:
            return False

        stored_otp = user.get("otp")
        stored_purpose = user.get("otp_purpose")
        expires_at = user.get("otp_expires_at")

        if stored_otp != otp or stored_purpose != purpose:
            return False

        if not expires_at or datetime.now() > expires_at:
            await self._clear_expired_otp(email)
            return False

        logger.info(f"OTP verified for {email} with purpose: {purpose}")
        return True


otp_service = OTPService()
