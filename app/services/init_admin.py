"""Initialize default super admin user"""

import asyncio
import os

from app.services.user_service import user_service
from app.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_ADMIN_EMAIL = os.getenv("SUPER_ADMIN_EMAIL", "admin@aaris.com")
DEFAULT_ADMIN_PASSWORD = os.getenv("SUPER_ADMIN_PASSWORD", "Admin@123456!")
DEFAULT_ADMIN_USERNAME = os.getenv("SUPER_ADMIN_USERNAME", "super_admin")
DEFAULT_ADMIN_NAME = os.getenv("SUPER_ADMIN_NAME", "Super Admin")


async def create_default_admin():
    """Create default super admin if not exists"""
    try:
        existing = await user_service.get_user_by_email(DEFAULT_ADMIN_EMAIL)
        if existing:
            logger.info(f"Admin user already exists: {DEFAULT_ADMIN_EMAIL}")
            return existing

        admin = await user_service.create_user(
            email=DEFAULT_ADMIN_EMAIL,
            password=DEFAULT_ADMIN_PASSWORD,
            name=DEFAULT_ADMIN_NAME,
            role="super_admin",
            username=DEFAULT_ADMIN_USERNAME,
        )

        await user_service.verify_email(DEFAULT_ADMIN_EMAIL)

        logger.info(f"✅ Default admin created: {DEFAULT_ADMIN_EMAIL}")
        logger.info(f"🔑 API Key: {admin['api_key']}")

        return admin
    except Exception as e:
        logger.error(f"Failed to create default admin: {e}")
        return None


if __name__ == "__main__":
    asyncio.run(create_default_admin())
