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

        # Update user record with OTP
        await self.collection.update_one(
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

        logger.info(f"OTP created for {email} with purpose: {purpose}")
        return otp

    async def verify_otp(self, email: str, otp: str, purpose: str) -> bool:
        """Verify OTP for user"""
        await self.initialize()

        user = await self.collection.find_one({"email": email})
        if not user:
            return False

        stored_otp = user.get("otp")
        stored_purpose = user.get("otp_purpose")
        expires_at = user.get("otp_expires_at")

        # Check if OTP exists and matches
        if not stored_otp or stored_otp != otp:
            return False

        # Check if purpose matches
        if stored_purpose != purpose:
            return False

        # Check if OTP is expired
        if not expires_at or datetime.now() > expires_at:
            # Clear expired OTP
            await self.collection.update_one(
                {"email": email},
                {
                    "$unset": {"otp": "", "otp_purpose": "", "otp_expires_at": ""},
                    "$set": {"updated_at": datetime.now()},
                },
            )
            return False

        logger.info(f"OTP verified for {email} with purpose: {purpose}")
        return True


otp_service = OTPService()
