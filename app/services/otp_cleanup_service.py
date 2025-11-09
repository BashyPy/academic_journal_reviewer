"""OTP cleanup service for expired OTPs"""

from datetime import datetime

from app.services.mongodb_service import mongodb_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


class OTPCleanupService:
    def __init__(self):
        self.collection = None

    async def initialize(self):
        """Initialize users collection"""
        if self.collection is None:
            db = await mongodb_service.get_database()
            self.collection = db["users"]

    async def cleanup_expired_otps(self) -> int:
        """Remove expired OTPs from users table"""
        await self.initialize()

        if self.collection is None:
            logger.error("Database collection is not initialized.")
            return 0

        try:
            # Clear expired OTPs from regular users
            result = await self.collection.update_many(
                {"otp_expires_at": {"$lt": datetime.now()}},
                {
                    "$unset": {"otp": "", "otp_purpose": "", "otp_expires_at": ""},
                    "$set": {"updated_at": datetime.now()},
                },
            )

            # Remove temporary user records created for email changes
            temp_result = await self.collection.delete_many(
                {"temporary": True, "created_at": {"$lt": datetime.now()}}
            )

            total_cleaned = result.modified_count + temp_result.deleted_count
            if total_cleaned > 0:
                logger.info(f"Cleaned up {total_cleaned} expired OTP records")

            return total_cleaned
        except Exception as e:
            logger.error(f"An error occurred during OTP cleanup: {e}")
            return 0


otp_cleanup_service = OTPCleanupService()
