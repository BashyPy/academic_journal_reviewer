"""OTP generation and verification service"""

import secrets
from datetime import datetime, timedelta

from app.services.mongodb_service import mongodb_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


class OTPService:
    def __init__(self):
        self.collection = None

    async def initialize(self):
        """Initialize OTP collection"""
        if self.collection is None:
            db = await mongodb_service.get_database()
            self.collection = db["otps"]
            await self.collection.create_index("email")
            await self.collection.create_index("expires_at")

    def generate_otp(self) -> str:
        """Generate 6-digit OTP"""
        return "".join([str(secrets.randbelow(10)) for _ in range(6)])

    async def create_otp(self, email: str, purpose: str = "verification") -> str:
        """Create and store OTP"""
        await self.initialize()
        otp = self.generate_otp()
        expires_at = datetime.now() + timedelta(minutes=10)

        await self.collection.delete_many({"email": email, "purpose": purpose})
        await self.collection.insert_one(
            {
                "email": email,
                "otp": otp,
                "purpose": purpose,
                "created_at": datetime.now(),
                "expires_at": expires_at,
                "verified": False,
            }
        )

        logger.info(f"OTP created for {email}")
        return otp

    async def verify_otp(self, email: str, otp: str, purpose: str = "verification") -> bool:
        """Verify OTP"""
        await self.initialize()
        doc = await self.collection.find_one(
            {
                "email": email,
                "otp": otp,
                "purpose": purpose,
                "verified": False,
                "expires_at": {"$gt": datetime.now()},
            }
        )

        if doc:
            await self.collection.update_one({"_id": doc["_id"]}, {"$set": {"verified": True}})
            logger.info(f"OTP verified for {email}")
            return True

        logger.warning(f"Invalid OTP for {email}")
        return False


otp_service = OTPService()
